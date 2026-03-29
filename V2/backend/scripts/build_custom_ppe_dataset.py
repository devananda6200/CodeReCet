from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required. Install with: pip install pyyaml") from exc


TARGET_CLASSES = ["person", "ppe_vest", "helmet"]
TARGET_CLASS_TO_ID = {name: index for index, name in enumerate(TARGET_CLASSES)}


@dataclass
class SourceSpec:
    slug: str
    parser: str


@dataclass
class Record:
    image_path: Path
    labels: list[tuple[int, float, float, float, float]]
    split: str
    source: str

    @property
    def bytes(self) -> int:
        return self.image_path.stat().st_size


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a custom PPE YOLO dataset from Kaggle sources.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output dataset directory (will contain images/, labels/, data.yaml).",
    )
    parser.add_argument(
        "--kaggle-json",
        required=True,
        help="Path to kaggle.json containing API credentials.",
    )
    parser.add_argument(
        "--work-dir",
        default="data/tmp_dataset_build",
        help="Working directory for temporary downloads.",
    )
    parser.add_argument(
        "--max-size-gb",
        type=float,
        default=4.0,
        help="Maximum final dataset size in GB.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic sampling/shuffling.",
    )
    return parser.parse_args()


def run(command: list[str], env: dict[str, str]) -> None:
    result = subprocess.run(command, env=env, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(command)
            + "\n\nSTDOUT:\n"
            + result.stdout
            + "\n\nSTDERR:\n"
            + result.stderr
        )


def download_dataset(slug: str, target_dir: Path, env: dict[str, str], kaggle_exe: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    run(
        [
            kaggle_exe,
            "datasets",
            "download",
            "-d",
            slug,
            "-p",
            str(target_dir),
            "--unzip",
            "--force",
        ],
        env=env,
    )
    return target_dir


def normalized_name(raw: str) -> str:
    return raw.strip().lower().replace("-", "_").replace(" ", "_")


def map_class_name(raw: str) -> int | None:
    name = normalized_name(raw)
    if name in {"person", "persons", "worker", "workers"}:
        return TARGET_CLASS_TO_ID["person"]
    if name in {"helmet", "hardhat", "hat"}:
        return TARGET_CLASS_TO_ID["helmet"]
    if name in {"safety_vest", "vest", "reflective_vest", "reflective", "jacket"}:
        return TARGET_CLASS_TO_ID["ppe_vest"]
    return None


def hash_split(path: Path) -> str:
    digest = hashlib.md5(str(path).encode("utf-8")).hexdigest()  # noqa: S324
    value = int(digest[:8], 16) / 0xFFFFFFFF
    if value < 0.8:
        return "train"
    if value < 0.9:
        return "val"
    return "test"


def parse_yolo_txt(label_path: Path, id_map: dict[int, int]) -> list[tuple[int, float, float, float, float]]:
    labels: list[tuple[int, float, float, float, float]] = []
    if not label_path.exists():
        return labels
    for line in label_path.read_text(encoding="utf-8").splitlines():
        row = line.strip().split()
        if len(row) != 5:
            continue
        source_id = int(float(row[0]))
        mapped_id = id_map.get(source_id)
        if mapped_id is None:
            continue
        labels.append((mapped_id, float(row[1]), float(row[2]), float(row[3]), float(row[4])))
    return labels


def build_id_map_from_yaml(dataset_root: Path) -> dict[int, int]:
    yaml_candidates = list(dataset_root.rglob("*.yaml")) + list(dataset_root.rglob("*.yml"))
    for candidate in yaml_candidates:
        try:
            payload = yaml.safe_load(candidate.read_text(encoding="utf-8"))
        except Exception:
            continue
        names = payload.get("names") if isinstance(payload, dict) else None
        if names is None:
            continue
        if isinstance(names, dict):
            source = {int(k): str(v) for k, v in names.items()}
        elif isinstance(names, list):
            source = {idx: str(name) for idx, name in enumerate(names)}
        else:
            continue
        mapped = {idx: mapped_id for idx, name in source.items() if (mapped_id := map_class_name(name)) is not None}
        if mapped:
            return mapped
    return {}


def parse_css_dataset(dataset_root: Path, source_name: str) -> list[Record]:
    css_root = dataset_root / "css-data"
    source_names = {
        0: "hardhat",
        1: "mask",
        2: "no_hardhat",
        3: "no_mask",
        4: "no_safety_vest",
        5: "person",
        6: "safety_cone",
        7: "safety_vest",
        8: "machinery",
        9: "vehicle",
    }
    id_map = {idx: mapped_id for idx, name in source_names.items() if (mapped_id := map_class_name(name)) is not None}
    records: list[Record] = []
    for source_split, final_split in [("train", "train"), ("valid", "val"), ("test", "test")]:
        images_dir = css_root / source_split / "images"
        labels_dir = css_root / source_split / "labels"
        if not images_dir.exists() or not labels_dir.exists():
            continue
        for image_path in sorted(images_dir.glob("*")):
            if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                continue
            label_path = labels_dir / f"{image_path.stem}.txt"
            labels = parse_yolo_txt(label_path, id_map)
            records.append(Record(image_path=image_path, labels=labels, split=final_split, source=source_name))
    return records


def parse_generic_yolo_dataset(dataset_root: Path, source_name: str) -> list[Record]:
    id_map = build_id_map_from_yaml(dataset_root)
    if not id_map:
        # Fallback assumption used by simple two-class helmet/vest datasets.
        id_map = {0: TARGET_CLASS_TO_ID["helmet"], 1: TARGET_CLASS_TO_ID["ppe_vest"]}

    records: list[Record] = []
    for labels_dir in dataset_root.rglob("labels"):
        images_dir = labels_dir.parent / "images"
        if not images_dir.exists():
            continue
        split_name = labels_dir.parent.name.lower()
        if split_name in {"train", "training"}:
            final_split = "train"
        elif split_name in {"valid", "val", "validation"}:
            final_split = "val"
        elif split_name in {"test", "testing"}:
            final_split = "test"
        else:
            final_split = "train"
        for image_path in sorted(images_dir.glob("*")):
            if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                continue
            label_path = labels_dir / f"{image_path.stem}.txt"
            labels = parse_yolo_txt(label_path, id_map)
            records.append(Record(image_path=image_path, labels=labels, split=final_split, source=source_name))
    return records


def voc_box_to_yolo(width: float, height: float, x_min: float, y_min: float, x_max: float, y_max: float) -> tuple[float, float, float, float]:
    x_center = ((x_min + x_max) / 2.0) / width
    y_center = ((y_min + y_max) / 2.0) / height
    box_width = (x_max - x_min) / width
    box_height = (y_max - y_min) / height
    return x_center, y_center, box_width, box_height


def parse_voc_dataset(dataset_root: Path, source_name: str) -> list[Record]:
    annotations_dir = dataset_root / "annotations"
    images_dir = dataset_root / "images"
    if not annotations_dir.exists() or not images_dir.exists():
        return []

    image_index: dict[str, Path] = {}
    for image_path in images_dir.glob("*.*"):
        image_index[image_path.stem] = image_path

    records: list[Record] = []
    for xml_path in sorted(annotations_dir.glob("*.xml")):
        image_path = image_index.get(xml_path.stem)
        if image_path is None:
            continue
        tree = ET.parse(xml_path)
        root = tree.getroot()

        size = root.find("size")
        if size is None:
            continue
        width = float(size.findtext("width", default="0"))
        height = float(size.findtext("height", default="0"))
        if width <= 0 or height <= 0:
            continue

        labels: list[tuple[int, float, float, float, float]] = []
        for obj in root.findall("object"):
            name = obj.findtext("name", default="")
            mapped_id = map_class_name(name)
            if mapped_id is None:
                continue
            bbox = obj.find("bndbox")
            if bbox is None:
                continue
            x_min = float(bbox.findtext("xmin", default="0"))
            y_min = float(bbox.findtext("ymin", default="0"))
            x_max = float(bbox.findtext("xmax", default="0"))
            y_max = float(bbox.findtext("ymax", default="0"))
            labels.append((mapped_id, *voc_box_to_yolo(width, height, x_min, y_min, x_max, y_max)))

        records.append(
            Record(
                image_path=image_path,
                labels=labels,
                split=hash_split(image_path),
                source=source_name,
            )
        )

    return records


def ensure_dirs(base: Path) -> None:
    for split in ("train", "val", "test"):
        (base / "images" / split).mkdir(parents=True, exist_ok=True)
        (base / "labels" / split).mkdir(parents=True, exist_ok=True)


def write_label_file(path: Path, labels: list[tuple[int, float, float, float, float]]) -> None:
    lines = [f"{cls_id} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}" for cls_id, xc, yc, w, h in labels]
    path.write_text("\n".join(lines), encoding="utf-8")


def cap_and_copy_records(records: list[Record], output_dir: Path, max_bytes: int, seed: int) -> dict[str, int]:
    ensure_dirs(output_dir)
    random.Random(seed).shuffle(records)

    bytes_used = 0
    copied = 0
    split_counts = {"train": 0, "val": 0, "test": 0}
    class_counts = {name: 0 for name in TARGET_CLASSES}

    for index, record in enumerate(records):
        item_bytes = record.bytes
        if bytes_used + item_bytes > max_bytes:
            continue

        ext = record.image_path.suffix.lower()
        image_name = f"img_{index:07d}{ext}"
        label_name = f"img_{index:07d}.txt"

        image_target = output_dir / "images" / record.split / image_name
        label_target = output_dir / "labels" / record.split / label_name
        shutil.copy2(record.image_path, image_target)
        write_label_file(label_target, record.labels)

        bytes_used += item_bytes
        copied += 1
        split_counts[record.split] += 1
        for cls_id, *_ in record.labels:
            class_counts[TARGET_CLASSES[cls_id]] += 1

    return {
        "images": copied,
        "bytes": bytes_used,
        "train_images": split_counts["train"],
        "val_images": split_counts["val"],
        "test_images": split_counts["test"],
        "person_boxes": class_counts["person"],
        "ppe_vest_boxes": class_counts["ppe_vest"],
        "helmet_boxes": class_counts["helmet"],
    }


def write_data_yaml(output_dir: Path) -> None:
    payload = {
        "path": str(output_dir.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {0: "person", 1: "ppe_vest", 2: "helmet"},
    }
    (output_dir / "data.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def build_records(raw_root: Path, sources: Iterable[SourceSpec]) -> list[Record]:
    all_records: list[Record] = []
    for source in sources:
        source_dir = raw_root / source.slug.replace("/", "__")
        if source.parser == "css":
            records = parse_css_dataset(source_dir, source.slug)
        elif source.parser == "voc":
            records = parse_voc_dataset(source_dir, source.slug)
        elif source.parser == "yolo":
            records = parse_generic_yolo_dataset(source_dir, source.slug)
        else:
            raise ValueError(f"Unknown parser type: {source.parser}")
        all_records.extend(records)
    return all_records


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    work_dir = Path(args.work_dir).resolve()
    kaggle_json = Path(args.kaggle_json).resolve()

    if not kaggle_json.exists():
        raise FileNotFoundError(f"kaggle.json not found: {kaggle_json}")

    kaggle_exe = shutil.which("kaggle")
    if not kaggle_exe:
        scripts_dir = Path(os.sys.executable).resolve().parent
        exe_name = "kaggle.exe" if os.name == "nt" else "kaggle"
        candidate = scripts_dir / exe_name
        if candidate.exists():
            kaggle_exe = str(candidate)
    if not kaggle_exe:
        raise RuntimeError("Kaggle CLI executable not found. Install via: pip install kaggle")

    env = os.environ.copy()
    env["KAGGLE_CONFIG_DIR"] = str(kaggle_json.parent)

    sources = [
        SourceSpec(slug="snehilsanyal/construction-site-safety-image-dataset-roboflow", parser="css"),
        SourceSpec(slug="andrewmvd/hard-hat-detection", parser="voc"),
        SourceSpec(slug="maryamborzoo/safety-helmet-and-vest", parser="yolo"),
    ]

    raw_root = work_dir / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)

    for source in sources:
        source_dir = raw_root / source.slug.replace("/", "__")
        download_dataset(source.slug, source_dir, env=env, kaggle_exe=kaggle_exe)

    records = build_records(raw_root, sources)
    if not records:
        raise RuntimeError("No records were built. Check source structure and parser mappings.")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    max_bytes = int(args.max_size_gb * 1024 * 1024 * 1024)
    summary = cap_and_copy_records(records, output_dir=output_dir, max_bytes=max_bytes, seed=args.seed)
    write_data_yaml(output_dir)

    manifest = {
        "output_dir": str(output_dir),
        "max_size_gb": args.max_size_gb,
        "source_count": len(sources),
        "sources": [source.slug for source in sources],
        "summary": summary,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

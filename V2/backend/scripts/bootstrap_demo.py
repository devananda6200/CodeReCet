from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    print(f"Starter workspace ready at: {root}")
    print("Place your trained YOLO checkpoint at backend/models/best.pt before Phase 2 inference wiring.")


if __name__ == "__main__":
    main()


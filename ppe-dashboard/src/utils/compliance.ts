import type { BoundingBox, Detection, PersonRecord, PersonStatus } from '../types';

/**
 * Calculate the Intersection over Union (IoU) of two bounding boxes.
 */
export function calculateIoU(box1: BoundingBox, box2: BoundingBox): number {
  const x1 = Math.max(box1.x, box2.x);
  const y1 = Math.max(box1.y, box2.y);
  const x2 = Math.min(box1.x + box1.w, box2.x + box2.w);
  const y2 = Math.min(box1.y + box1.h, box2.y + box2.h);

  if (x2 < x1 || y2 < y1) return 0;

  const intersectionArea = (x2 - x1) * (y2 - y1);
  const box1Area = box1.w * box1.h;
  const box2Area = box2.w * box2.h;

  return intersectionArea / (box1Area + box2Area - intersectionArea);
}

/**
 * Check if a small box is mostly inside a targeted region of a larger box.
 * @param itemBox The bounding box of the item (e.g., helmet, vest).
 * @param personBox The bounding box of the person.
 * @param region 'head' or 'torso'
 */
export function isItemInRegion(itemBox: BoundingBox, personBox: BoundingBox, region: 'head' | 'torso'): boolean {
  // Define regions relative to the person's bounding box
  let regionY = personBox.y;
  let regionH = personBox.h;

  if (region === 'head') {
    // Top 25% of the person box
    regionH = personBox.h * 0.25;
  } else if (region === 'torso') {
    // 20% to 70% of the person box
    regionY = personBox.y + personBox.h * 0.2;
    regionH = personBox.h * 0.5;
  }

  const targetedRegion: BoundingBox = {
    x: personBox.x,
    y: regionY,
    w: personBox.w,
    h: regionH,
  };

  // Check if item center is within the targeted region, or calculate IoU
  const itemCenterX = itemBox.x + itemBox.w / 2;
  const itemCenterY = itemBox.y + itemBox.h / 2;

  const isCenterInside =
    itemCenterX >= targetedRegion.x &&
    itemCenterX <= targetedRegion.x + targetedRegion.w &&
    itemCenterY >= targetedRegion.y &&
    itemCenterY <= targetedRegion.y + targetedRegion.h;

  if (isCenterInside) return true;

  // Fallback to intersection threshold check if center isn't perfectly inside
  const x1 = Math.max(targetedRegion.x, itemBox.x);
  const y1 = Math.max(targetedRegion.y, itemBox.y);
  const x2 = Math.min(targetedRegion.x + targetedRegion.w, itemBox.x + itemBox.w);
  const y2 = Math.min(targetedRegion.y + targetedRegion.h, itemBox.y + itemBox.h);

  if (x2 < x1 || y2 < y1) return false;
  const intersectionArea = (x2 - x1) * (y2 - y1);
  const itemArea = itemBox.w * itemBox.h;

  return (intersectionArea / itemArea) > 0.3; // At least 30% of the item is in the target region
}

export function evaluateCompliance(detections: Detection[]): PersonRecord[] {
  const persons = detections.filter((d) => d.class === 'person');
  const helmets = detections.filter((d) => d.class === 'helmet');
  const vests = detections.filter((d) => d.class === 'safety_vest');

  return persons.map((person) => {
    // Find if any helmet belongs to this person
    const hasHelmet = helmets.some((helmet) => isItemInRegion(helmet.box, person.box, 'head'));
    
    // Find if any vest belongs to this person
    const hasVest = vests.some((vest) => isItemInRegion(vest.box, person.box, 'torso'));

    let status: PersonStatus = 'compliant';
    if (!hasHelmet && !hasVest) status = 'missing_both';
    else if (!hasHelmet) status = 'missing_helmet';
    else if (!hasVest) status = 'missing_vest';

    return {
      id: person.id,
      box: person.box,
      status,
      helmetDetected: hasHelmet,
      vestDetected: hasVest,
    };
  });
}

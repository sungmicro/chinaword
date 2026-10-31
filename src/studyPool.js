import { matchesStudyGroup } from './lessons.js';

export function selectStudyPool(items, mineItems, group, mineOnly) {
  if (mineOnly && mineItems.length) return mineItems;
  return items.filter((item) => matchesStudyGroup(item, group));
}

export function randomIndex(length, previousIndex = -1) {
  if (length <= 1) return 0;
  let nextIndex = Math.floor(Math.random() * length);
  while (nextIndex === previousIndex) nextIndex = Math.floor(Math.random() * length);
  return nextIndex;
}

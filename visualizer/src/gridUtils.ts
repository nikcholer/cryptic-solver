import type { PuzzleClue } from './types';

export function iterateClueCells(clue: PuzzleClue, clues: Record<string, PuzzleClue>): Array<[number, number]> {
  const cells: Array<[number, number]> = [];
  const segments = clue.linked_entries?.length
    ? clue.linked_entries.map((clueId) => clues[clueId]).filter((value): value is PuzzleClue => Boolean(value))
    : [clue];

  segments.forEach((segment) => {
    let { x, y } = segment;
    for (let index = 0; index < segment.length; index += 1) {
      cells.push([x, y]);
      if (segment.direction === 'Across') {
        x += 1;
      } else {
        y += 1;
      }
    }
  });

  return cells;
}

export function sortClues(clues: Record<string, PuzzleClue>) {
  return Object.values(clues).sort((left, right) => {
    const numLeft = Number.parseInt(left.id, 10);
    const numRight = Number.parseInt(right.id, 10);
    if (numLeft !== numRight) return numLeft - numRight;
    return left.direction.localeCompare(right.direction);
  });
}

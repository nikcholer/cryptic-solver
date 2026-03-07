import type { CSSProperties } from 'react';

import { Cell } from './Cell';
import type { GridCell } from '../types';

interface CrosswordGridProps {
  grid: GridCell[][];
  width: number;
  height: number;
  onSelectCell?: (x: number, y: number) => void;
}

export function CrosswordGrid({ grid, width, height, onSelectCell }: CrosswordGridProps) {
  return (
    <div
      className="crossword-grid"
      style={
        {
          '--grid-cols': width,
          '--grid-rows': height,
        } as CSSProperties
      }
    >
      {grid.map((row) => row.map((cell) => <Cell key={`${cell.x}-${cell.y}`} cell={cell} onSelectCell={onSelectCell} />))}
    </div>
  );
}
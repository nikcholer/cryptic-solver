import type { GridCell } from '../types';

interface CellProps {
  cell: GridCell;
  onSelectCell?: (x: number, y: number) => void;
}

export function Cell({ cell, onSelectCell }: CellProps) {
  if (cell.isBlack) {
    return <div className="crossword-cell black-cell" />;
  }

  return (
    <button
      type="button"
      className={`crossword-cell ${cell.isActive ? 'active' : ''} ${cell.letter ? 'filled' : ''}`}
      data-x={cell.x}
      data-y={cell.y}
      onClick={() => onSelectCell?.(cell.x, cell.y)}
    >
      {cell.clueNumber && <span className="clue-number">{cell.clueNumber}</span>}
      <span className="cell-letter">{cell.letter}</span>
    </button>
  );
}
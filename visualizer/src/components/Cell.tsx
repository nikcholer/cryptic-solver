import React from 'react';
import type { GridCell } from '../types';

interface CellProps {
    cell: GridCell;
}

export const Cell: React.FC<CellProps> = ({ cell }) => {
    if (cell.isBlack) {
        return (
            <div className="crossword-cell black-cell" />
        );
    }

    // We are avoiding Tailwind mostly for premium vanilla aesthetics 
    // but using generic class names that we will define in index.css
    return (
        <div
            className={`crossword-cell ${cell.isActive ? 'active' : ''} ${cell.letter ? 'filled' : ''}`}
            data-x={cell.x}
            data-y={cell.y}
        >
            {cell.clueNumber && (
                <span className="clue-number">{cell.clueNumber}</span>
            )}
            {cell.letter && (
                <span className="cell-letter">{cell.letter}</span>
            )}
        </div>
    );
};

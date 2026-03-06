import React from 'react';
import { Cell } from './Cell';
import type { GridCell } from '../types';

interface CrosswordGridProps {
    grid: GridCell[][];
    width: number;
    height: number;
}

export const CrosswordGrid: React.FC<CrosswordGridProps> = ({ grid, width, height }) => {
    return (
        <div
            className="crossword-grid"
            style={{
                '--grid-cols': width,
                '--grid-rows': height,
            } as React.CSSProperties}
        >
            {grid.map((row, y) =>
                row.map((cell, x) => (
                    <Cell key={`${x}-${y}`} cell={cell} />
                ))
            )}
        </div>
    );
};

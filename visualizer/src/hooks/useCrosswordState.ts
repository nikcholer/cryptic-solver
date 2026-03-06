import { useState, useMemo } from 'react';
import gridDataRaw from '../data/grid_state.json';
import progressDataRaw from '../data/progress.json';
import type { GridStateData, ProgressEvent, GridCell } from '../types';

const gridData = gridDataRaw as unknown as GridStateData;
const progressData: ProgressEvent[] = progressDataRaw as unknown as ProgressEvent[];

export function useCrosswordState() {
    const [currentEventIndex, setCurrentEventIndex] = useState(0);

    // Compute the full set of playable coordinates from gridData.clues
    const playableCells = useMemo(() => {
        const cells = new Set<string>();
        const clueNumbers: Record<string, string> = {};

        Object.entries(gridData.clues).forEach(([clueId, meta]) => {
            // Match the digits from the start of the clue ID (e.g. "10A" -> "10")
            const numMatch = clueId.match(/^(\d+)/);
            if (numMatch) {
                clueNumbers[`${meta.x},${meta.y}`] = numMatch[1];
            }

            let { x, y } = meta;
            for (let i = 0; i < meta.length; i++) {
                cells.add(`${x},${y}`);
                if (meta.direction === "Across") {
                    x++;
                } else {
                    y++;
                }
            }
        });
        return { cells, clueNumbers };
    }, []);

    const { cells, clueNumbers } = playableCells;

    // Determine active clue
    const activeEvent = progressData[currentEventIndex];
    const activeClueId = activeEvent?.id;

    // Derive cell letters from all progress events up to currentEventIndex
    const currentLetters = useMemo(() => {
        const letters: Record<string, string> = {};

        // Play through events up to the current index
        for (let i = 0; i <= currentEventIndex; i++) {
            const event = progressData[i];
            if (!event) continue;

            const meta = gridData.clues[event.id];
            if (!meta) continue;

            let { x, y } = meta;
            // Use the known exact "answer" if available, else use "pattern" 
            // (Pattern often has '.' for unknown letters)
            const textToApply = (event.answer || event.pattern || "").replace(/\./g, " ");

            for (let j = 0; j < meta.length; j++) {
                const char = textToApply[j];
                if (char && char !== " ") {
                    letters[`${x},${y}`] = char;
                }
                if (meta.direction === "Across") {
                    x++;
                } else {
                    y++;
                }
            }
        }
        return letters;
    }, [currentEventIndex]);

    // Compute active cell coordinates for highlighting
    const activeCells = useMemo(() => {
        const active = new Set<string>();
        if (!activeClueId) return active;

        const meta = gridData.clues[activeClueId];
        if (meta) {
            let { x, y } = meta;
            for (let j = 0; j < meta.length; j++) {
                active.add(`${x},${y}`);
                if (meta.direction === "Across") {
                    x++;
                } else {
                    y++;
                }
            }
        }
        return active;
    }, [activeClueId]);

    // Generate the 2D grid
    const grid: GridCell[][] = useMemo(() => {
        const newGrid: GridCell[][] = [];
        for (let y = 0; y < gridData.height; y++) {
            const row: GridCell[] = [];
            for (let x = 0; x < gridData.width; x++) {
                const key = `${x},${y}`;
                const isBlack = !cells.has(key);
                row.push({
                    x,
                    y,
                    isBlack,
                    clueNumber: clueNumbers[key],
                    letter: currentLetters[key] || "",
                    isActive: activeCells.has(key)
                });
            }
            newGrid.push(row);
        }
        return newGrid;
    }, [cells, clueNumbers, currentLetters, activeCells]);

    return {
        grid,
        width: gridData.width,
        height: gridData.height,
        progressData,
        currentEventIndex,
        activeEvent,
        setCurrentEventIndex,
        gridData
    };
}

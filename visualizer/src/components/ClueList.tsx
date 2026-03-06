import React, { useMemo } from 'react';
import type { GridStateData, ProgressEvent } from '../types';

interface ClueListProps {
    gridData: GridStateData;
    activeClueId: string | undefined;
    progressData: ProgressEvent[];
    currentEventIndex: number;
}

export const ClueList: React.FC<ClueListProps> = ({
    gridData,
    activeClueId,
    progressData,
    currentEventIndex
}) => {
    // Extract clue strings and parses up to the current timeline point
    const clueDetails = useMemo(() => {
        const details: Record<string, { text: string; parse?: string; answer?: string }> = {};

        // First pass: just grab any clue text we can find from the whole progress log 
        // so we can display the clue even before the timeline reaches it.
        progressData.forEach(event => {
            if (!details[event.id]) {
                details[event.id] = { text: event.clue };
            }
        });

        // Second pass: grab answers and parses ONLY UP TO the current event index
        for (let i = 0; i <= currentEventIndex; i++) {
            const event = progressData[i];
            if (event && event.answer) {
                details[event.id].answer = event.answer;
            }
            if (event && event.parse) {
                details[event.id].parse = event.parse;
            }
        }
        return details;
    }, [progressData, currentEventIndex]);

    const clues = Object.entries(gridData.clues)
        .map(([id, meta]) => ({ id, ...meta }))
        .sort((a, b) => {
            const matchA = a.id.match(/^(\d+)/);
            const matchB = b.id.match(/^(\d+)/);
            const numA = matchA ? parseInt(matchA[1], 10) : 0;
            const numB = matchB ? parseInt(matchB[1], 10) : 0;
            return numA - numB;
        });

    const across = clues.filter(c => c.direction === 'Across');
    const down = clues.filter(c => c.direction === 'Down');

    const renderClueList = (title: string, items: typeof clues) => (
        <div className="crw-clues-section">
            <h3>{title}</h3>
            <ul className="crw-clues-list">
                {items.map(clue => {
                    const isActive = clue.id === activeClueId;
                    const detail = clueDetails[clue.id];
                    return (
                        <li
                            key={clue.id}
                            className={`crw-clue-item ${isActive ? 'active' : ''} ${detail?.answer ? 'solved' : ''}`}
                        >
                            <div className="crw-clue-header">
                                <span className="clue-id">{clue.id}</span>
                                <span className="clue-text">
                                    {detail?.text || "..."} <span className="clue-meta">({clue.length})</span>
                                </span>
                            </div>

                            {detail?.answer && (
                                <div className="crw-clue-resolution">
                                    <span className="clue-answer">{detail.answer}</span>
                                    {detail.parse && <div className="clue-parse">{detail.parse}</div>}
                                </div>
                            )}
                        </li>
                    );
                })}
            </ul>
        </div>
    );

    return (
        <div className="crw-clues">
            {renderClueList('Across', across)}
            {renderClueList('Down', down)}
        </div>
    );
};

import React, { useEffect, useState } from 'react';
import { Play, Pause, SkipBack, SkipForward, Rewind, FastForward } from 'lucide-react';
import type { ProgressEvent } from '../types';

interface TimelineControlsProps {
    currentEventIndex: number;
    totalEvents: number;
    onScrub: (index: number) => void;
    activeEvent?: ProgressEvent;
}

export const TimelineControls: React.FC<TimelineControlsProps> = ({
    currentEventIndex,
    totalEvents,
    onScrub,
    activeEvent
}) => {
    const [isPlaying, setIsPlaying] = useState(false);

    useEffect(() => {
        if (!isPlaying) return;

        const timeout = window.setTimeout(() => {
            onScrub(Math.min(currentEventIndex + 1, totalEvents - 1));
        }, 800);

        return () => clearTimeout(timeout);
    }, [isPlaying, currentEventIndex, totalEvents, onScrub]);

    // Pause if we hit the end
    useEffect(() => {
        if (currentEventIndex >= totalEvents - 1 && isPlaying) {
            setIsPlaying(false);
        }
    }, [currentEventIndex, totalEvents, isPlaying]);

    const progressPercentage = ((currentEventIndex) / (totalEvents - 1)) * 100;

    return (
        <div className="timeline-controls">
            <div className="active-event-display">
                {activeEvent ? (
                    <>
                        <span className="event-badge">{activeEvent.id}</span>
                        <span className="event-clue">{activeEvent.clue}</span>
                        <div className="event-meta">
                            <span className="event-status">{activeEvent.status}</span>
                        </div>
                    </>
                ) : (
                    <span className="event-clue empty">Ready to solve...</span>
                )}
            </div>

            <div className="transport-buttons">
                <button className="icon-btn" onClick={() => onScrub(0)} disabled={currentEventIndex === 0}>
                    <SkipBack size={20} />
                </button>
                <button className="icon-btn" onClick={() => onScrub(Math.max(0, currentEventIndex - 1))} disabled={currentEventIndex === 0}>
                    <Rewind size={20} />
                </button>
                <button className="icon-btn primary-btn" onClick={() => setIsPlaying(!isPlaying)}>
                    {isPlaying ? <Pause size={24} /> : <Play size={24} />}
                </button>
                <button className="icon-btn" onClick={() => onScrub(Math.min(totalEvents - 1, currentEventIndex + 1))} disabled={currentEventIndex === totalEvents - 1}>
                    <FastForward size={20} />
                </button>
                <button className="icon-btn" onClick={() => onScrub(totalEvents - 1)} disabled={currentEventIndex === totalEvents - 1}>
                    <SkipForward size={20} />
                </button>
            </div>

            <div className="slider-container">
                <input
                    type="range"
                    min="0"
                    max={totalEvents - 1}
                    value={currentEventIndex}
                    onChange={(e) => {
                        setIsPlaying(false);
                        onScrub(parseInt(e.target.value, 10));
                    }}
                    className="timeline-slider"
                />
                <div className="timeline-progress" style={{ width: `${progressPercentage}%` }}></div>
            </div>
        </div>
    );
};

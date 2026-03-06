export type Direction = "Across" | "Down";

export interface ClueMetadata {
    direction: Direction;
    length: number;
    uncertain?: boolean;
    x: number;
    y: number;
}

export interface GridStateData {
    _debug: {
        hlines: number[];
        image: string;
        image_size: number[];
        vlines: number[];
    };
    clues: Record<string, ClueMetadata>;
    height: number;
    width: number;
    placed_answers: Record<string, string>;
}

export interface ProgressEvent {
    id: string;
    direction: Direction;
    enum: string;
    pattern: string;
    clue: string;
    status: string;
    answer?: string;
    parse?: string;
}

export interface GridCell {
    x: number;
    y: number;
    isBlack: boolean;
    clueNumber?: string;
    letter: string;
    isActive: boolean; // Part of the currently focused clue
}

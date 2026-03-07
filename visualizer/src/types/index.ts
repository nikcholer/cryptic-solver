export type Direction = 'Across' | 'Down';
export type ClueStatus = 'untouched' | 'in_progress' | 'plausible' | 'confirmed' | 'conflict';
export type ValidationResult = 'confirmed' | 'plausible' | 'conflict';
export type HintKind = 'clue_type' | 'structure' | 'wordplay_focus' | 'candidate_space' | 'answer_reveal';

export interface PuzzleClueMetadata {
  direction: Direction;
  length: number;
  uncertain?: boolean;
  x: number;
  y: number;
}

export interface PuzzleClue {
  id: string;
  direction: Direction;
  clue: string;
  enum: string;
  length: number;
  x: number;
  y: number;
  uncertain?: boolean;
}

export interface PuzzleGrid {
  width: number;
  height: number;
  clues: Record<string, PuzzleClueMetadata>;
}

export interface PuzzleDefinition {
  puzzle_id: string;
  grid: PuzzleGrid;
  clues: Record<string, PuzzleClue>;
}

export interface HintRecord {
  level: number;
  kind: HintKind;
  text: string;
}

export interface ValidationRecord {
  result: ValidationResult;
  reason: string;
  confidence?: number | null;
}

export interface EntryRecord {
  answer: string;
  source: string;
  status: ValidationResult;
  updated_at: string;
}

export interface ClueState {
  status: ClueStatus;
  current_pattern: string;
  hint_level_shown: number;
  hints: HintRecord[];
  validation?: ValidationRecord | null;
}

export interface SessionState {
  selectedClueId: string | null;
  version: number;
  cells: Record<string, string>;
  entries: Record<string, EntryRecord>;
  clueStates: Record<string, ClueState>;
}

export interface PuzzleResponse {
  puzzle: PuzzleDefinition;
}

export interface SessionResponse {
  sessionId: string;
  puzzle: PuzzleDefinition;
  sessionState: SessionState;
}

export interface CreateSessionResponse extends SessionResponse {}

export interface GridCell {
  x: number;
  y: number;
  isBlack: boolean;
  clueNumber?: string;
  letter: string;
  isActive: boolean;
}
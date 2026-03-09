export type Direction = 'Across' | 'Down';
export type ClueStatus = 'untouched' | 'in_progress' | 'plausible' | 'confirmed' | 'conflict' | 'forced';
export type ValidationResult = 'confirmed' | 'plausible' | 'conflict';
export type HintKind = 'clue_type' | 'structure' | 'wordplay_focus' | 'candidate_space' | 'answer_reveal';

export interface PuzzleClue {
  id: string;
  direction: Direction;
  clue: string;
  enum?: string | null;
  length: number;
  answer_length: number;
  x: number;
  y: number;
  uncertain?: boolean;
  linked_entries?: string[] | null;
}

export interface PuzzleGrid {
  width: number;
  height: number;
  clues: Record<string, { direction: Direction; length: number; x: number; y: number }>;
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
  symbolic_followup?: string | null;
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

export interface RuntimeUsage {
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  requests: number;
}

export interface SessionState {
  selectedClueId: string | null;
  version: number;
  cells: Record<string, string>;
  entries: Record<string, EntryRecord>;
  clueStates: Record<string, ClueState>;
  runtimeUsage: RuntimeUsage;
}

export interface PuzzleSummary {
  puzzleId: string;
}

export interface PuzzleListResponse {
  puzzles: PuzzleSummary[];
}

export interface PuzzleResponse {
  puzzle: PuzzleDefinition;
}

export interface SessionResponse {
  sessionId: string;
  puzzle: PuzzleDefinition;
  sessionState: SessionState;
}

export interface ThesaurusCandidate {
  word: string;
  pos?: string | null;
  length: number;
}

export interface ThesaurusLookupResponse {
  term: string;
  length?: number | null;
  candidates: ThesaurusCandidate[];
}

export interface GridCell {
  x: number;
  y: number;
  isBlack: boolean;
  clueNumber?: string;
  letter: string;
  isActive: boolean;
}

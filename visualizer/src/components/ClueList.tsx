import type { ClueState, PuzzleClue } from '../types';
import { formatStatus } from '../format';

interface ClueListProps {
  title: string;
  clues: PuzzleClue[];
  clueStates: Record<string, ClueState>;
  activeClueId: string | null;
  onSelectClue: (clueId: string) => void;
}

export function ClueList({
  title,
  clues,
  clueStates,
  activeClueId,
  onSelectClue,
}: ClueListProps) {
  return (
    <section className="crw-clues-section">
      <h3>{title}</h3>
      <ul className="crw-clues-list">
        {clues.map((clue) => {
          const clueState = clueStates[clue.id];
          const isActive = clue.id === activeClueId;
          const hintCount = clueState?.hints.length ?? 0;
          return (
            <li key={clue.id}>
              <button
                type="button"
                className={`crw-clue-item ${isActive ? 'active' : ''} ${clueState?.status ?? 'untouched'}`}
                onClick={() => onSelectClue(clue.id)}
              >
                <div className="crw-clue-header">
                  <span className="clue-id">{clue.id}</span>
                  <span className="clue-text">
                    {clue.clue}{clue.enum ? <span className="clue-meta"> {clue.enum}</span> : null}
                  </span>
                </div>
                <div className="crw-clue-state-row">
                  <span className={`clue-status-badge ${clueState?.status ?? 'untouched'}`}>
                    {formatStatus(clueState?.status ?? 'untouched')}
                  </span>
                  <span className="clue-pattern">{clueState?.current_pattern ?? '.'.repeat(clue.answer_length)}</span>
                  {hintCount > 0 && <span className="hint-pill">{hintCount} hint{hintCount === 1 ? '' : 's'}</span>}
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
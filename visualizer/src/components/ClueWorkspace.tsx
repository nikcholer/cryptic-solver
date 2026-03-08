import type { ClueState, PuzzleClue } from '../types';

interface ClueWorkspaceProps {
  clue: PuzzleClue | null;
  clueState: ClueState | null;
  draftAnswer: string;
  justification: string;
  onDraftAnswerChange: (nextValue: string) => void;
  onJustificationChange: (nextValue: string) => void;
  onSubmitAnswer: () => void;
  onAcceptAnswer: () => void;
  onClearAnswer: () => void;
  onRequestHint: () => void;
  isBusy: boolean;
}

export function ClueWorkspace({
  clue,
  clueState,
  draftAnswer,
  justification,
  onDraftAnswerChange,
  onJustificationChange,
  onSubmitAnswer,
  onAcceptAnswer,
  onClearAnswer,
  onRequestHint,
  isBusy,
}: ClueWorkspaceProps) {
  if (!clue) {
    return (
      <section className="workspace-card workspace-empty">
        <h2>Select a clue</h2>
        <p>Choose any clue from the list to start filling answers and request staged hints.</p>
      </section>
    );
  }

  return (
    <section className="workspace-card">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">Focused clue</p>
          <h2>{clue.id}</h2>
        </div>
        <span className={`clue-status-badge large ${clueState?.status ?? 'untouched'}`}>
          {clueState?.status?.replace('_', ' ') ?? 'untouched'}
        </span>
      </div>

      <p className="workspace-clue-text">{clue.clue}</p>
      <div className="workspace-meta-row">
        {clue.enum ? <span className="workspace-enum">{clue.enum}</span> : null}
        <span className="workspace-pattern">Pattern: {clueState?.current_pattern ?? '.'.repeat(clue.answer_length)}</span>
      </div>

      {clue.linked_entries && clue.linked_entries.length > 1 ? (
        <p className="workspace-linked">Linked entries: {clue.linked_entries.join(' -> ')}</p>
      ) : null}

      <label className="answer-label" htmlFor="clue-answer-input">
        Your answer
      </label>
      <div className="answer-controls">
        <input
          id="clue-answer-input"
          value={draftAnswer}
          onChange={(event) => onDraftAnswerChange(event.target.value.toUpperCase())}
          className="answer-input"
          placeholder="Enter answer"
          disabled={isBusy}
        />
        <button
          type="button"
          className="action-btn primary"
          onClick={onSubmitAnswer}
          disabled={isBusy || draftAnswer.trim().length === 0}
        >
          Check answer
        </button>
        <button
          type="button"
          className="action-btn"
          onClick={onClearAnswer}
          disabled={isBusy || ((!clueState?.current_pattern || !clueState.current_pattern.replace(/\./g, '').length) && !draftAnswer.trim().length)}
        >
          Clear answer
        </button>
        <button type="button" className="action-btn" onClick={onRequestHint} disabled={isBusy}>
          Next hint
        </button>
      </div>

      <label className="answer-label" htmlFor="clue-justification-input">
        Why I think this works (optional)
      </label>
      <textarea
        id="clue-justification-input"
        value={justification}
        onChange={(event) => onJustificationChange(event.target.value)}
        className="answer-justification"
        placeholder="Explain your parse, definition reading, or why the clue seems to fit."
        disabled={isBusy}
        rows={3}
      />

      {clueState?.validation?.result === 'conflict' && draftAnswer.trim().length > 0 ? (
        <div className="override-row">
          <button type="button" className="action-btn override" onClick={onAcceptAnswer} disabled={isBusy}>
            Accept anyway
          </button>
        </div>
      ) : null}

      {clueState?.validation && (
        <div className={`validation-card ${clueState.validation.result}`}>
          <strong>{clueState.validation.result}</strong>
          <p>{clueState.validation.reason}</p>
        </div>
      )}

      <div className="hint-stack">
        <h3>Hints shown</h3>
        {clueState?.hints.length ? (
          clueState.hints.map((hint) => (
            <article key={`${hint.level}-${hint.kind}`} className="hint-card">
              <div className="hint-card-header">
                <span className="hint-level">Level {hint.level}</span>
                <span className="hint-kind">{hint.kind.replace('_', ' ')}</span>
              </div>
              <p>{hint.text}</p>
            </article>
          ))
        ) : (
          <p className="hint-empty">No hints revealed yet.</p>
        )}
      </div>
    </section>
  );
}
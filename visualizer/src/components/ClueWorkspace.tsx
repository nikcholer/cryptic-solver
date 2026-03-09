import type { ClueState, PuzzleClue, ThesaurusCandidate } from '../types';
import { formatStatus } from '../format';
import { ThesaurusPanel } from './ThesaurusPanel';
import { HintStack } from './HintStack';

interface ClueWorkspaceProps {
  clue: PuzzleClue | null;
  clueState: ClueState | null;
  draftAnswer: string;
  justification: string;
  thesaurusTerm: string;
  thesaurusCandidates: ThesaurusCandidate[];
  onDraftAnswerChange: (nextValue: string) => void;
  onJustificationChange: (nextValue: string) => void;
  onThesaurusTermChange: (nextValue: string) => void;
  onLookupThesaurus: () => void;
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
  thesaurusTerm,
  thesaurusCandidates,
  onDraftAnswerChange,
  onJustificationChange,
  onThesaurusTermChange,
  onLookupThesaurus,
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

  const hasFilledPattern = clueState?.current_pattern ? clueState.current_pattern.replace(/\./g, '').length > 0 : false;
  const canClear = hasFilledPattern || draftAnswer.trim().length > 0;

  return (
    <section className="workspace-card">
      <div className="workspace-header">
        <div>
          <p className="workspace-kicker">Focused clue</p>
          <h2>{clue.id}</h2>
        </div>
        <span className={`clue-status-badge large ${clueState?.status ?? 'untouched'}`}>
          {formatStatus(clueState?.status ?? 'untouched')}
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
          disabled={isBusy || !canClear}
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
          {clueState.validation.symbolic_followup ? (
            <p><strong>Suggested next step:</strong> {clueState.validation.symbolic_followup}</p>
          ) : null}
        </div>
      )}

      <ThesaurusPanel
        answerLength={clue.answer_length}
        thesaurusTerm={thesaurusTerm}
        thesaurusCandidates={thesaurusCandidates}
        onThesaurusTermChange={onThesaurusTermChange}
        onLookupThesaurus={onLookupThesaurus}
        isBusy={isBusy}
      />

      <HintStack hints={clueState?.hints ?? []} />
    </section>
  );
}

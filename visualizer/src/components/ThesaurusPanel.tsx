import type { ThesaurusCandidate } from '../types';

interface ThesaurusPanelProps {
  answerLength: number;
  thesaurusTerm: string;
  thesaurusCandidates: ThesaurusCandidate[];
  onThesaurusTermChange: (nextValue: string) => void;
  onLookupThesaurus: () => void;
  isBusy: boolean;
}

export function ThesaurusPanel({
  answerLength,
  thesaurusTerm,
  thesaurusCandidates,
  onThesaurusTermChange,
  onLookupThesaurus,
  isBusy,
}: ThesaurusPanelProps) {
  return (
    <section className="thesaurus-panel">
      <div className="hint-card-header">
        <span>Explore definition</span>
        <span>{answerLength} letters</span>
      </div>
      <div className="thesaurus-controls">
        <input
          value={thesaurusTerm}
          onChange={(event) => onThesaurusTermChange(event.target.value)}
          className="thesaurus-input"
          placeholder="e.g. story, writer, team"
          disabled={isBusy}
        />
        <button
          type="button"
          className="action-btn"
          onClick={onLookupThesaurus}
          disabled={isBusy || thesaurusTerm.trim().length === 0}
        >
          Lookup
        </button>
      </div>
      {thesaurusCandidates.length ? (
        <div className="thesaurus-results">
          {thesaurusCandidates.map((candidate) => (
            <span key={`${candidate.word}-${candidate.pos ?? 'any'}`} className="thesaurus-chip">
              {candidate.word}
              {candidate.pos ? ` (${candidate.pos})` : ''}
            </span>
          ))}
        </div>
      ) : (
        <p className="hint-empty">No local thesaurus results yet.</p>
      )}
    </section>
  );
}

import type { HintRecord } from '../types';
import { formatStatus } from '../format';

interface HintStackProps {
  hints: HintRecord[];
}

export function HintStack({ hints }: HintStackProps) {
  return (
    <div className="hint-stack">
      <h3>Hints shown</h3>
      {hints.length ? (
        hints.map((hint) => (
          <article key={`${hint.level}-${hint.kind}`} className="hint-card">
            <div className="hint-card-header">
              <span className="hint-level">Level {hint.level}</span>
              <span className="hint-kind">{formatStatus(hint.kind)}</span>
            </div>
            <p>{hint.text}</p>
          </article>
        ))
      ) : (
        <p className="hint-empty">No hints revealed yet.</p>
      )}
    </div>
  );
}

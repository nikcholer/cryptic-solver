import type { ChangeEvent } from 'react';
import { ClueList } from './components/ClueList';
import { ClueWorkspace } from './components/ClueWorkspace';
import { CrosswordGrid } from './components/CrosswordGrid';
import { formatTokens } from './format';
import { useTutorSession } from './hooks/useTutorSession';
import './index.css';

export function App() {
  const {
    puzzle,
    availablePuzzleIds,
    currentPuzzleId,
    choosePuzzle,
    sessionId,
    sessionState,
    grid,
    acrossClues,
    downClues,
    selectedClue,
    draftAnswer,
    setDraftAnswer,
    justification,
    setJustification,
    thesaurusTerm,
    setThesaurusTerm,
    thesaurusCandidates,
    isLoading,
    isSubmitting,
    error,
    uploadPdf,
    lookupThesaurus,
    selectClue,
    selectCell,
    submitAnswer,
    acceptAnswer,
    clearAnswer,
    requestNextHint,
  } = useTutorSession();

  async function handlePdfSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    await uploadPdf(file);
  }

  if (isLoading) {
    return (
      <div className="app-shell centered-state">
        <h1>Cryptic Tutor</h1>
        <p>Loading puzzle session...</p>
      </div>
    );
  }

  if (!puzzle || !sessionState) {
    return (
      <div className="app-shell centered-state">
        <h1>Cryptic Tutor</h1>
        <p>{error ?? 'Unable to initialize the puzzle session.'}</p>
      </div>
    );
  }

  const allCluesConfirmed = Object.values(sessionState.clueStates).every((clueState) => clueState.status === 'confirmed');

  return (
    <div className={`app-shell ${allCluesConfirmed ? 'puzzle-complete' : ''}`}>
      <header className="app-header">
        <div>
          <p className="app-kicker">Interactive cryptic tutorial</p>
          <h1>Cryptic Tutor</h1>
        </div>
        <div className="header-actions">
          <label className={`upload-btn ${isSubmitting ? 'disabled' : ''}`}>
            <input type="file" accept="application/pdf" onChange={handlePdfSelected} disabled={isSubmitting} />
            Upload PDF
          </label>
          <div className="session-chip-group">
            <label className="puzzle-picker">
              <span className="sr-only">Choose puzzle</span>
              <select value={currentPuzzleId} onChange={(event) => choosePuzzle(event.target.value)} disabled={isSubmitting}>
                {availablePuzzleIds.map((puzzleId) => (
                  <option key={puzzleId} value={puzzleId}>
                    {puzzleId}
                  </option>
                ))}
              </select>
            </label>
            {sessionId && <span className="session-chip muted">Session {sessionId}</span>}
            <span className="session-chip usage-chip">Input {formatTokens(sessionState.runtimeUsage.input_tokens)}</span>
            <span className="session-chip usage-chip">Output {formatTokens(sessionState.runtimeUsage.output_tokens)}</span>
            {sessionState.runtimeUsage.cached_input_tokens > 0 ? (
              <span className="session-chip usage-chip muted">
                Cached {formatTokens(sessionState.runtimeUsage.cached_input_tokens)}
              </span>
            ) : null}
            <span className="session-chip usage-chip muted">Calls {formatTokens(sessionState.runtimeUsage.requests)}</span>
          </div>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {allCluesConfirmed ? (
        <section className="completion-banner">
          <p className="completion-kicker">Puzzle complete</p>
          <h2>Every clue is confirmed.</h2>
          <p>The tutor agrees with the full solve.</p>
        </section>
      ) : null}

      <main className="main-layout">
        <section className="grid-panel">
          <div className="grid-card">
            <CrosswordGrid
              grid={grid}
              width={puzzle.grid.width}
              height={puzzle.grid.height}
              onSelectCell={selectCell}
            />
          </div>
          <ClueWorkspace
            clue={selectedClue}
            clueState={selectedClue ? sessionState.clueStates[selectedClue.id] ?? null : null}
            draftAnswer={draftAnswer}
            onDraftAnswerChange={setDraftAnswer}
            justification={justification}
            thesaurusTerm={thesaurusTerm}
            thesaurusCandidates={thesaurusCandidates}
            onJustificationChange={setJustification}
            onThesaurusTermChange={setThesaurusTerm}
            onLookupThesaurus={lookupThesaurus}
            onSubmitAnswer={submitAnswer}
            onAcceptAnswer={acceptAnswer}
            onClearAnswer={clearAnswer}
            onRequestHint={requestNextHint}
            isBusy={isSubmitting}
          />
        </section>

        <aside className="sidebar-panel">
          <ClueList
            title="Across"
            clues={acrossClues}
            clueStates={sessionState.clueStates}
            activeClueId={sessionState.selectedClueId}
            onSelectClue={selectClue}
          />
          <ClueList
            title="Down"
            clues={downClues}
            clueStates={sessionState.clueStates}
            activeClueId={sessionState.selectedClueId}
            onSelectClue={selectClue}
          />
        </aside>
      </main>
    </div>
  );
}

export default App;

import { ClueList } from './components/ClueList';
import { ClueWorkspace } from './components/ClueWorkspace';
import { CrosswordGrid } from './components/CrosswordGrid';
import { useTutorSession } from './hooks/useTutorSession';
import './index.css';

export function App() {
  const {
    puzzle,
    sessionId,
    sessionState,
    grid,
    acrossClues,
    downClues,
    selectedClue,
    draftAnswer,
    setDraftAnswer,
    isLoading,
    isSubmitting,
    error,
    selectClue,
    selectCell,
    submitAnswer,
    requestNextHint,
  } = useTutorSession();

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

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="app-kicker">Interactive cryptic tutorial</p>
          <h1>Cryptic Tutor</h1>
        </div>
        <div className="session-chip-group">
          <span className="session-chip">Puzzle {puzzle.puzzle_id}</span>
          {sessionId && <span className="session-chip muted">Session {sessionId}</span>}
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

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
            onSubmitAnswer={submitAnswer}
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
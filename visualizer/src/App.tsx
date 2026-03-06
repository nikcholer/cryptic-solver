import { CrosswordGrid } from './components/CrosswordGrid';
import { TimelineControls } from './components/TimelineControls';
import { ClueList } from './components/ClueList';
import { useCrosswordState } from './hooks/useCrosswordState';
import './index.css';

export function App() {
  const {
    grid,
    width,
    height,
    progressData,
    currentEventIndex,
    activeEvent,
    setCurrentEventIndex,
    gridData
  } = useCrosswordState();

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Cryptic AI Visualizer</h1>
        <p>Interactive playback of chronological grid resolution</p>
      </header>

      <main className="main-content">
        <div className="left-panel">
          <div className="grid-container">
            <CrosswordGrid grid={grid} width={width} height={height} />
          </div>
          <TimelineControls
            currentEventIndex={currentEventIndex}
            totalEvents={progressData.length}
            onScrub={setCurrentEventIndex}
            activeEvent={activeEvent}
          />
        </div>

        <aside className="right-panel">
          <ClueList
            gridData={gridData}
            activeClueId={activeEvent?.id}
            progressData={progressData}
            currentEventIndex={currentEventIndex}
          />
        </aside>
      </main>
    </div>
  );
}

export default App;

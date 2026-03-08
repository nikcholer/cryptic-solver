import { startTransition, useEffect, useMemo, useState } from 'react';
import type {
  CreateSessionResponse,
  GridCell,
  PuzzleClue,
  PuzzleDefinition,
  PuzzleResponse,
  SessionResponse,
  SessionState,
} from '../types';

const DEFAULT_PUZZLE_ID = import.meta.env.VITE_PUZZLE_ID ?? 'cryptic-2026-03-03';
const SESSION_STORAGE_KEY = `cryptic-tutor-session:${DEFAULT_PUZZLE_ID}`;

async function fetchJson<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

function getStoredSessionId(): string | null {
  try {
    return window.localStorage.getItem(SESSION_STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeSessionId(sessionId: string | null): void {
  try {
    if (sessionId) {
      window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
    } else {
      window.localStorage.removeItem(SESSION_STORAGE_KEY);
    }
  } catch {
    // Ignore storage issues and continue with ephemeral sessions.
  }
}

function iterateClueCells(clue: PuzzleClue, clues: Record<string, PuzzleClue>): Array<[number, number]> {
  const cells: Array<[number, number]> = [];
  const segments = clue.linked_entries?.length
    ? clue.linked_entries.map((clueId) => clues[clueId]).filter((value): value is PuzzleClue => Boolean(value))
    : [clue];

  segments.forEach((segment) => {
    let { x, y } = segment;
    for (let index = 0; index < segment.length; index += 1) {
      cells.push([x, y]);
      if (segment.direction === 'Across') {
        x += 1;
      } else {
        y += 1;
      }
    }
  });

  return cells;
}

function sortClues(clues: Record<string, PuzzleClue>) {
  return Object.values(clues).sort((left, right) => {
    const numLeft = Number.parseInt(left.id, 10);
    const numRight = Number.parseInt(right.id, 10);
    if (numLeft !== numRight) return numLeft - numRight;
    return left.direction.localeCompare(right.direction);
  });
}

export function useTutorSession() {
  const [puzzle, setPuzzle] = useState<PuzzleDefinition | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionState, setSessionState] = useState<SessionState | null>(null);
  const [draftAnswer, setDraftAnswer] = useState('');
  const [justification, setJustification] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setIsLoading(true);
      setError(null);
      try {
        const puzzleResponse = await fetchJson<PuzzleResponse>(`/api/puzzles/${DEFAULT_PUZZLE_ID}`);
        let sessionResponse: SessionResponse | CreateSessionResponse | null = null;
        const storedSessionId = getStoredSessionId();

        if (storedSessionId) {
          try {
            const resumed = await fetchJson<SessionResponse>(`/api/sessions/${storedSessionId}`);
            if (resumed.puzzle.puzzle_id === DEFAULT_PUZZLE_ID) {
              sessionResponse = resumed;
            } else {
              storeSessionId(null);
            }
          } catch {
            storeSessionId(null);
          }
        }

        if (!sessionResponse) {
          sessionResponse = await fetchJson<CreateSessionResponse>('/api/sessions', {
            method: 'POST',
            body: JSON.stringify({ puzzleId: DEFAULT_PUZZLE_ID }),
          });
          storeSessionId(sessionResponse.sessionId);
        }

        if (cancelled) return;

        startTransition(() => {
          setPuzzle(puzzleResponse.puzzle);
          setSessionId(sessionResponse.sessionId);
          setSessionState(sessionResponse.sessionState);
          setDraftAnswer('');
          setJustification('');
        });
      } catch (caught) {
        if (cancelled) return;
        setError(caught instanceof Error ? caught.message : 'Unable to load puzzle session.');
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, []);

  const selectedClue = useMemo(() => {
    if (!puzzle || !sessionState?.selectedClueId) {
      return null;
    }
    return puzzle.clues[sessionState.selectedClueId] ?? null;
  }, [puzzle, sessionState]);

  useEffect(() => {
    if (!selectedClue || !sessionState) {
      setDraftAnswer('');
      setJustification('');
      return;
    }

    const existing = sessionState.entries[selectedClue.id]?.answer ?? '';
    setDraftAnswer(existing);
    setJustification('');
  }, [selectedClue?.id]);

  const clueList = useMemo(() => (puzzle ? sortClues(puzzle.clues) : []), [puzzle]);

  const cellClueMap = useMemo(() => {
    const nextMap: Record<string, string[]> = {};

    clueList.forEach((clue) => {
      iterateClueCells(clue, puzzle?.clues ?? {}).forEach(([x, y]) => {
        const key = `${x},${y}`;
        nextMap[key] ??= [];
        nextMap[key].push(clue.id);
      });
    });

    return nextMap;
  }, [clueList, puzzle]);

  const activeCells = useMemo(() => {
    const active = new Set<string>();
    if (!selectedClue) {
      return active;
    }

    iterateClueCells(selectedClue, puzzle?.clues ?? {}).forEach(([x, y]) => {
      active.add(`${x},${y}`);
    });
    return active;
  }, [selectedClue, puzzle]);

  const playableCells = useMemo(() => {
    if (!puzzle) {
      return { cells: new Set<string>(), clueNumbers: {} as Record<string, string> };
    }

    const cells = new Set<string>();
    const clueNumbers: Record<string, string> = {};

    clueList.forEach((clue) => {
      const clueNumber = clue.id.match(/^(\d+)/)?.[1];
      if (clueNumber) {
        clueNumbers[`${clue.x},${clue.y}`] = clueNumber;
      }

      iterateClueCells(clue, puzzle.clues).forEach(([x, y]) => {
        cells.add(`${x},${y}`);
      });
    });

    return { cells, clueNumbers };
  }, [clueList, puzzle]);

  const grid = useMemo<GridCell[][]>(() => {
    if (!puzzle || !sessionState) {
      return [];
    }

    const nextGrid: GridCell[][] = [];
    for (let y = 0; y < puzzle.grid.height; y += 1) {
      const row: GridCell[] = [];
      for (let x = 0; x < puzzle.grid.width; x += 1) {
        const key = `${x},${y}`;
        const isBlack = !playableCells.cells.has(key);
        row.push({
          x,
          y,
          isBlack,
          clueNumber: playableCells.clueNumbers[key],
          letter: sessionState.cells[key] ?? '',
          isActive: activeCells.has(key),
        });
      }
      nextGrid.push(row);
    }
    return nextGrid;
  }, [activeCells, playableCells, puzzle, sessionState]);

  const acrossClues = clueList.filter((clue) => clue.direction === 'Across');
  const downClues = clueList.filter((clue) => clue.direction === 'Down');

  async function refreshSession(nextSessionId: string) {
    const response = await fetchJson<SessionResponse>(`/api/sessions/${nextSessionId}`);
    storeSessionId(response.sessionId);
    startTransition(() => {
      setSessionState(response.sessionState);
    });
  }

  async function selectClue(clueId: string) {
    if (!sessionId) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await fetchJson(`/api/sessions/${sessionId}/select-clue`, {
        method: 'POST',
        body: JSON.stringify({ clueId }),
      });
      await refreshSession(sessionId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to select clue.');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function selectCell(x: number, y: number) {
    const clueIds = cellClueMap[`${x},${y}`] ?? [];
    if (clueIds.length === 0) {
      return;
    }

    if (clueIds.length === 1 || !sessionState?.selectedClueId) {
      await selectClue(clueIds[0]);
      return;
    }

    const currentIndex = clueIds.indexOf(sessionState.selectedClueId);
    const nextIndex = currentIndex === -1 ? 0 : (currentIndex + 1) % clueIds.length;
    await selectClue(clueIds[nextIndex]);
  }

  async function submitAnswer() {
    if (!sessionId || !selectedClue) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await fetchJson(`/api/sessions/${sessionId}/entries`, {
        method: 'POST',
        body: JSON.stringify({ clueId: selectedClue.id, answer: draftAnswer, justification }),
      });
      await refreshSession(sessionId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to submit answer.');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function acceptAnswer() {
    if (!sessionId || !selectedClue) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await fetchJson(`/api/sessions/${sessionId}/entries/${selectedClue.id}/accept`, {
        method: 'POST',
        body: JSON.stringify({ answer: draftAnswer, justification }),
      });
      await refreshSession(sessionId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to accept answer.');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function clearAnswer() {
    if (!sessionId || !selectedClue) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await fetchJson(`/api/sessions/${sessionId}/entries/${selectedClue.id}`, {
        method: 'DELETE',
      });
      setDraftAnswer('');
      await refreshSession(sessionId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to clear answer.');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function requestNextHint() {
    if (!sessionId || !selectedClue) {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await fetchJson(`/api/sessions/${sessionId}/clues/${selectedClue.id}/next-hint`, {
        method: 'POST',
        body: JSON.stringify({ mode: 'incremental' }),
      });
      await refreshSession(sessionId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to fetch next hint.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return {
    puzzle,
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
    isLoading,
    isSubmitting,
    error,
    selectClue,
    selectCell,
    submitAnswer,
    acceptAnswer,
    clearAnswer,
    requestNextHint,
  };
}

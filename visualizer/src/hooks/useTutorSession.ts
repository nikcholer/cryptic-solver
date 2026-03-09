import { startTransition, useEffect, useMemo, useState } from 'react';
import type {
  CreateSessionResponse,
  GridCell,
  PuzzleClue,
  PuzzleDefinition,
  PuzzleListResponse,
  PuzzleResponse,
  SessionResponse,
  SessionState,
  ThesaurusLookupResponse,
} from '../types';

const DEFAULT_PUZZLE_ID = import.meta.env.VITE_PUZZLE_ID ?? 'cryptic-2026-03-03';

function sessionStorageKey(puzzleId: string): string {
  return `cryptic-tutor-session:${puzzleId}`;
}

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

function getStoredSessionId(puzzleId: string): string | null {
  try {
    return window.localStorage.getItem(sessionStorageKey(puzzleId));
  } catch {
    return null;
  }
}

function storeSessionId(puzzleId: string, sessionId: string | null): void {
  try {
    const key = sessionStorageKey(puzzleId);
    if (sessionId) {
      window.localStorage.setItem(key, sessionId);
    } else {
      window.localStorage.removeItem(key);
    }
  } catch {
    // Ignore storage issues and continue with ephemeral sessions.
  }
}

async function fetchFormJson<T>(input: RequestInfo, body: FormData): Promise<T> {
  const response = await fetch(input, { method: 'POST', body });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
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
  const [availablePuzzleIds, setAvailablePuzzleIds] = useState<string[]>([]);
  const [currentPuzzleId, setCurrentPuzzleId] = useState(DEFAULT_PUZZLE_ID);
  const [puzzle, setPuzzle] = useState<PuzzleDefinition | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionState, setSessionState] = useState<SessionState | null>(null);
  const [draftAnswer, setDraftAnswer] = useState('');
  const [justification, setJustification] = useState('');
  const [thesaurusTerm, setThesaurusTerm] = useState('');
  const [thesaurusCandidates, setThesaurusCandidates] = useState<ThesaurusLookupResponse['candidates']>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      setIsLoading(true);
      setError(null);
      try {
        const [listResponse, puzzleResponse] = await Promise.all([
          fetchJson<PuzzleListResponse>('/api/puzzles'),
          fetchJson<PuzzleResponse>(`/api/puzzles/${currentPuzzleId}`),
        ]);
        let sessionResponse: SessionResponse | CreateSessionResponse | null = null;
        const storedSessionId = getStoredSessionId(currentPuzzleId);

        if (storedSessionId) {
          try {
            const resumed = await fetchJson<SessionResponse>(`/api/sessions/${storedSessionId}`);
            if (resumed.puzzle.puzzle_id === currentPuzzleId) {
              sessionResponse = resumed;
            } else {
              storeSessionId(currentPuzzleId, null);
            }
          } catch {
            storeSessionId(currentPuzzleId, null);
          }
        }

        if (!sessionResponse) {
          sessionResponse = await fetchJson<CreateSessionResponse>('/api/sessions', {
            method: 'POST',
            body: JSON.stringify({ puzzleId: currentPuzzleId }),
          });
          storeSessionId(currentPuzzleId, sessionResponse.sessionId);
        }

        if (cancelled) return;

        startTransition(() => {
          setAvailablePuzzleIds(listResponse.puzzles.map((item) => item.puzzleId));
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
  }, [currentPuzzleId]);

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
      setThesaurusTerm('');
      setThesaurusCandidates([]);
      return;
    }

    const existing = sessionState.entries[selectedClue.id]?.answer ?? '';
    setDraftAnswer(existing);
    setThesaurusTerm('');
    setThesaurusCandidates([]);
  }, [selectedClue?.id, sessionState?.entries, sessionState]);

  useEffect(() => {
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

  async function refreshSession(nextSessionId: string, puzzleId = currentPuzzleId) {
    const response = await fetchJson<SessionResponse>(`/api/sessions/${nextSessionId}`);
    storeSessionId(puzzleId, response.sessionId);
    startTransition(() => {
      setSessionState(response.sessionState);
      setPuzzle(response.puzzle);
      setSessionId(response.sessionId);
    });
  }

  async function uploadPdf(file: File) {
    setIsSubmitting(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const response = await fetchFormJson<SessionResponse>('/api/imports/pdf', form);
      storeSessionId(response.puzzle.puzzle_id, response.sessionId);
      startTransition(() => {
        setAvailablePuzzleIds((current) => Array.from(new Set([...current, response.puzzle.puzzle_id])).sort());
        setCurrentPuzzleId(response.puzzle.puzzle_id);
        setPuzzle(response.puzzle);
        setSessionId(response.sessionId);
        setSessionState(response.sessionState);
        setDraftAnswer('');
        setJustification('');
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to import PDF puzzle.');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function lookupThesaurus() {
    if (!selectedClue || !thesaurusTerm.trim()) {
      setThesaurusCandidates([]);
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      const params = new URLSearchParams({ term: thesaurusTerm.trim(), length: String(selectedClue.answer_length) });
      const response = await fetchJson<ThesaurusLookupResponse>(`/api/thesaurus?${params.toString()}`);
      setThesaurusCandidates(response.candidates);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to look up thesaurus entries.');
    } finally {
      setIsSubmitting(false);
    }
  }

  function choosePuzzle(puzzleId: string) {
    if (puzzleId === currentPuzzleId) {
      return;
    }
    startTransition(() => {
      setCurrentPuzzleId(puzzleId);
      setDraftAnswer('');
      setJustification('');
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
  };
}

import { startTransition, useCallback, useEffect, useMemo, useState } from 'react';
import type {
  GridCell,
  PuzzleDefinition,
  PuzzleListResponse,
  PuzzleResponse,
  SessionResponse,
  SessionState,
  ThesaurusLookupResponse,
} from '../types';
import { fetchJson, fetchFormJson } from '../api';
import { getStoredSessionId, storeSessionId } from '../sessionStorage';
import { iterateClueCells, sortClues } from '../gridUtils';

const DEFAULT_PUZZLE_ID = import.meta.env.VITE_PUZZLE_ID ?? 'cryptic-2026-03-03';

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

  const withSubmit = useCallback(
    (fallbackMessage: string, action: () => Promise<void>) => {
      return async () => {
        setIsSubmitting(true);
        setError(null);
        try {
          await action();
        } catch (caught) {
          setError(caught instanceof Error ? caught.message : fallbackMessage);
        } finally {
          setIsSubmitting(false);
        }
      };
    },
    [],
  );

  // -- Bootstrap: load puzzle list, puzzle definition, and session ---------

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
        let sessionResponse: SessionResponse | null = null;
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
          sessionResponse = await fetchJson<SessionResponse>('/api/sessions', {
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

  // -- Derived state -------------------------------------------------------

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

  // -- Actions -------------------------------------------------------------

  async function refreshSession(nextSessionId: string, puzzleId = currentPuzzleId) {
    const response = await fetchJson<SessionResponse>(`/api/sessions/${nextSessionId}`);
    storeSessionId(puzzleId, response.sessionId);
    startTransition(() => {
      setSessionState(response.sessionState);
      setPuzzle(response.puzzle);
      setSessionId(response.sessionId);
    });
  }

  const uploadPdf = useCallback(
    (file: File) =>
      withSubmit('Unable to import PDF puzzle.', async () => {
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
      })(),
    [withSubmit],
  );

  const lookupThesaurus = useCallback(async () => {
    if (!selectedClue || !thesaurusTerm.trim()) {
      setThesaurusCandidates([]);
      return;
    }

    await withSubmit('Unable to look up thesaurus entries.', async () => {
      const params = new URLSearchParams({ term: thesaurusTerm.trim(), length: String(selectedClue.answer_length) });
      const response = await fetchJson<ThesaurusLookupResponse>(`/api/thesaurus?${params.toString()}`);
      setThesaurusCandidates(response.candidates);
    })();
  }, [selectedClue, thesaurusTerm, withSubmit]);

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
    if (!sessionId) return;
    await withSubmit('Unable to select clue.', async () => {
      await fetchJson(`/api/sessions/${sessionId}/select-clue`, {
        method: 'POST',
        body: JSON.stringify({ clueId }),
      });
      await refreshSession(sessionId);
    })();
  }

  async function selectCell(x: number, y: number) {
    const clueIds = cellClueMap[`${x},${y}`] ?? [];
    if (clueIds.length === 0) return;

    if (clueIds.length === 1 || !sessionState?.selectedClueId) {
      await selectClue(clueIds[0]);
      return;
    }

    const currentIndex = clueIds.indexOf(sessionState.selectedClueId);
    const nextIndex = currentIndex === -1 ? 0 : (currentIndex + 1) % clueIds.length;
    await selectClue(clueIds[nextIndex]);
  }

  async function submitAnswer() {
    if (!sessionId || !selectedClue) return;
    await withSubmit('Unable to submit answer.', async () => {
      await fetchJson(`/api/sessions/${sessionId}/entries`, {
        method: 'POST',
        body: JSON.stringify({ clueId: selectedClue.id, answer: draftAnswer, justification }),
      });
      await refreshSession(sessionId);
    })();
  }

  async function acceptAnswer() {
    if (!sessionId || !selectedClue) return;
    await withSubmit('Unable to accept answer.', async () => {
      await fetchJson(`/api/sessions/${sessionId}/entries/${selectedClue.id}/accept`, {
        method: 'POST',
        body: JSON.stringify({ answer: draftAnswer, justification }),
      });
      await refreshSession(sessionId);
    })();
  }

  async function clearAnswer() {
    if (!sessionId || !selectedClue) return;
    await withSubmit('Unable to clear answer.', async () => {
      await fetchJson(`/api/sessions/${sessionId}/entries/${selectedClue.id}`, {
        method: 'DELETE',
      });
      setDraftAnswer('');
      await refreshSession(sessionId);
    })();
  }

  async function requestNextHint() {
    if (!sessionId || !selectedClue) return;
    await withSubmit('Unable to fetch next hint.', async () => {
      await fetchJson(`/api/sessions/${sessionId}/clues/${selectedClue.id}/next-hint`, {
        method: 'POST',
        body: JSON.stringify({ mode: 'incremental' }),
      });
      await refreshSession(sessionId);
    })();
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

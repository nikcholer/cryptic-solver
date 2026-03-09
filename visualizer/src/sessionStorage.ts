function sessionStorageKey(puzzleId: string): string {
  return `cryptic-tutor-session:${puzzleId}`;
}

export function getStoredSessionId(puzzleId: string): string | null {
  try {
    return window.localStorage.getItem(sessionStorageKey(puzzleId));
  } catch {
    return null;
  }
}

export function storeSessionId(puzzleId: string, sessionId: string | null): void {
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

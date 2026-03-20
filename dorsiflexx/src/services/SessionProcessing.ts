/**
 * Module-level singleton for tracking background ML session processing.
 * Allows exercise-in-progress to fire disconnect() in the background
 * and notify the home screen when analysis is complete.
 */

type CompletedSession = { session_id: string; date: string };
type Listener = (session: CompletedSession) => void;

let _completed: CompletedSession | null = null;
const _listeners = new Set<Listener>();

export function setPendingSession(
  session_id: string,
  date: string,
  promise: Promise<any>,
): void {
  _completed = null;
  promise
    .then(() => {
      const session = { session_id, date };
      _completed = session;
      _listeners.forEach((l) => l(session));
    })
    .catch(() => {
      // ML processing failed — silently ignore, no banner
    });
}

/** Call on home screen mount to grab a result that arrived before the screen did. */
export function consumeCompletedSession(): CompletedSession | null {
  const result = _completed;
  _completed = null;
  return result;
}

/** Subscribe to future session completions. Returns an unsubscribe function. */
export function subscribeToSessionComplete(listener: Listener): () => void {
  _listeners.add(listener);
  return () => _listeners.delete(listener);
}

/**
 * Format a result message with a prefix character.
 *
 * Prefix conventions:
 *   + created
 *   ~ modified (edge/connection)
 *   * changed (property)
 *   - removed
 *   ! meta/group operation
 *   @ bulk/layout operation
 */
export function formatResult(
  success: boolean,
  message: string,
  prefix?: string,
): string {
  if (!success) return `ERROR: ${message}`;
  if (prefix) return `${prefix} ${message}`;
  return message;
}

/**
 * Suggest a correction for a misspelled input by finding the closest
 * candidate using Levenshtein distance. Returns null if no candidate
 * is close enough (distance > 3).
 */
export function suggest(input: string, candidates: string[]): string | null {
  if (candidates.length === 0) return null;

  let best: string | null = null;
  let bestDist = Infinity;

  for (const candidate of candidates) {
    const dist = levenshtein(input.toLowerCase(), candidate.toLowerCase());
    if (dist < bestDist) {
      bestDist = dist;
      best = candidate;
    }
  }

  return bestDist <= 3 ? best : null;
}

/**
 * Compute Levenshtein distance between two strings.
 */
function levenshtein(a: string, b: string): number {
  const m = a.length;
  const n = b.length;

  // Use a single-row DP array
  const prev = new Array<number>(n + 1);
  for (let j = 0; j <= n; j++) prev[j] = j;

  for (let i = 1; i <= m; i++) {
    let prevDiag = prev[0];
    prev[0] = i;
    for (let j = 1; j <= n; j++) {
      const temp = prev[j];
      if (a[i - 1] === b[j - 1]) {
        prev[j] = prevDiag;
      } else {
        prev[j] = 1 + Math.min(prevDiag, prev[j - 1], prev[j]);
      }
      prevDiag = temp;
    }
  }

  return prev[n];
}

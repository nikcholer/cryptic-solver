/** Replace underscores with spaces for display (e.g. "in_progress" → "in progress"). */
export function formatStatus(status: string): string {
  return status.replace(/_/g, ' ');
}

const tokenFormatter = new Intl.NumberFormat('en-GB');

export function formatTokens(count: number): string {
  return tokenFormatter.format(count);
}

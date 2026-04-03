const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/+$/, '');

function resolveApiInput(input: RequestInfo | URL): RequestInfo | URL {
  if (typeof input !== 'string') {
    return input;
  }

  if (!input.startsWith('/') || !API_BASE_URL) {
    return input;
  }

  return `${API_BASE_URL}${input}`;
}

export async function fetchJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await fetch(resolveApiInput(input), {
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

export async function fetchFormJson<T>(input: RequestInfo | URL, body: FormData): Promise<T> {
  const response = await fetch(resolveApiInput(input), { method: 'POST', body });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

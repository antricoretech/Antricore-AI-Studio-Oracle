/* One API adapter for the entire UI. Keeping HTTP concerns here gives the
   views consistent errors, cancellation, bounded retries, and authenticated
   cloud-mode behavior. */

import { notify } from './core.js';

export class ApiError extends Error {
  constructor(message, status = 0, payload = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
  }
}

function parsePayload(text) {
  if (!text) return null;
  try { return JSON.parse(text); } catch { return { detail: text }; }
}

function errorMessage(payload, fallback) {
  const detail = payload && typeof payload === 'object'
    ? (payload.detail || payload.message || payload.error)
    : payload;
  if (Array.isArray(detail)) return detail.map((item) => item.msg || item).join('; ');
  if (detail && typeof detail === 'object') return JSON.stringify(detail);
  return String(detail || fallback || 'Request failed').slice(0, 350);
}

function wait(delay, signal) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, delay);
    if (!signal) return;
    signal.addEventListener('abort', () => {
      clearTimeout(timer);
      reject(new DOMException('The request was aborted.', 'AbortError'));
    }, { once: true });
  });
}

export async function api(url, options = {}) {
  const {
    retries = 0,
    retryDelayMs = 250,
    ...requestOptions
  } = options;
  const method = (requestOptions.method || 'GET').toUpperCase();
  const signal = requestOptions.signal;
  const headers = new Headers(requestOptions.headers || {});
  headers.set('Accept', 'application/json');
  if (requestOptions.body && !(requestOptions.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const safeRetries = method === 'GET' ? Math.max(0, retries) : 0;

  for (let attempt = 0; attempt <= safeRetries; attempt += 1) {
    try {
      const response = await fetch(url, { ...requestOptions, headers, signal });
      const payload = parsePayload(await response.text());
      if (response.ok) return payload;

      const error = new ApiError(errorMessage(payload, response.statusText), response.status, payload);
      if (response.status === 401) notify('Studio authentication is required for this worker.', true);
      if (response.status >= 500 && attempt < safeRetries) {
        await wait(retryDelayMs * (2 ** attempt), signal);
        continue;
      }
      throw error;
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      if (attempt < safeRetries) {
        await wait(retryDelayMs * (2 ** attempt), signal);
        continue;
      }
      if (error instanceof ApiError) throw error;
      throw new ApiError(error.message || 'Network request failed', 0, null);
    }
  }
  throw new ApiError('Request failed after retries', 0, null);
}

export const get = (url, options = {}) => api(url, { ...options, method: 'GET', retries: options.retries ?? 2 });

export const post = (url, data, options = {}) => api(url, {
  ...options,
  method: 'POST',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  body: JSON.stringify(data),
});

export const patch = (url, data, options = {}) => api(url, {
  ...options,
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  body: JSON.stringify(data),
});

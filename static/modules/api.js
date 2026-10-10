/* One API adapter for the entire UI. Keeping HTTP concerns here gives the
   views consistent errors and makes authenticated cloud mode transparent. */

import { notify } from './core.js';

export async function api(url, options = {}) {
  const response = await fetch(url, options);
  const text = await response.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  if (!response.ok) {
    if (response.status === 401) notify('Studio authentication is required for this worker.', true);
    const detail = typeof data === 'object' ? (data.detail || data) : data;
    throw new Error(String(detail || response.statusText).slice(0, 350));
  }
  return data;
}

export const post = (url, data) => api(url, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data),
});

/* Shared browser primitives. Keep this module dependency-free so every view
   can use the same state, DOM construction and notification behaviour. */

export const state = {
  personas: [], workflows: [], checkpoints: [], assets: [], jobs: [], links: [],
  series: [], models: [], monitoring: null, health: null,
};

export const names = {
  dashboard: 'Overview', personas: 'Persona Library', generate: 'Production Studio',
  assets: 'Media Review', voice: 'Voice & Narration', funnels: 'Link Tracking',
  workflows: 'Workflow Manager', series: 'Series Studio', monitoring: 'Monitoring',
};

export const $ = (selector, root = document) => root.querySelector(selector);

export function el(tag, attrs = {}, text = '') {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === 'class') node.className = value;
    else if (value !== undefined && value !== null) node.setAttribute(key, value);
  }
  if (text) node.textContent = text;
  return node;
}

export function clear(node) {
  if (node) while (node.firstChild) node.removeChild(node.firstChild);
}

export function notify(message, bad = false) {
  const banner = $('#message');
  if (!banner) return;
  banner.textContent = message;
  banner.className = 'notice' + (bad ? ' error' : '');
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => banner.classList.add('hidden'), 6500);
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const helper = el('textarea', {}, text);
    document.body.append(helper);
    helper.select();
    document.execCommand('copy');
    helper.remove();
  }
}

export function readableValue(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  if (Array.isArray(value)) return value.map(readableValue).join('; ');
  if (typeof value === 'object') {
    const preferred = value.canonical_identity_prompt || value.public_disclosure || value.short_disclosure;
    if (preferred) return readableValue(preferred);
    return JSON.stringify(value);
  }
  return String(value);
}

export function emptyAction(target, label) {
  const button = el('button', { class: 'secondary go-tab', type: 'button' }, label);
  button.dataset.target = target;
  return button;
}

export function options(selector, values, empty) {
  const target = $(selector);
  if (!target) return target;
  const previous = target.value;
  clear(target);
  if (empty) target.append(el('option', { value: '' }, empty));
  for (const option of values) target.append(el('option', { value: option.value }, option.name));
  if ([...target.options].some((option) => option.value === previous)) target.value = previous;
  return target;
}

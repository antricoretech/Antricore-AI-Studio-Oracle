import { $, clear, el } from './core.js';

const navGroupStorageKey = 'persona-studio.nav-groups.v1';

const navGroups = [
  { label: 'Create', key: 'create', items: [
    ['personas', 'persona-library', 'Persona library', '◎', '02'],
    ['personas', 'new-persona', 'New persona', '+', '', 'persona-form'],
    ['personas', 'reference-vault', 'Reference vault', '◇', '', 'reference-form'],
    ['generate', 'generation-brief', 'Generation brief', '✦', '03', 'brief-import'],
  ] },
  { label: 'Produce', key: 'produce', items: [
    ['orchestrator', 'persona-orchestrator', 'Persona Orchestrator', '💎', '04', 'orchestrator'],
    ['photostudio', 'photo-studio', 'Photo Studio', '📷', '03', 'photo-studio'],
    ['generate', 'image-studio', 'Legacy studio', '◉', '', 'job-form'],
    ['generate', 'video-studio', 'Video studio', '▷', '', 'job-form'],
    ['voice', 'voice-studio', 'Voice & narration', '◖', ''],
    ['series', 'series-studio', 'Series studio', '↻', ''],
  ] },
  { label: 'Review & export', key: 'review', items: [
    ['assets', 'media-review', 'Media review', '▧', '04'],
    ['assets', 'approval-queue', 'Approval queue', '✓', '', 'gallery'],
    ['assets', 'export-packages', 'Export packages', '↓', '', 'gallery'],
    ['funnels', 'link-tracking', 'Link tracking', '↗', '07'],
  ] },
  { label: 'Operations', key: 'operations', items: [
    ['workflows', 'workflow-manager', 'Workflow manager', '⌘', '06'],
    ['monitoring', 'monitoring', 'Monitoring', '◌', '09'],
  ] },
];

function readNavGroupState() {
  try { return JSON.parse(localStorage.getItem(navGroupStorageKey) || '{}'); }
  catch { return {}; }
}

export function setNavGroupOpen(group, open, persist = true) {
  if (!group) return;
  group.classList.toggle('is-collapsed', !open);
  const toggle = group.querySelector('.nav-group-toggle');
  if (toggle) {
    toggle.setAttribute('aria-expanded', String(open));
    toggle.querySelector('.nav-group-chevron').textContent = open ? '⌄' : '›';
  }
  if (persist) {
    const saved = readNavGroupState();
    saved[group.dataset.navGroup] = open;
    localStorage.setItem(navGroupStorageKey, JSON.stringify(saved));
  }
}

function buildNavButton(item) {
  const [target, key, label, icon, shortcut, focus] = item;
  const attrs = { 'data-tab': target, 'data-nav-key': key, class: 'nav nav-sub' };
  if (focus) attrs['data-focus'] = focus;
  const button = el('button', attrs);
  button.append(el('span', { class: 'nav-icon', 'aria-hidden': 'true' }, icon), el('span', {}, label));
  if (shortcut) button.append(el('kbd', {}, shortcut));
  return button;
}

export function mountNavigation() {
  const nav = $('.nav-list');
  if (!nav || nav.dataset.grouped === 'true') return;
  nav.dataset.grouped = 'true';
  clear(nav);
  nav.append(el('p', { class: 'nav-label' }, 'Workspace'));
  const overview = el('button', { 'data-tab': 'dashboard', 'data-nav-key': 'overview', class: 'nav active', 'aria-current': 'page' });
  overview.append(el('span', { class: 'nav-icon', 'aria-hidden': 'true' }, '⌂'), el('span', {}, 'Overview'), el('kbd', {}, '01'));
  nav.append(overview);
  const savedGroups = readNavGroupState();
  for (const groupData of navGroups) {
    const open = savedGroups[groupData.key] === true;
    const group = el('div', { class: 'nav-group' + (open ? '' : ' is-collapsed'), 'data-nav-group': groupData.key });
    const toggle = el('button', { class: 'nav-group-toggle', type: 'button', 'aria-expanded': String(open), 'aria-controls': 'nav-submenu-' + groupData.key });
    toggle.append(el('span', { class: 'nav-group-chevron', 'aria-hidden': 'true' }, open ? '⌄' : '›'), el('span', {}, groupData.label));
    toggle.addEventListener('click', () => setNavGroupOpen(group, group.classList.contains('is-collapsed')));
    const submenu = el('div', { class: 'nav-submenu', id: 'nav-submenu-' + groupData.key });
    groupData.items.forEach((item) => submenu.append(buildNavButton(item)));
    group.append(toggle, submenu);
    nav.append(group);
  }
}

import { get, post } from './modules/api.js';

const navGroups = [
  { label: 'Identity', items: [
    ['overview', 'Overview', '⌂'],
    ['personas', 'Master Personas', '◎'],
    ['references', 'Reference Packs', '◇'],
    ['content-packs', 'ContentPacks', '◆'],
  ] },
  { label: 'Production', items: [
    ['production', 'Production Queue', '▶'],
    ['assets', 'Asset Review', '▣'],
  ] },
  { label: 'Publishing', items: [
    ['publishing', 'Publishing Readiness', '↗'],
  ] },
];

const viewMeta = {
  overview: ['Overview', 'One source of truth for the new Master Persona journey.'],
  personas: ['Master Personas', 'Create and inspect PersonaVersion-bound identities.'],
  references: ['Reference Packs', 'Review identity sources, rights, assets, and canonical selection.'],
  'content-packs': ['ContentPacks', 'Bind creator style and adult/glamour identity anchors to one version.'],
  production: ['Production Queue', 'Track jobs and their PersonaVersion lineage.'],
  assets: ['Asset Review', 'Review generated and imported media before it becomes publishable.'],
  publishing: ['Publishing Readiness', 'Prepare approved, disclosed, policy-checked content for account delivery.'],
};

const state = {
  view: 'overview',
  personas: [],
  activePersonaId: '',
  summary: {},
  versions: [],
  references: [],
  contentPacks: [],
  jobs: [],
  assets: [],
  submittingPersona: false,
  freezingPersona: false,
  controller: null,
  requestToken: 0,
};

const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  }[character]));
}

function badge(value) {
  const label = String(value || 'unknown');
  return `<span class="badge ${escapeHtml(label.toLowerCase())}">${escapeHtml(label)}</span>`;
}

function setStatus(message, tone = '') {
  const target = $('#workspace-status');
  target.textContent = message;
  target.className = `status ${tone}`.trim();
}

function activePersona() {
  return state.personas.find((persona) => persona.id === state.activePersonaId) || null;
}

function renderNavigation() {
  $('#workspace-nav').innerHTML = navGroups.map((group) => `<div class="nav-group">
    <p class="nav-group-label">${escapeHtml(group.label)}</p>
    ${group.items.map(([id, label, icon]) => `<button class="nav-button" type="button" data-view="${escapeHtml(id)}" aria-current="${state.view === id ? 'page' : 'false'}"><span class="nav-icon" aria-hidden="true">${icon}</span><span>${escapeHtml(label)}</span></button>`).join('')}
  </div>`).join('');
}

function renderPersonaSelect() {
  const select = $('#persona-select');
  if (!state.personas.length) {
    select.innerHTML = '<option value="">No Master Personas available</option>';
    select.disabled = true;
    return;
  }
  select.innerHTML = state.personas.map((persona) => `<option value="${escapeHtml(persona.id)}">${escapeHtml(persona.name || persona.id)}</option>`).join('');
  select.value = state.activePersonaId;
  select.disabled = false;
}

function renderHeader() {
  const [title, description] = viewMeta[state.view] || viewMeta.overview;
  $('#view-title').textContent = title;
  $('#view-description').textContent = description;
  document.title = `${title} · AI Influencer Studio`;
}

function emptyState(message, actionView = '') {
  const action = actionView ? `<button class="button secondary" type="button" data-view="${escapeHtml(actionView)}">Open next step</button>` : '';
  return `<div class="empty"><p>${escapeHtml(message)}</p>${action}</div>`;
}

const defaultCharacteristics = JSON.stringify({
  consistency_anchor: '',
  face: {},
  physique: {},
  style: {},
  personality: {},
  world: {},
  camera: {},
}, null, 2);

function renderOverview() {
  const persona = activePersona();
  const summary = state.summary;
  return `<div class="metric-grid">
    <div class="metric"><div class="metric-label">Master Personas</div><div class="metric-value">${escapeHtml(summary.personas || 0)}</div></div>
    <div class="metric"><div class="metric-label">Queued / completed jobs</div><div class="metric-value">${escapeHtml(summary.jobs || 0)}</div></div>
    <div class="metric"><div class="metric-label">Approved assets</div><div class="metric-value">${escapeHtml(summary.approved || 0)}</div></div>
    <div class="metric"><div class="metric-label">Tracked link clicks</div><div class="metric-value">${escapeHtml(summary.clicks || 0)}</div></div>
  </div>
  <div class="panel-grid">
    <section class="journey-card" aria-labelledby="journey-heading">
      <div class="section-heading"><div><p class="eyebrow">Canonical journey</p><h2 id="journey-heading">${persona ? escapeHtml(persona.name) : 'No Master Persona selected'}</h2></div>${persona ? badge(persona.current_version?.state || (persona.identity_locked ? 'frozen' : 'draft')) : ''}</div>
      <p class="helper">New production identities move through explicit version, reference, content, generation, and review states.</p>
      <div class="journey-steps">
        <div class="journey-step"><strong>01 · Identity</strong><span>Persona + immutable version</span></div>
        <div class="journey-step"><strong>02 · Canonical sources</strong><span>Review packs, rights, and anchors</span></div>
        <div class="journey-step"><strong>03 · ContentPacks</strong><span>Style and Identity Core authority</span></div>
        <div class="journey-step"><strong>04 · Review</strong><span>Approve before export or publishing</span></div>
      </div>
    </section>
    <section class="panel" aria-labelledby="next-heading">
      <div class="section-heading"><div><p class="eyebrow">Next action</p><h2 id="next-heading">Continue the canonical flow</h2></div></div>
      ${persona ? `<div class="callout"><p><strong>Active PersonaVersion:</strong> ${escapeHtml(persona.current_version?.id || 'available through versions')}</p><p class="helper">Start with ReferencePack review, then author ContentPacks from approved canonical anchors.</p></div><div class="entity-actions" style="margin-top: 14px"><button class="button primary" type="button" data-view="references">Review sources</button><button class="button secondary" type="button" data-view="content-packs">Manage ContentPacks</button></div>` : emptyState('Create a new Master Persona through the canonical creation flow.', 'personas')}
    </section>
  </div>`;
}

function renderPersonasLegacy() {
  if (!state.personas.length) return emptyState('No Master Personas are available in the canonical store.');
  const persona = activePersona();
  return `<div class="panel-grid">
    <section class="panel" aria-labelledby="persona-list-heading"><div class="section-heading"><div><p class="eyebrow">Identity registry</p><h2 id="persona-list-heading">Master Personas</h2></div>${badge(`${state.personas.length} records`)}</div><div class="card-list">${state.personas.map((item) => `<article class="entity-card"><div><h3>${escapeHtml(item.name || item.id)}</h3><p>${escapeHtml(item.description || 'No description recorded.')}</p><div class="entity-meta">${badge(item.current_version?.state || (item.identity_locked ? 'frozen' : 'draft'))}${badge(`Age ${item.age || '—'}`)}<span class="badge">${escapeHtml(item.id)}</span></div></div><div class="entity-actions"><button class="button secondary" type="button" data-persona-id="${escapeHtml(item.id)}">Select</button></div></article>`).join('')}</div></section>
    <section class="panel" aria-labelledby="persona-detail-heading"><div class="section-heading"><div><p class="eyebrow">Selected identity</p><h2 id="persona-detail-heading">${escapeHtml(persona?.name || 'None')}</h2></div></div>${persona ? `<p class="helper">${escapeHtml(persona.appearance || 'Appearance details are not recorded.')}</p><div class="callout"><p><strong>Disclosure:</strong> ${escapeHtml(persona.disclosure || 'No disclosure recorded.')}</p><p><strong>Version:</strong> ${escapeHtml(persona.current_version?.id || 'Load versions from the canonical API')}</p></div><div class="entity-actions" style="margin-top: 14px"><button class="button secondary" type="button" data-view="references">Open ReferencePacks</button><button class="button secondary" type="button" data-view="content-packs">Open ContentPacks</button></div>` : emptyState('Select a Master Persona to inspect its version lineage.')}</section>
  </div>`;
}

function renderPersonasCanonical() {
  const persona = activePersona();
  const currentVersion = persona?.current_version;
  const canFreeze = persona && currentVersion?.state === 'draft' && !state.freezingPersona;
  return `<div class="panel-grid">
    <section class="panel" aria-labelledby="persona-create-heading">
      <div class="section-heading"><div><p class="eyebrow">Canonical identity</p><h2 id="persona-create-heading">Create Master Persona</h2></div>${badge('new structure')}</div>
      <p class="helper">This creates a new Persona and its initial draft PersonaVersion. Existing legacy personas are not reused.</p>
      <form id="persona-create-form" class="persona-form">
        <div class="form-grid">
          <div class="field"><label for="persona-create-name">Name</label><input id="persona-create-name" name="name" minlength="2" maxlength="80" required placeholder="e.g. Mira Vale"></div>
          <div class="field"><label for="persona-create-age">Age</label><input id="persona-create-age" name="age" type="number" min="18" max="110" required value="25"></div>
        </div>
        <div class="field"><label for="persona-create-description">Creator description</label><textarea id="persona-create-description" name="description" minlength="8" maxlength="1500" required placeholder="Who this fictional adult creator is and what she makes."></textarea></div>
        <div class="field"><label for="persona-create-appearance">Appearance</label><textarea id="persona-create-appearance" name="appearance" minlength="8" maxlength="1500" required placeholder="Stable facial identity, hair, eyes, body, and visual traits."></textarea></div>
        <div class="field"><label for="persona-create-disclosure">Disclosure</label><input id="persona-create-disclosure" name="disclosure" minlength="10" maxlength="250" required value="Fictional AI-generated adult persona"></div>
        <div class="field"><label for="persona-create-characteristics">Identity characteristics JSON <span class="field-hint">optional structured anchors</span></label><textarea id="persona-create-characteristics" name="characteristics" class="code-field" spellcheck="false">${escapeHtml(defaultCharacteristics)}</textarea></div>
        <div class="form-actions"><button class="button primary" type="submit" ${state.submittingPersona ? 'disabled' : ''}>${state.submittingPersona ? 'Creating…' : 'Create Persona'}</button></div>
        <p id="persona-form-error" class="form-error" role="alert" hidden></p>
      </form>
    </section>
    <section class="panel" aria-labelledby="persona-list-heading">
      <div class="section-heading"><div><p class="eyebrow">Identity registry</p><h2 id="persona-list-heading">Master Personas</h2></div>${badge(`${state.personas.length} records`)}</div>
      ${state.personas.length ? `<div class="card-list">${state.personas.map((item) => `<article class="entity-card"><div><h3>${escapeHtml(item.name || item.id)}</h3><p>${escapeHtml(item.description || 'No description recorded.')}</p><div class="entity-meta">${badge(item.current_version?.state || (item.identity_locked ? 'frozen' : 'draft'))}${badge(`Age ${item.age || '—'}`)}<span class="badge">${escapeHtml(item.id)}</span></div></div><div class="entity-actions"><button class="button secondary" type="button" data-persona-id="${escapeHtml(item.id)}">${item.id === state.activePersonaId ? 'Selected' : 'Select'}</button></div></article>`).join('')}</div>` : emptyState('No Master Personas are available yet. Create the first canonical identity here.')}
    </section>
  </div>
  <section class="panel" aria-labelledby="persona-detail-heading">
    <div class="section-heading"><div><p class="eyebrow">Selected identity</p><h2 id="persona-detail-heading">${escapeHtml(persona?.name || 'No persona selected')}</h2></div>${persona ? badge(currentVersion?.state || 'draft') : ''}</div>
    ${persona ? `<p class="helper">${escapeHtml(persona.appearance || 'Appearance details are not recorded.')}</p><div class="callout"><p><strong>Disclosure:</strong> ${escapeHtml(persona.disclosure || 'No disclosure recorded.')}</p><p><strong>Current PersonaVersion:</strong> ${escapeHtml(currentVersion?.id || 'not available')}</p><p><strong>Lifecycle:</strong> ${currentVersion?.state === 'frozen' ? 'Frozen and ready for downstream lineage.' : 'Draft; freeze after identity review.'}</p></div><div class="entity-actions detail-actions"><button class="button primary" type="button" data-freeze-persona ${canFreeze ? '' : 'disabled'}>${state.freezingPersona ? 'Freezing…' : currentVersion?.state === 'frozen' ? 'PersonaVersion frozen' : 'Freeze PersonaVersion'}</button><button class="button secondary" type="button" data-view="references">Open ReferencePacks</button><button class="button secondary" type="button" data-view="content-packs">Open ContentPacks</button></div>` : emptyState('Select a Master Persona to inspect its version lineage.')}
    ${persona ? `<div class="version-section"><div class="section-heading"><div><p class="eyebrow">Immutable lineage</p><h3 id="version-lineage-heading">PersonaVersions</h3></div>${badge(`${state.versions.length} version${state.versions.length === 1 ? '' : 's'}`)}</div>${state.versions.length ? `<div class="version-list">${state.versions.map((version) => `<article class="version-card"><div><strong>Version ${escapeHtml(version.version_no)}</strong><span class="version-id">${escapeHtml(version.id)}</span></div><div class="entity-meta">${badge(version.state)}${version.source ? badge(version.source) : ''}${version.frozen_at ? badge('frozen at ' + version.frozen_at) : ''}</div></article>`).join('')}</div>` : emptyState('No PersonaVersion records returned for this persona.')}</div>` : ''}
  </section>`;
}

function renderReferences() {
  if (!state.activePersonaId) return emptyState('Select or create a Master Persona before reviewing references.', 'personas');
  if (!state.references.length) return emptyState('No ReferencePacks are available for this PersonaVersion yet.');
  return `<section class="panel" aria-labelledby="references-heading"><div class="section-heading"><div><p class="eyebrow">Identity sources</p><h2 id="references-heading">ReferencePack review state</h2></div><a class="button secondary" href="/content-packs?persona_id=${encodeURIComponent(state.activePersonaId)}">Open ContentPack studio</a></div><div class="card-list">${state.references.map((pack) => { const canonical = (pack.items || []).filter((item) => item.canonical_selected).length; return `<article class="entity-card"><div><h3>${escapeHtml(pack.name || pack.pack_type)}</h3><p>${escapeHtml(pack.content_class || 'identity')} · ${pack.items?.length || 0} item(s)</p><div class="entity-meta">${badge(pack.review)}${pack.canonical_selected ? badge('canonical') : badge('not selected')}${badge(`${canonical} anchor(s)`)}</div></div><div class="entity-actions"><button class="button secondary" type="button" data-view="content-packs">Use in ContentPack flow</button></div></article>`; }).join('')}</div></section>`;
}

function renderContentPacks() {
  if (!state.activePersonaId) return emptyState('Select or create a Master Persona before managing ContentPacks.', 'personas');
  return `<section class="panel" aria-labelledby="content-heading"><div class="section-heading"><div><p class="eyebrow">Style + identity</p><h2 id="content-heading">ContentPacks for ${escapeHtml(activePersona()?.name || state.activePersonaId)}</h2></div><a class="button primary" href="/content-packs?persona_id=${encodeURIComponent(state.activePersonaId)}">Open authoring studio</a></div><p class="helper">The dedicated workspace creates pending packs from approved canonical ReferencePacks and keeps adult/glamour classes inside Identity Core.</p>${state.contentPacks.length ? `<div class="card-list">${state.contentPacks.map((pack) => `<article class="entity-card"><div><h3>${escapeHtml(pack.name)}</h3><p>${escapeHtml(pack.content_class)} · ${pack.items?.length || 0} linked anchor(s)</p><div class="entity-meta">${badge(pack.review)}${pack.identity_core ? badge('Identity Core') : ''}${badge(pack.identity_authority)}</div></div><div class="entity-actions"><a class="button secondary" href="/content-packs?persona_id=${encodeURIComponent(state.activePersonaId)}">Review</a></div></article>`).join('')}</div>` : emptyState('No ContentPacks have been created for this persona yet. Use the authoring studio to create one.')}</section>`;
}

function renderProduction() {
  if (!state.jobs.length) return emptyState('No production jobs are recorded yet.');
  return `<section class="panel" aria-labelledby="jobs-heading"><div class="section-heading"><div><p class="eyebrow">Execution lineage</p><h2 id="jobs-heading">Recent production jobs</h2></div></div><div class="table-wrap"><table><thead><tr><th>Job</th><th>Persona</th><th>Status</th><th>Version lineage</th></tr></thead><tbody>${state.jobs.map((job) => `<tr><td>${escapeHtml(job.id)}</td><td>${escapeHtml(job.persona_name || job.persona_id)}</td><td>${badge(job.status)}</td><td>${escapeHtml(job.lineage?.persona_version_id || 'not recorded')}</td></tr>`).join('')}</tbody></table></div></section>`;
}

function renderAssets() {
  if (!state.assets.length) return emptyState('No generated or imported assets are recorded yet.');
  return `<section class="panel" aria-labelledby="assets-heading"><div class="section-heading"><div><p class="eyebrow">Human review gate</p><h2 id="assets-heading">Recent assets</h2></div></div><div class="table-wrap"><table><thead><tr><th>Asset</th><th>Kind</th><th>Persona</th><th>Review</th><th>File</th></tr></thead><tbody>${state.assets.map((asset) => `<tr><td>${escapeHtml(asset.id)}</td><td>${escapeHtml(asset.kind)}</td><td>${escapeHtml(asset.persona_name || asset.persona_id)}</td><td>${badge(asset.review)}</td><td><a class="asset-link" href="/api/assets/${encodeURIComponent(asset.id)}/file" target="_blank" rel="noreferrer">Open media</a></td></tr>`).join('')}</tbody></table></div></section>`;
}

function renderPublishing() {
  const persona = activePersona();
  return `<section class="panel" aria-labelledby="publishing-heading"><div class="section-heading"><div><p class="eyebrow">Outbound control</p><h2 id="publishing-heading">Publishing readiness</h2></div>${badge('planned')}</div><div class="callout"><p><strong>Account-aware publishing is not connected yet.</strong></p><p class="helper">The future Instagram integration will require a persona-owned account, approved media, disclosure metadata, destination-policy checks, and an explicit publish action.</p></div><div class="card-list" style="margin-top: 16px"><div class="entity-card"><div><h3>Identity lineage</h3><p>${persona ? 'Active PersonaVersion is available for downstream checks.' : 'Select a Master Persona first.'}</p></div>${persona ? badge('ready') : badge('pending')}</div><div class="entity-card"><div><h3>Media approval</h3><p>Only approved assets may advance to publishing.</p></div>${badge('required')}</div><div class="entity-card"><div><h3>Platform account mapping</h3><p>Instagram account ownership and token storage remain a future implementation phase.</p></div>${badge('planned')}</div></div></section>`;
}

function renderView() {
  const renderer = { overview: renderOverview, personas: renderPersonasCanonical, references: renderReferences, 'content-packs': renderContentPacks, production: renderProduction, assets: renderAssets, publishing: renderPublishing }[state.view] || renderOverview;
  $('#workspace-view').innerHTML = renderer();
}

async function loadViewData() {
  state.controller?.abort();
  state.controller = new AbortController();
  const token = ++state.requestToken;
  const signal = state.controller.signal;
  renderNavigation();
  renderHeader();
  renderPersonaSelect();
  renderView();
  setStatus('Loading canonical workspace data…');
  try {
    const requests = { overview: [], personas: state.activePersonaId ? [`/api/personas/${encodeURIComponent(state.activePersonaId)}/versions`] : [], references: state.activePersonaId ? [`/api/personas/${encodeURIComponent(state.activePersonaId)}/reference-packs`] : [], 'content-packs': state.activePersonaId ? [`/api/personas/${encodeURIComponent(state.activePersonaId)}/content-packs`] : [], production: ['/api/jobs'], assets: ['/api/assets'], publishing: [] }[state.view] || [];
    const results = await Promise.all(requests.map((url) => get(url, { signal })));
    if (signal.aborted || token !== state.requestToken) return;
    if (state.view === 'references') state.references = Array.isArray(results[0]) ? results[0] : results[0]?.packs || [];
    if (state.view === 'content-packs') state.contentPacks = Array.isArray(results[0]) ? results[0] : results[0]?.content_packs || [];
    if (state.view === 'production') state.jobs = results[0] || [];
    if (state.view === 'assets') state.assets = results[0] || [];
    if (state.view === 'personas') state.versions = results[0] || [];
    renderView();
    setStatus('Canonical workspace ready.', 'success');
  } catch (error) {
    if (error.name === 'AbortError') return;
    setStatus(error.message, 'error');
  }
}

async function loadBase() {
  setStatus('Loading Master Personas…');
  try {
    const [personas, summary] = await Promise.all([get('/api/personas'), get('/api/summary')]);
    state.personas = Array.isArray(personas) ? personas : personas?.personas || [];
    state.summary = summary || {};
    const requested = new URLSearchParams(window.location.search).get('persona_id');
    const preferred = requested || state.activePersonaId;
    state.activePersonaId = state.personas.some((persona) => persona.id === preferred) ? preferred : (state.personas[0]?.id || '');
    renderPersonaSelect();
    renderView();
    await loadViewData();
  } catch (error) {
    setStatus(error.message, 'error');
    $('#workspace-view').innerHTML = emptyState('The canonical API could not load. Refresh after the local service is ready.');
  }
}

function navigate(view) {
  if (!viewMeta[view]) return;
  state.view = view;
  window.location.hash = view;
  loadViewData();
}

function showPersonaFormError(message) {
  const target = $('#persona-form-error');
  if (!target) return;
  target.textContent = message;
  target.hidden = !message;
}

async function createPersona(event) {
  event.preventDefault();
  const form = event.target;
  showPersonaFormError('');
  if (!form.reportValidity()) return;
  let characteristics;
  try {
    characteristics = JSON.parse(form.elements.characteristics.value || '{}');
    if (!characteristics || Array.isArray(characteristics) || typeof characteristics !== 'object') throw new Error('Characteristics must be a JSON object.');
  } catch (error) {
    showPersonaFormError(`Invalid characteristics JSON: ${error.message}`);
    return;
  }
  state.submittingPersona = true;
  renderView();
  try {
    const created = await post('/api/personas', {
      name: form.elements.name.value.trim(),
      age: Number(form.elements.age.value),
      description: form.elements.description.value.trim(),
      appearance: form.elements.appearance.value.trim(),
      disclosure: form.elements.disclosure.value.trim(),
      characteristics,
    });
    state.activePersonaId = created.id;
    setStatus(`Created ${created.name} with draft PersonaVersion ${created.current_version?.version_no || 1}.`, 'success');
    state.submittingPersona = false;
    await loadBase();
  } catch (error) {
    state.submittingPersona = false;
    renderView();
    setStatus(error.message, 'error');
    showPersonaFormError(error.message);
  }
}

async function freezePersona() {
  if (!state.activePersonaId || state.freezingPersona) return;
  const persona = activePersona();
  if (persona?.current_version?.state !== 'draft') return;
  state.freezingPersona = true;
  renderView();
  try {
    const result = await post(`/api/personas/${encodeURIComponent(state.activePersonaId)}/freeze`, {});
    state.freezingPersona = false;
    setStatus(`PersonaVersion ${result.frozen_version?.version_no || ''} is frozen and ready for lineage.`, 'success');
    await loadBase();
  } catch (error) {
    state.freezingPersona = false;
    renderView();
    setStatus(error.message, 'error');
  }
}

$('#workspace-nav').addEventListener('click', (event) => {
  const button = event.target.closest('[data-view]');
  if (button) navigate(button.dataset.view);
});
$('#workspace-view').addEventListener('click', (event) => {
  const personaButton = event.target.closest('[data-persona-id]');
  if (personaButton) {
    state.activePersonaId = personaButton.dataset.personaId;
    renderPersonaSelect();
    renderView();
    loadViewData();
    return;
  }
  const freezeButton = event.target.closest('[data-freeze-persona]');
  if (freezeButton) {
    freezePersona();
    return;
  }
  const button = event.target.closest('[data-view]');
  if (button) navigate(button.dataset.view);
});
$('#workspace-view').addEventListener('submit', (event) => {
  if (event.target.id === 'persona-create-form') createPersona(event);
});
$('#persona-select').addEventListener('change', (event) => {
  state.activePersonaId = event.target.value;
  loadViewData();
});
$('#refresh-button').addEventListener('click', loadBase);
window.addEventListener('hashchange', () => {
  const view = window.location.hash.slice(1);
  if (viewMeta[view] && view !== state.view) {
    state.view = view;
    loadViewData();
  }
});

const initialView = window.location.hash.slice(1);
if (viewMeta[initialView]) state.view = initialView;
loadBase();

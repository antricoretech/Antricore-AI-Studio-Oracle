import { get, put, post, patch } from './modules/api.js';

const navGroups = [
  { label: 'Identity', items: [
    ['overview', 'Overview', '⌂'],
    ['personas', 'Master Personas', '◎'],
    ['references', 'Reference Packs', '◇'],
    ['content-packs', 'ContentPacks', '◆'],
    ['creator', 'Creator System', 'C'],
    ['content-briefs', 'Content Briefs', 'B'],
    ['benchmarks', 'Identity Benchmarks', '◉'],
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
  creator: ['Creator System', 'Define personality, audience, voice, brand, and content pillars for one PersonaVersion.'],
  'content-briefs': ['Content Briefs', 'Turn the Creator System into approved, reusable production direction.'],
  benchmarks: ['Identity Benchmarks', 'Compare identity-conditioning methods against one frozen PersonaVersion.'],
  production: ['Production Queue', 'Track jobs and their PersonaVersion lineage.'],
  assets: ['Asset Review', 'Review generated and imported media before it becomes publishable.'],
  publishing: ['Publishing Readiness', 'Prepare approved, disclosed, policy-checked content for account delivery.'],
};

const CANONICAL_PERSONA_DRAFT_KEY = 'persona-studio.canonical-persona-draft.v1';
const CANONICAL_GENERATION_DRAFT_KEY = 'persona-studio.canonical-generation-draft.v1';

const state = {
  view: 'overview',
  personas: [],
  activePersonaId: '',
  summary: {},
  versions: [],
  references: [],
  referenceAssets: [],
  assetReferenceLinks: [],
  selectedReferencePackId: '',
  contentPacks: [],
  creatorProfile: null,
  savingCreatorProfile: false,
  contentBriefs: [],
  contentArtifacts: [],
  creatingContentBrief: false,
  creatingContentArtifact: false,
  assessingContentArtifact: '',
  approvingContentArtifact: '',
  editingContentArtifactId: '',
  approvingContentBrief: '',
  editingContentBriefId: '',
  benchmarkCatalog: { execution_status: 'deferred_final_gate', methods: [], scenarios: [] },
  benchmarks: [],
  creatingBenchmark: false,
  jobs: [],
  assets: [],
  assessingAssetId: '',
  savingAssetAssessment: '',
  assetPublishingReadiness: {},
  assetPlatformReadiness: {},
  publishingPolicies: null,
  publishingAccounts: [],
  publishingAssets: [],
  publishingArtifacts: [],
  selectedPublishingAssetId: '',
  selectedPublishingAccountId: '',
  selectedPublishingArtifactId: '',
  publishingReadiness: null,
  publishingResult: null,
  publishingBusy: false,
  verifyingPublishingAccountId: '',
  creatingPublishingAccount: false,
  workflows: [],
  preflight: null,
  preflightFingerprint: '',
  preflighting: false,
  submittingJob: false,
  generationDraft: { workflow_id: '', prompt: '', width: 768, height: 1152, content_pack_id: '', rights_confirmed: false },
  generationDraftImported: false,
  generationSourceModel: '',
  submittingPersona: false,
  personaDraft: null,
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

function readCanonicalPersonaDraft() {
  try {
    const raw = sessionStorage.getItem(CANONICAL_PERSONA_DRAFT_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(CANONICAL_PERSONA_DRAFT_KEY);
    const draft = JSON.parse(raw);
    return draft && typeof draft === 'object' && !Array.isArray(draft) ? draft : null;
  } catch (error) {
    console.warn('Canonical Persona draft could not be loaded:', error);
    return null;
  }
}

function readCanonicalGenerationDraft() {
  try {
    const raw = sessionStorage.getItem(CANONICAL_GENERATION_DRAFT_KEY);
    if (!raw) return null;
    sessionStorage.removeItem(CANONICAL_GENERATION_DRAFT_KEY);
    const draft = JSON.parse(raw);
    return draft && typeof draft === 'object' && !Array.isArray(draft) ? draft : null;
  } catch (error) {
    console.warn('Canonical generation draft could not be loaded:', error);
    return null;
  }
}

function badge(value) {
  const label = String(value || 'unknown');
  return `<span class="badge ${escapeHtml(label.toLowerCase())}">${escapeHtml(label)}</span>`;
}

function setStatus(message, tone = '') {
  const target = $('#workspace-status');
  target.textContent = message;
  target.className = `status ${tone}`.trim();
  target.setAttribute('role', tone === 'error' ? 'alert' : 'status');
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
  const draft = state.personaDraft || {};
  const draftCharacteristics = draft.characteristics || defaultCharacteristics;
  const draftCharacteristicsText = typeof draftCharacteristics === 'string'
    ? draftCharacteristics
    : JSON.stringify(draftCharacteristics, null, 2);
  return `<div class="panel-grid">
    <section class="panel" aria-labelledby="persona-create-heading">
      <div class="section-heading"><div><p class="eyebrow">Canonical identity</p><h2 id="persona-create-heading">Create Master Persona</h2></div>${badge('new structure')}</div>
      <p class="helper">This creates a new Persona and its initial draft PersonaVersion. Existing legacy personas are not reused.</p>
      ${state.personaDraft ? '<div class="callout"><p><strong>Draft imported from legacy Vault synthesis.</strong></p><p class="helper">Review and edit the identity anchors before creating the canonical Persona. No record or media job has been created yet.</p></div>' : ''}
      <form id="persona-create-form" class="persona-form">
        <div class="form-grid">
          <div class="field"><label for="persona-create-name">Name</label><input id="persona-create-name" name="name" minlength="2" maxlength="80" required placeholder="e.g. Mira Vale" value="${escapeHtml(draft.name || '')}"></div>
          <div class="field"><label for="persona-create-age">Age</label><input id="persona-create-age" name="age" type="number" min="18" max="110" required value="${escapeHtml(draft.age || 25)}"></div>
        </div>
        <div class="field"><label for="persona-create-description">Creator description</label><textarea id="persona-create-description" name="description" minlength="8" maxlength="1500" required placeholder="Who this fictional adult creator is and what she makes.">${escapeHtml(draft.description || '')}</textarea></div>
        <div class="field"><label for="persona-create-appearance">Appearance</label><textarea id="persona-create-appearance" name="appearance" minlength="8" maxlength="1500" required placeholder="Stable facial identity, hair, eyes, body, and visual traits.">${escapeHtml(draft.appearance || '')}</textarea></div>
        <div class="field"><label for="persona-create-disclosure">Disclosure</label><input id="persona-create-disclosure" name="disclosure" minlength="10" maxlength="250" required value="${escapeHtml(draft.disclosure || 'Fictional AI-generated adult persona')}"></div>
        <div class="field"><label for="persona-create-characteristics">Identity characteristics JSON <span class="field-hint">optional structured anchors</span></label><textarea id="persona-create-characteristics" name="characteristics" class="code-field" spellcheck="false">${escapeHtml(draftCharacteristicsText)}</textarea></div>
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

function renderReferencesLegacy() {
  if (!state.activePersonaId) return emptyState('Select or create a Master Persona before reviewing references.', 'personas');
  if (!state.references.length) return emptyState('No ReferencePacks are available for this PersonaVersion yet.');
  return `<section class="panel" aria-labelledby="references-heading"><div class="section-heading"><div><p class="eyebrow">Identity sources</p><h2 id="references-heading">ReferencePack review state</h2></div><a class="button secondary" href="/content-packs?persona_id=${encodeURIComponent(state.activePersonaId)}">Open ContentPack studio</a></div><div class="card-list">${state.references.map((pack) => { const canonical = (pack.items || []).filter((item) => item.canonical_selected).length; return `<article class="entity-card"><div><h3>${escapeHtml(pack.name || pack.pack_type)}</h3><p>${escapeHtml(pack.content_class || 'identity')} · ${pack.items?.length || 0} item(s)</p><div class="entity-meta">${badge(pack.review)}${pack.canonical_selected ? badge('canonical') : badge('not selected')}${badge(`${canonical} anchor(s)`)}</div></div><div class="entity-actions"><button class="button secondary" type="button" data-view="content-packs">Use in ContentPack flow</button></div></article>`; }).join('')}</div></section>`;
}

function reviewOption(value, selected) {
  return `<option value="${escapeHtml(value)}" ${value === selected ? 'selected' : ''}>${escapeHtml(value)}</option>`;
}

function referenceAssetOptions(item) {
  const assets = state.referenceAssets.filter((asset) => asset.persona_id === state.activePersonaId && asset.kind === 'image');
  const current = item.asset_id ? `<option value="${escapeHtml(item.asset_id)}" selected>Keep current linked asset · ${escapeHtml(item.asset_id)}</option>` : '<option value="">Select an image asset</option>';
  return `${current}${assets.filter((asset) => asset.id !== item.asset_id).map((asset) => `<option value="${escapeHtml(asset.id)}">${escapeHtml(asset.id)} · ${escapeHtml(asset.filename || 'image')} · ${escapeHtml(asset.review || 'pending')}</option>`).join('')}`;
}

function referenceLineage(item, pack) {
  if (!item.asset_id) return { state: 'missing', label: 'missing asset', detail: 'No image asset is linked to this reference item.' };
  if (item.asset_review !== 'approved') {
    const review = item.asset_review || 'pending';
    return { state: review === 'rejected' ? 'rejected' : 'stale', label: `asset ${review}`, detail: `Linked asset is ${review}; approve it in Asset Review before reuse.` };
  }
  if (!item.asset_persona_version_id || item.asset_persona_version_id !== pack.persona_version_id) {
    return { state: 'mismatch', label: 'version mismatch', detail: `Linked asset belongs to ${item.asset_persona_version_id || 'an unknown PersonaVersion'}, but this pack belongs to ${pack.persona_version_id || 'an unknown PersonaVersion'}.` };
  }
  if (item.review !== 'approved') {
    const review = item.review || 'pending';
    return { state: review === 'rejected' ? 'rejected' : 'blocked', label: `item ${review}`, detail: `Reference item review is ${review}; it cannot be a canonical anchor yet.` };
  }
  if (!item.rights_confirmed) return { state: 'blocked', label: 'rights required', detail: 'Confirm rights for this reference item before canonical selection.' };
  if (!item.canonical_eligible) return { state: 'blocked', label: 'not eligible', detail: 'This reference item is not marked eligible for canonical identity use.' };
  return { state: 'ready', label: 'lineage ready', detail: 'Approved asset, item review, rights, and PersonaVersion lineage are aligned.' };
}

function packLineageSummary(pack) {
  const items = pack.items || [];
  const statuses = items.map((item) => referenceLineage(item, pack));
  return {
    ready: statuses.filter((status) => status.state === 'ready').length,
    stale: statuses.filter((status) => status.state !== 'ready').length,
    staleCanonical: items.filter((item, index) => item.canonical_selected && statuses[index].state !== 'ready').length,
  };
}

function assetReferenceLinks(asset) {
  const links = [];
  state.assetReferenceLinks.forEach((pack) => {
    (pack.items || []).forEach((item) => {
      if (item.asset_id === asset.id) links.push({ pack, item, lineage: referenceLineage(item, pack) });
    });
  });
  return links;
}

function contentPackAnchorSummary(pack) {
  const items = pack.items || [];
  const stale = items.filter((item) => !item.asset_id || item.asset_review !== 'approved' || item.asset_persona_version_id !== pack.persona_version_id);
  return { total: items.length, stale: stale.length, ready: items.length - stale.length };
}

function renderCrossViewLineageNotice() {
  if (state.view === 'content-packs') {
    const stalePacks = state.contentPacks.filter((pack) => contentPackAnchorSummary(pack).stale > 0);
    if (stalePacks.length) return `<div class="callout stale-callout"><p><strong>Stale anchor warning:</strong> ${stalePacks.length} ContentPack(s) contain an unapproved, missing, or PersonaVersion-mismatched anchor. Review them before reuse.</p></div>`;
  }
  if (state.view === 'assets') {
    const linked = state.assets.flatMap((asset) => assetReferenceLinks(asset));
    const stale = linked.filter((link) => link.lineage.state !== 'ready');
    if (stale.length) return `<div class="callout stale-callout"><p><strong>Stale lineage warning:</strong> ${stale.length} ReferencePack linkage(s) are not currently reusable. Rejected, pending, missing, rights-blocked, or PersonaVersion-mismatched assets cannot become canonical anchors.</p></div>`;
  }
  return '';
}

function renderAssetLineagePanel() {
  if (state.view !== 'assets') return '';
  const linkedAssets = state.assets.filter((asset) => assetReferenceLinks(asset).length);
  if (!linkedAssets.length) return '';
  return `<section class="panel lineage-panel" aria-labelledby="asset-lineage-heading"><div class="section-heading"><div><p class="eyebrow">Canonical linkage</p><h2 id="asset-lineage-heading">Reference linkage</h2></div>${badge(`${linkedAssets.length} linked asset${linkedAssets.length === 1 ? '' : 's'}`)}</div><p class="helper">These links are evaluated against the active PersonaVersion. A link may exist in storage while still being stale or blocked for canonical reuse.</p><div class="asset-lineage-list">${linkedAssets.map((asset) => `<article class="entity-card"><div><h3>${escapeHtml(asset.filename || asset.id)}</h3><p>${escapeHtml(asset.id)} · ${escapeHtml(asset.persona_version_id || 'unknown PersonaVersion')}</p><div class="entity-meta">${assetReferenceLinks(asset).map((link) => badge(`${link.pack.name || link.pack.pack_type}: ${link.lineage.label}`)).join('')}</div><div class="lineage-detail-list">${assetReferenceLinks(asset).map((link) => `<div class="lineage-status ${escapeHtml(link.lineage.state)}" data-lineage-state="${escapeHtml(link.lineage.state)}"><span>${escapeHtml(link.item.label || link.item.id)} · ${escapeHtml(link.lineage.detail)}</span></div>`).join('')}</div></div></article>`).join('')}</div></section>`;
}

function renderReferenceItem(pack, item) {
  const lineage = referenceLineage(item, pack);
  const canonicalEligible = lineage.state === 'ready';
  return `<article class="reference-item">
    <div class="reference-item-heading"><div><h3>${escapeHtml(item.label || item.id)}</h3><p class="helper">${escapeHtml(item.role || 'supporting_reference')} · ${escapeHtml(item.content_class || pack.content_class || 'identity')}</p></div>${badge(item.review)}${item.canonical_selected ? badge('canonical') : ''}</div>
    <div class="entity-meta">${item.asset_id ? badge(`asset ${item.asset_id}`) : badge('asset not linked')}${item.rights_confirmed ? badge('rights confirmed') : badge('rights required')}${item.canonical_eligible ? badge('eligible') : badge('not eligible')}</div>
    <div class="lineage-status ${escapeHtml(lineage.state)}" data-lineage-state="${escapeHtml(lineage.state)}">${badge(lineage.label)} <span>${escapeHtml(lineage.detail)}${item.canonical_selected && !canonicalEligible ? ' Existing canonical selection has been invalidated by this state.' : ''}</span></div>
    <div class="reference-controls">
      <form class="inline-form" data-reference-item-review="${escapeHtml(item.id)}" data-reference-pack-id="${escapeHtml(pack.id)}">
        <label>Review<select name="review">${reviewOption('pending', item.review)}${reviewOption('approved', item.review)}${reviewOption('rejected', item.review)}</select></label>
        <label class="check-field"><input type="checkbox" name="rights_confirmed" ${item.rights_confirmed ? 'checked' : ''}> Rights confirmed</label>
        <button class="button secondary" type="submit">Save item</button>
      </form>
      <form class="inline-form" data-reference-item-asset="${escapeHtml(item.id)}" data-reference-pack-id="${escapeHtml(pack.id)}">
        <label>Linked image asset<select name="asset_id">${referenceAssetOptions(item)}</select></label>
        <button class="button secondary" type="submit">Link asset</button>
      </form>
    </div>
    <p class="helper">${canonicalEligible ? 'This item can become a canonical identity anchor.' : 'Canonical selection requires approved item review, confirmed rights, a linked approved image, and matching PersonaVersion lineage.'}</p>
  </article>`;
}

function renderReferencesCanonical() {
  if (!state.activePersonaId) return emptyState('Select or create a Master Persona before reviewing references.', 'personas');
  if (!state.references.length) return emptyState('No ReferencePacks are available for this PersonaVersion yet.');
  const selectedPack = state.references.find((pack) => pack.id === state.selectedReferencePackId) || state.references[0];
  const eligibleItems = (selectedPack.items || []).filter((item) => referenceLineage(item, selectedPack).state === 'ready');
  const packRights = (selectedPack.items || []).length > 0 && selectedPack.items.every((item) => item.rights_confirmed);
  const selectedSummary = packLineageSummary(selectedPack);
  return `<section class="panel" aria-labelledby="references-heading">
    <div class="section-heading"><div><p class="eyebrow">Identity sources</p><h2 id="references-heading">Review ReferencePacks</h2></div><a class="button secondary" href="/content-packs?persona_id=${encodeURIComponent(state.activePersonaId)}">Open ContentPack studio</a></div>
    <p class="helper">Review every item, confirm rights, link the correct PersonaVersion image asset, then explicitly select canonical identity anchors. Adult/glamour packs follow the same review gates and remain eligible to become Identity Core anchors.</p>
    <div class="lineage-overview" aria-label="ReferencePack lineage summary">${state.references.map((pack) => { const summary = packLineageSummary(pack); return `<span>${escapeHtml(pack.name || pack.pack_type)}: ${summary.ready} ready, ${summary.stale} stale${summary.staleCanonical ? `, ${summary.staleCanonical} selected anchor(s) invalidated` : ''}</span>`; }).join('')}</div>
    <div class="reference-pack-grid"><div class="card-list">${state.references.map((pack) => { const canonical = (pack.items || []).filter((item) => item.canonical_selected).length; return `<article class="entity-card ${pack.id === selectedPack.id ? 'selected-entity' : ''}"><div><h3>${escapeHtml(pack.name || pack.pack_type)}</h3><p>${escapeHtml(pack.content_class || 'identity')} · ${pack.items?.length || 0} item(s)</p><div class="entity-meta">${badge(pack.review)}${pack.canonical_selected ? badge('canonical') : badge('not selected')}${badge(`${canonical} anchor(s)`)}</div></div><div class="entity-actions"><button class="button secondary" type="button" data-reference-pack-id="${escapeHtml(pack.id)}">${pack.id === selectedPack.id ? 'Selected' : 'Review pack'}</button></div></article>`; }).join('')}</div>
      <div class="reference-detail">
        <div class="section-heading"><div><p class="eyebrow">Selected pack</p><h2>${escapeHtml(selectedPack.name || selectedPack.pack_type)}</h2></div>${badge(selectedPack.review)}</div>
        <div class="callout"><p><strong>Authority:</strong> ${escapeHtml(selectedPack.identity_authority || 'identity')}</p><p><strong>PersonaVersion:</strong> ${escapeHtml(selectedPack.persona_version_id || 'not linked')}</p><p><strong>Lineage summary:</strong> ${selectedSummary.ready} ready, ${selectedSummary.stale} stale or blocked item(s).</p><p><strong>Canonical status:</strong> ${selectedPack.canonical_selected ? `${selectedSummary.staleCanonical ? `${selectedSummary.staleCanonical} selected anchor(s) stale; ` : ''}selected anchors are active for this pack.` : 'No canonical anchors selected.'}</p></div>
        <form class="pack-review-form" data-reference-pack-review="${escapeHtml(selectedPack.id)}">
          <label>Pack review<select name="review">${reviewOption('pending', selectedPack.review)}${reviewOption('approved', selectedPack.review)}${reviewOption('rejected', selectedPack.review)}</select></label>
          <label class="check-field"><input type="checkbox" name="rights_confirmed" ${packRights ? 'checked' : ''}> Confirm rights for all items</label>
          <button class="button primary" type="submit">Save pack review</button>
        </form>
        <div class="reference-items"><div class="section-heading"><div><p class="eyebrow">Pack contents</p><h3>Reference items</h3></div>${badge(`${selectedPack.items?.length || 0} items`)}</div>${selectedPack.items?.length ? selectedPack.items.map((item) => renderReferenceItem(selectedPack, item)).join('') : emptyState('This pack has no items to review.')}</div>
        <form class="canonical-form" data-reference-canonical="${escapeHtml(selectedPack.id)}">
          <div class="section-heading"><div><p class="eyebrow">Canonical selection</p><h3>Identity anchors</h3></div>${badge(`${eligibleItems.length} eligible`)}</div>
          <p class="helper">Choose one or more eligible items. Selection is explicit and can be cleared; review changes automatically invalidate stale canonical state.</p>
          <div class="canonical-options">${eligibleItems.length ? eligibleItems.map((item) => `<label class="canonical-option"><input type="checkbox" name="item_ids" value="${escapeHtml(item.id)}" ${item.canonical_selected ? 'checked' : ''}> ${escapeHtml(item.label || item.id)}</label>`).join('') : emptyState('No items are eligible yet. Complete item review, rights confirmation, asset linkage, and asset approval first.')}</div>
          <div class="form-actions"><button class="button primary" type="submit" ${selectedPack.review === 'approved' && eligibleItems.length ? '' : 'disabled'}>Select canonical anchors</button><button class="button secondary" type="button" data-clear-reference-canonical="${escapeHtml(selectedPack.id)}" ${selectedPack.canonical_selected ? '' : 'disabled'}>Clear selection</button></div>
        </form>
      </div>
    </div>
  </section>`;
}

function renderContentPacks() {
  if (!state.activePersonaId) return emptyState('Select or create a Master Persona before managing ContentPacks.', 'personas');
  return `<section class="panel" aria-labelledby="content-heading"><div class="section-heading"><div><p class="eyebrow">Style + identity</p><h2 id="content-heading">ContentPacks for ${escapeHtml(activePersona()?.name || state.activePersonaId)}</h2></div><a class="button primary" href="/content-packs?persona_id=${encodeURIComponent(state.activePersonaId)}">Open authoring studio</a></div><p class="helper">The dedicated workspace creates pending packs from approved canonical ReferencePacks and keeps adult/glamour classes inside Identity Core.</p>${state.contentPacks.length ? `<div class="card-list">${state.contentPacks.map((pack) => `<article class="entity-card"><div><h3>${escapeHtml(pack.name)}</h3><p>${escapeHtml(pack.content_class)} · ${pack.items?.length || 0} linked anchor(s)</p><div class="entity-meta">${badge(pack.review)}${pack.identity_core ? badge('Identity Core') : ''}${badge(pack.identity_authority)}</div></div><div class="entity-actions"><a class="button secondary" href="/content-packs?persona_id=${encodeURIComponent(state.activePersonaId)}">Review</a></div></article>`).join('')}</div>` : emptyState('No ContentPacks have been created for this persona yet. Use the authoring studio to create one.')}</section>`;
}

function renderProductionLegacy() {
  if (!state.jobs.length) return emptyState('No production jobs are recorded yet.');
  return `<section class="panel" aria-labelledby="jobs-heading"><div class="section-heading"><div><p class="eyebrow">Execution lineage</p><h2 id="jobs-heading">Recent production jobs</h2></div></div><div class="table-wrap"><table><thead><tr><th>Job</th><th>Persona</th><th>Status</th><th>Version lineage</th></tr></thead><tbody>${state.jobs.map((job) => `<tr><td>${escapeHtml(job.id)}</td><td>${escapeHtml(job.persona_name || job.persona_id)}</td><td>${badge(job.status)}</td><td>${escapeHtml(job.lineage?.persona_version_id || 'not recorded')}</td></tr>`).join('')}</tbody></table></div></section>`;
}

function renderGenerationForm() {
  const readyWorkflows = state.workflows.filter((workflow) => workflow.ready);
  if (!state.generationDraft.workflow_id && readyWorkflows[0]) state.generationDraft.workflow_id = readyWorkflows[0].id;
  const draft = state.generationDraft;
  const selectedWorkflow = state.workflows.find((workflow) => workflow.id === draft.workflow_id);
  const preflightChecks = state.preflight?.checks || [];
  return `<section class="panel" aria-labelledby="generation-heading">
    <div class="section-heading"><div><p class="eyebrow">Controlled generation</p><h2 id="generation-heading">Author a generation request</h2></div>${state.preflight ? badge(`preflight ${state.preflight.overall}`) : badge('preflight required')}</div>
    <p class="helper">Select a locally verified workflow, describe the scene, and run the read-only preflight before queueing. Catalog recipes remain visible but cannot be queued until their verified graph and required model are installed.</p>
    ${state.generationDraftImported ? `<div class="callout"><p><strong>Draft imported from legacy Orchestrator.</strong></p><p class="helper">Review the prompt, confirm rights, select an approved ContentPack if needed, and run preflight before queueing. Requested legacy model: ${escapeHtml(state.generationSourceModel || 'not recorded')}.</p></div>` : ''}
    <form id="generation-form" class="generation-form">
      <div class="form-grid generation-grid">
        <div class="field"><label for="generation-workflow">Verified workflow</label><select id="generation-workflow" name="workflow_id" required>${state.workflows.length ? state.workflows.map((workflow) => `<option value="${escapeHtml(workflow.id)}" ${workflow.id === draft.workflow_id ? 'selected' : ''} ${workflow.ready ? '' : 'disabled'}>${escapeHtml(workflow.label || workflow.id)} · ${workflow.ready ? 'ready' : 'catalog / not installed'}</option>`).join('') : '<option value="">No workflow catalog entries available</option>'}</select></div>
        <div class="field"><label for="generation-content-pack">ContentPack <span class="field-hint">optional</span></label><select id="generation-content-pack" name="content_pack_id"><option value="">Use approved canonical anchors</option>${state.contentPacks.map((pack) => `<option value="${escapeHtml(pack.id)}" ${pack.id === draft.content_pack_id ? 'selected' : ''} ${pack.review === 'approved' ? '' : 'disabled'}>${escapeHtml(pack.name)} · ${escapeHtml(pack.review)}</option>`).join('')}</select></div>
      </div>
      <div class="field"><label for="generation-prompt">Prompt</label><textarea id="generation-prompt" name="prompt" minlength="5" maxlength="3000" required placeholder="Describe the approved, disclosed scene to generate.">${escapeHtml(draft.prompt)}</textarea></div>
      <div class="form-grid generation-dimensions"><div class="field"><label for="generation-width">Width</label><input id="generation-width" name="width" type="number" min="256" max="2048" step="8" value="${escapeHtml(draft.width)}" required></div><div class="field"><label for="generation-height">Height</label><input id="generation-height" name="height" type="number" min="256" max="2048" step="8" value="${escapeHtml(draft.height)}" required></div><label class="check-field generation-rights"><input type="checkbox" name="rights_confirmed" ${draft.rights_confirmed ? 'checked' : ''}> Rights and likeness confirmed</label></div>
      <div class="form-actions"><button class="button secondary" type="button" data-generation-action="preflight" ${state.preflighting ? 'disabled' : ''}>${state.preflighting ? 'Checking…' : 'Run preflight'}</button><button class="button primary" type="submit" ${state.submittingJob || state.preflight?.overall !== 'ready' ? 'disabled' : ''}>${state.submittingJob ? 'Queueing…' : 'Queue generation'}</button></div>
      ${preflightChecks.length ? `<div class="preflight-results" role="status"><div class="section-heading"><div><p class="eyebrow">Read-only validation</p><h3>Preflight checks</h3></div>${badge(state.preflight.overall)}</div>${preflightChecks.map((check) => `<div class="preflight-row"><span>${escapeHtml(check.id)}</span><span>${escapeHtml(check.detail || check.status)}</span>${badge(check.status)}</div>`).join('')}</div>` : `<p class="helper">${selectedWorkflow ? `Selected: ${escapeHtml(selectedWorkflow.label || selectedWorkflow.id)}${selectedWorkflow.requires_reference ? ' · reference input required' : ''}` : 'Choose a verified workflow before running preflight.'}</p>`}
    </form>
  </section>`;
}

function renderJobProgress(job) {
  const percent = Math.max(0, Math.min(100, Number(job.progress_percent || 0)));
  const progress = job.progress || {};
  const children = Array.isArray(progress.children) ? progress.children : [];
  return `<div class="job-progress" aria-label="Job progress"><div class="job-progress-heading"><strong>${escapeHtml(job.progress_stage || job.status || 'queued')}</strong><span>${percent}%</span></div><div class="job-progress-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}" aria-label="${escapeHtml(job.progress_stage || 'Job')} progress"><span style="width:${percent}%"></span></div>${job.progress_detail ? `<p class="helper">${escapeHtml(job.progress_detail)}</p>` : ''}${children.length ? `<ul class="job-child-progress">${children.map((child) => `<li><span>${escapeHtml(child.label || child.id || 'Output')}</span>${badge(child.state || 'queued')}<span>${escapeHtml(child.percent || 0)}%</span></li>`).join('')}</ul>` : ''}</div>`;
}

function renderProductionCanonical() {
  const persona = activePersona();
  const version = persona?.current_version;
  const activeJobs = state.jobs.filter((job) => ['queued', 'running', 'submitted', 'cancelling'].includes(job.status)).length;
  return `${renderGenerationForm()}<div class="panel-grid">
    <section class="panel" aria-labelledby="readiness-heading">
      <div class="section-heading"><div><p class="eyebrow">Generation readiness</p><h2 id="readiness-heading">Before a job starts</h2></div>${badge(activeJobs ? `${activeJobs} active` : 'idle')}</div>
      <p class="helper">Queueing remains subject to the canonical backend gates. This panel makes the prerequisites visible without installing or selecting generation models.</p>
      <div class="readiness-grid">
        <div class="readiness-item"><div><strong>Master Persona</strong><span>${persona ? escapeHtml(persona.name) : 'Select a persona'}</span></div>${persona ? badge('ready') : badge('required')}</div>
        <div class="readiness-item"><div><strong>PersonaVersion</strong><span>${version ? `${escapeHtml(version.id)} · ${escapeHtml(version.state)}` : 'Create a PersonaVersion'}</span></div>${version ? badge('lineage ready') : badge('required')}</div>
        <div class="readiness-item"><div><strong>Rights and disclosure</strong><span>Every job must confirm likeness/input rights and carry disclosure metadata.</span></div>${badge('required')}</div>
        <div class="readiness-item"><div><strong>Model installation gate</strong><span>Image, audio, and video models remain deferred until final installation.</span></div>${badge('deferred')}</div>
      </div>
      <div class="callout readiness-callout"><p><strong>Generation action status:</strong> The canonical job API is available for approved workflows and assets; a dedicated authoring form will be added after queue observability is verified.</p><p class="helper">Use ReferencePack, ContentPack, and Asset Review first so identity anchors and media approvals are explicit.</p></div>
    </section>
    <section class="panel" aria-labelledby="queue-summary-heading">
      <div class="section-heading"><div><p class="eyebrow">Queue summary</p><h2 id="queue-summary-heading">Production Queue</h2></div>${badge(`${state.jobs.length} recorded`)}</div>
      <div class="queue-summary"><div><strong>${activeJobs}</strong><span>active</span></div><div><strong>${state.jobs.filter((job) => job.status === 'completed').length}</strong><span>completed</span></div><div><strong>${state.jobs.filter((job) => ['failed', 'interrupted'].includes(job.status)).length}</strong><span>failed</span></div></div>
    </section>
  </div>
  <section class="panel" aria-labelledby="jobs-heading">
    <div class="section-heading"><div><p class="eyebrow">Execution lineage</p><h2 id="jobs-heading">Recent jobs</h2></div></div>
    ${state.jobs.length ? `<div class="job-list">${state.jobs.map((job) => `<article class="job-card">
      <div class="job-heading"><div><h3>${escapeHtml(job.workflow_id || job.id)}</h3><p class="helper">${escapeHtml(job.id)} · ${escapeHtml(job.persona_name || job.persona_id)} · attempt ${escapeHtml(job.attempt || 1)}</p></div><div class="entity-meta">${badge(job.status)}${badge(job.type || 'job')}</div></div>
      <p class="job-prompt">${escapeHtml(job.prompt || 'No prompt recorded.')}</p>
      ${renderJobProgress(job)}
      <div class="entity-meta">${badge(`PersonaVersion ${job.lineage?.persona_version_id || 'not recorded'}`)}${job.lineage?.content_pack_id ? badge(`ContentPack ${job.lineage.content_pack_id}`) : ''}${job.lineage?.source_asset_id ? badge(`source ${job.lineage.source_asset_id}`) : ''}</div>
      ${job.error ? `<p class="job-error">${escapeHtml(job.error)}</p>` : ''}
      <div class="job-actions">${['queued', 'running', 'submitted', 'cancelling'].includes(job.status) ? `<button class="button secondary" type="button" data-job-action="cancel" data-job-id="${escapeHtml(job.id)}">Cancel job</button>` : ''}${['failed', 'interrupted', 'cancelled'].includes(job.status) ? `<button class="button secondary" type="button" data-job-action="retry" data-job-id="${escapeHtml(job.id)}">Retry job</button>` : ''}</div>
    </article>`).join('')}</div>` : emptyState('No production jobs are recorded yet. Generation will appear here after a canonical job is queued.')}
  </section>`;
}

function generationPreflightFingerprint(draft) {
  return JSON.stringify({
    workflow_id: draft?.workflow_id || '',
    width: Number(draft?.width || 0),
    height: Number(draft?.height || 0),
  });
}

function renderAssetsLegacy() {
  if (!state.assets.length) return emptyState('No generated or imported assets are recorded yet.');
  return `<section class="panel" aria-labelledby="assets-heading"><div class="section-heading"><div><p class="eyebrow">Human review gate</p><h2 id="assets-heading">Recent assets</h2></div></div><div class="table-wrap"><table><thead><tr><th>Asset</th><th>Kind</th><th>Persona</th><th>Review</th><th>File</th></tr></thead><tbody>${state.assets.map((asset) => `<tr><td>${escapeHtml(asset.id)}</td><td>${escapeHtml(asset.kind)}</td><td>${escapeHtml(asset.persona_name || asset.persona_id)}</td><td>${badge(asset.review)}</td><td><a class="asset-link" href="/api/assets/${encodeURIComponent(asset.id)}/file" target="_blank" rel="noreferrer">Open media</a></td></tr>`).join('')}</tbody></table></div></section>`;
}

function renderAssetQuality(asset) {
  const checks = Array.isArray(asset.quality?.checks) ? asset.quality.checks : [];
  if (!checks.length) return '<p class="helper">Quality checks not recorded yet.</p>';
  return `<div class="artifact-quality-checks" aria-label="Asset quality checks">${checks.map((check) => `<div class="artifact-quality-check"><span>${escapeHtml(check.id || 'check')}</span>${badge(check.status || 'unknown')}<small>${escapeHtml(check.detail || '')}</small></div>`).join('')}</div>`;
}

function renderAssetAssessment(asset) {
  const scores = asset.quality?.assessment?.scores || {};
  const score = (key) => scores[key] === undefined ? '' : escapeHtml(scores[key]);
  return `<form class="asset-assessment-form" data-asset-assessment="${escapeHtml(asset.id)}"><p class="eyebrow">Quality assessment</p><div class="form-grid"><label>Identity <input name="identity_score" type="number" min="0" max="1" step="0.01" value="${score('identity_score')}" placeholder="0–1"></label><label>Anatomy <input name="anatomy_score" type="number" min="0" max="1" step="0.01" value="${score('anatomy_score')}" placeholder="0–1"></label><label>Hands <input name="hands_score" type="number" min="0" max="1" step="0.01" value="${score('hands_score')}" placeholder="0–1"></label><label>Facial drift <input name="facial_drift_score" type="number" min="0" max="1" step="0.01" value="${score('facial_drift_score')}" placeholder="0–1"></label><label>Temporal stability <input name="temporal_stability_score" type="number" min="0" max="1" step="0.01" value="${score('temporal_stability_score')}" placeholder="video only"></label><label>Audio timing <input name="audio_timing_score" type="number" min="0" max="1" step="0.01" value="${score('audio_timing_score')}" placeholder="optional"></label><label>Evaluator <input name="evaluator" maxlength="120" value="${escapeHtml(asset.quality?.assessment?.evaluator || 'local_operator')}" required></label><label class="span-2">Notes <textarea name="notes" rows="2" maxlength="2000" placeholder="Record manual findings or evaluator context.">${escapeHtml(asset.quality?.assessment?.notes || '')}</textarea></label></div><button class="button secondary" type="submit" ${state.savingAssetAssessment === asset.id ? 'disabled' : ''}>${state.savingAssetAssessment === asset.id ? 'Saving assessment…' : 'Save assessment'}</button></form>`;
}

function renderAssetPublishingReadiness(asset) {
  const report = state.assetPublishingReadiness[asset.id];
  if (!report) return '';
  return `<div class="callout ${report.ready ? '' : 'stale-callout'}" aria-live="polite"><p><strong>Publishing readiness:</strong> ${badge(report.status)}</p><div class="entity-meta">${report.checks.map((check) => badge(`${check.id}: ${check.status}`)).join('')}</div></div>`;
}

function renderAssetPlatformReadiness(asset) {
  const report = state.assetPlatformReadiness[asset.id];
  if (!report) return '';
  const platform = report.platform_readiness || {};
  return `<div class="callout ${platform.ready ? '' : 'stale-callout'}" aria-live="polite"><p><strong>${escapeHtml(platform.platform || 'Platform')} readiness (${escapeHtml(platform.format || 'format')}):</strong> ${badge(platform.status || 'blocked')}</p><p class="helper">${escapeHtml(platform.execution_status || 'local policy evaluation')}</p><div class="artifact-quality-checks" aria-label="Platform readiness checks">${(platform.checks || []).map((check) => `<div class="artifact-quality-check"><span>${escapeHtml(check.id || 'check')}</span>${badge(check.status || 'unknown')}<small>${escapeHtml(check.detail || '')}</small></div>`).join('')}</div></div>`;
}

function renderAssetsCanonical() {
  return `<section class="panel" aria-labelledby="assets-heading">
    <div class="section-heading"><div><p class="eyebrow">Human review gate</p><h2 id="assets-heading">Asset Review</h2></div>${badge(`${state.assets.length} asset${state.assets.length === 1 ? '' : 's'}`)}</div>
    <p class="helper">Generated and imported media remain pending until an explicit review decision. Approval is required before canonical anchoring, export, or publishing.</p>
    ${state.assets.length ? `<div class="asset-review-list">${state.assets.map((asset) => `<article class="asset-review-card">
      <div class="asset-review-summary"><div><p class="eyebrow">${escapeHtml(asset.kind || 'media')}</p><h3>${escapeHtml(asset.filename || asset.id)}</h3><p class="helper">${escapeHtml(asset.id)} · ${escapeHtml(asset.persona_name || asset.persona_id)} · PersonaVersion ${escapeHtml(asset.persona_version_id || 'not recorded')}</p></div><div class="entity-meta">${badge(asset.review)}${badge(asset.quality?.status || 'quality pending')}${asset.rights_confirmed ? badge('rights confirmed') : badge('rights required')}</div></div>
      <div class="asset-review-meta"><span>${escapeHtml(asset.prompt || 'No generation/import description recorded.')}</span><span>${asset.disclosure ? `Disclosure: ${escapeHtml(asset.disclosure)}` : 'Disclosure not recorded'}</span></div>
      ${renderAssetQuality(asset)}
      ${renderAssetAssessment(asset)}
      ${renderAssetPublishingReadiness(asset)}
      ${renderAssetPlatformReadiness(asset)}
      ${asset.reviewed_at ? `<p class="helper">Reviewed by ${escapeHtml(asset.reviewer || 'local operator')} at ${escapeHtml(asset.reviewed_at)}: ${escapeHtml(asset.review_reason || 'No reason recorded.')}</p>` : '<p class="helper">Review evidence has not been recorded yet.</p>'}
      <div class="asset-review-actions"><form class="inline-form" data-asset-review="${escapeHtml(asset.id)}"><label>Review<select name="review">${reviewOption('pending', asset.review)}${reviewOption('approved', asset.review)}${reviewOption('rejected', asset.review)}</select></label><label>Reviewer<input name="reviewer" maxlength="120" value="${escapeHtml(asset.reviewer || 'local_operator')}" required></label><label>Reason<input name="reason" maxlength="1000" value="${escapeHtml(asset.review_reason || '')}" placeholder="Why is this decision being made?" required></label><button class="button primary" type="submit">Save review</button></form><button class="button secondary" type="button" data-asset-quality="${escapeHtml(asset.id)}" ${state.assessingAssetId === asset.id ? 'disabled' : ''}>${state.assessingAssetId === asset.id ? 'Refreshing quality…' : 'Refresh quality'}</button><button class="button secondary" type="button" data-asset-publishing-readiness="${escapeHtml(asset.id)}">Check publishing readiness</button><button class="button secondary" type="button" data-asset-platform-readiness="${escapeHtml(asset.id)}">Check Instagram readiness</button><a class="button secondary" href="/api/assets/${encodeURIComponent(asset.id)}/file" target="_blank" rel="noreferrer">Open media</a>${asset.review === 'approved' ? `<a class="button secondary" href="/api/assets/${encodeURIComponent(asset.id)}/package" target="_blank" rel="noreferrer">Export package</a>` : ''}</div>
    </article>`).join('')}</div>` : emptyState('No generated or imported assets are recorded yet. Assets will appear here after an import or generation job.')}
  </section>`;
}

function benchmarkValue(value, suffix = '') {
  if (value === null || value === undefined || value === '') return '—';
  return `${escapeHtml(value)}${suffix}`;
}

function renderBenchmarkSummary(summary) {
  if (!summary?.length) return emptyState('No benchmark results have been recorded yet. Complete cases after the approved local runtime is available.');
  return `<div class="table-wrap benchmark-summary"><table><caption>Identity-conditioning method comparison</caption><thead><tr><th scope="col">Method</th><th scope="col">Coverage</th><th scope="col">Score</th><th scope="col">Identity</th><th scope="col">Latency</th><th scope="col">Selection</th></tr></thead><tbody>${summary.map((item) => `<tr><th scope="row">${escapeHtml(item.label || item.method)}</th><td class="tabular-nums">${escapeHtml(item.completed_cases)}/${escapeHtml(item.total_cases)} (${escapeHtml(Math.round((item.coverage || 0) * 100))}%)</td><td class="tabular-nums">${benchmarkValue(item.mean_score)}</td><td class="tabular-nums">${benchmarkValue(item.mean_identity_score)}</td><td class="tabular-nums">${benchmarkValue(item.mean_latency_ms, ' ms')}</td><td>${badge(item.selection_status)}</td></tr>`).join('')}</tbody></table></div>`;
}

function renderBenchmarkCase(benchmark, item) {
  const terminal = ['completed', 'blocked', 'failed'].includes(item.status);
  return `<article class="benchmark-case"><div class="section-heading"><div><p class="eyebrow">${escapeHtml(item.method)}</p><h3>${escapeHtml(item.scenario_label)}</h3><p class="helper">${escapeHtml(item.content_class)} · ${escapeHtml(item.scenario_id)}</p></div>${badge(item.status)}</div><p class="benchmark-prompt">${escapeHtml(item.prompt)}</p>${item.error ? `<p class="job-error">${escapeHtml(item.error)}</p>` : ''}${terminal ? `<div class="entity-meta">${item.output_asset_id ? badge(`asset ${item.output_asset_id}`) : badge('no output asset')}${item.metrics?.identity_score !== undefined ? badge(`identity ${item.metrics.identity_score}`) : ''}</div>` : `<form class="benchmark-result-form" data-identity-benchmark-result="${escapeHtml(item.id)}" data-benchmark-id="${escapeHtml(benchmark.id)}"><div class="benchmark-result-grid"><div class="field"><label>Status<select name="status"><option value="completed">Completed</option><option value="blocked">Blocked</option><option value="failed">Failed</option></select></label></div><div class="field"><label>Output Asset ID <span class="field-hint">optional</span><input name="output_asset_id" placeholder="asset id"></label></div></div><div class="benchmark-metrics"><div class="field"><label>Identity score<input name="identity_score" type="number" min="0" max="1" step="0.01" placeholder="0–1"></label></div><div class="field"><label>Prompt adherence<input name="prompt_adherence" type="number" min="0" max="1" step="0.01" placeholder="0–1"></label></div><div class="field"><label>Anatomy score<input name="anatomy_score" type="number" min="0" max="1" step="0.01" placeholder="0–1"></label></div><div class="field"><label>Style consistency<input name="style_consistency" type="number" min="0" max="1" step="0.01" placeholder="0–1"></label></div><div class="field"><label>Latency (ms)<input name="latency_ms" type="number" min="0" step="1" placeholder="optional"></label></div><div class="field"><label>Peak memory (MB)<input name="peak_memory_mb" type="number" min="0" step="1" placeholder="optional"></label></div></div><label class="field"><span>Notes or failure detail</span><textarea name="notes" rows="2" placeholder="Record measurement context or why this case was blocked."></textarea></label><div class="form-actions"><button class="button secondary" type="submit">Record case result</button></div></form>`}</article>`;
}

const DEFAULT_CREATOR_PILLARS = [
  { key: 'lifestyle', name: 'Lifestyle', description: 'Daily life, routines, and believable personal moments.', formats: ['photos', 'reels', 'stories'], content_classes: ['lifestyle'], identity_authority: 'style', identity_core: false, audience_goal: 'Build familiarity and trust.' },
  { key: 'fashion', name: 'Fashion', description: 'Outfits, styling, trends, and signature wardrobe choices.', formats: ['photos', 'reels', 'brand_content'], content_classes: ['fashion'], identity_authority: 'style', identity_core: false, audience_goal: 'Create visual recognition and saveable inspiration.' },
  { key: 'travel', name: 'Travel', description: 'Places, experiences, and culture through the persona point of view.', formats: ['photos', 'cinematic_campaigns', 'stories'], content_classes: ['travel'], identity_authority: 'style', identity_core: false, audience_goal: 'Invite discovery and conversation.' },
  { key: 'storytelling', name: 'Storytelling', description: 'Personal stories, points of view, and day-in-the-life narratives.', formats: ['reels', 'stories', 'captions'], content_classes: ['storytelling'], identity_authority: 'identity', identity_core: false, audience_goal: 'Build emotional connection.' },
  { key: 'product_reviews', name: 'Product Reviews', description: 'Honest reviews, unboxings, demonstrations, and comparisons.', formats: ['reels', 'photos', 'brand_content'], content_classes: ['product_reviews'], identity_authority: 'style', identity_core: false, audience_goal: 'Help the audience make confident decisions.' },
  { key: 'tutorials', name: 'Tutorials', description: 'Practical tips and how-to content taught in the creator voice.', formats: ['reels', 'carousels', 'stories'], content_classes: ['tutorials'], identity_authority: 'identity', identity_core: false, audience_goal: 'Deliver useful, repeatable value.' },
  { key: 'brand_content', name: 'Brand Content', description: 'Collaborations, campaigns, and UGC with clear brand fit.', formats: ['product_ads', 'reels', 'photos'], content_classes: ['brand_content'], identity_authority: 'style', identity_core: false, audience_goal: 'Create credible commercial partnerships.' },
  { key: 'adult_glamour', name: 'Adult/Glamour Editorial', description: 'Adult glamour, lingerie, boudoir, and editorial styling within the same canonical identity.', formats: ['editorial_photos', 'reels', 'brand_content'], content_classes: ['adult_glamour'], identity_authority: 'identity_and_style', identity_core: true, audience_goal: 'Express confident adult glamour without creating a separate identity system.' },
];

function creatorCsv(value) {
  return Array.isArray(value) ? value.join(', ') : String(value || '');
}

function renderCreatorPillar(pillar) {
  return `<article class="creator-pillar" data-creator-pillar><div class="section-heading"><div><p class="eyebrow">Content pillar</p><h3>${escapeHtml(pillar.name || 'New pillar')}</h3></div>${pillar.identity_core ? badge('Identity Core') : badge('style authority')}</div><div class="form-grid creator-pillar-grid"><label>Key<input name="pillar_key" value="${escapeHtml(pillar.key)}" maxlength="80"></label><label>Name<input name="pillar_name" value="${escapeHtml(pillar.name)}" maxlength="120" required></label><label class="span-2">Description<textarea name="pillar_description" rows="2" maxlength="500">${escapeHtml(pillar.description)}</textarea></label><label>Formats<input name="pillar_formats" value="${escapeHtml(creatorCsv(pillar.formats))}" placeholder="photos, reels, stories"></label><label>Content classes<input name="pillar_content_classes" value="${escapeHtml(creatorCsv(pillar.content_classes))}" placeholder="lifestyle, fashion"></label><label>Identity authority<select name="pillar_identity_authority"><option value="identity" ${pillar.identity_authority === 'identity' ? 'selected' : ''}>Identity</option><option value="style" ${pillar.identity_authority === 'style' ? 'selected' : ''}>Style</option><option value="identity_and_style" ${pillar.identity_authority === 'identity_and_style' ? 'selected' : ''}>Identity and style</option></select></label><label>Audience goal<input name="pillar_audience_goal" value="${escapeHtml(pillar.audience_goal)}" maxlength="300"></label><label class="check-field"><input name="pillar_identity_core" type="checkbox" ${pillar.identity_core ? 'checked' : ''}><span>Use as Identity Core anchor</span></label></div></article>`;
}

function renderCreatorSystem() {
  if (!state.activePersonaId) return emptyState('Select or create a Master Persona before defining the Creator System.', 'personas');
  const persona = activePersona();
  const envelope = state.creatorProfile || {};
  const profile = envelope.profile || {};
  const frozen = (envelope.version_state || persona?.current_version?.state) === 'frozen';
  const pillars = profile.content_pillars?.length ? profile.content_pillars : DEFAULT_CREATOR_PILLARS;
  const personality = profile.personality || {};
  const audience = profile.audience || {};
  const brand = profile.brand || {};
  const voice = profile.voice || {};
  return `<section class="panel" aria-labelledby="creator-system-heading"><div class="section-heading"><div><p class="eyebrow">Phase 6 · canonical creative system</p><h2 id="creator-system-heading">Creator System</h2></div>${badge(frozen ? 'frozen' : 'draft')}</div><p class="helper">Define how this Master Persona thinks, speaks, serves its audience, and turns one identity into repeatable content. Adult/glamour remains a content pillar inside the same Identity Core, not a separate persona.</p>${frozen ? '<div class="callout readiness-callout"><p><strong>This PersonaVersion is frozen.</strong></p><p class="helper">Create a new draft PersonaVersion before changing the Creator System.</p></div>' : ''}<form id="creator-profile-form" class="creator-profile-form"><fieldset ${frozen ? 'disabled' : ''}><legend class="sr-only">Creator identity and content system</legend><div class="creator-section"><div class="section-heading"><div><p class="eyebrow">Who they are</p><h3>Personality and voice</h3></div></div><div class="form-grid"><label>Personality traits<textarea name="personality_traits" rows="2" placeholder="Confident, witty, curious">${escapeHtml(personality.traits)}</textarea></label><label>Interests and values<textarea name="personality_interests" rows="2" placeholder="Fashion, travel, self-expression">${escapeHtml(personality.interests_and_values)}</textarea></label><label>Speaking style<textarea name="personality_speech_style" rows="2" placeholder="Smart, warm, concise, relatable">${escapeHtml(personality.speech_style)}</textarea></label><label>Humor<textarea name="personality_humor" rows="2" placeholder="Dry wit, playful observations">${escapeHtml(personality.humor)}</textarea></label><label>Signature behaviors<textarea name="personality_mannerisms" rows="2" placeholder="A recurring greeting, pose, or phrase">${escapeHtml(personality.mannerisms)}</textarea></label></div></div><div class="creator-section"><div class="section-heading"><div><p class="eyebrow">Who they serve</p><h3>Audience definition</h3></div></div><div class="form-grid"><label>Primary audience<textarea name="audience_primary" rows="2" placeholder="Adults interested in ...">${escapeHtml(audience.primary)}</textarea></label><label>Audience needs<textarea name="audience_needs" rows="2" placeholder="Inspiration, education, confidence">${escapeHtml(audience.needs)}</textarea></label><label>Relationship to audience<textarea name="audience_relationship" rows="2" placeholder="Trusted friend and practical guide">${escapeHtml(audience.relationship)}</textarea></label><label>Locales and language<textarea name="audience_locales" rows="2" placeholder="English, global urban audience">${escapeHtml(audience.locales)}</textarea></label></div></div><div class="creator-section"><div class="section-heading"><div><p class="eyebrow">How the brand behaves</p><h3>Positioning and disclosure</h3></div></div><div class="form-grid"><label>Brand positioning<textarea name="brand_positioning" rows="2" placeholder="Luxury fashion and relatable lifestyle creator">${escapeHtml(brand.positioning)}</textarea></label><label>Brand promise<textarea name="brand_promise" rows="2" placeholder="What the audience can consistently expect">${escapeHtml(brand.promise)}</textarea></label><label>Boundaries<textarea name="brand_boundaries" rows="2" placeholder="Topics, claims, or collaborations to avoid">${escapeHtml(brand.boundaries)}</textarea></label><label>Voice tone<textarea name="voice_tone" rows="2" placeholder="Smart, confident, warm">${escapeHtml(voice.tone)}</textarea></label><label>Vocabulary and CTA style<textarea name="voice_vocabulary" rows="2" placeholder="Preferred words, rhythm, and calls to action">${escapeHtml(voice.vocabulary)}</textarea></label><label>Disclosure<textarea name="disclosure" rows="2" minlength="20" maxlength="300" required>${escapeHtml(profile.disclosure || 'Fictional adult character. AI-generated synthetic media.')}</textarea></label></div></div><div class="creator-section"><div class="section-heading"><div><p class="eyebrow">What they share</p><h3>Content pillars</h3></div>${badge(`${pillars.length} pillars`)}</div><p class="helper">Each pillar can guide story, visual style, audience goal, and format. The adult/glamour pillar is intentionally marked as Identity Core plus style authority.</p><div class="creator-pillar-list">${pillars.map(renderCreatorPillar).join('')}</div></div></fieldset><p id="creator-profile-form-error" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button primary" type="submit" ${frozen || state.savingCreatorProfile ? 'disabled' : ''}>${state.savingCreatorProfile ? 'Saving...' : 'Save Creator System'}</button></div></form></section>`;
}

function renderContentBriefEditor({ brief, profile, pillars, contentPacks, versionState }) {
  const value = (key) => escapeHtml(brief[key] || '');
  const selected = (candidate, current) => candidate === current ? 'selected' : '';
  return `<section class="panel" aria-labelledby="brief-edit-heading"><div class="section-heading"><div><p class="eyebrow">Phase 6 · draft revision</p><h2 id="brief-edit-heading">Edit draft ContentBrief</h2></div>${badge(versionState)}${badge(`revision ${brief.revision || 1}`)}</div><p class="helper">Draft revisions stay attached to PersonaVersion ${escapeHtml(brief.persona_version_id)}. Approved briefs cannot be edited; create a new draft when the production direction must change.</p><form id="content-brief-form" class="content-brief-form"><div class="form-grid"><label>Title<input name="title" minlength="2" maxlength="160" required value="${value('title')}"></label><label>Format<select name="format"><option value="reel" ${selected('reel', brief.format)}>Reel</option><option value="photo" ${selected('photo', brief.format)}>Photo</option><option value="carousel" ${selected('carousel', brief.format)}>Carousel</option><option value="story" ${selected('story', brief.format)}>Story</option><option value="product_ad" ${selected('product_ad', brief.format)}>Product ad</option></select></label><label>Content class<select name="content_class"><option value="identity" ${selected('identity', brief.content_class)}>Identity / lifestyle</option><option value="fashion" ${selected('fashion', brief.content_class)}>Fashion</option><option value="adult_glamour" ${selected('adult_glamour', brief.content_class)}>Adult/glamour editorial</option><option value="lingerie" ${selected('lingerie', brief.content_class)}>Lingerie editorial</option><option value="boudoir" ${selected('boudoir', brief.content_class)}>Boudoir editorial</option></select></label><label>Creator System pillar<select name="pillar_key" required><option value="">Select a pillar</option>${pillars.map((pillar) => `<option value="${escapeHtml(pillar.key)}" ${selected(pillar.key, brief.pillar_key)}>${escapeHtml(pillar.name)}${pillar.identity_core ? ' · Identity Core' : ''}</option>`).join('')}</select></label></div><div class="form-grid"><label>Audience goal<textarea name="audience_goal" rows="2" maxlength="500">${value('audience_goal')}</textarea></label><label>Emotional objective<textarea name="emotional_objective" rows="2" maxlength="500">${value('emotional_objective')}</textarea></label></div><div class="form-grid"><label>Story direction<textarea name="story_direction" rows="3" maxlength="2000">${value('story_direction')}</textarea></label><label>Visual direction<textarea name="visual_direction" rows="3" maxlength="2000">${value('visual_direction')}</textarea></label><label>Motion direction<textarea name="motion_direction" rows="3" maxlength="2000">${value('motion_direction')}</textarea></label></div><div class="form-grid"><label>Caption direction<textarea name="caption_direction" rows="3" maxlength="1200">${value('caption_direction')}</textarea></label><label>Script direction<textarea name="script_direction" rows="3" maxlength="2000">${value('script_direction')}</textarea></label><label>ContentPack <span class="field-hint">optional</span><select name="content_pack_id"><option value="">Use pillar guidance only</option>${contentPacks.map((pack) => `<option value="${escapeHtml(pack.id)}" ${selected(pack.id, brief.content_pack_id)} ${pack.review === 'approved' || pack.id === brief.content_pack_id ? '' : 'disabled'}>${escapeHtml(pack.name)} · ${escapeHtml(pack.content_class)} · ${escapeHtml(pack.review)}</option>`).join('')}</select></label></div><div class="field"><label>Disclosure<textarea name="disclosure" rows="2" minlength="20" maxlength="300" required>${value('disclosure')}</textarea></label></div><p id="content-brief-form-error" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button primary" type="submit" ${state.creatingContentBrief ? 'disabled' : ''}>${state.creatingContentBrief ? 'Saving...' : 'Update draft brief'}</button><button class="button secondary" type="button" data-brief-cancel>Cancel</button></div></form></section>`;
}

function renderContentBriefs() {
  if (!state.activePersonaId) return emptyState('Select or create a Master Persona before authoring Content Briefs.', 'personas');
  const persona = activePersona();
  const profileEnvelope = state.creatorProfile || {};
  const profile = profileEnvelope.profile || {};
  const versionState = profileEnvelope.version_state || persona?.current_version?.state || 'draft';
  const pillars = profile.content_pillars || [];
  const contentPacks = state.contentPacks || [];
  const approvedArtifactCounts = state.contentArtifacts.reduce((counts, artifact) => {
    if (artifact.status === 'approved') counts[artifact.content_brief_id] = (counts[artifact.content_brief_id] || 0) + 1;
    return counts;
  }, {});
  const canAuthor = Boolean(profile.id);
  const editingBrief = state.contentBriefs.find((brief) => brief.id === state.editingContentBriefId && brief.status === 'draft');
  if (editingBrief) return renderContentBriefEditor({ brief: editingBrief, profile, pillars, contentPacks, versionState });
  return `<div class="panel-grid">
    <section class="panel" aria-labelledby="brief-create-heading">
      <div class="section-heading"><div><p class="eyebrow">Phase 6 Â· reusable direction</p><h2 id="brief-create-heading">Create Content Brief</h2></div>${badge(versionState)}</div>
      <p class="helper">Capture the audience goal, emotional outcome, story, visual language, motion, caption, and script direction before production. Adult/glamour briefs must select the canonical adult/glamour Identity Core pillar.</p>
      ${!canAuthor ? `<div class="callout readiness-callout"><p><strong>Create and save the Creator System first.</strong></p><p class="helper">A ContentBrief cannot exist without a PersonaVersion-bound Creator Profile.</p><div class="entity-actions"><button class="button secondary" type="button" data-view="creator">Open Creator System</button></div></div>` : ''}
      <form id="content-brief-form" class="content-brief-form">
        <fieldset ${canAuthor ? '' : 'disabled'}>
          <div class="form-grid"><label>Title<input name="title" minlength="2" maxlength="160" required placeholder="e.g. Evening skincare ritual"></label><label>Format<select name="format"><option value="reel">Reel</option><option value="photo">Photo</option><option value="carousel">Carousel</option><option value="story">Story</option><option value="product_ad">Product ad</option></select></label><label>Content class<select name="content_class"><option value="identity">Identity / lifestyle</option><option value="fashion">Fashion</option><option value="adult_glamour">Adult/glamour editorial</option><option value="lingerie">Lingerie editorial</option><option value="boudoir">Boudoir editorial</option></select></label><label>Creator System pillar<select name="pillar_key" required><option value="">Select a pillar</option>${pillars.map((pillar) => `<option value="${escapeHtml(pillar.key)}">${escapeHtml(pillar.name)}${pillar.identity_core ? ' Â· Identity Core' : ''}</option>`).join('')}</select></label></div>
          <div class="form-grid"><label>Audience goal<textarea name="audience_goal" rows="2" maxlength="500" placeholder="What should this help or invite the audience to do?"></textarea></label><label>Emotional objective<textarea name="emotional_objective" rows="2" maxlength="500" placeholder="How should the audience feel after watching or reading?"></textarea></label></div>
          <div class="form-grid"><label>Story direction<textarea name="story_direction" rows="3" maxlength="2000" placeholder="Beginning, tension, turn, and payoff."></textarea></label><label>Visual direction<textarea name="visual_direction" rows="3" maxlength="2000" placeholder="Location, wardrobe, composition, lighting, and canonical identity anchors."></textarea></label><label>Motion direction<textarea name="motion_direction" rows="3" maxlength="2000" placeholder="Performance, gestures, camera movement, and pacing."></textarea></label></div>
          <div class="form-grid"><label>Caption direction<textarea name="caption_direction" rows="3" maxlength="1200" placeholder="Hook, value, CTA, and disclosure placement."></textarea></label><label>Script direction<textarea name="script_direction" rows="3" maxlength="2000" placeholder="Spoken beats, pauses, and delivery guidance."></textarea></label><label>Approved ContentPack <span class="field-hint">optional</span><select name="content_pack_id"><option value="">Use pillar guidance only</option>${contentPacks.map((pack) => `<option value="${escapeHtml(pack.id)}" ${pack.review === 'approved' ? '' : 'disabled'}>${escapeHtml(pack.name)} Â· ${escapeHtml(pack.content_class)} Â· ${escapeHtml(pack.review)}</option>`).join('')}</select></label></div>
          <div class="field"><label>Disclosure<textarea name="disclosure" rows="2" minlength="20" maxlength="300" required>${escapeHtml(profile.disclosure || 'Fictional adult character. AI-generated synthetic media.')}</textarea></label></div>
        </fieldset>
        <p id="content-brief-form-error" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button primary" type="submit" ${!canAuthor || state.creatingContentBrief ? 'disabled' : ''}>${state.creatingContentBrief ? 'Saving...' : 'Save draft brief'}</button></div>
      </form>
    </section>
    <section class="panel" aria-labelledby="brief-list-heading"><div class="section-heading"><div><p class="eyebrow">Production library</p><h2 id="brief-list-heading">Reusable Content Briefs</h2></div>${badge(`${state.contentBriefs.length} brief${state.contentBriefs.length === 1 ? '' : 's'}`)}</div>${state.contentBriefs.length ? `<div class="card-list">${state.contentBriefs.map((brief) => { const approvedCount = approvedArtifactCounts[brief.id] || 0; return `<article class="entity-card"><div><h3>${escapeHtml(brief.title)}</h3><p>${escapeHtml(brief.format)} Â· ${escapeHtml(brief.content_class)}${brief.pillar_key ? ` Â· ${escapeHtml(brief.pillar_key)}` : ''}</p><div class="entity-meta">${badge(brief.status)}${badge(brief.persona_version_id)}${brief.content_pack_id ? badge('ContentPack linked') : badge('pillar-led')}${badge(`${approvedCount} approved artifact${approvedCount === 1 ? '' : 's'}`)}</div><p class="helper">${escapeHtml(brief.emotional_objective || brief.audience_goal || brief.story_direction || 'No objective recorded yet.')}</p></div><div class="entity-actions">${brief.status === 'draft' ? `<button class="button secondary" type="button" data-brief-approve="${escapeHtml(brief.id)}" ${state.approvingContentBrief ? 'disabled' : ''}>${state.approvingContentBrief === brief.id ? 'Approving...' : 'Approve for production'}</button>` : ''}${brief.status === 'approved' ? `<button class="button primary" type="button" data-brief-handoff="${escapeHtml(brief.id)}">Hand off to Production</button>` : ''}</div></article>`; }).join('')}</div>` : emptyState('No ContentBriefs exist for this PersonaVersion yet. Create the first reusable story and production direction above.')}</section>
  </div>`;
}

function renderContentArtifactQuality(artifact) {
  const quality = artifact.quality || {};
  const checks = Array.isArray(quality.checks) ? quality.checks : [];
  if (!checks.length) return '<p class="helper">Quality check has not run yet.</p>';
  return `<div class="artifact-quality-checks" aria-label="Content quality checks">${checks.map((check) => `<div class="artifact-quality-check"><span>${badge(check.status)}</span><span>${escapeHtml(check.detail)}</span></div>`).join('')}</div>`;
}

function renderContentArtifactEditor(artifact) {
  return `<section class="panel content-artifacts-panel" aria-labelledby="artifact-edit-heading"><div class="section-heading"><div><p class="eyebrow">Phase 6 · draft revision</p><h2 id="artifact-edit-heading">Edit ${escapeHtml(artifact.artifact_type)} draft</h2></div>${badge(`revision ${artifact.revision || 1}`)}</div><p class="helper">Draft copy remains bound to ContentBrief ${escapeHtml(artifact.content_brief_id)} and PersonaVersion ${escapeHtml(artifact.persona_version_id)}. Saving creates a new artifact revision and re-runs the quality checks.</p><form id="content-artifact-edit-form" class="content-artifact-form"><input type="hidden" name="artifact_type" value="${escapeHtml(artifact.artifact_type)}"><label>Artifact copy<textarea name="content" rows="10" maxlength="5000" required>${escapeHtml(artifact.content)}</textarea></label><p id="content-artifact-edit-error" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button primary" type="submit" ${state.creatingContentArtifact ? 'disabled' : ''}>${state.creatingContentArtifact ? 'Saving...' : 'Save artifact revision'}</button><button class="button secondary" type="button" data-artifact-edit-cancel>Cancel</button></div></form></section>`;
}

function renderContentArtifacts() {
  const approvedBriefs = state.contentBriefs.filter((brief) => brief.status === 'approved');
  const briefNames = Object.fromEntries(state.contentBriefs.map((brief) => [brief.id, brief.title]));
  return `<section class="panel content-artifacts-panel" aria-labelledby="content-artifacts-heading"><div class="section-heading"><div><p class="eyebrow">Reviewable output</p><h2 id="content-artifacts-heading">Caption and Script Drafts</h2></div>${badge(`${state.contentArtifacts.length} artifact${state.contentArtifacts.length === 1 ? '' : 's'}`)}</div><p class="helper">Create deterministic draft templates from an approved ContentBrief, run structural quality checks, then review the copy before any production or publishing handoff. These checks do not censor adult/glamour content and are not model-generated.</p>${approvedBriefs.length ? `<form id="content-artifact-create-form" class="content-artifact-form"><div class="form-grid"><label>Approved ContentBrief<select name="content_brief_id" required>${approvedBriefs.map((brief) => `<option value="${escapeHtml(brief.id)}">${escapeHtml(brief.title)} · ${escapeHtml(brief.content_class)}</option>`).join('')}</select></label><label>Artifact type<select name="artifact_type"><option value="caption">Caption draft</option><option value="script">Script draft</option></select></label></div><label>Optional operator copy <span class="field-hint">leave blank to create a structured template</span><textarea name="content" rows="4" maxlength="5000" placeholder="Paste or write reviewed copy here, or leave blank for the deterministic template."></textarea><p id="content-artifact-form-error" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button primary" type="submit" ${state.creatingContentArtifact ? 'disabled' : ''}>${state.creatingContentArtifact ? 'Creating...' : 'Create draft artifact'}</button></div></form>` : `<div class="callout readiness-callout"><p><strong>Approve a ContentBrief first.</strong></p><p class="helper">Caption and script artifacts inherit the frozen PersonaVersion, disclosure, and adult/glamour Identity Core checks from the approved brief.</p></div>`}${state.contentArtifacts.length ? `<div class="card-list artifact-list">${state.contentArtifacts.map((artifact) => { const qualityStatus = artifact.quality_status || 'pending'; const busy = state.assessingContentArtifact === artifact.id || state.approvingContentArtifact === artifact.id; return `<article class="entity-card"><div><h3>${escapeHtml(artifact.artifact_type)} · ${escapeHtml(briefNames[artifact.content_brief_id] || artifact.content_brief_id)}</h3><div class="entity-meta">${badge(artifact.status)}${badge(`revision ${artifact.revision || 1}`)}${badge(artifact.source || 'operator')}${badge(qualityStatus)}</div><p class="artifact-content">${escapeHtml(artifact.content)}</p><p class="helper">Disclosure: ${escapeHtml(artifact.disclosure)}</p>${renderContentArtifactQuality(artifact)}</div><div class="entity-actions">${artifact.status === 'draft' ? `<button class="button secondary" type="button" data-artifact-quality="${escapeHtml(artifact.id)}" ${busy ? 'disabled' : ''}>${state.assessingContentArtifact === artifact.id ? 'Checking...' : 'Run quality check'}</button><button class="button primary" type="button" data-artifact-approve="${escapeHtml(artifact.id)}" ${(busy || qualityStatus === 'failed') ? 'disabled' : ''}>${state.approvingContentArtifact === artifact.id ? 'Approving...' : 'Approve artifact'}</button>` : ''}${artifact.status === 'approved' ? `<span class="badge approved">Ready for handoff</span>` : ''}</div></article>`; }).join('')}</div>` : emptyState('No caption or script artifacts exist yet. Approve a brief, then create the first draft above.')}</section>`;
}

function renderContentArtifactEditControls() {
  const drafts = state.contentArtifacts.filter((artifact) => artifact.status === 'draft');
  if (!drafts.length) return '';
  return `<section class="panel" aria-labelledby="artifact-edit-list-heading"><div class="section-heading"><div><p class="eyebrow">Draft maintenance</p><h2 id="artifact-edit-list-heading">Revise artifact copy</h2></div>${badge(`${drafts.length} editable`)}</div><p class="helper">Edit draft copy before approval. Each successful save increments the artifact revision and re-runs its quality checks.</p><div class="entity-actions">${drafts.map((artifact) => `<button class="button secondary" type="button" data-artifact-edit="${escapeHtml(artifact.id)}">Edit ${escapeHtml(artifact.artifact_type)} draft</button>`).join('')}</div></section>`;
}

function renderContentBriefsWithEditing() {
  const editingBrief = state.contentBriefs.find((brief) => brief.id === state.editingContentBriefId && brief.status === 'draft');
  if (editingBrief) {
    const profile = state.creatorProfile?.profile || {};
    return renderContentBriefEditor({
      brief: editingBrief,
      profile,
      pillars: profile.content_pillars || [],
      contentPacks: state.contentPacks || [],
      versionState: state.creatorProfile?.version_state || activePersona()?.current_version?.state || 'draft',
    });
  }
  const drafts = state.contentBriefs.filter((brief) => brief.status === 'draft');
  const controls = drafts.length ? `<section class="panel" aria-labelledby="brief-edit-list-heading"><div class="section-heading"><div><p class="eyebrow">Draft maintenance</p><h2 id="brief-edit-list-heading">Revise before approval</h2></div>${badge(`${drafts.length} editable`)}</div><p class="helper">Edit a draft to refine the creative direction. Each successful save increments its revision; approved briefs remain immutable.</p><div class="entity-actions">${drafts.map((brief) => `<button class="button secondary" type="button" data-brief-edit="${escapeHtml(brief.id)}">Edit ${escapeHtml(brief.title)}</button>`).join('')}</div></section>` : '';
  const editingArtifact = state.contentArtifacts.find((artifact) => artifact.id === state.editingContentArtifactId && artifact.status === 'draft');
  if (editingArtifact) return `${renderContentBriefs()}${controls}${renderContentArtifactEditor(editingArtifact)}`;
  return `${renderContentBriefs()}${controls}${renderContentArtifacts()}${renderContentArtifactEditControls()}`;
}

function renderIdentityBenchmarks() {
  if (!state.activePersonaId) return emptyState('Select or create a Master Persona before planning identity benchmarks.', 'personas');
  const persona = activePersona();
  const frozen = persona?.current_version?.state === 'frozen';
  const methods = state.benchmarkCatalog.methods || [];
  const scenarios = state.benchmarkCatalog.scenarios || [];
  return `<section class="panel" aria-labelledby="benchmark-heading"><div class="section-heading"><div><p class="eyebrow">Phase 5 · model-deferred</p><h2 id="benchmark-heading">Identity-conditioning benchmarks</h2></div>${badge(state.benchmarkCatalog.execution_status || 'deferred_final_gate')}</div><p class="helper">Create a reproducible comparison plan against the active frozen PersonaVersion. Adult/glamour remains part of the same Identity Core anchor system. Model installation and execution are intentionally deferred.</p><div class="readiness-grid benchmark-readiness"><div class="readiness-item"><div><strong>PersonaVersion</strong><span>${escapeHtml(persona?.current_version?.id || 'not available')}</span></div>${frozen ? badge('ready') : badge('freeze required')}</div><div class="readiness-item"><div><strong>Canonical anchor</strong><span>Resolved by the server from approved, rights-confirmed media</span></div>${badge('server gated')}</div><div class="readiness-item"><div><strong>Runtime/model gate</strong><span>Results can be recorded later on the target Mac</span></div>${badge('deferred')}</div></div>${!frozen ? `<div class="callout readiness-callout"><p><strong>Freeze this PersonaVersion before creating a benchmark.</strong></p><p class="helper">Review canonical ReferencePack anchors first, then return here.</p><div class="entity-actions"><button class="button secondary" type="button" data-view="personas">Open Master Persona</button><button class="button secondary" type="button" data-view="references">Review anchors</button></div></div>` : ''}<form id="identity-benchmark-create-form" class="benchmark-plan-form" aria-labelledby="benchmark-plan-heading"><div class="section-heading"><div><p class="eyebrow">Benchmark plan</p><h3 id="benchmark-plan-heading">Select methods and scenarios</h3></div>${badge(`${methods.length} methods`)}</div><div class="field"><label>Base model identifier <span class="field-hint">optional until final gate</span><input name="base_model_id" maxlength="160" placeholder="pending-final-gate"></label></div><fieldset class="benchmark-options"><legend>Identity methods</legend><div class="benchmark-option-grid">${methods.map((method) => `<label class="benchmark-option"><input type="checkbox" name="methods" value="${escapeHtml(method.id)}" checked><span><strong>${escapeHtml(method.label)}</strong><small>${escapeHtml(method.category)} · ${escapeHtml(method.execution_status)}</small></span></label>`).join('')}</div></fieldset><fieldset class="benchmark-options"><legend>Scenarios</legend><div class="benchmark-option-grid">${scenarios.map((scenario) => `<label class="benchmark-option"><input type="checkbox" name="scenario_ids" value="${escapeHtml(scenario.id)}" checked><span><strong>${escapeHtml(scenario.label)}</strong><small>${escapeHtml(scenario.content_class)}</small></span></label>`).join('')}</div></fieldset><p id="identity-benchmark-form-error" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button primary" type="submit" ${frozen && !state.creatingBenchmark ? '' : 'disabled'}>${state.creatingBenchmark ? 'Creating plan…' : 'Create benchmark plan'}</button></div></form>${state.benchmarks.length ? `<div class="benchmark-list">${state.benchmarks.map((benchmark) => `<article class="benchmark-card"><div class="section-heading"><div><p class="eyebrow">Benchmark plan</p><h3>${escapeHtml(benchmark.id)}</h3><p class="helper">PersonaVersion ${escapeHtml(benchmark.persona_version_id)} · ${escapeHtml(benchmark.anchor_content_class)} anchor · ${escapeHtml(benchmark.base_model_id || 'model not selected')}</p></div>${badge(benchmark.status)}</div><div class="entity-meta">${badge(`${benchmark.cases.length} cases`)}${badge(`anchor ${benchmark.anchor_asset_id}`)}${benchmark.status === 'completed' ? badge('review summary ready') : badge('no automatic selection')}</div>${renderBenchmarkSummary(benchmark.summary)}<div class="benchmark-cases"><div class="section-heading"><div><p class="eyebrow">Case results</p><h3>Record measured outcomes</h3></div></div>${benchmark.cases.map((item) => renderBenchmarkCase(benchmark, item)).join('')}</div></article>`).join('')}</div>` : emptyState('No identity benchmark plans exist for this PersonaVersion yet. Create one after the canonical anchor is ready.')}</section>`;
}

function renderPublishingLegacy() {
  const persona = activePersona();
  const accounts = state.publishingAccounts || [];
  return `<section class="panel" aria-labelledby="publishing-heading"><div class="section-heading"><div><p class="eyebrow">Phase 8 · local contract</p><h2 id="publishing-heading">Publishing readiness</h2></div>${badge(state.publishingPolicies?.execution_status || 'catalog_only')}</div><div class="callout"><p><strong>External publishing remains disabled.</strong></p><p class="helper">This phase records persona-owned account bindings and dry-run evidence only. Provider: local dry-run provider. No OAuth token, outbound request, or publish action is performed.</p></div><div class="card-list" style="margin-top: 16px"><div class="entity-card"><div><h3>Identity lineage</h3><p>${persona ? 'Active PersonaVersion is available for downstream checks.' : 'Select a Master Persona first.'}</p></div>${persona ? badge('ready') : badge('pending')}</div><div class="entity-card"><div><h3>Media approval</h3><p>Only approved assets may advance to publishing.</p></div>${badge('required')}</div><div class="entity-card"><div><h3>Platform account mapping</h3><p>Account records are local, secret-free, and remain unverified until Phase 8 provider verification is added.</p></div>${badge(accounts.length ? `${accounts.length} configured` : 'planned')}</div></div>${persona ? `<section class="subpanel" aria-labelledby="account-binding-heading"><div class="section-heading"><div><p class="eyebrow">Persona-owned mapping</p><h3 id="account-binding-heading">Publishing accounts</h3></div>${badge(`${accounts.length} account${accounts.length === 1 ? '' : 's'}`)}</div><form id="publishing-account-form" class="content-artifact-form"><div class="form-grid"><label>Platform<select name="platform"><option value="instagram">Instagram</option></select></label><label>Account label<input name="account_label" minlength="2" maxlength="120" required placeholder="Main creator account"></label><label>Account type<select name="account_type"><option value="professional">Professional</option><option value="creator">Creator</option><option value="business">Business</option></select></label><label>Handle <span class="field-hint">optional</span><input name="handle" maxlength="120" placeholder="@persona"></label><label>External account ID <span class="field-hint">optional placeholder</span><input name="external_account_id" maxlength="160" placeholder="configured later"></label></div><p class="helper">Do not enter passwords or access tokens. New records stay unverified and cannot publish.</p><p id="publishing-account-form-error" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button primary" type="submit" ${state.creatingPublishingAccount ? 'disabled' : ''}>${state.creatingPublishingAccount ? 'Saving…' : 'Save local account binding'}</button></div></form>${accounts.length ? `<div class="entity-list">${accounts.map((account) => `<article class="entity-card"><div><h4>${escapeHtml(account.account_label)}</h4><p class="helper">${escapeHtml(account.platform)} · ${escapeHtml(account.account_type)}${account.handle ? ` · ${escapeHtml(account.handle)}` : ''}</p></div>${badge(account.status)}</article>`).join('')}</div>` : emptyState('No persona-owned publishing account is configured yet.')}</section>` : `<div class="callout readiness-callout"><p><strong>Select a Master Persona first.</strong></p><p class="helper">Account bindings must belong to one canonical persona.</p></div>`}</section>`;
}

function publishingProviderCatalog() {
  return state.publishingPolicies?.providers || [];
}

function publishingMetaProvider() {
  return publishingProviderCatalog().find((provider) => provider.id === 'meta_instagram') || {};
}

function renderPublishingChecks(checks) {
  if (!Array.isArray(checks) || !checks.length) return '<p class="helper">No readiness checks have been returned yet.</p>';
  return `<div class="artifact-quality-checks" aria-label="Instagram publishing readiness checks">${checks.map((check) => `<div class="artifact-quality-check"><span>${escapeHtml(check.id || 'check')}</span>${badge(check.status || 'unknown')}<small>${escapeHtml(check.detail || '')}</small></div>`).join('')}</div>`;
}

function renderPublishing() {
  const persona = activePersona();
  const accounts = state.publishingAccounts || [];
  const assets = state.publishingAssets || [];
  const artifacts = (state.publishingArtifacts || []).filter((artifact) => artifact.artifact_type === 'caption');
  const provider = publishingMetaProvider();
  const selectedAsset = assets.find((asset) => asset.id === state.selectedPublishingAssetId);
  const selectedAccount = accounts.find((account) => account.id === state.selectedPublishingAccountId);
  const selectedArtifact = artifacts.find((artifact) => artifact.id === state.selectedPublishingArtifactId);
  const format = selectedAsset?.kind === 'video' ? 'reel' : 'feed_image';
  const platformReadiness = state.publishingReadiness?.platform_readiness || state.publishingReadiness;
  const resultAttempt = state.publishingResult?.attempt;
  const resultResponse = resultAttempt?.response || {};
  const resultMedia = resultResponse.media || {};
  const resultChecks = resultResponse.checks || state.publishingResult?.checks || [];
  const readinessPanel = state.publishingReadiness ? `<div class="callout ${platformReadiness?.ready ? '' : 'stale-callout'}" aria-live="polite"><p><strong>Instagram readiness:</strong> ${badge(platformReadiness?.status || 'blocked')}</p>${renderPublishingChecks(platformReadiness?.checks || [])}</div>` : '';
  const resultPanel = state.publishingResult ? `<div class="callout ${state.publishingResult.error ? 'stale-callout' : ''}" aria-live="polite"><p><strong>${state.publishingResult.error ? 'Publishing action failed' : (resultResponse.execution_status === 'published' ? 'Published' : 'Dry-run recorded')}</strong></p><p class="helper">${escapeHtml(state.publishingResult.error || resultResponse.status || 'No status returned.')}</p>${resultAttempt ? `<div class="entity-meta">${badge(resultAttempt.status)}${badge(resultAttempt.dry_run ? 'dry-run' : 'external attempt')}${resultMedia.media_id ? badge(`media ${resultMedia.media_id}`) : ''}</div>` : ''}${resultChecks.length ? renderPublishingChecks(resultChecks) : ''}</div>` : '';
  const accountOptions = accounts.map((account) => `<option value="${escapeHtml(account.id)}" ${account.id === state.selectedPublishingAccountId ? 'selected' : ''}>${escapeHtml(account.account_label)} · ${escapeHtml(account.status)}</option>`).join('');
  const assetOptions = assets.map((asset) => `<option value="${escapeHtml(asset.id)}" ${asset.id === state.selectedPublishingAssetId ? 'selected' : ''}>${escapeHtml(asset.filename || asset.id)} · ${escapeHtml(asset.kind)} · ${escapeHtml(asset.content_class || 'identity')}</option>`).join('');
  const artifactOptions = artifacts.map((artifact) => `<option value="${escapeHtml(artifact.id)}" ${artifact.id === state.selectedPublishingArtifactId ? 'selected' : ''}>${escapeHtml((artifact.content || '').slice(0, 80))} · approved</option>`).join('');
  return `<section class="panel" aria-labelledby="publishing-heading"><div class="section-heading"><div><p class="eyebrow">Phase 8 · operator workflow</p><h2 id="publishing-heading">Publishing readiness</h2></div>${badge(provider.supports_publish ? 'live gate configured' : 'dry-run boundary')}</div><div class="callout"><p><strong>Review locally, then choose the delivery action.</strong></p><p class="helper">Dry-run records readiness evidence without external calls. Live publishing appears only when the Meta provider is explicitly configured and all server-side account, asset, caption, policy, and public-media checks pass. Adult/glamour content remains an Identity Core style anchor, but Instagram eligibility is evaluated separately.</p></div>${persona ? `<section class="subpanel" aria-labelledby="publishing-action-heading"><div class="section-heading"><div><p class="eyebrow">Approved output handoff</p><h3 id="publishing-action-heading">Prepare a publish attempt</h3></div>${badge(`${assets.length} approved candidate${assets.length === 1 ? '' : 's'}`)}</div><form id="publishing-workflow-form" class="content-artifact-form"><div class="form-grid"><label>Instagram account<select name="account_id" required ${accounts.length ? '' : 'disabled'}><option value="">${accounts.length ? 'Select an account' : 'No account binding available'}</option>${accountOptions}</select></label><label>Asset<select name="asset_id" required ${assets.length ? '' : 'disabled'}><option value="">${assets.length ? 'Select approved media' : 'No approved media available'}</option>${assetOptions}</select></label><label>Approved caption<select name="content_artifact_id" required ${artifacts.length ? '' : 'disabled'}><option value="">${artifacts.length ? 'Select approved caption' : 'No approved caption available'}</option>${artifactOptions}</select></label><label>Format<select name="format" required><option value="feed_image" ${format === 'feed_image' ? 'selected' : ''}>Feed image</option><option value="reel" ${format === 'reel' ? 'selected' : ''}>Reel</option></select></label></div><p class="helper">${escapeHtml(selectedAccount?.account_label || 'No account selected')} · ${escapeHtml(selectedAsset?.content_class || 'No asset selected')} · ${selectedArtifact ? 'approved caption selected' : 'no approved caption selected'}. Tokens are never entered or displayed here.</p><label class="checkbox-row"><input type="checkbox" name="confirm_external"><span>I understand that the live action can contact Instagram and create a public post.</span></label><p id="publishing-workflow-form-error" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button secondary" type="button" data-publishing-readiness ${state.publishingBusy ? 'disabled' : ''}>${state.publishingBusy ? 'Checking…' : 'Check readiness'}</button><button class="button secondary" type="button" data-publishing-dry-run ${state.publishingBusy ? 'disabled' : ''}>${state.publishingBusy ? 'Working…' : 'Record dry-run'}</button><button class="button secondary" type="submit" name="publish_action" value="live" ${state.publishingBusy || !provider.supports_publish ? 'disabled' : ''}>${state.publishingBusy ? 'Publishing…' : 'Publish to Instagram'}</button></div></form>${selectedAsset ? `<div class="entity-actions"><button class="button secondary" type="button" data-publishing-prepare-media="${escapeHtml(selectedAsset.id)}" ${state.publishingBusy ? 'disabled' : ''}>Prepare public media URL</button></div>` : ''}${readinessPanel}${resultPanel}</section>` : `<div class="callout readiness-callout"><p><strong>Select a Master Persona first.</strong></p><p class="helper">Account bindings, assets, and captions must belong to one canonical persona.</p></div>`}<section class="subpanel" aria-labelledby="account-binding-heading"><div class="section-heading"><div><p class="eyebrow">Persona-owned mapping</p><h3 id="account-binding-heading">Publishing accounts</h3></div>${badge(`${accounts.length} account${accounts.length === 1 ? '' : 's'}`)}</div>${persona ? `<form id="publishing-account-form" class="content-artifact-form"><div class="form-grid"><label>Platform<select name="platform"><option value="instagram">Instagram</option></select></label><label>Account label<input name="account_label" minlength="2" maxlength="120" required placeholder="Main creator account"></label><label>Account type<select name="account_type"><option value="professional">Professional</option><option value="creator">Creator</option><option value="business">Business</option></select></label><label>Handle <span class="field-hint">optional</span><input name="handle" maxlength="120" placeholder="@persona"></label><label>External account ID <span class="field-hint">optional placeholder</span><input name="external_account_id" maxlength="160" placeholder="configured later"></label></div><p class="helper">Do not enter passwords or access tokens. New records stay unverified until provider verification is intentionally started.</p><p id="publishing-account-form-error" class="form-error" role="alert" hidden></p><div class="form-actions"><button class="button primary" type="submit" ${state.creatingPublishingAccount ? 'disabled' : ''}>${state.creatingPublishingAccount ? 'Saving…' : 'Save local account binding'}</button></div></form>` : ''}${accounts.length ? `<div class="entity-list">${accounts.map((account) => `<article class="entity-card"><div><h4>${escapeHtml(account.account_label)}</h4><p class="helper">${escapeHtml(account.platform)} · ${escapeHtml(account.account_type)}${account.handle ? ` · ${escapeHtml(account.handle)}` : ''}${account.external_account_id ? ` · ${escapeHtml(account.external_account_id)}` : ''}</p></div><div class="entity-actions">${badge(account.status)}${account.status === 'authorized' || account.status === 'verified' ? `<button class="button secondary" type="button" data-publishing-verify="${escapeHtml(account.id)}" ${state.verifyingPublishingAccountId === account.id ? 'disabled' : ''}>${state.verifyingPublishingAccountId === account.id ? 'Verifying…' : 'Verify account'}</button>` : ''}</div></article>`).join('')}</div>` : emptyState('No persona-owned publishing account is configured yet.')}</section></section>`;
}

function renderView() {
  const renderer = { overview: renderOverview, personas: renderPersonasCanonical, references: renderReferencesCanonical, 'content-packs': renderContentPacks, creator: renderCreatorSystem, 'content-briefs': renderContentBriefsWithEditing, benchmarks: renderIdentityBenchmarks, production: renderProductionCanonical, assets: renderAssetsCanonical, publishing: renderPublishing }[state.view] || renderOverview;
  $('#workspace-view').innerHTML = `${renderCrossViewLineageNotice()}${renderAssetLineagePanel()}${renderer()}`;
}

async function loadViewData() {
  state.controller?.abort();
  state.controller = new AbortController();
  const token = ++state.requestToken;
  const signal = state.controller.signal;
  $('#workspace-view').setAttribute('aria-busy', 'true');
  renderNavigation();
  renderHeader();
  renderPersonaSelect();
  renderView();
  setStatus('Loading canonical workspace data…');
  try {
    const requests = { overview: [], personas: state.activePersonaId ? [`/api/personas/${encodeURIComponent(state.activePersonaId)}/versions`] : [], references: state.activePersonaId ? [`/api/personas/${encodeURIComponent(state.activePersonaId)}/reference-packs`, '/api/assets'] : [], 'content-packs': state.activePersonaId ? [`/api/personas/${encodeURIComponent(state.activePersonaId)}/content-packs`] : [], creator: state.activePersonaId ? [`/api/personas/${encodeURIComponent(state.activePersonaId)}/creator-profile`] : [], 'content-briefs': state.activePersonaId ? [`/api/personas/${encodeURIComponent(state.activePersonaId)}/content-briefs`, `/api/personas/${encodeURIComponent(state.activePersonaId)}/creator-profile`, `/api/personas/${encodeURIComponent(state.activePersonaId)}/content-packs`, `/api/personas/${encodeURIComponent(state.activePersonaId)}/content-artifacts`] : [], benchmarks: state.activePersonaId ? ['/api/identity-conditioning/catalog', `/api/personas/${encodeURIComponent(state.activePersonaId)}/identity-benchmarks`] : ['/api/identity-conditioning/catalog'], production: state.activePersonaId ? ['/api/jobs', '/api/workflows', `/api/personas/${encodeURIComponent(state.activePersonaId)}/content-packs`] : ['/api/jobs', '/api/workflows'], assets: state.activePersonaId ? ['/api/assets', `/api/personas/${encodeURIComponent(state.activePersonaId)}/reference-packs`] : ['/api/assets'], publishing: state.activePersonaId ? ['/api/publishing/policies', `/api/personas/${encodeURIComponent(state.activePersonaId)}/publishing-accounts`] : ['/api/publishing/policies'] }[state.view] || [];
    const results = await Promise.all(requests.map((url) => get(url, { signal })));
    if (signal.aborted || token !== state.requestToken) return;
    if (state.view === 'references') {
      state.references = Array.isArray(results[0]) ? results[0] : results[0]?.packs || [];
      state.referenceAssets = Array.isArray(results[1]) ? results[1] : [];
      if (!state.references.some((pack) => pack.id === state.selectedReferencePackId)) state.selectedReferencePackId = state.references[0]?.id || '';
    }
    if (state.view === 'content-packs') state.contentPacks = Array.isArray(results[0]) ? results[0] : results[0]?.content_packs || [];
    if (state.view === 'creator') state.creatorProfile = results[0] || null;
    if (state.view === 'content-briefs') {
      state.contentBriefs = Array.isArray(results[0]) ? results[0] : results[0]?.content_briefs || [];
      state.creatorProfile = results[1] || null;
      state.contentPacks = Array.isArray(results[2]) ? results[2] : results[2]?.content_packs || [];
      state.contentArtifacts = Array.isArray(results[3]) ? results[3] : results[3]?.content_artifacts || [];
    }
    if (state.view === 'benchmarks') {
      state.benchmarkCatalog = results[0] || { execution_status: 'deferred_final_gate', methods: [], scenarios: [] };
      state.benchmarks = state.activePersonaId ? (Array.isArray(results[1]) ? results[1] : []) : [];
    }
    if (state.view === 'production') {
      state.jobs = results[0] || [];
      state.workflows = Array.isArray(results[1]) ? results[1] : [];
      if (state.activePersonaId) state.contentPacks = Array.isArray(results[2]) ? results[2] : [];
    }
    if (state.view === 'assets') {
      state.assets = results[0] || [];
      state.assetReferenceLinks = Array.isArray(results[1]) ? results[1] : results[1]?.packs || [];
    }
    if (state.view === 'personas') state.versions = results[0] || [];
    if (state.view === 'publishing' && state.activePersonaId) {
      state.publishingPolicies = results[0] || null;
      state.publishingAccounts = Array.isArray(results[1]) ? results[1] : [];
      const [publishingAssets, publishingArtifacts] = await Promise.all([
        get('/api/assets', { signal }),
        get(`/api/personas/${encodeURIComponent(state.activePersonaId)}/content-artifacts`, { signal }),
      ]);
      state.publishingAssets = (Array.isArray(publishingAssets) ? publishingAssets : []).filter((asset) => asset.persona_id === state.activePersonaId && asset.review === 'approved' && ['image', 'video'].includes(asset.kind));
      state.publishingArtifacts = (Array.isArray(publishingArtifacts) ? publishingArtifacts : []).filter((artifact) => artifact.persona_id === state.activePersonaId && artifact.status === 'approved');
      if (!state.publishingAssets.some((asset) => asset.id === state.selectedPublishingAssetId)) state.selectedPublishingAssetId = state.publishingAssets[0]?.id || '';
      if (!state.publishingAccounts.some((account) => account.id === state.selectedPublishingAccountId)) state.selectedPublishingAccountId = state.publishingAccounts[0]?.id || '';
      if (!state.publishingArtifacts.some((artifact) => artifact.id === state.selectedPublishingArtifactId && artifact.artifact_type === 'caption')) state.selectedPublishingArtifactId = state.publishingArtifacts.find((artifact) => artifact.artifact_type === 'caption')?.id || '';
    }
    renderView();
    $('#workspace-view').setAttribute('aria-busy', 'false');
    setStatus('Canonical workspace ready.', 'success');
  } catch (error) {
    if (error.name === 'AbortError') return;
    $('#workspace-view').setAttribute('aria-busy', 'false');
    setStatus(error.message, 'error');
  }
}

async function loadBase() {
  if (state.personaDraft === null) state.personaDraft = readCanonicalPersonaDraft();
  if (!state.generationDraftImported) {
    const importedGeneration = readCanonicalGenerationDraft();
    if (importedGeneration) {
      const width = Number(importedGeneration.width);
      const height = Number(importedGeneration.height);
      state.generationDraft = {
        ...state.generationDraft,
        workflow_id: String(importedGeneration.workflow_id || 'default_image_api'),
        prompt: String(importedGeneration.prompt || '').trim().slice(0, 3000),
        width: Number.isFinite(width) && width >= 256 && width <= 2048 ? width : 768,
        height: Number.isFinite(height) && height >= 256 && height <= 2048 ? height : 1152,
        content_pack_id: String(importedGeneration.content_pack_id || ''),
        rights_confirmed: false,
      };
      state.generationSourceModel = String(importedGeneration.legacy_model || '');
      state.generationDraftImported = true;
    }
  }
  $('#workspace-view').setAttribute('aria-busy', 'true');
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
    $('#workspace-view').setAttribute('aria-busy', 'false');
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
    state.personaDraft = null;
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

async function reviewReferencePack(event) {
  const form = event.target;
  const packId = form.dataset.referencePackReview;
  try {
    await patch(`/api/personas/${encodeURIComponent(state.activePersonaId)}/reference-packs/${encodeURIComponent(packId)}/review`, {
      review: form.elements.review.value,
      rights_confirmed: form.elements.rights_confirmed.checked,
    });
    setStatus('ReferencePack review state saved.', 'success');
    await loadViewData();
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

async function reviewReferenceItem(event) {
  const form = event.target;
  const packId = form.dataset.referencePackId;
  const itemId = form.dataset.referenceItemReview;
  try {
    await patch(`/api/personas/${encodeURIComponent(state.activePersonaId)}/reference-packs/${encodeURIComponent(packId)}/items/${encodeURIComponent(itemId)}/review`, {
      review: form.elements.review.value,
      rights_confirmed: form.elements.rights_confirmed.checked,
    });
    setStatus('ReferencePack item review state saved.', 'success');
    await loadViewData();
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

async function linkReferenceAsset(event) {
  const form = event.target;
  const packId = form.dataset.referencePackId;
  const itemId = form.dataset.referenceItemAsset;
  const assetId = form.elements.asset_id.value;
  if (!assetId) {
    setStatus('Select an image asset before linking.', 'error');
    return;
  }
  try {
    await post(`/api/personas/${encodeURIComponent(state.activePersonaId)}/reference-packs/${encodeURIComponent(packId)}/items/${encodeURIComponent(itemId)}/asset`, { asset_id: assetId });
    setStatus('ReferencePack item linked to the media asset.', 'success');
    await loadViewData();
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

async function selectReferenceCanonical(event) {
  const form = event.target;
  const packId = form.dataset.referenceCanonical;
  const itemIds = [...form.querySelectorAll('input[name="item_ids"]:checked')].map((input) => input.value);
  try {
    await patch(`/api/personas/${encodeURIComponent(state.activePersonaId)}/reference-packs/${encodeURIComponent(packId)}/canonical`, { selected: true, item_ids: itemIds });
    setStatus('Canonical identity anchors selected.', 'success');
    await loadViewData();
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

async function clearReferenceCanonical(packId) {
  try {
    await patch(`/api/personas/${encodeURIComponent(state.activePersonaId)}/reference-packs/${encodeURIComponent(packId)}/canonical`, { selected: false, item_ids: [] });
    setStatus('Canonical selection cleared.', 'success');
    await loadViewData();
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

async function reviewAsset(event) {
  const form = event.target;
  const assetId = form.dataset.assetReview;
  try {
    await patch(`/api/assets/${encodeURIComponent(assetId)}/review`, {
      review: form.elements.review.value,
      reviewer: form.elements.reviewer.value.trim(),
      reason: form.elements.reason.value.trim(),
    });
    setStatus('Asset review state saved.', 'success');
    await loadViewData();
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

async function assessAssetQuality(assetId) {
  state.assessingAssetId = assetId;
  renderView();
  try {
    await post(`/api/assets/${encodeURIComponent(assetId)}/quality`, {});
    state.assessingAssetId = '';
    setStatus('Asset quality evidence refreshed.', 'success');
    await loadViewData();
  } catch (error) {
    state.assessingAssetId = '';
    renderView();
    setStatus(error.message, 'error');
  }
}

async function recordAssetAssessment(event) {
  const form = event.target;
  const assetId = form.dataset.assetAssessment;
  const scoreFields = ['identity_score', 'anatomy_score', 'hands_score', 'facial_drift_score', 'temporal_stability_score', 'audio_timing_score'];
  const payload = { evaluator: form.elements.evaluator.value.trim(), notes: form.elements.notes.value.trim() };
  scoreFields.forEach((field) => {
    const value = form.elements[field].value.trim();
    if (value !== '') payload[field] = Number(value);
  });
  state.savingAssetAssessment = assetId;
  renderView();
  try {
    await post(`/api/assets/${encodeURIComponent(assetId)}/assessment`, payload);
    state.savingAssetAssessment = '';
    setStatus('Asset quality assessment saved.', 'success');
    await loadViewData();
  } catch (error) {
    state.savingAssetAssessment = '';
    renderView();
    setStatus(error.message, 'error');
  }
}

async function checkAssetPublishingReadiness(assetId) {
  try {
    const report = await get(`/api/assets/${encodeURIComponent(assetId)}/publishing-readiness`);
    state.assetPublishingReadiness[assetId] = report;
    renderView();
    setStatus(report.ready ? 'Asset is ready for the future publishing gate.' : 'Asset publishing readiness is blocked.', report.ready ? 'success' : 'error');
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

async function createPublishingAccount(event) {
  event.preventDefault();
  const form = event.target;
  const errorTarget = $('#publishing-account-form-error');
  if (!form.reportValidity()) return;
  if (errorTarget) { errorTarget.textContent = ''; errorTarget.hidden = true; }
  state.creatingPublishingAccount = true;
  renderView();
  try {
    await post(`/api/personas/${encodeURIComponent(state.activePersonaId)}/publishing-accounts`, {
      platform: form.elements.platform.value,
      account_label: form.elements.account_label.value.trim(),
      account_type: form.elements.account_type.value,
      handle: form.elements.handle.value.trim() || null,
      external_account_id: form.elements.external_account_id.value.trim() || null,
    });
    state.creatingPublishingAccount = false;
    setStatus('Local publishing account binding saved; verification remains deferred.', 'success');
    await loadViewData();
  } catch (error) {
    state.creatingPublishingAccount = false;
    renderView();
    setStatus(error.message, 'error');
  }
}

async function checkAssetPlatformReadiness(assetId) {
  try {
    const report = await get(`/api/assets/${encodeURIComponent(assetId)}/platform-readiness?platform=instagram`);
    state.assetPlatformReadiness[assetId] = report;
    renderView();
    const platform = report.platform_readiness || {};
    setStatus(platform.ready ? 'Asset is ready for the configured Instagram gate.' : 'Instagram readiness is blocked pending Phase 8 account and delivery requirements.', platform.ready ? 'success' : 'error');
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

function syncPublishingSelection(form) {
  state.selectedPublishingAccountId = form.elements.account_id?.value || '';
  state.selectedPublishingAssetId = form.elements.asset_id?.value || '';
  state.selectedPublishingArtifactId = form.elements.content_artifact_id?.value || '';
}

function publishingFormValues() {
  const form = $('#publishing-workflow-form');
  if (!form) return null;
  syncPublishingSelection(form);
  return {
    form,
    accountId: form.elements.account_id.value,
    assetId: form.elements.asset_id.value,
    contentArtifactId: form.elements.content_artifact_id.value,
    format: form.elements.format.value,
  };
}

async function checkPublishingWorkflowReadiness() {
  const values = publishingFormValues();
  if (!values?.accountId || !values.assetId || !values.format) {
    setStatus('Select an account, approved asset, and format before checking readiness.', 'error');
    return;
  }
  state.publishingBusy = true;
  renderView();
  try {
    state.publishingReadiness = await get(`/api/assets/${encodeURIComponent(values.assetId)}/platform-readiness?platform=instagram&format=${encodeURIComponent(values.format)}&account_id=${encodeURIComponent(values.accountId)}`);
    state.publishingBusy = false;
    renderView();
    const platform = state.publishingReadiness.platform_readiness || {};
    setStatus(platform.ready ? 'Instagram readiness passed.' : 'Instagram readiness is blocked; resolve the listed checks.', platform.ready ? 'success' : 'error');
  } catch (error) {
    state.publishingBusy = false;
    renderView();
    setStatus(error.message, 'error');
  }
}

async function recordPublishingDryRun() {
  const values = publishingFormValues();
  if (!values?.accountId || !values.assetId || !values.format || !values.contentArtifactId) {
    setStatus('Select an account, approved asset, format, and approved caption before recording a dry-run.', 'error');
    return;
  }
  state.publishingBusy = true;
  renderView();
  try {
    state.publishingResult = await post(`/api/assets/${encodeURIComponent(values.assetId)}/publish-dry-run`, {
      provider: 'local_dry_run', account_id: values.accountId, format: values.format,
      content_artifact_id: values.contentArtifactId,
      idempotency_key: `ui-dry-run-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    });
    state.publishingBusy = false;
    renderView();
    setStatus('Local publishing dry-run recorded; no external call was made.', 'success');
  } catch (error) {
    state.publishingBusy = false;
    state.publishingResult = { error: error.message, checks: error.payload?.detail?.checks || [] };
    renderView();
    setStatus(error.message, 'error');
  }
}

async function publishWorkflow(event) {
  event.preventDefault();
  const values = publishingFormValues();
  if (!values || !values.form.reportValidity()) return;
  const provider = publishingMetaProvider();
  if (!provider.supports_publish) {
    setStatus('Live Instagram publishing is disabled by provider configuration.', 'error');
    return;
  }
  if (!values.form.elements.confirm_external.checked) {
    setStatus('Confirm the external publishing action before continuing.', 'error');
    return;
  }
  state.publishingBusy = true;
  renderView();
  try {
    state.publishingResult = await post(`/api/assets/${encodeURIComponent(values.assetId)}/publish`, {
      provider: 'meta_instagram', account_id: values.accountId, format: values.format,
      content_artifact_id: values.contentArtifactId,
      idempotency_key: `ui-publish-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    });
    state.publishingBusy = false;
    renderView();
    setStatus('Instagram publish completed and was recorded in the audit trail.', 'success');
  } catch (error) {
    state.publishingBusy = false;
    state.publishingResult = { error: error.message, checks: error.payload?.detail?.checks || [] };
    renderView();
    setStatus(error.message, 'error');
  }
}

async function preparePublishingMedia(assetId) {
  state.publishingBusy = true;
  renderView();
  try {
    await post(`/api/assets/${encodeURIComponent(assetId)}/public-media`, {});
    state.publishingBusy = false;
    setStatus('Public media URL prepared locally; reachability is still a deployment responsibility.', 'success');
    await loadViewData();
  } catch (error) {
    state.publishingBusy = false;
    renderView();
    setStatus(error.message, 'error');
  }
}

async function verifyPublishingAccount(accountId) {
  state.verifyingPublishingAccountId = accountId;
  renderView();
  try {
    await post(`/api/publishing-accounts/${encodeURIComponent(accountId)}/verify`, {});
    state.verifyingPublishingAccountId = '';
    setStatus('Publishing account verification completed.', 'success');
    await loadViewData();
  } catch (error) {
    state.verifyingPublishingAccountId = '';
    renderView();
    setStatus(error.message, 'error');
  }
}

function creatorList(value) {
  return String(value || '').split(',').map((item) => item.trim()).filter(Boolean);
}

function showContentBriefFormError(message) {
  const target = $('#content-brief-form-error');
  if (!target) return;
  target.textContent = message;
  target.hidden = !message;
}

async function createContentBrief(event) {
  event.preventDefault();
  const form = event.target;
  showContentBriefFormError('');
  if (!form.reportValidity()) return;
  const briefId = state.editingContentBriefId;
  const payload = {
    title: form.elements.title.value.trim(),
    format: form.elements.format.value,
    content_class: form.elements.content_class.value,
    pillar_key: form.elements.pillar_key.value,
    audience_goal: form.elements.audience_goal.value.trim(),
    emotional_objective: form.elements.emotional_objective.value.trim(),
    story_direction: form.elements.story_direction.value.trim(),
    visual_direction: form.elements.visual_direction.value.trim(),
    motion_direction: form.elements.motion_direction.value.trim(),
    caption_direction: form.elements.caption_direction.value.trim(),
    script_direction: form.elements.script_direction.value.trim(),
    content_pack_id: form.elements.content_pack_id.value || null,
    disclosure: form.elements.disclosure.value.trim(),
  };
  state.creatingContentBrief = true;
  renderView();
  try {
    await (briefId
      ? put(`/api/personas/${encodeURIComponent(state.activePersonaId)}/content-briefs/${encodeURIComponent(briefId)}`, payload)
      : post(`/api/personas/${encodeURIComponent(state.activePersonaId)}/content-briefs`, payload));
    state.creatingContentBrief = false;
    state.editingContentBriefId = '';
    setStatus(briefId ? 'ContentBrief draft revision saved.' : 'ContentBrief draft saved. Freeze the PersonaVersion before approval.', 'success');
    await loadViewData();
  } catch (error) {
    state.creatingContentBrief = false;
    renderView();
    showContentBriefFormError(error.message);
    setStatus(error.message, 'error');
  }
}

function showContentArtifactFormError(message) {
  const target = $('#content-artifact-form-error');
  if (!target) return;
  target.textContent = message;
  target.hidden = !message;
}

function showContentArtifactEditError(message) {
  const target = $('#content-artifact-edit-error');
  if (!target) return;
  target.textContent = message;
  target.hidden = !message;
}

async function createContentArtifact(event) {
  event.preventDefault();
  const form = event.target;
  showContentArtifactFormError('');
  if (!form.reportValidity()) return;
  state.creatingContentArtifact = true;
  renderView();
  try {
    await post(`/api/personas/${encodeURIComponent(state.activePersonaId)}/content-briefs/${encodeURIComponent(form.elements.content_brief_id.value)}/artifacts`, {
      artifact_type: form.elements.artifact_type.value,
      content: form.elements.content.value.trim(),
    });
    state.creatingContentArtifact = false;
    setStatus('Content artifact draft created for review.', 'success');
    await loadViewData();
  } catch (error) {
    state.creatingContentArtifact = false;
    renderView();
    showContentArtifactFormError(error.message);
    setStatus(error.message, 'error');
  }
}

async function saveContentArtifact(event) {
  event.preventDefault();
  const form = event.target;
  showContentArtifactEditError('');
  if (!form.reportValidity()) return;
  const artifactId = state.editingContentArtifactId;
  state.creatingContentArtifact = true;
  renderView();
  try {
    await put(`/api/personas/${encodeURIComponent(state.activePersonaId)}/content-artifacts/${encodeURIComponent(artifactId)}`, {
      artifact_type: form.elements.artifact_type.value,
      content: form.elements.content.value.trim(),
    });
    state.creatingContentArtifact = false;
    state.editingContentArtifactId = '';
    setStatus('Content artifact revision saved and quality checks re-run.', 'success');
    await loadViewData();
  } catch (error) {
    state.creatingContentArtifact = false;
    renderView();
    showContentArtifactEditError(error.message);
    setStatus(error.message, 'error');
  }
}

async function assessContentArtifact(artifactId) {
  state.assessingContentArtifact = artifactId;
  renderView();
  try {
    await post(`/api/personas/${encodeURIComponent(state.activePersonaId)}/content-artifacts/${encodeURIComponent(artifactId)}/quality`, {});
    state.assessingContentArtifact = '';
    setStatus('Content artifact quality checks completed.', 'success');
    await loadViewData();
  } catch (error) {
    state.assessingContentArtifact = '';
    renderView();
    setStatus(error.message, 'error');
  }
}

async function approveContentArtifact(artifactId) {
  state.approvingContentArtifact = artifactId;
  renderView();
  try {
    await patch(`/api/personas/${encodeURIComponent(state.activePersonaId)}/content-artifacts/${encodeURIComponent(artifactId)}/review`, { review: 'approved' });
    state.approvingContentArtifact = '';
    setStatus('Content artifact approved and ready for downstream handoff.', 'success');
    await loadViewData();
  } catch (error) {
    state.approvingContentArtifact = '';
    renderView();
    setStatus(error.message, 'error');
  }
}

async function approveContentBrief(briefId) {
  state.approvingContentBrief = briefId;
  renderView();
  try {
    await patch(`/api/personas/${encodeURIComponent(state.activePersonaId)}/content-briefs/${encodeURIComponent(briefId)}/approve`, {});
    state.approvingContentBrief = '';
    setStatus('ContentBrief approved for production handoff.', 'success');
    await loadViewData();
  } catch (error) {
    state.approvingContentBrief = '';
    renderView();
    setStatus(error.message, 'error');
  }
}

async function handoffContentBrief(briefId) {
  try {
    const resolved = await get(`/api/personas/${encodeURIComponent(state.activePersonaId)}/content-briefs/${encodeURIComponent(briefId)}/resolve`);
    const handoff = resolved.production_handoff || {};
    const prompt = [handoff.story_direction, handoff.visual_direction, handoff.motion_direction, handoff.emotional_objective].filter(Boolean).join('\n\n').slice(0, 3000);
    sessionStorage.setItem(CANONICAL_GENERATION_DRAFT_KEY, JSON.stringify({
      workflow_id: '',
      prompt,
      width: 768,
      height: 1152,
      content_pack_id: resolved.content_pack?.id || '',
      brief_id: resolved.id,
      disclosure: handoff.disclosure,
      content_artifacts: resolved.content_artifacts || [],
    }));
    window.location.assign(`/workspace?persona_id=${encodeURIComponent(state.activePersonaId)}#production`);
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

function showCreatorFormError(message) {
  const target = $('#creator-profile-form-error');
  if (!target) return;
  target.textContent = message;
  target.hidden = !message;
}

async function saveCreatorProfile(event) {
  event.preventDefault();
  const form = event.target;
  showCreatorFormError('');
  const rows = [...form.querySelectorAll('[data-creator-pillar]')];
  const contentPillars = rows.map((row) => ({
    key: row.elements.pillar_key.value.trim(),
    name: row.elements.pillar_name.value.trim(),
    description: row.elements.pillar_description.value.trim(),
    formats: creatorList(row.elements.pillar_formats.value),
    content_classes: creatorList(row.elements.pillar_content_classes.value),
    identity_authority: row.elements.pillar_identity_authority.value,
    identity_core: row.elements.pillar_identity_core.checked,
    audience_goal: row.elements.pillar_audience_goal.value.trim(),
  }));
  state.savingCreatorProfile = true;
  renderView();
  try {
    await put(`/api/personas/${encodeURIComponent(state.activePersonaId)}/creator-profile`, {
      personality: {
        traits: form.elements.personality_traits.value.trim(),
        interests_and_values: form.elements.personality_interests.value.trim(),
        speech_style: form.elements.personality_speech_style.value.trim(),
        humor: form.elements.personality_humor.value.trim(),
        mannerisms: form.elements.personality_mannerisms.value.trim(),
      },
      audience: {
        primary: form.elements.audience_primary.value.trim(),
        needs: form.elements.audience_needs.value.trim(),
        relationship: form.elements.audience_relationship.value.trim(),
        locales: form.elements.audience_locales.value.trim(),
      },
      brand: {
        positioning: form.elements.brand_positioning.value.trim(),
        promise: form.elements.brand_promise.value.trim(),
        boundaries: form.elements.brand_boundaries.value.trim(),
      },
      voice: {
        tone: form.elements.voice_tone.value.trim(),
        vocabulary: form.elements.voice_vocabulary.value.trim(),
      },
      disclosure: form.elements.disclosure.value.trim(),
      content_pillars: contentPillars,
    });
    state.savingCreatorProfile = false;
    setStatus('Creator System saved for the active PersonaVersion.', 'success');
    await loadViewData();
  } catch (error) {
    state.savingCreatorProfile = false;
    renderView();
    showCreatorFormError(error.message);
    setStatus(error.message, 'error');
  }
}

function showBenchmarkFormError(message) {
  const target = $('#identity-benchmark-form-error');
  if (!target) return;
  target.textContent = message;
  target.hidden = !message;
}

async function createIdentityBenchmark(event) {
  event.preventDefault();
  const form = event.target;
  showBenchmarkFormError('');
  const methods = [...form.querySelectorAll('input[name="methods"]:checked')].map((input) => input.value);
  const scenarioIds = [...form.querySelectorAll('input[name="scenario_ids"]:checked')].map((input) => input.value);
  if (!methods.length || !scenarioIds.length) {
    showBenchmarkFormError('Select at least one identity method and one benchmark scenario.');
    return;
  }
  state.creatingBenchmark = true;
  renderView();
  try {
    await post(`/api/personas/${encodeURIComponent(state.activePersonaId)}/identity-benchmarks`, {
      base_model_id: form.elements.base_model_id.value.trim() || null,
      methods,
      scenario_ids: scenarioIds,
    });
    state.creatingBenchmark = false;
    setStatus('Identity benchmark plan created. Model execution remains deferred.', 'success');
    await loadViewData();
  } catch (error) {
    state.creatingBenchmark = false;
    renderView();
    showBenchmarkFormError(error.message);
    setStatus(error.message, 'error');
  }
}

async function recordIdentityBenchmarkResult(event) {
  event.preventDefault();
  const form = event.target;
  const metrics = {};
  ['identity_score', 'prompt_adherence', 'anatomy_score', 'style_consistency', 'latency_ms', 'peak_memory_mb'].forEach((name) => {
    if (form.elements[name].value !== '') metrics[name] = Number(form.elements[name].value);
  });
  try {
    await post(`/api/personas/${encodeURIComponent(state.activePersonaId)}/identity-benchmarks/${encodeURIComponent(form.dataset.benchmarkId)}/cases/${encodeURIComponent(form.dataset.identityBenchmarkResult)}/result`, {
      status: form.elements.status.value,
      metrics,
      notes: form.elements.notes.value.trim(),
      output_asset_id: form.elements.output_asset_id.value.trim() || null,
    });
    setStatus('Identity benchmark case recorded.', 'success');
    await loadViewData();
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

async function actOnJob(jobId, action) {
  try {
    await post(`/api/jobs/${encodeURIComponent(jobId)}/${action}`, {});
    setStatus(`Job ${action} request accepted.`, 'success');
    await loadViewData();
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

function readGenerationDraft(form) {
  return {
    workflow_id: form.elements.workflow_id.value,
    prompt: form.elements.prompt.value.trim(),
    width: Number(form.elements.width.value),
    height: Number(form.elements.height.value),
    content_pack_id: form.elements.content_pack_id.value,
    rights_confirmed: form.elements.rights_confirmed.checked,
  };
}

function syncGenerationDraft(form) {
  const nextDraft = readGenerationDraft(form);
  if (state.preflight && state.preflightFingerprint !== generationPreflightFingerprint(nextDraft)) {
    state.preflight = null;
    state.preflightFingerprint = '';
  }
  state.generationDraft = nextDraft;
}

async function runGenerationPreflight() {
  const form = $('#generation-form');
  if (!form) return;
  if (!form.reportValidity()) return;
  syncGenerationDraft(form);
  if (!state.generationDraft.workflow_id) {
    setStatus('Select a verified workflow before running preflight.', 'error');
    return;
  }
  state.preflighting = true;
  renderView();
  const { workflow_id: workflowId, width, height } = state.generationDraft;
  const requestFingerprint = generationPreflightFingerprint(state.generationDraft);
  try {
    const result = await get(`/api/preflight?workflow_id=${encodeURIComponent(workflowId)}&width=${encodeURIComponent(width)}&height=${encodeURIComponent(height)}`);
    const liveForm = $('#generation-form');
    const liveDraft = liveForm ? readGenerationDraft(liveForm) : state.generationDraft;
    if (requestFingerprint !== generationPreflightFingerprint(liveDraft)) {
      state.generationDraft = liveDraft;
      state.preflighting = false;
      state.preflight = null;
      state.preflightFingerprint = '';
      renderView();
      setStatus('Generation inputs changed while preflight was running. Run preflight again.', 'error');
      return;
    }
    state.generationDraft = liveDraft;
    state.preflight = result;
    state.preflightFingerprint = requestFingerprint;
    state.preflighting = false;
    renderView();
    setStatus(`Preflight ${state.preflight.overall}.`, state.preflight.overall === 'ready' ? 'success' : 'error');
  } catch (error) {
    state.preflighting = false;
    state.preflight = null;
    state.preflightFingerprint = '';
    renderView();
    setStatus(error.message, 'error');
  }
}

async function createGenerationJob(event) {
  event.preventDefault();
  const form = event.target;
  if (!form.reportValidity()) return;
  syncGenerationDraft(form);
  if (!state.generationDraft.rights_confirmed) {
    setStatus('Confirm rights and likeness inputs before queueing generation.', 'error');
    return;
  }
  if (state.preflight?.overall !== 'ready') {
    renderView();
    setStatus('Run a passing preflight before queueing generation.', 'error');
    return;
  }
  state.submittingJob = true;
  renderView();
  try {
    const queued = await post('/api/jobs', {
      persona_id: state.activePersonaId,
      workflow_id: state.generationDraft.workflow_id,
      prompt: state.generationDraft.prompt,
      width: state.generationDraft.width,
      height: state.generationDraft.height,
      content_pack_id: state.generationDraft.content_pack_id || null,
      rights_confirmed: true,
    });
    state.submittingJob = false;
    state.preflight = null;
    state.preflightFingerprint = '';
    state.generationDraftImported = false;
    state.generationSourceModel = '';
    setStatus(`Generation job ${queued.id} queued.`, 'success');
    await loadViewData();
  } catch (error) {
    state.submittingJob = false;
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
  const referencePackButton = event.target.closest('button[data-reference-pack-id]');
  if (referencePackButton) {
    state.selectedReferencePackId = referencePackButton.dataset.referencePackId;
    renderView();
    return;
  }
  const clearCanonicalButton = event.target.closest('[data-clear-reference-canonical]');
  if (clearCanonicalButton) {
    clearReferenceCanonical(clearCanonicalButton.dataset.clearReferenceCanonical);
    return;
  }
  const jobButton = event.target.closest('[data-job-action]');
  if (jobButton) {
    actOnJob(jobButton.dataset.jobId, jobButton.dataset.jobAction);
    return;
  }
  const generationAction = event.target.closest('[data-generation-action]');
  if (generationAction) {
    runGenerationPreflight();
    return;
  }
  const editBriefButton = event.target.closest('[data-brief-edit]');
  if (editBriefButton) {
    state.editingContentBriefId = editBriefButton.dataset.briefEdit;
    renderView();
    return;
  }
  const editArtifactButton = event.target.closest('[data-artifact-edit]');
  if (editArtifactButton) {
    state.editingContentArtifactId = editArtifactButton.dataset.artifactEdit;
    renderView();
    return;
  }
  const cancelBriefButton = event.target.closest('[data-brief-cancel]');
  if (cancelBriefButton) {
    state.editingContentBriefId = '';
    renderView();
    return;
  }
  const cancelArtifactButton = event.target.closest('[data-artifact-edit-cancel]');
  if (cancelArtifactButton) {
    state.editingContentArtifactId = '';
    renderView();
    return;
  }
  const approveArtifactButton = event.target.closest('[data-artifact-approve]');
  if (approveArtifactButton) {
    approveContentArtifact(approveArtifactButton.dataset.artifactApprove);
    return;
  }
  const qualityArtifactButton = event.target.closest('[data-artifact-quality]');
  if (qualityArtifactButton) {
    assessContentArtifact(qualityArtifactButton.dataset.artifactQuality);
    return;
  }
  const qualityAssetButton = event.target.closest('[data-asset-quality]');
  if (qualityAssetButton) {
    assessAssetQuality(qualityAssetButton.dataset.assetQuality);
    return;
  }
  const publishingReadinessButton = event.target.closest('[data-asset-publishing-readiness]');
  if (publishingReadinessButton) {
    checkAssetPublishingReadiness(publishingReadinessButton.dataset.assetPublishingReadiness);
    return;
  }
  const platformReadinessButton = event.target.closest('[data-asset-platform-readiness]');
  if (platformReadinessButton) {
    checkAssetPlatformReadiness(platformReadinessButton.dataset.assetPlatformReadiness);
    return;
  }
  const workflowReadinessButton = event.target.closest('[data-publishing-readiness]');
  if (workflowReadinessButton) {
    checkPublishingWorkflowReadiness();
    return;
  }
  const dryRunButton = event.target.closest('[data-publishing-dry-run]');
  if (dryRunButton) {
    recordPublishingDryRun();
    return;
  }
  const prepareMediaButton = event.target.closest('[data-publishing-prepare-media]');
  if (prepareMediaButton) {
    preparePublishingMedia(prepareMediaButton.dataset.publishingPrepareMedia);
    return;
  }
  const verifyAccountButton = event.target.closest('[data-publishing-verify]');
  if (verifyAccountButton) {
    verifyPublishingAccount(verifyAccountButton.dataset.publishingVerify);
    return;
  }
  const approveBriefButton = event.target.closest('[data-brief-approve]');
  if (approveBriefButton) {
    approveContentBrief(approveBriefButton.dataset.briefApprove);
    return;
  }
  const handoffBriefButton = event.target.closest('[data-brief-handoff]');
  if (handoffBriefButton) {
    handoffContentBrief(handoffBriefButton.dataset.briefHandoff);
    return;
  }
  const button = event.target.closest('[data-view]');
  if (button) navigate(button.dataset.view);
});
$('#workspace-view').addEventListener('submit', (event) => {
  if (event.target.id === 'persona-create-form') {
    createPersona(event);
    return;
  }
  if (event.target.id === 'generation-form') {
    createGenerationJob(event);
    return;
  }
  if (event.target.id === 'creator-profile-form') {
    saveCreatorProfile(event);
    return;
  }
  if (event.target.id === 'content-brief-form') {
    createContentBrief(event);
    return;
  }
  if (event.target.id === 'content-artifact-create-form') {
    createContentArtifact(event);
    return;
  }
  if (event.target.id === 'content-artifact-edit-form') {
    saveContentArtifact(event);
    return;
  }
  if (event.target.id === 'identity-benchmark-create-form') {
    createIdentityBenchmark(event);
    return;
  }
  if (event.target.id === 'publishing-account-form') {
    createPublishingAccount(event);
    return;
  }
  if (event.target.id === 'publishing-workflow-form') {
    publishWorkflow(event);
    return;
  }
  if (event.target.matches('[data-identity-benchmark-result]')) {
    recordIdentityBenchmarkResult(event);
    return;
  }
  if (event.target.matches('[data-reference-pack-review]')) {
    event.preventDefault();
    reviewReferencePack(event);
    return;
  }
  if (event.target.matches('[data-reference-item-review]')) {
    event.preventDefault();
    reviewReferenceItem(event);
    return;
  }
  if (event.target.matches('[data-reference-item-asset]')) {
    event.preventDefault();
    linkReferenceAsset(event);
    return;
  }
  if (event.target.matches('[data-reference-canonical]')) {
    event.preventDefault();
    selectReferenceCanonical(event);
    return;
  }
  if (event.target.matches('[data-asset-review]')) {
    event.preventDefault();
    reviewAsset(event);
    return;
  }
  if (event.target.matches('[data-asset-assessment]')) {
    event.preventDefault();
    recordAssetAssessment(event);
  }
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

'use strict';

import { $, clear, copyText, el, emptyAction, names, notify, options, readableValue, state } from './modules/core.js';
import { api, post } from './modules/api.js';
import { mountNavigation, setNavGroupOpen } from './modules/navigation.js';
import { initPhotoStudio, renderPhotoStudio } from './modules/photostudio.js';
import { initOrchestrator } from './modules/orchestrator.js';

const CHATGPT_BRIEF_PROMPT = `You are a production planner for a local, self-hosted AI media pipeline.
Return ONLY valid UTF-8 JSON matching config/generation_brief.example.json with schema_version "1.0". Do not add Markdown fences or commentary.

Create one original fictional adult fashion, glamour or lifestyle persona. The character must be 18 or older and clearly disclosed as AI-generated. Bold glamour, sensual editorial styling, swimwear and lingerie-inspired fashion are allowed when the subject is clearly an adult and the context is non-explicit. Do not use a real person's name, face, body, voice or private data, and do not describe minors, explicit sexual acts, impersonation or deceptive real-person content.

Make the persona distinctive by combining: an original name; adult age; facial geometry; hair, eyes and skin details; one subtle fictional distinguishing mark; body proportions; adult age cues; posture and movement; wardrobe; materials and palette; accessories and grooming; glamour direction; personality traits; interests and values; speech style; mannerisms; cultural/world setting; home base; recurring locations; content pillars; camera framing; lens and depth; lighting; color grade; and a consistent identity anchor. Avoid generic words such as "beautiful model" without concrete traits.

Allowed image models: flux2-klein-4b, z-image-turbo.
Allowed video model: wan22-ti2v-5b.
Allowed sizes: 1280*704 or 704*1280.

INPUTS TO FILL:
- Character name or naming style:
- Adult age:
- Facial features, hair, eyes, skin and fictional distinguishing mark:
- Body proportions and glamour direction:
- Personality, interests and content lane:
- Cultural/world setting and recurring locations:
- Wardrobe, materials and color palette:
- Image scene, lighting and composition:
- Video action, expression and camera movement:
- Optional narration text and tone:
- Vertical or landscape aspect ratio:
- Seed, or let the system choose one:

The persona.characteristics object must contain face, physique, style, personality, world and camera sections with the detailed traits above. Return schema_version, title, persona, image, video, voice, assembly and review. Keep the same identity anchor in both image and video prompts. Include a useful negative prompt and the AI disclosure.`;

const PERSONA_BRIEF_PROMPT = `Create one original fictional adult persona for a local AI fashion/lifestyle studio.
Return ONLY valid UTF-8 JSON in this shape: {"schema_version":"persona-1.0","persona":{...}}. Do not add Markdown fences or commentary.

The persona must be 18 or older and clearly disclosed as AI-generated. Bold glamour, sensual editorial styling, swimwear and lingerie-inspired fashion are allowed when the subject is clearly an adult and the context is non-explicit. Never use a real person's name, face, body, voice or private data. Do not describe minors, explicit sexual acts, impersonation or deceptive real-person content.

Fill every field with specific, visual, production-ready details. Avoid generic phrases such as "beautiful model". Use contrast and recurring signatures so the character is recognisable: face geometry, complexion, eye shape and color, hair texture and parting, one subtle fictional distinguishing feature, adult proportions, posture, wardrobe silhouettes, materials, palette, accessories, grooming, glamour direction, personality contradictions, interests, speech style, mannerisms, world setting, recurring locations, content pillars and camera language.

INPUTS TO PROVIDE:
- Naming style and character name (or ask for three options):
- Adult age:
- Face shape, complexion, eyes, hair and fictional distinguishing feature:
- Adult build, posture, movement and age cues:
- Wardrobe, fabrics, palette, accessories, grooming and glamour direction:
- Personality traits, interests, values, speech style and mannerisms:
- Cultural/world context supplied by the creator, home base and recurring locations:
- Content pillars, glamour direction and platform/disclosure boundaries:
- Default framing, lens/depth, lighting and color grade:
- Consistency anchor: traits that must never change:

Return name, age, appearance, description, consistency_anchor, disclosure and a characteristics object containing face, physique, style, personality, world and camera sections.`;

const pipelineSteps = [
  ['persona', 'Persona', 'personas', 'persona-library'],
  ['photo', 'Photo Studio', 'photostudio', 'photo-studio'],
  ['brief', 'Brief', 'generate', 'generation-brief'],
  ['image', 'Master image', 'generate', 'image-studio'],
  ['video', 'Motion video', 'generate', 'video-studio'],
  ['voice', 'Voice (optional)', 'voice', 'voice-studio'],
  ['review', 'Review & export', 'assets', 'media-review'],
  ['series', 'Series reuse', 'series', 'series-studio']
];

function renderPipelineRail() {
  const rail = $('#pipeline-rail');
  if (!rail) return;
  const activePanel = document.querySelector('.panel.active')?.id;
  const activeKey = document.querySelector('.nav.active')?.dataset.navKey;
  rail.querySelectorAll('.pipeline-rail-step').forEach((step) => {
    const active = step.dataset.navKey === activeKey || (!activeKey && step.dataset.target === activePanel);
    step.classList.toggle('active', active);
  });
}

function mountPipelineRail() {
  const main = $('.main');
  if (!main || $('#pipeline-rail')) return;
  const rail = el('div', { id: 'pipeline-rail', class: 'pipeline-rail', 'aria-label': 'Connected production pipeline' });
  const intro = el('div', { class: 'pipeline-rail-intro' });
  intro.append(el('span', { class: 'eyebrow' }, 'CONNECTED PIPELINE'), el('small', {}, 'Each approved output becomes the next step’s input.'));
  rail.append(intro);
  const steps = el('div', { class: 'pipeline-rail-steps' });
  pipelineSteps.forEach(([key, label, target, navKey], index) => {
    const button = el('button', { type: 'button', class: 'pipeline-rail-step', 'data-target': target, 'data-nav-key': navKey });
    button.append(el('b', {}, String(index + 1).padStart(2, '0')), el('span', {}, label));
    button.addEventListener('click', () => {
      const nav = document.querySelector('[data-nav-key="' + navKey + '"]');
      tab(target, nav || button);
    });
    steps.append(button);
    if (index < pipelineSteps.length - 1) steps.append(el('span', { class: 'pipeline-rail-line', 'aria-hidden': 'true' }));
  });
  rail.append(steps);
  const anchor = $('#dashboard');
  main.insertBefore(rail, anchor || main.firstChild);
  renderPipelineRail();
}

function mountDashboardLayout() {
  const dashboard = $('#dashboard');
  if (!dashboard || dashboard.dataset.modernLayout === 'true') return;
  dashboard.dataset.modernLayout = 'true';
  dashboard.innerHTML = `<div class="dashboard-welcome"><div><p class="eyebrow">TURN IDEAS INTO CONSISTENT MEDIA</p><h1>Welcome to Persona Studio</h1><p class="dashboard-lede">Plan, create and produce consistent media with fictional AI personas — from idea to series.</p></div><button class="workspace-selector" type="button"><span class="workspace-selector-icon">◎</span><span><small>Workspace</small><strong>Creative team</strong></span><b>⌄</b></button></div><div class="dashboard-kpis"><div><span>PERSONAS</span><strong id="m-personas">0</strong><small>Identity records</small></div><div><span>RENDER JOBS</span><strong id="m-jobs">0</strong><small>Across all stages</small></div><div><span>MEDIA FILES</span><strong id="m-assets">0</strong><small>Images, video &amp; audio</small></div><div><span>APPROVED</span><strong id="m-approved">0</strong><small>Ready for export</small></div><div><span>TRACKED CLICKS</span><strong id="m-clicks">0</strong><small>Controlled links</small></div></div><div class="dashboard-two-col"><article class="card next-action-card"><div class="card-heading"><div><p class="eyebrow">NEXT ACTION</p><h3 id="dashboard-next-title">Complete your project brief</h3></div><span class="next-action-mark">✦</span></div><div class="next-action-body"><div class="next-action-icon">▤</div><div><p id="dashboard-next-copy">Add the identity, scene and motion details needed to generate consistent images, video and voice.</p><div class="hero-actions"><button class="primary go-tab" data-target="generate" type="button">Open brief <span aria-hidden="true">→</span></button><button class="secondary go-tab" data-target="personas" type="button">View personas</button></div></div></div></article><article class="card identity-consistency-card"><div class="card-heading"><div><p class="eyebrow">IDENTITY CONSISTENCY</p><h3>Frozen character library</h3></div><button class="text-action go-tab" data-target="personas" type="button">View all →</button></div><div id="dashboard-identity" class="identity-grid"></div></article></div><div class="dashboard-two-col dashboard-lower"><article class="card queue-dashboard-card"><div class="card-heading"><div><p class="eyebrow">PRODUCE</p><h3>Active render queue</h3></div><button class="text-action go-tab" data-target="generate" type="button">View all →</button></div><div id="dashboard-queue"></div></article><article class="card system-dashboard-card"><div class="card-heading"><div><p class="eyebrow">OPERATIONS</p><h3>System status</h3></div><button class="text-action go-tab" data-target="monitoring" type="button">Check all →</button></div><div class="system-status-summary"><span>All studio services</span><span><i class="system-dot ready"></i>Operational</span></div><div id="dashboard-system-status" class="system-status-grid"></div></article></div><section class="card dashboard-media-card"><div class="card-heading"><div><p class="eyebrow">LIBRARY</p><h3>Recent generated media</h3></div><button class="text-action go-tab" data-target="assets" type="button">View all →</button></div><div id="dashboard-recent-media" class="recent-media-grid"></div></section></section>`;
}

function mountTopbarEnhancements() {
  const actions = $('.topbar-actions');
  if (!actions || $('#global-search')) return;
  const search = el('label', { class: 'global-search' });
  search.append(el('span', { class: 'global-search-icon', 'aria-hidden': 'true' }, '⌕'));
  const input = el('input', { id: 'global-search', type: 'search', placeholder: 'Search personas, assets or studio sections…', 'aria-label': 'Search personas, assets or studio sections' });
  search.append(input, el('kbd', {}, '⌘ K'));
  actions.insertBefore(search, actions.firstChild);
  input.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    const query = input.value.trim().toLowerCase();
    if (!query) return;
    const persona = state.personas.find((item) => item.name.toLowerCase().includes(query));
    const asset = state.assets.find((item) => (item.prompt || '').toLowerCase().includes(query));
    const nav = [...document.querySelectorAll('.nav')].find((item) => item.textContent.toLowerCase().includes(query));
    if (persona) tab('personas', document.querySelector('[data-nav-key="persona-library"]'));
    else if (asset) tab('assets', document.querySelector('[data-nav-key="media-review"]'));
    else if (nav) nav.click();
    else notify('No studio result matched "' + input.value + '"', true);
  });
}

function mountDashboardMedia() {
  if ($('#dashboard-recent-media')) return;
  const dashboard = $('#dashboard');
  const grid = dashboard?.querySelector('.dashboard-grid');
  if (!grid) return;
  const card = el('section', { class: 'card dashboard-media-card' });
  const heading = el('div', { class: 'card-heading' });
  const copy = el('div');
  copy.append(el('p', { class: 'eyebrow' }, 'RECENT GENERATED'), el('h3', {}, 'Image & video library'));
  heading.append(copy);
  const open = el('button', { type: 'button', class: 'secondary' }, 'Open media review →');
  open.addEventListener('click', () => tab('assets', document.querySelector('[data-nav-key="media-review"]')));
  heading.append(open);
  card.append(heading, el('div', { id: 'dashboard-recent-media', class: 'recent-media-grid' }));
  grid.insertAdjacentElement('afterend', card);
}

function tab(id, trigger = null) {
  document.querySelectorAll('.panel').forEach((panel) => panel.classList.toggle('active', panel.id === id));
  const navKey = trigger?.dataset?.navKey || null;
  let selected = false;
  document.querySelectorAll('.nav').forEach((nav) => {
    const active = navKey ? nav.dataset.navKey === navKey : (!selected && nav.dataset.tab === id);
    if (active) selected = true;
    nav.classList.toggle('active', active);
    if (active) nav.setAttribute('aria-current', 'page');
    else nav.removeAttribute('aria-current');
  });
  document.querySelectorAll('.nav-group').forEach((group) => {
    const active = !!group.querySelector('.nav.active');
    group.classList.toggle('active', active);
    if (active) setNavGroupOpen(group, true);
  });
  $('#page-title').textContent = names[id] || id;
  renderPipelineRail();
  window.scrollTo({ top: 0 });
  if (id === 'generate') refreshReferences();
  if (id === 'photostudio') renderPhotoStudio();
  if (id === 'monitoring') refreshMonitor();
  const focus = trigger?.dataset?.focus;
  if (focus) window.setTimeout(() => document.getElementById(focus)?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
}

async function refresh() {
  try {
    const [personas, workflows, jobs, assets, links, summary, health, checkpoints, series, models] = await Promise.all([
      api('/api/personas'), api('/api/workflows'), api('/api/jobs'), api('/api/assets'),
      api('/api/links'), api('/api/summary'), api('/api/health'), api('/api/checkpoints'), api('/api/series'), api('/api/models')
    ]);
    Object.assign(state, { personas, workflows, jobs, assets, links, series, models, health, checkpoints: checkpoints.checkpoints || [] });
    for (const key of ['personas', 'jobs', 'assets', 'approved', 'clicks']) $('#m-' + key).textContent = summary[key];
    const connected = health.comfyui === 'connected';
    $('#comfy-status').textContent = connected ? 'ComfyUI bridge connected' : 'Direct CLI path available';
    $('#status-detail').textContent = connected ? 'Dashboard queue online' : 'Optional bridge offline';
    $('#status-dot').classList.toggle('ok', connected);
    const gpuStatus = $('#readiness-gpu');
    if (gpuStatus) { gpuStatus.textContent = connected ? 'Bridge online' : 'CLI path'; gpuStatus.classList.remove('muted'); }
    renderAll();
  } catch (error) {
    notify('Refresh failed: ' + error.message, true);
  }
}

async function refreshMonitor() {
  const button = $('#monitor-refresh');
  if (button) button.disabled = true;
  try {
    state.monitoring = await api('/api/monitor');
    renderMonitor();
  } catch (error) {
    notify('Monitoring check failed: ' + error.message, true);
  } finally {
    if (button) button.disabled = false;
  }
}

function renderAll() {
  const personaOptions = state.personas.map((persona) => ({ value: persona.id, name: persona.name + ' (' + persona.age + ')' }));
  options('#r-persona', personaOptions, 'Select a persona');
  options('#g-persona', personaOptions, 'Select a persona');
  options('#v-persona', personaOptions, 'Select a persona');
  const generationWorkflow = options('#g-workflow', state.workflows.filter((workflow) => workflow.category === 'image' || workflow.category === 'video').map((workflow) => ({ value: workflow.id, name: (workflow.label || workflow.id) + (workflow.ready ? '' : ' · setup required') + (workflow.requires_reference ? ' · reference' : '') })), 'Select workflow');
  if (generationWorkflow && !generationWorkflow.value) {
    const defaultImage = state.workflows.find((workflow) => workflow.id === 'default_image_api' && workflow.ready);
    if (defaultImage) generationWorkflow.value = defaultImage.id;
  }
  options('#g-checkpoint', state.checkpoints.map((checkpoint) => ({ value: checkpoint, name: checkpoint })), 'Choose a local checkpoint');
  renderPhotoStudio();
  if ($('#series-persona')) options('#series-persona', state.personas.filter((persona) => persona.identity_locked).map((persona) => ({ value: persona.id, name: persona.name + ' · frozen v' + persona.identity_version })), 'Freeze a persona first');
  if ($('#series-workflow')) {
    options('#series-workflow', state.workflows.filter((workflow) => workflow.ready && workflow.category === 'video').map((workflow) => ({ value: workflow.id, name: workflow.label || workflow.id })), 'Optional: select a verified graph for dashboard queue');
    $('#series-workflow').removeAttribute('required');
    if (!$('#series-workflow').value) {
      const defaultVideo = state.workflows.find((workflow) => workflow.id === 'wan22_ti2v_5b_default_api' && workflow.ready);
      if (defaultVideo) $('#series-workflow').value = defaultVideo.id;
    }
  }
  if ($('#asset-import-persona')) options('#asset-import-persona', personaOptions, 'Select persona for imported output');
  renderPersonas(); renderJobs(); renderDashboardMedia(); renderDashboardIdentity(); renderDashboardQueue(); renderDashboardSystem(); renderDashboardNextAction(); renderGallery(); renderLinks(); renderWorkflows(); renderSeries(); refreshReferences();
}

function mediaPreview(asset, className = '') {
  const preview = el('div', { class: 'media-preview ' + className + ' media-kind-' + asset.kind });
  const url = '/api/assets/' + asset.id + '/file';
  if (asset.kind === 'image') preview.append(el('img', { src: url, loading: 'lazy', alt: 'Generated image for ' + asset.persona_name }));
  else if (asset.kind === 'video') preview.append(el('video', { src: url, controls: '', muted: '', preload: 'metadata' }));
  else preview.append(el('span', { class: 'media-audio-mark', 'aria-label': 'Generated audio' }, 'AUDIO'));
  return preview;
}

function renderDashboardMedia() {
  const root = $('#dashboard-recent-media');
  if (!root) return;
  clear(root);
  const recent = state.assets.filter((asset) => asset.kind === 'image' || asset.kind === 'video').slice(0, 6);
  if (!recent.length) {
    root.append(el('p', { class: 'muted' }, 'Generated images and videos will appear here after your first render.'), emptyAction('generate', 'Open image or video studio →'));
    return;
  }
  recent.forEach((asset) => {
    const item = el('article', { class: 'recent-media-item' });
    item.append(mediaPreview(asset, 'recent-media-preview'));
    const body = el('div', { class: 'recent-media-copy' });
    body.append(el('strong', {}, asset.persona_name), el('small', {}, asset.kind.toUpperCase() + ' · ' + asset.review));
    body.append(el('span', { class: 'media-status status-' + asset.review }, asset.review));
    item.append(body);
    item.addEventListener('click', () => tab('assets', document.querySelector('[data-nav-key="media-review"]')));
    root.append(item);
  });
}

function renderDashboardIdentity() {
  const root = $('#dashboard-identity');
  if (!root) return;
  clear(root);
  const personas = state.personas.slice(0, 3);
  if (!personas.length) {
    root.append(el('p', { class: 'muted' }, 'Your frozen persona profiles will appear here.'), emptyAction('personas', 'Create a persona →'));
    return;
  }
  personas.forEach((persona) => {
    const card = el('article', { class: 'identity-card' });
    const visual = el('div', { class: 'identity-visual' });
    const image = state.assets.find((asset) => asset.persona_id === persona.id && asset.kind === 'image' && asset.review === 'approved') || state.assets.find((asset) => asset.persona_id === persona.id && asset.kind === 'image');
    if (image) visual.append(el('img', { src: '/api/assets/' + image.id + '/file', loading: 'lazy', alt: persona.name + ' reference' }));
    else visual.append(el('span', { class: 'identity-initials' }, persona.name.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase()));
    const copy = el('div', { class: 'identity-copy' });
    const frozen = Boolean(persona.identity_locked);
    copy.append(el('strong', {}, persona.name), el('small', {}, 'Age ' + persona.age + ' · ' + (frozen ? 'Frozen identity v' + persona.identity_version : 'Draft identity')));
    const status = el('span', { class: 'identity-status ' + (frozen ? 'consistent' : 'attention') });
    status.append(el('i', { 'aria-hidden': 'true' }), frozen ? 'Consistent' : 'Needs freeze');
    copy.append(status);
    const bar = el('div', { class: 'identity-meter' });
    const fill = el('span'); fill.style.width = frozen ? '100%' : '48%'; bar.append(fill);
    copy.append(bar);
    card.append(visual, copy);
    root.append(card);
  });
}

function renderDashboardQueue() {
  const root = $('#dashboard-queue');
  if (!root) return;
  clear(root);
  if (!state.jobs.length) {
    root.append(el('p', { class: 'muted' }, 'No render jobs yet. Start an image or video job to see it here.'), emptyAction('generate', 'Open generation →'));
    return;
  }
  const table = el('div', { class: 'queue-table', role: 'table', 'aria-label': 'Active render queue' });
  const header = el('div', { class: 'queue-row queue-header', role: 'row' });
  ['#', 'Name', 'Type', 'Persona', 'Status', 'Progress', 'Actions'].forEach((label) => header.append(el('span', { role: 'columnheader' }, label)));
  table.append(header);
  state.jobs.slice(0, 6).forEach((job, index) => {
    const row = el('div', { class: 'queue-row', role: 'row' });
    const progress = job.status === 'completed' ? 100 : job.status === 'running' ? 58 : job.status === 'failed' ? 0 : 12;
    row.append(el('span', { class: 'queue-number' }, String(index + 1).padStart(2, '0')), el('strong', {}, (job.prompt || '').slice(0, 34) || 'Untitled render'), el('span', {}, job.workflow_id || job.type || 'Render'), el('span', {}, job.persona_name || '—'));
    row.append(el('span', { class: 'queue-status status-' + job.status }, job.status));
    const progressCell = el('span', { class: 'queue-progress' });
    const progressBar = el('i'); progressBar.style.setProperty('--progress', progress + '%'); progressCell.append(progressBar, el('small', {}, progress + '%'));
    const actions = el('span', { class: 'queue-actions' });
    appendJobActions(actions, state.jobs[index]);
    row.append(progressCell, actions);
    table.append(row);
  });
  root.append(table);
}

function renderDashboardSystem() {
  const root = $('#dashboard-system-status');
  if (!root) return;
  clear(root);
  const connected = state.health?.comfyui === 'connected';
  const summary = document.querySelector('.system-status-summary');
  if (summary) {
    const statusText = summary.querySelector('span:last-child');
    if (statusText) statusText.innerHTML = '<i class="system-dot ready"></i>' + (connected ? 'GPU bridge online' : 'Direct CLI ready');
  }
  const items = [
    ['Image generation', 'Local CLI ready', true, 'image'],
    ['Video generation', connected ? 'ComfyUI connected' : 'CLI path available', true, 'video'],
    ['Voice generation', 'Kokoro optional', true, 'voice'],
    ['Exports & delivery', 'Manual review required', true, 'export']
  ];
  items.forEach(([label, detail, ready, kind]) => {
    const item = el('button', { type: 'button', class: 'system-status-item' });
    item.append(el('span', { class: 'system-status-icon system-' + kind, 'aria-hidden': 'true' }, kind === 'image' ? '▧' : kind === 'video' ? '▷' : kind === 'voice' ? '◖' : '↑'));
    const copy = el('span'); copy.append(el('strong', {}, label), el('small', {}, detail));
    const dot = el('i', { class: ready ? 'system-dot ready' : 'system-dot' });
    item.append(copy, dot);
    item.addEventListener('click', () => tab(kind === 'export' ? 'assets' : kind === 'voice' ? 'voice' : 'generate'));
    root.append(item);
  });
}

function renderDashboardNextAction() {
  const title = $('#dashboard-next-title');
  const copy = $('#dashboard-next-copy');
  const primary = document.querySelector('.next-action-card .primary.go-tab');
  if (!title || !copy || !primary) return;
  let next;
  if (!state.personas.length) {
    next = ['Create your first persona', 'Start with an original fictional adult identity, then freeze its visual anchors for continuity.', 'personas', 'Create persona'];
  } else if (!state.jobs.length) {
    next = ['Load a generation brief', 'Turn the frozen identity into a master image and motion-ready scene without leaving the local pipeline.', 'generate', 'Open brief'];
  } else if (!state.assets.length) {
    next = ['Review the first render', 'Your queue has work in progress. Inspect the output for identity, anatomy, rights and disclosure before approval.', 'generate', 'Open queue'];
  } else {
    next = ['Continue the character series', 'Reuse the approved master image, voice and continuity anchor to plan the next episode.', 'series', 'Open series'];
  }
  title.textContent = next[0];
  copy.textContent = next[1];
  primary.dataset.target = next[2];
  primary.childNodes[0].textContent = next[3] + ' ';
}

function renderPersonas() {
  const root = $('#personas-list'); clear(root);
  if (!state.personas.length) {
    root.append(el('p', { class: 'muted' }, 'No persona yet. Start with an original fictional adult identity.'), emptyAction('personas', 'Create the first persona →'));
    return;
  }
  for (const persona of state.personas) {
    const box = el('div', { class: 'listitem' });
    box.append(el('strong', {}, persona.name), el('small', {}, 'Age ' + persona.age + ' · ' + persona.disclosure));
    box.append(el('small', {}, persona.appearance.slice(0, 110)));
    const actions = el('div', { class: 'persona-list-actions' });
    if (persona.identity_locked) {
      actions.append(el('span', { class: 'pill approved' }, 'Identity frozen v' + persona.identity_version));
      actions.append(el('small', { class: 'muted' }, 'Use this canonical profile for every new episode.'));
    } else {
      const freeze = el('button', { type: 'button', class: 'secondary' }, 'Freeze identity');
      freeze.addEventListener('click', async () => {
        try { await api('/api/personas/' + persona.id + '/freeze', { method: 'POST' }); notify(persona.name + ' identity frozen'); await refresh(); }
        catch (error) { notify(error.message, true); }
      });
      actions.append(freeze, el('small', { class: 'muted' }, 'Freeze after appearance and references are final.'));
    }
    box.append(actions);
    const media = state.assets.filter((asset) => asset.persona_id === persona.id && (asset.kind === 'image' || asset.kind === 'video')).slice(0, 4);
    if (media.length) {
      const strip = el('div', { class: 'persona-media-strip' });
      media.forEach((asset) => {
        const thumb = mediaPreview(asset, 'persona-media-thumb');
        thumb.title = 'Open media review';
        thumb.addEventListener('click', () => tab('assets', document.querySelector('[data-nav-key="media-review"]')));
        strip.append(thumb);
      });
      box.append(el('small', { class: 'persona-media-label' }, 'Recent generated media'), strip);
    } else box.append(el('small', { class: 'persona-media-empty' }, 'No generated image or video yet'));
    root.append(box);
  }
}

async function refreshReferences() {
  const personaId = $('#g-persona').value;
  const select = $('#g-reference');
  const previous = select.value;
  clear(select); select.append(el('option', { value: '' }, 'No reference supplied'));
  if (personaId) {
    try {
      const references = await api('/api/personas/' + personaId + '/references');
      for (const reference of references) select.append(el('option', { value: 'ref:' + reference.id }, 'Master: ' + reference.label));
      const approvedImages = state.assets.filter((item) => item.persona_id === personaId && item.kind === 'image' && item.review === 'approved');
      for (const asset of approvedImages) {
        select.append(el('option', { value: 'asset:' + asset.id }, 'Approved image: ' + asset.prompt.slice(0, 40)));
      }
      if ([...select.options].some((option) => option.value === previous)) select.value = previous;
      else if (approvedImages.length) select.value = 'asset:' + approvedImages[0].id;
    } catch { /* A missing reference list should not block the rest of the dashboard. */ }
  }
  options('#g-audio', state.assets.filter((asset) => asset.persona_id === personaId && asset.kind === 'audio').map((asset) => ({ value: asset.id, name: asset.prompt.slice(0, 70) })), 'No audio selected');
  const referencePersona = $('#r-persona').value;
  const view = $('#reference-list'); clear(view);
  if (referencePersona) {
    try {
      const references = await api('/api/personas/' + referencePersona + '/references');
      for (const reference of references) {
        const box = el('div', { class: 'reference' });
        box.append(el('img', { src: '/api/references/' + reference.id + '/file', alt: reference.label, loading: 'lazy' }), el('small', {}, reference.label));
        view.append(box);
      }
    } catch { /* Keep the vault usable if one preview is unavailable. */ }
  }
}

function renderJobs() {
  const root = $('#job-list'); clear(root);
  if (!state.jobs.length) {
    root.append(el('p', { class: 'muted' }, 'No render jobs yet. Configure a workflow to start a local render.'), emptyAction('generate', 'Open generation →'));
    return;
  }
  for (const job of state.jobs.slice(0, 20)) {
    const box = el('div', { class: 'listitem' });
    const row = el('div', { class: 'row' });
    row.append(el('strong', {}, job.persona_name + ' · ' + job.workflow_id), el('span', { class: 'pill ' + job.status }, job.status));
    box.append(row, el('small', {}, (job.prompt || '').slice(0, 160)));
    if (job.error) box.append(el('small', {}, 'Error: ' + job.error));
    const actions = el('div', { class: 'job-actions' });
    appendJobActions(actions, job);
    if (actions.childElementCount) box.append(actions);
    root.append(box);
  }
}

function appendJobActions(target, job) {
  if (!target || !job) return;
  const active = ['queued', 'running', 'submitted', 'cancelling'].includes(job.status);
  const retryable = ['failed', 'interrupted', 'cancelled'].includes(job.status);
  if (!active && !retryable) return;
  const action = el('button', { type: 'button', class: 'secondary compact-action' }, active ? 'Cancel' : 'Retry');
  action.addEventListener('click', async () => {
    action.disabled = true;
    try {
      const verb = active ? 'cancel' : 'retry';
      const result = await api('/api/jobs/' + job.id + '/' + verb, { method: 'POST' });
      notify(active ? 'Job cancelled' : 'Job queued for retry (attempt ' + result.attempt + ')');
      await refresh();
    } catch (error) {
      notify(error.message, true);
      action.disabled = false;
    }
  });
  target.append(action);
}

function renderGallery() {
  const root = $('#gallery'); clear(root);
  if (!state.assets.length) {
    root.append(el('p', { class: 'muted' }, 'No generated media yet. Start with a persona, then queue a render.'), emptyAction('generate', 'Open generation →'));
    return;
  }
  for (const asset of state.assets) {
    const card = el('article', { class: 'asset' });
    const preview = el('div', { class: 'preview' });
    const url = '/api/assets/' + asset.id + '/file';
    if (asset.kind === 'image') preview.append(el('img', { src: url, loading: 'lazy', alt: 'Generated media by ' + asset.persona_name }));
    else if (asset.kind === 'video') preview.append(el('video', { src: url, controls: '', preload: 'metadata' }));
    else preview.append(el('audio', { src: url, controls: '' }));
    const body = el('div', { class: 'asset-content' });
    body.append(el('strong', {}, asset.persona_name), el('small', {}, asset.kind.toUpperCase() + ' · ' + asset.review), el('small', {}, asset.prompt.slice(0, 105)), el('small', {}, 'Disclosure: ' + (asset.disclosure || 'Fictional adult character. AI-generated synthetic media.')));
    if (asset.quality?.status) body.append(el('small', { class: asset.quality.status === 'error' ? 'error-text' : asset.quality.status === 'ready' ? 'ready-text' : 'muted' }, 'Quality gate: ' + asset.quality.status));
    const controls = el('div', { class: 'asset-controls' });
    for (const status of ['approved', 'rejected']) {
      const button = el('button', { type: 'button' }, status === 'approved' ? '✓ Approve' : '× Reject');
      button.addEventListener('click', async () => {
        try {
          await api('/api/assets/' + asset.id + '/review', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ review: status }) });
          notify('Media marked ' + status); refresh();
        } catch (error) { notify(error.message, true); }
      });
      controls.append(button);
    }
    controls.append(el('a', { href: url, download: asset.filename, target: '_blank', rel: 'noopener' }, '↓ Download'));
    if (asset.review === 'approved') controls.append(el('a', { href: '/api/assets/' + asset.id + '/package', download: 'asset_' + asset.id + '.zip' }, '↓ Export package'));
    if (asset.review === 'approved' && asset.kind === 'image') {
      const useForVideo = el('button', { type: 'button' }, 'Use for video');
      useForVideo.addEventListener('click', async () => {
        const nav = document.querySelector('[data-nav-key="video-studio"]');
        $('#g-persona').value = asset.persona_id;
        tab('generate', nav);
        await refreshReferences();
        $('#g-reference').value = 'asset:' + asset.id;
        notify('Approved master image attached to the video stage');
      });
      controls.append(useForVideo);
    } else if (asset.review === 'approved' && asset.kind === 'video') {
      const addNarration = el('button', { type: 'button' }, 'Add narration');
      addNarration.addEventListener('click', () => {
        const nav = document.querySelector('[data-nav-key="voice-studio"]');
        tab('voice', nav);
        $('#v-persona').value = asset.persona_id;
        notify('Video selected as the narration hand-off');
      });
      controls.append(addNarration);
    } else if (asset.review === 'approved' && asset.kind === 'audio') {
      const useInVideo = el('button', { type: 'button' }, 'Use in video');
      useInVideo.addEventListener('click', async () => {
        const nav = document.querySelector('[data-nav-key="video-studio"]');
        $('#g-persona').value = asset.persona_id;
        tab('generate', nav);
        await refreshReferences();
        $('#g-audio').value = asset.id;
        notify('Approved narration attached to the video stage');
      });
      controls.append(useInVideo);
    }
    body.append(controls); card.append(preview, body); root.append(card);
  }
}

function renderLinks() {
  const root = $('#link-list'); clear(root);
  if (!state.links.length) { root.append(el('p', { class: 'muted' }, 'Create a link to track controlled campaign tests.')); return; }
  for (const link of state.links) {
    const item = el('div', { class: 'listitem' });
    item.append(el('strong', {}, link.label), el('small', {}, link.clicks + ' clicks'));
    item.append(el('a', { href: '/go/' + link.code, target: '_blank', rel: 'noopener' }, location.origin + '/go/' + link.code));
    root.append(item);
  }
}

function renderWorkflows() {
  const root = $('#workflow-list'); clear(root);
  if (!state.workflows.length) { root.append(el('p', { class: 'muted' }, 'No workflow recipes found.')); return; }
  for (const workflow of state.workflows) {
    const item = el('div', { class: 'listitem' });
    const status = workflow.ready ? 'READY' : (workflow.backend === 'direct-cli' ? 'CLI RECIPE' : 'IMPORT REQUIRED');
    const capability = workflow.task ? ' · ' + workflow.task : '';
    const memory = workflow.min_vram_gb ? ' · ≥' + workflow.min_vram_gb + ' GiB VRAM' : '';
    item.append(el('strong', {}, workflow.label || workflow.id), el('small', {}, status + ' · ' + workflow.category + (workflow.model ? ' · ' + workflow.model : '') + (workflow.requires_reference ? ' · REQUIRES REFERENCE' : '')));
    if (capability || memory) item.append(el('small', {}, capability + memory));
    if (workflow.description) item.append(el('small', {}, workflow.description));
    root.append(item);
  }
}

function monitorPill(status) {
  const label = status === 'ready' ? 'READY' : status === 'warning' ? 'CHECK' : status === 'degraded' ? 'DEGRADED' : 'ERROR';
  return el('span', { class: 'pill ' + (status === 'ready' ? 'completed' : status === 'warning' || status === 'degraded' ? 'running' : 'failed') }, label);
}

function monitorRow(item) {
  const row = el('div', { class: 'monitor-row' });
  const copy = el('div');
  copy.append(el('strong', {}, item.label || item.id), el('small', {}, item.detail || ''));
  row.append(copy, monitorPill(item.status));
  return row;
}

function renderMonitor() {
  const data = state.monitoring;
  if (!data) return;
  const overview = $('#monitor-overview');
  clear(overview);
  const title = data.overall.status === 'ready' ? 'All checked systems ready' : data.overall.status === 'degraded' ? 'Core app ready · attention required' : 'Monitoring found a core error';
  const overviewCopy = el('div', { class: 'monitor-overview-copy' });
  overviewCopy.append(el('strong', {}, title), el('small', {}, data.overall.detail + ' · Last checked ' + data.checked_at));
  overview.append(overviewCopy);
  overview.append(monitorPill(data.overall.status === 'ready' ? 'ready' : data.overall.status === 'degraded' ? 'degraded' : 'error'));
  clear($('#monitor-api')); $('#monitor-api').append(monitorRow({ label: 'Studio API', detail: data.api.detail + ' · v' + data.api.version, status: data.api.status }));
  if (data.security) $('#monitor-api').append(monitorRow({ label: 'Access security', detail: data.security.detail, status: data.security.status }));
  clear($('#monitor-connections')); data.connections.forEach((item) => $('#monitor-connections').append(monitorRow(item)));
  clear($('#monitor-runtime')); data.runtime.forEach((item) => $('#monitor-runtime').append(monitorRow(item)));
  clear($('#monitor-models')); data.models.forEach((item) => $('#monitor-models').append(monitorRow({ ...item, detail: item.detail + ' · ' + item.license })));
  clear($('#monitor-workflows')); $('#monitor-workflows').append(monitorRow({ label: 'Workflow inventory', detail: data.workflows.detail, status: data.workflows.status })); data.workflows.items.forEach((item) => $('#monitor-workflows').append(monitorRow({ label: item.label || item.id, detail: item.ready ? 'Verified dashboard graph' : 'Catalog recipe · setup required', status: item.ready ? 'ready' : 'warning' })));
  clear($('#monitor-queue')); $('#monitor-queue').append(monitorRow({ label: 'Render queue', detail: data.queue.detail, status: data.queue.status }));
  clear($('#monitor-storage')); $('#monitor-storage').append(monitorRow({ label: 'Persistent storage', detail: data.storage.detail + ' · ' + data.storage.used_pct + '% used', status: data.storage.status }));
}

function parseEpisodePlan(value) {
  const lines = value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (!lines.length) throw new Error('Add at least one episode line');
  return lines.map((line, index) => {
    const parts = line.split('|').map((part) => part.trim());
    if (parts.length < 3 || parts.some((part) => !part)) throw new Error('Episode ' + (index + 1) + ' must use: Title | visual direction | motion direction');
    return { title: parts[0], prompt: parts[1], video_prompt: parts.slice(2).join(' | ') };
  });
}

function renderSeries() {
  const root = $('#series-list');
  if (!root) return;
  clear(root);
  if (!state.series.length) {
    root.append(el('p', { class: 'muted' }, 'No series yet. Freeze a persona, then create a repeatable episode plan.'));
    return;
  }
  const readyWorkflows = state.workflows.filter((workflow) => workflow.ready && workflow.category === 'video');
  for (const series of state.series) {
    const card = el('article', { class: 'series-card' });
    const heading = el('div', { class: 'card-heading' });
    const headingCopy = el('div');
    headingCopy.append(el('p', { class: 'eyebrow' }, series.persona_name + ' · ' + series.status.toUpperCase()), el('h3', {}, series.title));
    const handoff = el('button', { type: 'button', class: 'secondary' }, 'Copy CLI handoff JSON');
    handoff.addEventListener('click', async () => {
      const identity = state.personas.find((item) => item.id === series.persona_id) || {};
      const persona = { name: series.persona_name, age: identity.age, appearance: identity.appearance || '', description: identity.description || '', consistency_anchor: identity.characteristics?.consistency_anchor || 'Keep the frozen identity capsule unchanged in every shot.', disclosure: identity.disclosure || 'Fictional AI-generated adult persona', characteristics: identity.characteristics || {} };
      const episodes = series.episodes.map((episode) => ({ episode_no: episode.episode_no, title: episode.title, prompt: episode.prompt, video_prompt: episode.video_prompt }));
      const briefs = episodes.map((episode) => ({ schema_version: '1.0', title: series.title + ' - ' + episode.title, persona, image: { enabled: true, model: 'flux2-klein-4b', prompt: episode.prompt, negative_prompt: 'blurry, deformed, extra fingers, duplicate person, watermark, typography, logo, child, teenager, minor, nudity, exposed genitals, explicit sexual activity, lingerie, real-person likeness', width: 704, height: 1280, seed: 42, steps: 4, guidance: 1, reference_paths: [], output: 'generated/' + series.id + '_episode_' + episode.episode_no + '_master.png' }, video: { enabled: true, model: 'wan22-ti2v-5b', prompt: episode.video_prompt, size: '704*1280', output: 'generated/' + series.id + '_episode_' + episode.episode_no + '.mp4' }, voice: { enabled: false, text: '', voice: 'af_heart', lang: 'a', output: 'generated/' + series.id + '_episode_' + episode.episode_no + '_narration.wav' }, assembly: { enabled: true, output: 'generated/' + series.id + '_episode_' + episode.episode_no + '_final.mp4', disclosure: 'Fictional adult character. AI-generated synthetic media.' }, review: { disclosure_required: true } }));
      await copyText(JSON.stringify({ series: { id: series.id, title: series.title, identity_version: series.identity_version, shared_prompt: series.shared_prompt }, persona, episodes, briefs }, null, 2));
      notify('Series CLI handoff JSON copied');
    });
    heading.append(headingCopy, handoff, el('span', { class: 'pill approved' }, 'FROZEN IDENTITY v' + (series.identity_version || '?')));
    card.append(heading, el('p', { class: 'muted series-description' }, series.description), el('p', { class: 'series-shared' }, 'Shared continuity: ' + series.shared_prompt));
    const list = el('div', { class: 'series-episodes' });
    for (const episode of series.episodes) {
      const row = el('div', { class: 'series-episode' });
      const copy = el('div');
      copy.append(el('strong', {}, String(episode.episode_no).padStart(2, '0') + ' · ' + episode.title), el('small', {}, episode.status.toUpperCase() + ' · ' + episode.prompt.slice(0, 180)));
      row.append(copy);
      if (episode.status === 'planned') {
        if (readyWorkflows.length) {
          const queue = el('button', { type: 'button', class: 'secondary' }, 'Queue episode');
          queue.addEventListener('click', async () => {
            if (!$('#series-rights').checked) { notify('Confirm fictional identity, rights-cleared inputs and AI disclosure first', true); return; }
            if (!$('#series-workflow').value) { notify('Choose a verified video workflow in the Series studio form first', true); return; }
            try {
              await api('/api/series/' + series.id + '/episodes/' + episode.id + '/queue', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ workflow_id: $('#series-workflow').value, rights_confirmed: true }) });
              notify('Episode queued: ' + episode.title); await refresh();
            } catch (error) { notify(error.message, true); }
          });
          row.append(queue);
        } else row.append(el('small', { class: 'muted' }, 'Import a verified video graph to queue, or use the CLI handoff JSON for the direct Python pipeline'));
      } else row.append(el('span', { class: 'pill ' + (episode.status === 'completed' ? 'completed' : 'running') }, episode.status));
      list.append(row);
    }
    card.append(list); root.append(card);
  }
}

function mountSeriesStudio() {
  if ($('#series')) return;
  const stageGrid = $('.stage-grid');
  if (stageGrid && !stageGrid.querySelector('[data-target="series"]')) {
    const stage = el('button', { class: 'stage-card go-tab', 'data-target': 'series', type: 'button' });
    stage.append(el('span', { class: 'stage-index' }, '06'), el('span', { class: 'stage-icon' }, '↻'), el('strong', {}, 'Repeat'), el('small', {}, 'Freeze a persona and plan a consistent episode series.'), el('span', { class: 'stage-link' }, 'Open series studio →'));
    stageGrid.append(stage);
  }
  const nav = $('.nav-list');
  const navButton = el('button', { 'data-tab': 'series', class: 'nav' });
  navButton.append(el('span', { class: 'nav-icon', 'aria-hidden': 'true' }, '↻'), el('span', {}, 'Series studio'), el('kbd', {}, '08'));
  navButton.addEventListener('click', () => tab('series'));
  const before = nav.querySelector('[data-tab="assets"]');
  nav.insertBefore(navButton, before || null);
  const panel = el('section', { id: 'series', class: 'panel' });
  panel.innerHTML = `<div class="section-heading page-heading"><div><p class="eyebrow">08 / CONTINUITY SYSTEM</p><h2>Series studio</h2><p class="muted">Freeze one canonical persona, then plan and render episodes that inherit the same identity every time.</p></div><span class="section-note">Persona lock required</span></div><div class="series-guide"><div><span>01</span><strong>Freeze identity</strong><small>Finish the persona, add references and lock the canonical details.</small></div><div><span>02</span><strong>Write the series bible</strong><small>Define the shared look, tone, locations and recurring rules.</small></div><div><span>03</span><strong>Plan episodes</strong><small>Give every episode its own scene and motion direction.</small></div><div><span>04</span><strong>Queue and review</strong><small>Render one episode at a time, then approve each export.</small></div></div><div class="two-col series-layout"><form id="series-form" class="card form accent-card"><div class="card-heading"><div><p class="eyebrow">NEW SERIES</p><h3>Repeatable episode plan</h3></div><span class="step-badge">01</span></div><label>Frozen persona<select id="series-persona" required></select></label><label>Series title<input id="series-title" required placeholder="e.g. Veyra's Liora Quay field notes"/></label><label>Series description<textarea id="series-description" rows="3" required placeholder="What the audience should feel and learn across the series…"></textarea></label><label>Shared continuity bible<textarea id="series-shared" rows="5" required placeholder="Keep the same identity anchor, wardrobe language, camera grade, voice and recurring locations in every episode…"></textarea></label><label>Episodes <span class="label-hint">One per line: Title | visual direction | motion direction</span><textarea id="series-episodes" rows="8" required placeholder="Episode 01 - Arrival | Veyra at the harbor in mineral teal tailoring | slow walk, coat moves in the coastal wind\nEpisode 02 - The fabric room | Veyra studies textiles in the studio | close hand movement, gentle camera push-in"></textarea></label><label>Video workflow<select id="series-workflow" required></select></label><label class="check"><input type="checkbox" id="series-rights" required/> I confirm this series uses a fictional adult persona, rights-cleared inputs and visible AI disclosure.</label><button type="submit" class="primary">Create series plan →</button><p class="fine muted">The persona is inherited from the frozen library record; episode prompts cannot silently replace its identity details.</p></form><div class="card"><div class="card-heading"><div><p class="eyebrow">SERIES LIBRARY</p><h3>Continuity plans</h3></div><span class="step-badge">02</span></div><div id="series-list" class="stack"></div></div></div></section>`;
  const cliNote = el('p', { class: 'series-cli-note' }, 'No API credits are required. Import a verified ComfyUI graph to queue here, or copy the CLI handoff JSON and run the same persona details and episode prompts through the direct Python pipeline on the GPU server.');
  panel.querySelector('#series-workflow').removeAttribute('required');
  panel.querySelector('.series-guide').after(cliNote);
  $('.main').insertBefore(panel, $('.main footer'));
  options('#series-persona', state.personas.filter((persona) => persona.identity_locked).map((persona) => ({ value: persona.id, name: persona.name + ' · frozen v' + persona.identity_version })), 'Freeze a persona first');
  options('#series-workflow', state.workflows.filter((workflow) => workflow.ready && workflow.category === 'video').map((workflow) => ({ value: workflow.id, name: workflow.label || workflow.id })), 'Import a verified video graph first');
  if ($('#series-workflow').options[0]) $('#series-workflow').options[0].textContent = 'Optional: select a verified graph for dashboard queue';
  on('#series-form', async () => {
    const episodes = parseEpisodePlan($('#series-episodes').value);
    await post('/api/series', { persona_id: $('#series-persona').value, title: $('#series-title').value, description: $('#series-description').value, shared_prompt: $('#series-shared').value, episodes });
    $('#series-form').reset(); notify('Series plan created'); await refresh();
  });
}

function mountAssetImporter() {
  const panel = $('#assets');
  if (!panel || $('#asset-import-form')) return;
  const form = el('form', { id: 'asset-import-form', class: 'card form asset-import-card' });
  form.innerHTML = `<div class="card-heading"><div><p class="eyebrow">LOCAL HANDOFF</p><h3>Import a completed pipeline output</h3><p class="muted fine">Use this after running the direct Python pipeline. The file stays pending until you review it.</p></div><span class="step-badge">05</span></div><div class="twobox"><label>Persona<select id="asset-import-persona" required></select></label><label>Media type<select id="asset-import-kind"><option value="video">Video</option><option value="image">Image</option><option value="audio">Audio</option></select></label></div><label>Output file<input id="asset-import-file" type="file" accept=".mp4,.webm,.gif,.png,.jpg,.jpeg,.webp,.wav,.mp3,.flac" required/></label><label>Scene / pipeline description<textarea id="asset-import-prompt" rows="2" required placeholder="Wan2.2 image-to-video episode with optional Kokoro narration and FFmpeg mux"></textarea></label><label>AI disclosure<input id="asset-import-disclosure" value="Fictional adult character. AI-generated synthetic media." required/></label><label class="check"><input type="checkbox" id="asset-import-rights" required/> I confirm the output and all source inputs are rights-cleared, fictional and ready for manual review.</label><button class="secondary" type="submit">Import for review →</button>`;
  const gallery = $('#gallery');
  panel.insertBefore(form, gallery);
  on('#asset-import-form', async () => {
    const data = new FormData();
    data.append('persona_id', $('#asset-import-persona').value);
    data.append('kind', $('#asset-import-kind').value);
    data.append('file', $('#asset-import-file').files[0]);
    data.append('prompt', $('#asset-import-prompt').value);
    data.append('disclosure', $('#asset-import-disclosure').value);
    data.append('rights_confirmed', $('#asset-import-rights').checked);
    await api('/api/assets/import', { method: 'POST', body: data });
    form.reset(); $('#asset-import-disclosure').value = 'Fictional adult character. AI-generated synthetic media.';
    notify('Pipeline output imported for manual review'); await refresh(); tab('assets');
  });
}

function mountMonitoring() {
  if ($('#monitoring')) return;
  const nav = $('.nav-list');
  const navButton = el('button', { 'data-tab': 'monitoring', class: 'nav' });
  navButton.append(el('span', { class: 'nav-icon', 'aria-hidden': 'true' }, '◌'), el('span', {}, 'Monitoring'), el('kbd', {}, '09'));
  navButton.addEventListener('click', () => tab('monitoring'));
  const linkButton = nav.querySelector('[data-tab="funnels"]');
  if (linkButton) linkButton.insertAdjacentElement('afterend', navButton); else nav.append(navButton);
  const panel = el('section', { id: 'monitoring', class: 'panel' });
  panel.innerHTML = `<div class="section-heading page-heading"><div><p class="eyebrow">09 / SYSTEM READINESS</p><h2>Monitoring</h2><p class="muted">Check the control plane, cloud connections, runtimes, model files, workflow graphs, queue and storage before starting a render session.</p></div><button id="monitor-refresh" class="secondary" type="button">Run checks ↻</button></div><div id="monitor-overview" class="monitor-overview"><div class="monitor-overview-copy"><strong>Monitoring has not run yet</strong><small>Run a check whenever the cloud worker starts or after installing a model.</small></div><span class="pill">NOT CHECKED</span></div><div class="monitor-grid"><div class="card monitor-card"><div class="card-heading"><div><p class="eyebrow">API</p><h3>Control plane</h3></div></div><div id="monitor-api" class="monitor-list"></div></div><div class="card monitor-card"><div class="card-heading"><div><p class="eyebrow">CONNECTIONS</p><h3>External bridges</h3></div></div><div id="monitor-connections" class="monitor-list"></div></div><div class="card monitor-card"><div class="card-heading"><div><p class="eyebrow">RUNTIME</p><h3>GPU & tools</h3></div></div><div id="monitor-runtime" class="monitor-list"></div></div><div class="card monitor-card"><div class="card-heading"><div><p class="eyebrow">MODEL FILES</p><h3>Local inventory</h3></div></div><div id="monitor-models" class="monitor-list"></div></div><div class="card monitor-card monitor-card-wide"><div class="card-heading"><div><p class="eyebrow">WORKFLOWS</p><h3>Render graph readiness</h3></div></div><div id="monitor-workflows" class="monitor-list"></div></div><div class="card monitor-card"><div class="card-heading"><div><p class="eyebrow">OPERATIONS</p><h3>Queue & storage</h3></div></div><div id="monitor-queue" class="monitor-list"></div><div id="monitor-storage" class="monitor-list"></div></div></div>`;
  $('.main').insertBefore(panel, $('.main footer'));
  $('#monitor-refresh').addEventListener('click', refreshMonitor);
}

const personaCharacteristicFields = {
  face: [
    ['face_shape', 'Face shape', 'oval, heart, softly angular…'],
    ['skin_tone', 'Skin tone / complexion', 'undertone, freckles, texture…'],
    ['eyes', 'Eyes', 'color, shape, brows, gaze…'],
    ['hair', 'Hair', 'color, length, texture, parting…'],
    ['distinguishing_features', 'Fictional distinguishing features', 'beauty mark, scar, glasses, signature detail…']
  ],
  physique: [
    ['height_and_build', 'Height and build', 'adult proportions, build and silhouette…'],
    ['posture_and_movement', 'Posture and movement', 'stance, walk, gestures, energy…'],
    ['age_cues', 'Adult age cues', 'mature styling and presentation, never ambiguous…']
  ],
  style: [
    ['glamour_direction', 'Glamour direction', 'high-glam editorial, runway bold, beachwear, pin-up-inspired or understated luxury…'],
    ['wardrobe', 'Wardrobe', 'silhouettes, garments, fabrics and styling rules…'],
    ['materials_and_palette', 'Materials and color palette', 'signature colors, textures and contrast…'],
    ['accessories_and_grooming', 'Accessories and grooming', 'jewelry, bags, makeup, nails, hair finish…']
  ],
  personality: [
    ['traits', 'Personality traits', 'three to five specific traits with useful contrasts…'],
    ['interests_and_values', 'Interests and values', 'hobbies, causes, tastes and motivations…'],
    ['speech_style', 'Speech style', 'pace, vocabulary, warmth, humor and point of view…'],
    ['mannerisms', 'Mannerisms', 'recurring expressions, gestures and habits…']
  ],
  world: [
    ['cultural_context', 'Cultural / world context', 'user-provided background and lived setting, not inferred identity…'],
    ['home_base', 'Home base', 'city or environment and its visual cues…'],
    ['recurring_locations', 'Recurring locations', 'cafes, studios, streets, travel spaces…'],
    ['content_pillars', 'Content pillars', 'fashion, food, travel, wellness, art…']
  ],
  camera: [
    ['framing', 'Default framing', 'portrait, medium shot, full body, vertical social crop…'],
    ['lens_and_depth', 'Lens and depth', 'lens feel, depth of field and camera distance…'],
    ['lighting', 'Lighting language', 'window light, overcast, flash, dusk…'],
    ['color_grade', 'Color grade', 'natural, warm editorial, muted, high contrast…']
  ]
};

function mountPersonaDetails() {
  const form = $('#persona-form');
  if (!form || $('#persona-details')) return;
  const details = el('div', { class: 'persona-details', id: 'persona-details' });
  const intro = el('div', { class: 'persona-details-intro' });
  intro.append(el('p', { class: 'eyebrow' }, 'CHARACTER DEPTH'), el('strong', {}, 'Add anchors ChatGPT and the render models can preserve.'));
  intro.append(el('span', { class: 'muted' }, 'Specific traits create a more recognisable persona than generic appearance words. Expand each group as needed.'));
  details.append(intro);
  Object.entries(personaCharacteristicFields).forEach(([section, fields], index) => {
    const group = el('details', { class: 'persona-detail-group' });
    if (index === 0) group.setAttribute('open', '');
    group.append(el('summary', {}, section.replace('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())));
    const grid = el('div', { class: 'persona-detail-grid' });
    fields.forEach(([key, label, placeholder]) => {
      const input = el('input', { id: 'p-' + key.replaceAll('_', '-'), placeholder });
      const field = el('label', {}, label); field.append(input); grid.append(field);
    });
    group.append(grid); details.append(group);
  });
  const submit = form.querySelector('button[type="submit"]');
  form.insertBefore(details, submit || null);
}

function readPersonaCharacteristics() {
  const result = {};
  Object.entries(personaCharacteristicFields).forEach(([section, fields]) => {
    result[section] = {};
    fields.forEach(([key]) => { result[section][key] = $('#p-' + key.replaceAll('_', '-')).value.trim(); });
  });
  return result;
}

function applyPersonaCharacteristics(characteristics = {}) {
  Object.entries(personaCharacteristicFields).forEach(([section, fields]) => {
    fields.forEach(([key]) => {
      const input = $('#p-' + key.replaceAll('_', '-'));
      if (input) input.value = readableValue(characteristics?.[section]?.[key]);
    });
  });
}

function mountPersonaImporter() {
  const form = $('#persona-form');
  if (!form || $('#persona-brief-import')) return;
  const card = el('div', { class: 'persona-brief-import', id: 'persona-brief-import' });
  const copy = el('div');
  copy.append(el('p', { class: 'eyebrow' }, 'CHATGPT PERSONA HANDOFF'), el('strong', {}, 'Generate a persona JSON, then add it directly.'));
  copy.append(el('span', { class: 'muted' }, 'Use the detailed prompt below in ChatGPT. The importer validates the character is an original fictional adult before saving it to the library.'));
  const actions = el('div', { class: 'persona-brief-actions' });
  const fileLabel = el('label', {}, 'Persona JSON');
  fileLabel.append(el('input', { type: 'file', id: 'persona-brief-file', accept: '.json,application/json' }));
  const copyButton = el('button', { type: 'button', class: 'secondary' }, 'Copy persona prompt');
  const importButton = el('button', { type: 'button', class: 'primary' }, 'Import persona JSON');
  actions.append(fileLabel, copyButton, importButton);
  const status = el('span', { id: 'persona-brief-status', class: 'fine muted', role: 'status' }, 'The imported file is saved immediately; review references separately before generation.');
  card.append(copy, actions, status);
  form.insertBefore(card, form.firstChild);
  copyButton.addEventListener('click', async () => { await copyText(PERSONA_BRIEF_PROMPT); notify('Persona prompt copied'); });
  importButton.addEventListener('click', async () => {
    const file = $('#persona-brief-file').files[0];
    if (!file) { notify('Choose a persona JSON file first', true); return; }
    importButton.disabled = true;
    try {
      const data = new FormData(); data.append('file', file);
      const persona = await api('/api/personas/import', { method: 'POST', body: data });
      status.textContent = persona.name + ' added to the persona library.';
      status.className = 'fine ready-text';
      $('#persona-brief-file').value = '';
      notify('Persona imported: ' + persona.name);
      await refresh();
    } catch (error) {
      status.textContent = error.message;
      status.className = 'fine error-text';
      notify(error.message, true);
    } finally { importButton.disabled = false; }
  });
}

function mountBriefImporter() {
  const form = $('#job-form');
  if (!form || $('#brief-import')) return;
  const card = el('div', { class: 'brief-import card', id: 'brief-import' });
  const copy = el('div');
  copy.append(el('p', { class: 'eyebrow' }, 'CHATGPT HANDOFF'), el('h3', {}, 'Load a generation brief'));
  copy.append(el('p', { class: 'muted' }, 'Load one JSON file to stage the persona, image, motion, canvas, seed and narration fields. Nothing renders automatically.'));
  const controls = el('div', { class: 'brief-import-controls' });
  const label = el('label', {}, 'Generation brief JSON');
  label.append(el('input', { type: 'file', id: 'brief-file', accept: '.json,application/json' }));
  controls.append(label, el('button', { type: 'button', class: 'secondary', id: 'brief-load' }, 'Load brief'));
  const status = el('p', { id: 'brief-status', class: 'fine muted', role: 'status' }, 'Use config/generation_brief.example.json as a starting point.');
  const help = el('details', { class: 'brief-help' });
  help.setAttribute('open', '');
  help.append(el('summary', {}, 'What to give ChatGPT for a unique persona'));
  const helpGrid = el('div', { class: 'brief-help-grid' });
  const helpItems = [
    ['Identity core', 'Original name, adult age, facial geometry, hair, eyes, skin and one subtle fictional distinguishing mark.'],
    ['Personality world', 'Temperament, interests, content lane, cultural setting, recurring locations and relationship to the audience.'],
    ['Visual language', 'Wardrobe, fabrics, color palette, grooming, glamour direction, lighting, lens and composition. Avoid generic “beautiful model” wording.'],
    ['Motion and voice', 'Specific action, expression, camera movement, pacing and optional narration tone or script.'],
    ['Continuity anchor', 'The traits that must never change between the master image and every video shot.'],
    ['Boundaries', 'Fictional adult only; bold glamour is allowed, while explicit sexual acts, minors, real-person likeness misuse and missing AI disclosure are not.']
  ];
  helpItems.forEach(([title, text]) => {
    const item = el('div', { class: 'brief-help-item' });
    item.append(el('strong', {}, title), el('span', {}, text));
    helpGrid.append(item);
  });
  const promptButton = el('button', { type: 'button', class: 'secondary brief-copy-prompt' }, 'Copy ChatGPT prompt');
  promptButton.addEventListener('click', async () => {
    try {
      await copyText(CHATGPT_BRIEF_PROMPT);
      notify('ChatGPT brief prompt copied');
    } catch {
      notify('ChatGPT brief prompt copied');
    }
  });
  help.append(helpGrid, promptButton);
  card.append(copy, controls, status, help);
  const anchor = form.querySelector('.twobox');
  form.insertBefore(card, anchor || form.firstChild);

  const promptLabel = $('#g-prompt').closest('label');
  if (promptLabel && !$('#g-video-prompt')) {
    const motion = el('label', {}, 'Motion direction');
    motion.append(el('textarea', { id: 'g-video-prompt', rows: '4', placeholder: 'How the same character moves, looks, gestures and how the camera behaves…' }));
    promptLabel.parentNode.insertBefore(motion, promptLabel.nextSibling);
  }
  $('#brief-load').addEventListener('click', async () => {
    const file = $('#brief-file').files[0];
    if (!file) { notify('Choose a generation brief JSON file first', true); return; }
    const button = $('#brief-load'); button.disabled = true;
    try {
      const data = new FormData(); data.append('file', file);
      const brief = await api('/api/briefs/validate', { method: 'POST', body: data });
      $('#p-name').value = brief.persona.name;
      $('#p-age').value = brief.persona.age;
      $('#p-appearance').value = brief.persona.appearance;
      $('#p-description').value = (brief.persona.description + '\n\nConsistency anchor: ' + readableValue(brief.persona.consistency_anchor)).slice(0, 1500);
      applyPersonaCharacteristics(brief.persona.characteristics);
      $('#g-prompt').value = brief.image.prompt;
      $('#g-video-prompt').value = brief.video.prompt;
      $('#g-negative').value = brief.image.negative_prompt;
      $('#g-seed').value = brief.image.seed;
      const ratio = brief.image.width + 'x' + brief.image.height;
      const ratioSelect = $('#g-ratio');
      if (![...ratioSelect.options].some((option) => option.value === ratio)) ratioSelect.append(el('option', { value: ratio }, ratio));
      ratioSelect.value = ratio;
      $('#v-text').value = brief.voice.text || '';
      $('#v-voice').value = brief.voice.voice || 'af_heart';
      status.textContent = 'Brief validated. Save the staged persona, upload any listed references separately, then select a workflow and review before queueing.';
      status.className = 'fine ready-text';
      notify('Generation brief loaded for review');
      tab('personas');
    } catch (error) {
      status.textContent = error.message;
      status.className = 'fine error-text';
      notify(error.message, true);
    } finally { button.disabled = false; }
  });
}

function mountGenerationPreflight() {
  const form = $('#job-form');
  const workflow = $('#g-workflow');
  if (!form || !workflow || $('#generation-preflight')) return;
  const card = el('div', { id: 'generation-preflight', class: 'generation-preflight' });
  const status = el('span', { class: 'fine muted', role: 'status' }, 'Run a read-only check before queueing.');
  const button = el('button', { type: 'button', class: 'secondary compact-action' }, 'Run preflight');
  card.append(status, button);
  workflow.closest('label')?.insertAdjacentElement('afterend', card);
  button.addEventListener('click', async () => {
    if (!workflow.value) { status.textContent = 'Select a workflow first.'; status.className = 'fine error-text'; return; }
    button.disabled = true;
    try {
      const ratio = ($('#g-ratio')?.value || '768x1152').split('x').map(Number);
      const result = await api('/api/preflight?workflow_id=' + encodeURIComponent(workflow.value) + '&width=' + ratio[0] + '&height=' + ratio[1]);
      const warning = result.checks.filter((item) => item.status !== 'ready');
      status.textContent = result.overall === 'ready' ? 'Preflight ready.' : 'Preflight ' + result.overall + ': ' + warning.map((item) => item.detail).join(' · ');
      status.className = 'fine ' + (result.overall === 'ready' ? 'ready-text' : 'muted');
    } catch (error) {
      status.textContent = error.message;
      status.className = 'fine error-text';
    } finally { button.disabled = false; }
  });
}

function on(form, callback) {
  $(form).addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = event.submitter;
    if (button) button.disabled = true;
    try { await callback(); } catch (error) { notify(error.message, true); }
    finally { if (button) button.disabled = false; }
  });
}

document.querySelectorAll('.nav').forEach((nav) => nav.addEventListener('click', () => tab(nav.dataset.tab)));
document.addEventListener('click', (event) => {
  const trigger = event.target.closest('.go-tab');
  if (trigger) { event.preventDefault(); tab(trigger.dataset.target); }
});
$('#refresh').addEventListener('click', refresh);
$('#jobs-refresh').addEventListener('click', refresh);
$('#g-persona').addEventListener('change', refreshReferences);
$('#r-persona').addEventListener('change', refreshReferences);
mountPersonaImporter();
mountPersonaDetails();
mountBriefImporter();
mountGenerationPreflight();
// Safe default direction for new adult glamour jobs. The safety checker remains
// enabled; these defaults only make the intended content lane explicit.
$('#g-prompt').placeholder = 'Adult editorial glamour portrait, confident pose, polished fashion styling, tasteful non-explicit direction…';
$('#g-negative').value = 'blurry, deformed, extra fingers, duplicate person, watermark, typography, logo, child, teenager, minor, nudity, exposed genitals, explicit sexual activity, lingerie, real-person likeness';
mountDashboardLayout();
mountTopbarEnhancements();
mountSeriesStudio();
mountAssetImporter();
mountMonitoring();
mountNavigation();
document.querySelectorAll('.nav').forEach((nav) => nav.addEventListener('click', () => tab(nav.dataset.tab, nav)));
mountPipelineRail();
mountDashboardMedia();

on('#persona-form', async () => {
  await post('/api/personas', { name: $('#p-name').value, age: +$('#p-age').value, appearance: $('#p-appearance').value, description: $('#p-description').value, characteristics: readPersonaCharacteristics() });
  $('#persona-form').reset(); notify('Persona created'); await refresh();
});
on('#reference-form', async () => {
  const data = new FormData(); data.append('file', $('#r-file').files[0]); data.append('label', $('#r-label').value); data.append('rights_confirmed', $('#r-rights').checked);
  await api('/api/personas/' + $('#r-persona').value + '/references', { method: 'POST', body: data });
  $('#r-file').value = ''; $('#r-rights').checked = false; notify('Reference added'); await refreshReferences();
});
on('#workflow-form', async () => {
  const data = new FormData(); data.append('file', $('#w-file').files[0]); data.append('label', $('#w-label').value);
  await api('/api/workflows', { method: 'POST', body: data }); $('#workflow-form').reset(); notify('API workflow imported'); await refresh();
});
on('#job-form', async () => {
  const [width, height] = $('#g-ratio').value.split('x').map(Number);
  const seed = $('#g-seed').value.trim(); const selectedReference = $('#g-reference').value;
  const selectedWorkflow = state.workflows.find((workflow) => workflow.id === $('#g-workflow').value);
  if (selectedWorkflow && !selectedWorkflow.ready) {
    throw new Error('This is a workflow recipe, not an installed graph. Run the direct CLI command or import its verified ComfyUI API JSON first.');
  }
  const data = { persona_id: $('#g-persona').value, workflow_id: $('#g-workflow').value, checkpoint: $('#g-checkpoint').value,
    reference_id: selectedReference.startsWith('ref:') ? selectedReference.slice(4) : null,
    source_asset_id: selectedReference.startsWith('asset:') ? selectedReference.slice(6) : null,
    audio_asset_id: $('#g-audio').value || null, prompt: $('#g-prompt').value, video_prompt: $('#g-video-prompt') ? ($('#g-video-prompt').value || null) : null, negative_prompt: $('#g-negative').value,
    width, height, rights_confirmed: $('#g-rights').checked };
  if (seed) data.seed = Number(seed);
  const result = await post('/api/jobs', data); notify('Job queued: ' + result.id.slice(0, 8)); $('#g-rights').checked = false; await refresh();
});
on('#voice-form', async () => {
  await post('/api/voice', { persona_id: $('#v-persona').value, voice: $('#v-voice').value, text: $('#v-text').value });
  notify('Voice WAV generated'); await refresh(); tab('assets');
});
on('#link-form', async () => { await post('/api/links', { label: $('#l-label').value, destination: $('#l-destination').value }); $('#l-label').value = ''; $('#l-destination').value = ''; notify('Tracking link created'); await refresh(); });

window.studioRefresh = refresh;
initPhotoStudio();
initOrchestrator();
refresh();
setInterval(() => {
  if (document.visibilityState !== 'visible') return;
  if ($('#generate').classList.contains('active')) refresh();
  if ($('#monitoring') && $('#monitoring').classList.contains('active')) refreshMonitor();
}, 30000);

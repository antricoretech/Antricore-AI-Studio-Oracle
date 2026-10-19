import { $, clear, copyText, el, notify, options, state } from './core.js';
import { api, post } from './api.js';

export const orchestratorState = {
  presets: null,
  personas: [],
  selectedPersona: null,
  compiledPersonaPrompt: null,
  masterAnchorCandidate: null,
  synthesizedScenes: null,
  batchResults: [],
  isCompiling: false,
  isRenderingAnchor: false,
  isSynthesizing: false,
  isBatchGenerating: false,
  activeStep: 1,
};

export async function initOrchestrator() {
  await loadPresets();
  await loadPersonas();
  setupEventListeners();
  renderPersonaSelector();
  setupJsonImport();
}

async function loadPresets() {
  try {
    orchestratorState.presets = await api('/api/orchestrator/presets');
    populatePresetDropdowns();
  } catch (err) {
    console.error('Failed to load orchestrator presets', err);
  }
}

export async function loadPersonas() {
  try {
    orchestratorState.personas = await api('/api/orchestrator/personas');
    renderPersonaSelector();
  } catch (err) {
    console.error('Failed to load personas', err);
  }
}

function populatePresetDropdowns() {
  const p = orchestratorState.presets;
  if (!p) return;

  // Aspect ratio dropdowns
  const ratios = p.aspect_ratios || [];
  const ratioHtml = ratios.map(r => `<option value="${r.id}" ${r.id === '2:3' ? 'selected' : ''}>${r.label}</option>`).join('');
  const orchRatio = $('#orch-aspect-ratio');
  const sceneRatio = $('#orch-scene-aspect-ratio');
  if (orchRatio) orchRatio.innerHTML = ratioHtml;
  if (sceneRatio) sceneRatio.innerHTML = ratioHtml;

  // Quality dropdowns
  const qualities = p.quality_levels || [];
  const qualHtml = qualities.map(q => `<option value="${q.id}" ${q.id === '4K' ? 'selected' : ''}>${q.label}</option>`).join('');
  const orchQuality = $('#orch-quality');
  const sceneQuality = $('#orch-scene-quality');
  if (orchQuality) orchQuality.innerHTML = qualHtml;
  if (sceneQuality) sceneQuality.innerHTML = qualHtml;

  // Categories
  const categories = p.categories || [];
  const catHtml = categories.map(c => `<option value="${c.id}">${c.label}</option>`).join('');
  const catSelect = $('#orch-category');
  if (catSelect) catSelect.innerHTML = catHtml;
}

function renderPersonaSelector() {
  const select = $('#orch-persona-select');
  if (!select) return;

  const currentVal = select.value;
  select.innerHTML = '<option value="">-- Choose an Existing Persona or Create New Below --</option>';

  orchestratorState.personas.forEach(p => {
    const lockedMark = p.identity_locked ? ' 🔒 (Master Locked)' : '';
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = `${p.name} (${p.age}yo · ${p.characteristics?.country || 'Unknown'}) ${lockedMark}`;
    select.appendChild(opt);
  });

  if (currentVal && orchestratorState.personas.some(p => p.id === currentVal)) {
    select.value = currentVal;
    selectPersona(currentVal);
  }
}

function selectPersona(pid) {
  const persona = orchestratorState.personas.find(p => p.id === pid);
  orchestratorState.selectedPersona = persona || null;
  renderPersonaDetails();
}

function renderPersonaDetails() {
  const wrap = $('#orch-active-persona-card');
  const detailsBox = $('#orch-persona-dna-preview');
  if (!wrap || !detailsBox) return;

  const p = orchestratorState.selectedPersona;
  if (!p) {
    wrap.classList.add('hidden');
    return;
  }

  wrap.classList.remove('hidden');
  const chars = p.characteristics || {};
  const body = chars.body_physics || {};
  const anchor = p.master_anchor;

  detailsBox.innerHTML = `
    <div class="orch-dna-badge-grid">
      <div class="orch-dna-pill"><span>Name:</span> <strong>${p.name}</strong></div>
      <div class="orch-dna-pill"><span>Age:</span> <strong>${p.age} years</strong></div>
      <div class="orch-dna-pill"><span>Country/Region:</span> <strong>${chars.country || 'Global'} (${chars.region || 'Heritage'})</strong></div>
      <div class="orch-dna-pill"><span>Body Physics:</span> <strong>${body.body_type || 'Curvy'} · ${body.measurements || '34D-24-35'}</strong></div>
      <div class="orch-dna-pill"><span>Status:</span> <strong>${p.identity_locked ? '🔒 Master Anchor Locked' : '⏳ Unlocked Draft'}</strong></div>
    </div>
    <div class="orch-dna-desc">
      <p><strong>Face & Likeness:</strong> ${chars.facial_identity || p.appearance || 'Natural facial features'}</p>
    </div>
  `;

  const anchorWrap = $('#orch-master-anchor-slot');
  if (anchorWrap) {
    if (anchor && anchor.url) {
      anchorWrap.innerHTML = `
        <div class="orch-anchor-pinned">
          <img src="${anchor.url}" alt="${p.name} Master Anchor" class="orch-anchor-img" />
          <div class="orch-anchor-meta">
            <span class="orch-lock-tag">🔒 Master Persona Anchor</span>
            <small>${p.name} · Locked Reference</small>
          </div>
        </div>
      `;
    } else {
      anchorWrap.innerHTML = `
        <div class="orch-anchor-empty">
          <span>📷</span>
          <p>No Master Anchor locked yet for ${p.name}. Compile prompt and render one below.</p>
        </div>
      `;
    }
  }
}

function setupEventListeners() {
  // Persona select dropdown
  const select = $('#orch-persona-select');
  if (select) {
    select.addEventListener('change', (e) => {
      selectPersona(e.target.value);
    });
  }

  // Compile Persona Master Prompt
  const compileBtn = $('#orch-compile-persona-btn');
  if (compileBtn) {
    compileBtn.addEventListener('click', handleCompilePersonaPrompt);
  }

  // Render Master Anchor Candidate
  const renderAnchorBtn = $('#orch-render-anchor-btn');
  if (renderAnchorBtn) {
    renderAnchorBtn.addEventListener('click', handleRenderMasterAnchor);
  }

  // Lock Master Anchor
  const lockAnchorBtn = $('#orch-lock-anchor-btn');
  if (lockAnchorBtn) {
    lockAnchorBtn.addEventListener('click', handleLockMasterAnchor);
  }

  // Synthesize Scenes
  const synthBtn = $('#orch-synth-scenes-btn');
  if (synthBtn) {
    synthBtn.addEventListener('click', handleSynthesizeScenes);
  }

  // Approve & Batch Generate
  const batchBtn = $('#orch-approve-batch-btn');
  if (batchBtn) {
    batchBtn.addEventListener('click', handleBatchGenerate);
  }

  // Export JSON
  const exportBtn = $('#orch-export-json-btn');
  if (exportBtn) {
    exportBtn.addEventListener('click', handleExportJson);
  }

  // Copy buttons
  setupCopyButtons();
}

function setupCopyButtons() {
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-copy-target]');
    if (!btn) return;
    const targetId = btn.getAttribute('data-copy-target');
    const targetEl = $(targetId);
    if (!targetEl) return;
    const textToCopy = targetEl.value || targetEl.textContent || '';
    copyText(textToCopy);
    const origHtml = btn.innerHTML;
    btn.innerHTML = '<span>✓ Copied!</span>';
    setTimeout(() => {
      btn.innerHTML = origHtml;
    }, 1800);
  });
}

function setupJsonImport() {
  const fileInput = $('#orch-import-json-file');
  const triggerBtn = $('#orch-import-json-btn');
  if (triggerBtn && fileInput) {
    triggerBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      try {
        const text = await file.text();
        const json = JSON.parse(text);
        const res = await post('/api/orchestrator/import-json', json);
        notify(`Persona "${res.name}" imported successfully!`, 'ok');
        await loadPersonas();
        selectPersona(res.id);
        const select = $('#orch-persona-select');
        if (select) select.value = res.id;
      } catch (err) {
        notify('Failed to import JSON: ' + err.message, 'err');
      }
      fileInput.value = '';
    });
  }
}

async function handleCompilePersonaPrompt() {
  const name = $('#orch-p-name')?.value.trim() || 'Elena Weber';
  const age = parseInt($('#orch-p-age')?.value, 10) || 23;
  const country = $('#orch-p-country')?.value.trim() || 'Germany';
  const region = $('#orch-p-region')?.value.trim() || 'Bavaria (Munich)';
  const facial = $('#orch-p-facial')?.value.trim() || 'Striking hazel-green eyes, soft natural jawline, dirty blonde wavy hair';
  const body_type = $('#orch-p-body-type')?.value.trim() || 'Curvy athletic hourglass';
  const measurements = $('#orch-p-measurements')?.value.trim() || '34D-24-35';
  const height = $('#orch-p-height')?.value.trim() || '5\'8"';
  const skin_tone = $('#orch-p-skin-tone')?.value.trim() || 'Fair golden undertone, subtle freckles';
  const breast_shape = $('#orch-p-breast-shape')?.value.trim() || 'Natural teardrop, realistic gravity';
  const content_mode = $('#orch-p-adult-toggle')?.checked ? 'adult' : 'glamour';
  const aspect_ratio = $('#orch-aspect-ratio')?.value || '2:3';
  const quality = $('#orch-quality')?.value || '4K';

  const payload = {
    name, age, country, region,
    facial_identity: facial,
    body_type, measurements, height, skin_tone, breast_shape,
    content_mode, aspect_ratio, quality
  };

  const gate = $('#orch-approval-gate-1');
  const spinner = $('#orch-compile-spinner');
  if (spinner) spinner.classList.remove('hidden');

  try {
    const res = await post('/api/orchestrator/compile-persona-prompt', payload);
    orchestratorState.compiledPersonaPrompt = res;

    // First ensure persona is saved/created
    let activePersona = orchestratorState.selectedPersona;
    if (!activePersona || activePersona.name !== name) {
      const createRes = await post('/api/orchestrator/create-persona', {
        name, age, country, region,
        facial_identity: facial,
        body_physics: { body_type, measurements, height, skin_tone, breast_shape },
        content_mode,
        master_prompt: res.positive_prompt,
        negative_prompt: res.negative_prompt,
        aspect_ratio, quality
      });
      await loadPersonas();
      selectPersona(createRes.id);
      const sel = $('#orch-persona-select');
      if (sel) sel.value = createRes.id;
    }

    // Populate Approval Gate 1
    if (gate) gate.classList.remove('hidden');
    $('#orch-master-positive').value = res.positive_prompt;
    $('#orch-master-negative').value = res.negative_prompt;
    $('#orch-routed-model-badge').textContent = `⚡ Model: ${res.recommended_model} (${res.routing_reason})`;
    $('#orch-token-badge').textContent = `~${res.token_estimate} tokens`;

    notify('Persona master prompt compiled! Review & approve below.', 'ok');
    gate.scrollIntoView({ behavior: 'smooth' });
  } catch (err) {
    notify('Compilation failed: ' + err.message, 'err');
  } finally {
    if (spinner) spinner.classList.add('hidden');
  }
}

async function handleRenderMasterAnchor() {
  const p = orchestratorState.selectedPersona;
  if (!p) {
    notify('Please select or create a persona first', 'warn');
    return;
  }

  const prompt = $('#orch-master-positive')?.value.trim();
  const negative_prompt = $('#orch-master-negative')?.value.trim();
  const aspect_ratio = $('#orch-aspect-ratio')?.value || '2:3';
  const quality = $('#orch-quality')?.value || '4K';
  const model = orchestratorState.compiledPersonaPrompt?.recommended_model || 'cyberrealistic-xl';

  const progress = $('#orch-anchor-progress');
  const candidateCard = $('#orch-candidate-card');
  if (progress) progress.classList.remove('hidden');

  try {
    const res = await post('/api/orchestrator/render-anchor', {
      persona_id: p.id,
      prompt,
      negative_prompt,
      model,
      aspect_ratio,
      quality,
    });

    orchestratorState.masterAnchorCandidate = res;
    if (candidateCard) {
      candidateCard.classList.remove('hidden');
      $('#orch-candidate-img').src = res.url;
      $('#orch-candidate-meta').textContent = `${res.width}×${res.height} · ${res.quality} · Seed: ${res.seed}`;
      candidateCard.scrollIntoView({ behavior: 'smooth' });
    }
    notify('Candidate master anchor generated! You can lock it as permanent reference.', 'ok');
  } catch (err) {
    notify('Anchor generation failed: ' + err.message, 'err');
  } finally {
    if (progress) progress.classList.add('hidden');
  }
}

async function handleLockMasterAnchor() {
  const p = orchestratorState.selectedPersona;
  const cand = orchestratorState.masterAnchorCandidate;
  if (!p || !cand) {
    notify('No anchor candidate to lock', 'warn');
    return;
  }

  try {
    const res = await post('/api/orchestrator/lock-anchor', {
      persona_id: p.id,
      asset_id: cand.asset_id
    });
    notify(`Master Anchor successfully locked for ${p.name}!`, 'ok');
    await loadPersonas();
    selectPersona(p.id);
  } catch (err) {
    notify('Failed to lock anchor: ' + err.message, 'err');
  }
}

async function handleSynthesizeScenes() {
  const p = orchestratorState.selectedPersona;
  if (!p) {
    notify('Please select an active persona first', 'warn');
    return;
  }

  const narrative = $('#orch-narrative')?.value.trim();
  if (!narrative) {
    notify('Please enter a creative story narrative', 'warn');
    return;
  }

  const category = $('#orch-category')?.value || 'adult_intimate';
  const batch_count = parseInt($('#orch-batch-count')?.value, 10) || 3;
  const aspect_ratio = $('#orch-scene-aspect-ratio')?.value || '2:3';
  const quality = $('#orch-scene-quality')?.value || '4K';

  const spinner = $('#orch-synth-spinner');
  if (spinner) spinner.classList.remove('hidden');

  try {
    const res = await post('/api/orchestrator/synthesize-scenes', {
      persona_id: p.id,
      narrative,
      category,
      batch_count,
      aspect_ratio,
      quality
    });

    orchestratorState.synthesizedScenes = res;
    renderApprovalGate2(res);
    notify(`Synthesized ${res.scenes.length} distinct scenes! Review and approve below.`, 'ok');
  } catch (err) {
    notify('Scene synthesis failed: ' + err.message, 'err');
  } finally {
    if (spinner) spinner.classList.add('hidden');
  }
}

function renderApprovalGate2(data) {
  const gate = $('#orch-approval-gate-2');
  const container = $('#orch-scenes-accordion');
  if (!gate || !container) return;

  gate.classList.remove('hidden');
  $('#orch-scenes-routed-model').textContent = `⚡ Model: ${data.model_id} (${data.routing_reason}) · Target: ${data.width}×${data.height} (${data.quality})`;

  container.innerHTML = data.scenes.map((s, idx) => `
    <div class="card orch-scene-review-card" data-scene-index="${idx}">
      <div class="orch-scene-head">
        <div>
          <span class="orch-scene-pill">Scene ${idx + 1}</span>
          <strong>${s.title}</strong>
        </div>
        <button type="button" class="secondary icon-button" data-copy-target="#orch-scene-prompt-${idx}" title="Copy Positive Prompt">
          📋 Copy Prompt
        </button>
      </div>
      <div class="orch-scene-meta-row">
        <span><strong>Location:</strong> ${s.location}</span>
        <span><strong>Costume:</strong> ${s.costume}</span>
        <span><strong>Expression:</strong> ${s.expression}</span>
        <span><strong>Shot:</strong> ${s.shot}</span>
      </div>
      <label class="ps-prompt-label">
        <span>Positive Prompt (Scene ${idx + 1})</span>
        <textarea id="orch-scene-prompt-${idx}" rows="4">${s.prompt}</textarea>
      </label>
      <label class="ps-prompt-label">
        <span>Negative Prompt (Scene ${idx + 1})</span>
        <input type="text" id="orch-scene-negative-${idx}" value="${s.negative_prompt}" />
      </label>
    </div>
  `).join('');

  gate.scrollIntoView({ behavior: 'smooth' });
}

async function handleBatchGenerate() {
  const p = orchestratorState.selectedPersona;
  const synth = orchestratorState.synthesizedScenes;
  if (!p || !synth) {
    notify('No synthesized scenes ready for batch generation', 'warn');
    return;
  }

  // Gather current edited values from the textareas
  const sceneItems = synth.scenes.map((s, idx) => ({
    title: s.title,
    location: s.location,
    costume: s.costume,
    expression: s.expression,
    shot: s.shot,
    prompt: $(`#orch-scene-prompt-${idx}`)?.value.trim() || s.prompt,
    negative_prompt: $(`#orch-scene-negative-${idx}`)?.value.trim() || s.negative_prompt,
  }));

  const payload = {
    persona_id: p.id,
    scenes: sceneItems,
    model: synth.model_id,
    aspect_ratio: synth.aspect_ratio,
    quality: synth.quality,
    rights_confirmed: true,
  };

  const progress = $('#orch-batch-progress');
  const resultsDeck = $('#orch-consistency-deck');
  if (progress) progress.classList.remove('hidden');

  try {
    const res = await post('/api/orchestrator/generate-batch', payload);
    orchestratorState.batchResults = res.assets || [];
    renderConsistencyDeck(res);
    notify(`Batch generation complete! Generated ${res.total_generated} consistent images.`, 'ok');
  } catch (err) {
    notify('Batch generation failed: ' + err.message, 'err');
  } finally {
    if (progress) progress.classList.add('hidden');
  }
}

function renderConsistencyDeck(res) {
  const deck = $('#orch-consistency-deck');
  const gallery = $('#orch-batch-gallery');
  const masterSlot = $('#orch-deck-master-slot');
  if (!deck || !gallery) return;

  deck.classList.remove('hidden');
  const p = orchestratorState.selectedPersona;

  // Render Master Anchor in Inspector slot
  if (masterSlot && p && p.master_anchor) {
    masterSlot.innerHTML = `
      <div class="orch-deck-anchor-card">
        <span class="orch-badge-master">MASTER ANCHOR (LOCKED)</span>
        <img src="${p.master_anchor.url}" alt="${p.name} Master" />
        <strong>${p.name}</strong>
        <small>Ground Truth Face & Body Physics</small>
      </div>
    `;
  }

  // Render Generated Batch
  gallery.innerHTML = res.assets.map((a, i) => `
    <div class="card orch-generated-card">
      <div class="orch-gen-head">
        <span class="orch-gen-badge">Image ${i + 1} (${a.quality})</span>
        <small>Seed: ${a.seed}</small>
      </div>
      <img src="${a.url}" alt="${a.title}" class="orch-gen-img" />
      <div class="orch-gen-body">
        <strong>${a.title}</strong>
        <p class="orch-gen-location">📍 ${a.location}</p>
        <p class="orch-gen-costume">👗 ${a.costume}</p>
        <p class="orch-gen-expr">😊 ${a.expression}</p>
      </div>
      <div class="orch-gen-actions">
        <a href="${a.url}" download="${a.filename}" class="primary button-link" target="_blank">
          ⬇ Download (${a.quality})
        </a>
      </div>
    </div>
  `).join('');

  deck.scrollIntoView({ behavior: 'smooth' });
}

function handleExportJson() {
  const p = orchestratorState.selectedPersona;
  if (!p) {
    notify('Please select a persona to export', 'warn');
    return;
  }
  window.location.href = `/api/orchestrator/export-json/${p.id}`;
}

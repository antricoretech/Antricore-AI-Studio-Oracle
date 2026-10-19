import { $, clear, el, notify, options, state } from './core.js';
import { api, post } from './api.js';

export const photoStudioState = {
  presets: null,
  selectedPersonaId: null,
  selectedLocation: null,
  selectedCostume: null,
  selectedExpression: null,
  selectedAngle: null,
  customLocation: '',
  customCostume: '',
  customExpression: '',
  customAngle: '',
  isGenerating: false,
  initialized: false,
  lastResult: null,
};

let compileDebounceTimer = null;

function debounceCompile() {
  clearTimeout(compileDebounceTimer);
  compileDebounceTimer = setTimeout(() => {
    compilePrompt();
  }, 350);
}

export async function initPhotoStudio() {
  if (photoStudioState.initialized) return;

  try {
    photoStudioState.presets = await api('/api/photo-studio/presets');
  } catch (err) {
    console.error('Failed to load Photo Studio presets', err);
  }

  // Persona selector change
  const personaSelect = $('#ps-persona-select');
  if (personaSelect) {
    personaSelect.addEventListener('change', (e) => {
      photoStudioState.selectedPersonaId = e.target.value;
      renderPersonaDetails();
      compilePrompt();
    });
  }

  // Custom inputs
  const bindInput = (id, stateKey) => {
    const input = $(id);
    if (!input) return;
    input.addEventListener('input', (e) => {
      photoStudioState[stateKey] = e.target.value.trim();
      const indicator = $(id.replace('custom-', '') + '-indicator');
      if (indicator) indicator.textContent = e.target.value.trim() ? 'Custom' : 'Preset';
      debounceCompile();
    });
  };

  bindInput('#ps-custom-location', 'customLocation');
  bindInput('#ps-custom-costume', 'customCostume');
  bindInput('#ps-custom-expression', 'customExpression');
  bindInput('#ps-custom-angle', 'customAngle');

  // Reset / Recompile button
  const recompileBtn = $('#ps-recompile-btn');
  if (recompileBtn) {
    recompileBtn.addEventListener('click', () => {
      $('#ps-custom-location').value = '';
      $('#ps-custom-costume').value = '';
      $('#ps-custom-expression').value = '';
      $('#ps-custom-angle').value = '';
      photoStudioState.customLocation = '';
      photoStudioState.customCostume = '';
      photoStudioState.customExpression = '';
      photoStudioState.customAngle = '';
      ['loc', 'costume', 'expr', 'angle'].forEach((k) => {
        const ind = $(`#ps-${k}-indicator`);
        if (ind) ind.textContent = 'Preset';
      });
      compilePrompt();
    });
  }

  // Approve & Generate button
  const approveBtn = $('#ps-approve-generate-btn');
  if (approveBtn) {
    approveBtn.addEventListener('click', () => {
      triggerGenerate();
    });
  }

  // New seed with same prompt
  const newSeedBtn = $('#ps-new-seed-btn');
  if (newSeedBtn) {
    newSeedBtn.addEventListener('click', () => {
      const seedInput = $('#ps-seed');
      if (seedInput) seedInput.value = '';
      triggerGenerate();
    });
  }

  // Go to media review
  const gotoGalleryBtn = $('#ps-goto-gallery-btn');
  if (gotoGalleryBtn) {
    gotoGalleryBtn.addEventListener('click', () => {
      const mediaNav = document.querySelector('[data-tab="assets"]');
      if (mediaNav) mediaNav.click();
    });
  }

  // Live token estimate on positive prompt manual edit
  const promptTextarea = $('#ps-approved-prompt');
  if (promptTextarea) {
    promptTextarea.addEventListener('input', () => {
      const tokens = promptTextarea.value.trim().split(/\s+/).filter(Boolean).length;
      const badge = $('#ps-token-badge');
      if (badge) badge.textContent = `~${tokens} words / tokens`;
    });
  }

  photoStudioState.initialized = true;
}

export function renderPhotoStudio() {
  if (!photoStudioState.initialized) {
    initPhotoStudio();
  }

  const personaSelect = $('#ps-persona-select');
  if (!personaSelect) return;

  const personaOptions = state.personas.map((p) => ({
    value: p.id,
    name: `${p.name} (${p.age})`,
  }));

  options('#ps-persona-select', personaOptions, 'Select Persona Anchor');

  if (!photoStudioState.selectedPersonaId && state.personas.length > 0) {
    // Prefer Lena Hartmann if available, otherwise first persona
    const lena = state.personas.find((p) => p.name.toLowerCase().includes('lena'));
    photoStudioState.selectedPersonaId = lena ? lena.id : state.personas[0].id;
    personaSelect.value = photoStudioState.selectedPersonaId;
  } else if (photoStudioState.selectedPersonaId) {
    personaSelect.value = photoStudioState.selectedPersonaId;
  }

  renderPersonaDetails();
  renderChips();

  // If prompt area is empty, compile default prompt
  const approvedPromptArea = $('#ps-approved-prompt');
  if (approvedPromptArea && !approvedPromptArea.value.trim() && photoStudioState.selectedPersonaId) {
    compilePrompt();
  }
}

function renderPersonaDetails() {
  const container = $('#ps-persona-details');
  if (!container) return;

  clear(container);

  const persona = state.personas.find((p) => p.id === photoStudioState.selectedPersonaId);
  if (!persona) {
    container.append(el('p', { class: 'muted' }, 'No persona selected. Please choose a persona above.'));
    return;
  }

  // Find recent image/reference for avatar
  const personaAssets = state.assets.filter((a) => a.persona_id === persona.id && a.kind === 'image');
  const avatarUrl = personaAssets.length > 0
    ? `/api/assets/${personaAssets[0].id}/file`
    : '/generated/lena_cyber_bikini_body.png';

  // Avatar block
  const avatarWrap = el('div', { class: 'persona-avatar-wrap' });
  const avatarImg = el('img', {
    class: 'persona-avatar-img',
    src: avatarUrl,
    alt: persona.name,
    onerror: "this.src='/generated/lena_cyber_bikini_body.png'",
  });
  avatarWrap.append(avatarImg);

  // Info box
  const infoBox = el('div', { class: 'persona-info-box' });
  const heading = el('h4', {}, `${persona.name}, ${persona.age} · Canonical Character`);
  const desc = el('p', {}, persona.appearance.length > 180 ? persona.appearance.slice(0, 180) + '…' : persona.appearance);

  const tags = el('div', { class: 'persona-anchors-tags' });
  const anchorTraits = [
    '✨ Defined cheekbones',
    '👁️ Hazel-green eyes (amber flecks)',
    '🌙 Crescent freckle below left eye',
    '🌊 Dark chestnut waves',
    '📸 100% DSLR Realism Anchor',
  ];
  anchorTraits.forEach((trait) => {
    tags.append(el('span', { class: 'persona-anchor-tag' }, trait));
  });

  infoBox.append(heading, desc, tags);

  // Reference thumbnails
  const refsWrap = el('div', { class: 'persona-ref-thumbnails' });
  personaAssets.slice(0, 3).forEach((asset) => {
    const thumb = el('img', {
      class: 'ref-thumb-mini',
      src: `/api/assets/${asset.id}/file`,
      title: asset.prompt ? asset.prompt.slice(0, 80) : 'Reference asset',
    });
    thumb.addEventListener('click', () => {
      // Preview in main viewport
      const viewport = $('#ps-image-viewport');
      if (viewport) {
        clear(viewport);
        const img = el('img', { src: `/api/assets/${asset.id}/file`, alt: 'Reference' });
        viewport.append(img);
        const badge = $('#ps-result-meta-badge');
        if (badge) badge.textContent = `Viewing reference asset #${asset.id.slice(0, 8)}`;
      }
    });
    refsWrap.append(thumb);
  });

  container.append(avatarWrap, infoBox, refsWrap);
}

function renderChips() {
  if (!photoStudioState.presets) return;

  const { locations, costumes, expressions, angles } = photoStudioState.presets;

  // 1. Locations
  const locContainer = $('#ps-location-chips');
  if (locContainer && locations) {
    clear(locContainer);
    if (!photoStudioState.selectedLocation) photoStudioState.selectedLocation = locations[0];
    locations.forEach((item) => {
      const btn = el('button', {
        type: 'button',
        class: 'chip-btn' + (photoStudioState.selectedLocation?.id === item.id ? ' active' : ''),
      }, item.label);
      btn.addEventListener('click', () => {
        photoStudioState.selectedLocation = item;
        $('#ps-custom-location').value = '';
        photoStudioState.customLocation = '';
        $('#ps-loc-indicator').textContent = 'Preset';
        renderChips();
        compilePrompt();
      });
      locContainer.append(btn);
    });
  }

  // 2. Costumes
  const costumeContainer = $('#ps-costume-chips');
  if (costumeContainer && costumes) {
    clear(costumeContainer);
    if (!photoStudioState.selectedCostume) photoStudioState.selectedCostume = costumes[0];
    costumes.forEach((item) => {
      const btn = el('button', {
        type: 'button',
        class: 'chip-btn' + (photoStudioState.selectedCostume?.id === item.id ? ' active' : ''),
      }, item.label);
      btn.addEventListener('click', () => {
        photoStudioState.selectedCostume = item;
        $('#ps-custom-costume').value = '';
        photoStudioState.customCostume = '';
        $('#ps-costume-indicator').textContent = 'Preset';
        renderChips();
        compilePrompt();
      });
      costumeContainer.append(btn);
    });
  }

  // 3. Expressions
  const exprContainer = $('#ps-expression-chips');
  if (exprContainer && expressions) {
    clear(exprContainer);
    if (!photoStudioState.selectedExpression) photoStudioState.selectedExpression = expressions[0];
    expressions.forEach((item) => {
      const btn = el('button', {
        type: 'button',
        class: 'chip-btn' + (photoStudioState.selectedExpression?.id === item.id ? ' active' : ''),
      }, item.label);
      btn.addEventListener('click', () => {
        photoStudioState.selectedExpression = item;
        $('#ps-custom-expression').value = '';
        photoStudioState.customExpression = '';
        $('#ps-expr-indicator').textContent = 'Preset';
        renderChips();
        compilePrompt();
      });
      exprContainer.append(btn);
    });
  }

  // 4. Angles
  const angleContainer = $('#ps-angle-chips');
  if (angleContainer && angles) {
    clear(angleContainer);
    if (!photoStudioState.selectedAngle) photoStudioState.selectedAngle = angles[0];
    angles.forEach((item) => {
      const btn = el('button', {
        type: 'button',
        class: 'chip-btn' + (photoStudioState.selectedAngle?.id === item.id ? ' active' : ''),
      }, item.label);
      btn.addEventListener('click', () => {
        photoStudioState.selectedAngle = item;
        $('#ps-custom-angle').value = '';
        photoStudioState.customAngle = '';
        $('#ps-angle-indicator').textContent = 'Preset';
        renderChips();
        compilePrompt();
      });
      angleContainer.append(btn);
    });
  }
}

export async function compilePrompt() {
  if (!photoStudioState.selectedPersonaId) return;

  const payload = {
    persona_id: photoStudioState.selectedPersonaId,
    location: photoStudioState.customLocation || photoStudioState.selectedLocation?.prompt || '',
    costume: photoStudioState.customCostume || photoStudioState.selectedCostume?.prompt || '',
    expression: photoStudioState.customExpression || photoStudioState.selectedExpression?.prompt || '',
    angle: photoStudioState.customAngle || photoStudioState.selectedAngle?.prompt || '',
    custom_direction: '',
    model_id: 'cyberrealistic-xl',
  };

  try {
    const data = await post('/api/photo-studio/compile-prompt', payload);
    const approvedArea = $('#ps-approved-prompt');
    const negativeArea = $('#ps-negative-prompt');
    const tokenBadge = $('#ps-token-badge');

    if (approvedArea) approvedArea.value = data.prompt;
    if (negativeArea) negativeArea.value = data.negative_prompt;
    if (tokenBadge) tokenBadge.textContent = `~${data.token_estimate} tokens (CLIP optimal)`;
  } catch (err) {
    console.error('Failed to compile Photo Studio prompt', err);
  }
}

export async function triggerGenerate() {
  if (photoStudioState.isGenerating) return;

  const promptInput = $('#ps-approved-prompt');
  if (!promptInput || !promptInput.value.trim()) {
    notify('Please review or enter a positive prompt in the approval gate.', true);
    return;
  }

  const personaId = photoStudioState.selectedPersonaId;
  if (!personaId) {
    notify('Please select an active persona anchor.', true);
    return;
  }

  const prompt = promptInput.value.trim();
  const negativePrompt = $('#ps-negative-prompt')?.value.trim() || '';

  const ratio = $('#ps-aspect-ratio')?.value || '768x1152';
  const [width, height] = ratio.split('x').map(Number);
  const steps = Number($('#ps-steps')?.value || 28);
  const guidance = Number($('#ps-guidance')?.value || 5.0);
  const seedVal = $('#ps-seed')?.value.trim();
  const seed = seedVal ? Number(seedVal) : null;

  const payload = {
    persona_id: personaId,
    prompt,
    negative_prompt: negativePrompt,
    model: 'cyberrealistic-xl',
    width,
    height,
    steps,
    guidance,
    seed,
    rights_confirmed: true,
  };

  const approveBtn = $('#ps-approve-generate-btn');
  const progressBox = $('#ps-progress-box');
  const progressStatus = $('#ps-progress-status');
  const progressSub = $('#ps-progress-sub');

  try {
    photoStudioState.isGenerating = true;
    if (approveBtn) approveBtn.disabled = true;
    if (progressBox) progressBox.classList.remove('hidden');

    if (progressStatus) progressStatus.textContent = 'Loading CyberRealistic XL on Apple Silicon (MPS)...';
    if (progressSub) progressSub.textContent = 'Preparing 16GB unified memory pipeline. Denoising begins shortly...';

    const timer = setTimeout(() => {
      if (progressStatus) progressStatus.textContent = 'Executing 28 denoising steps on MPS...';
      if (progressSub) progressSub.textContent = 'Applying camera perspective, costume, facial anchor, and skin texture (~35s left)...';
    }, 7000);

    const timer2 = setTimeout(() => {
      if (progressStatus) progressStatus.textContent = 'Denoising active...';
      if (progressSub) progressSub.textContent = 'Finalizing film grain, hazel eyes, and pore detailing...';
    }, 28000);

    const result = await post('/api/photo-studio/generate', payload);

    clearTimeout(timer);
    clearTimeout(timer2);

    photoStudioState.lastResult = result;

    // Display image in viewport
    const viewport = $('#ps-image-viewport');
    if (viewport) {
      clear(viewport);
      const img = el('img', {
        src: result.url,
        alt: result.prompt,
        loading: 'eager',
      });
      viewport.append(img);
    }

    // Update meta badge
    const badge = $('#ps-result-meta-badge');
    if (badge) {
      badge.textContent = `✓ Generated: Seed #${result.seed} · ${result.width}×${result.height} · CyberRealistic XL`;
      badge.className = 'result-badge ready';
    }

    // Show actions
    const actions = $('#ps-result-actions');
    const downloadBtn = $('#ps-download-btn');
    if (actions) actions.classList.remove('hidden');
    if (downloadBtn) {
      downloadBtn.href = result.url;
      downloadBtn.download = result.filename;
    }

    notify('✨ Image generated successfully and added to Media Review!');

    // Trigger studio state refresh so review tab has the new asset
    if (window.studioRefresh) {
      window.studioRefresh();
    }
  } catch (err) {
    console.error('Generation failed', err);
    notify('Image generation failed: ' + (err.message || String(err)), true);
  } finally {
    photoStudioState.isGenerating = false;
    if (approveBtn) approveBtn.disabled = false;
    if (progressBox) progressBox.classList.add('hidden');
  }
}

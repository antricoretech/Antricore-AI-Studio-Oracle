/**
 * AI INFLUENCER STUDIO - FRONTEND V2 CONTROLLER
 * Luxury Linear Hybrid UI Engine
 * - Tab 1: Exact Atelier Nordic Glass (Option 3) & Generic Master Persona Generator
 * - Tab 2: Photoshoot Orchestrator with Dual Modes & Live 4K Stage
 * - Tab 3: Obsidian Luxury Creator (Option 1), Persona Feed & Calendar (Option 2)
 * - Tab 4: Media Gallery & Deep Metadata Inspector Modal
 * - Tab 5: Hardware Acceleration Gauges & Task Queue
 */

document.addEventListener('DOMContentLoaded', () => {
  const CANONICAL_PERSONA_DRAFT_KEY = 'persona-studio.canonical-persona-draft.v1';

  // Global Application State
  const state = {
    personas: [],
    activePersonaId: 'maya_bhutia',
    activeTab: 'tab-vault',
    vaultSubView: 'subview-vault-inspector',
    storySubView: 'subview-creator',
    storyMode: 'personal', // 'personal' (🟣) or 'commercial' (🟡)
    storyFormat: 'single', // 'single' or 'carousel'
    selectedHookIdx: 0,
    currentHooksData: null,
    calendarData: null,
    carouselSlide: 1,
    galleryAssets: [],
    synthesizedDNA: null,
    orchMode: 'txt2img',
    orchAspectRatio: '9:16'
  };

  // DOM Elements Registry
  const els = {
    globalPersonaSelect: document.getElementById('global-persona-select'),
    headerPersonaAvatar: document.getElementById('header-persona-avatar'),
    headerVramChip: document.getElementById('header-vram-chip'),
    headerVramText: document.getElementById('header-vram-text'),

    // Primary Tabs
    tabButtons: document.querySelectorAll('.tab-btn'),
    tabPanels: document.querySelectorAll('.tab-panel'),

    // Tab 1: Vault Inspector (Option 3)
    vaultSubViewBtns: document.querySelectorAll('[data-vaultview]'),
    vaultSubViews: document.querySelectorAll('.vault-subview'),
    vaultActiveAnchorLbl: document.getElementById('vault-active-anchor-lbl'),
    vaultPersonaName: document.getElementById('vault-persona-name'),
    vaultPersonaDesc: document.getElementById('vault-persona-desc'),
    vaultTurnaroundGrid: document.getElementById('vault-turnaround-grid'),
    bioHeaderLine: document.getElementById('bio-header-line'),
    bioValHeight: document.getElementById('bio-val-height'),
    bioValEthnicity: document.getElementById('bio-val-ethnicity'),
    bioValFigure: document.getElementById('bio-val-figure'),
    bioValSkin: document.getElementById('bio-val-skin'),
    bioValWeight: document.getElementById('bio-val-weight'),
    bioValHair: document.getElementById('bio-val-hair'),
    vaultMacroCard: document.getElementById('vault-macro-card'),
    vaultMacroImg: document.getElementById('vault-macro-img'),
    vaultMacroTitle: document.getElementById('vault-macro-title'),
    vaultMacroDesc: document.getElementById('vault-macro-desc'),
    vaultCategoriesGrid: document.getElementById('vault-categories-grid'),
    vaultAdultGrid: document.getElementById('vault-adult-grid'),
    vaultAdultHeader: document.getElementById('vault-adult-header'),
    vaultAdultChevron: document.getElementById('vault-adult-chevron'),
    btnToggleVaultAdult: document.getElementById('btn-toggle-vault-adult'),
    btnQuickNewPersona: document.getElementById('btn-quick-new-persona'),
    btnDeleteActivePersona: document.getElementById('btn-delete-active-persona'),
    btnHeaderDeletePersona: document.getElementById('btn-header-delete-persona'),
    modalDeletePersona: document.getElementById('modal-delete-persona'),
    btnCloseDeleteModal: document.getElementById('btn-close-delete-modal'),
    btnCancelDeleteModal: document.getElementById('btn-cancel-delete-modal'),
    btnConfirmDeleteModal: document.getElementById('btn-confirm-delete-modal'),
    delModalPersonaSelect: document.getElementById('del-modal-persona-select'),
    delModalAvatar: document.getElementById('del-modal-avatar'),
    delModalName: document.getElementById('del-modal-name'),
    delModalMeta: document.getElementById('del-modal-meta'),

    // Tab 1: Vault Generator
    vaultNarrativeInput: document.getElementById('vault-narrative-input'),
    btnParseNarrative: document.getElementById('btn-parse-narrative'),
    btnFreezeMasterVault: document.getElementById('btn-freeze-master-vault'),
    rfWardrobeSig: document.getElementById('rf-wardrobe-sig'),
    rfWorldSig: document.getElementById('rf-world-sig'),
    synthBioHeader: document.getElementById('synth-bio-header'),
    synthValFigure: document.getElementById('synth-val-figure'),
    synthValBust: document.getElementById('synth-val-bust'),
    synthValWaist: document.getElementById('synth-val-waist'),
    synthValComplexion: document.getElementById('synth-val-complexion'),
    synthValEyes: document.getElementById('synth-val-eyes'),
    synthValHair: document.getElementById('synth-val-hair'),
    synthValFacial: document.getElementById('synth-val-facial'),
    synthValLips: document.getElementById('synth-val-lips'),
    synthValSkin: document.getElementById('synth-val-skin'),
    synthValSilhouette: document.getElementById('synth-val-silhouette'),
    synthCanonicalPrompt: document.getElementById('synth-canonical-prompt'),
    synthLiveStatusText: document.getElementById('synth-live-status-text'),
    synthStatusDot: document.getElementById('synth-status-dot'),
    freezeLiveStatus: document.getElementById('freeze-live-status'),
    vaultPackCompletionSummary: document.getElementById('vault-pack-completion-summary'),
    vaultGenTelemetryPanel: document.getElementById('vault-gen-telemetry-panel'),
    vaultGenProgressBar: document.getElementById('vault-gen-progress-bar'),
    vaultGenStepBadge: document.getElementById('vault-gen-step-badge'),
    vaultGenPercentBadge: document.getElementById('vault-gen-percent-badge'),
    vaultGenCurStep: document.getElementById('vault-gen-cur-step'),
    vaultGenTimeStarted: document.getElementById('vault-gen-time-started'),
    vaultGenTimeElapsed: document.getElementById('vault-gen-time-elapsed'),
    vaultGenTimeRemaining: document.getElementById('vault-gen-time-remaining'),

    // Tab 2: Photoshoot Orchestrator
    btnOrchModeTxt: document.getElementById('btn-orch-mode-txt'),
    btnOrchModeImg: document.getElementById('btn-orch-mode-img'),
    orchPromptInput: document.getElementById('orch-prompt-input'),
    orchImg2imgBox: document.getElementById('orch-img2img-box'),
    orchDenoisingSlider: document.getElementById('orch-denoising-slider'),
    denoisingValLbl: document.getElementById('denoising-val-lbl'),
    orchModelSelect: document.getElementById('orch-model-select'),
    orchFramingSelect: document.getElementById('orch-framing-select'),
    orchLensSelect: document.getElementById('orch-lens-select'),
    orchLightingSelect: document.getElementById('orch-lighting-select'),
    btnSuggestScenes: document.getElementById('btn-suggest-scenes'),
    orchSceneChipsContainer: document.getElementById('orch-scene-chips-container'),
    aspectButtons: document.querySelectorAll('.aspect-btn'),
    btnOrchGenerate: document.getElementById('btn-orch-generate'),
    orchCanvasImage: document.getElementById('orch-canvas-image'),
    orchCanvasEditorialOverlay: document.getElementById('orch-canvas-editorial-overlay'),
    btnCanvasToggleClean: document.getElementById('btn-canvas-toggle-clean'),
    btnCanvasToggleEditorial: document.getElementById('btn-canvas-toggle-editorial'),
    btnDownloadOrchRender: document.getElementById('btn-download-orch-render'),

    // Tab 3: Story Studio
    storySubViewBtns: document.querySelectorAll('[data-subview]'),
    storySubViews: document.querySelectorAll('.story-subview'),
    storyActivePersonaLbl: document.getElementById('story-active-persona-lbl'),
    btnFormatSingle: document.getElementById('btn-format-single'),
    btnFormatCarousel: document.getElementById('btn-format-carousel'),
    btnModePersonal: document.getElementById('btn-mode-personal'),
    btnModeCommercial: document.getElementById('btn-mode-commercial'),
    commercialFieldsWrap: document.getElementById('commercial-fields-wrap'),
    storyNicheSelect: document.getElementById('story-niche-select'),
    storyBrandName: document.getElementById('story-brand-name'),
    storyPromoCode: document.getElementById('story-promo-code'),
    btnGenerateHooks: document.getElementById('btn-generate-hooks'),
    storyHooksContainer: document.getElementById('story-hooks-container'),
    hookTexts: [
      document.getElementById('hook-text-0'),
      document.getElementById('hook-text-1'),
      document.getElementById('hook-text-2')
    ],
    stageMainImage: document.getElementById('stage-main-image'),
    stageOverlayPersona: document.getElementById('stage-overlay-persona'),
    overlayHookDisplay: document.getElementById('overlay-hook-display'),
    overlayDeckDisplay: document.getElementById('overlay-deck-display'),
    captionPreviewText: document.getElementById('caption-preview-text'),
    btnCopyCaption: document.getElementById('btn-copy-caption'),
    btnDownloadClean: document.getElementById('btn-download-clean'),
    btnDownloadEditorial: document.getElementById('btn-download-editorial'),
    btnScheduleThisPost: document.getElementById('btn-schedule-this-post'),
    carouselNavWrap: document.getElementById('carousel-nav-wrap'),
    carouselSlideIndicator: document.getElementById('carousel-slide-indicator'),
    btnPrevSlide: document.getElementById('btn-prev-slide'),
    btnNextSlide: document.getElementById('btn-next-slide'),

    // Tab 3 Feed
    feedPersonaName: document.getElementById('feed-persona-name'),
    personaFeedGrid: document.getElementById('persona-feed-grid'),
    feedFilterBtns: document.querySelectorAll('[data-feedfilter]'),

    // Tab 3 Calendar
    calendarDaysColumns: document.getElementById('calendar-days-columns'),
    gaugeRatioText: document.getElementById('gauge-ratio-text'),
    gaugeFillPersonal: document.getElementById('gauge-fill-personal'),
    gaugeFillCommercial: document.getElementById('gauge-fill-commercial'),
    gaugeStatusMsg: document.getElementById('gauge-status-msg'),
    inspThumbSide: document.getElementById('insp-thumb-side'),
    inspSideName: document.getElementById('insp-side-name'),
    inspSidePrompt: document.getElementById('insp-side-prompt'),
    inspSideHooks: document.getElementById('insp-side-hooks'),

    // Tab 4 Gallery
    galleryGrid: document.getElementById('gallery-grid'),
    galleryFilterPersona: document.getElementById('gallery-filter-persona'),
    galleryFilterCategory: document.getElementById('gallery-filter-category'),
    galleryFilterAr: document.getElementById('gallery-filter-ar'),
    galleryMetaModal: document.getElementById('gallery-meta-modal'),
    modalMetaTitle: document.getElementById('modal-meta-title'),
    modalMetaThumb: document.getElementById('modal-meta-thumb'),
    modalMetaPersona: document.getElementById('modal-meta-persona'),
    modalMetaModel: document.getElementById('modal-meta-model'),
    modalMetaSeed: document.getElementById('modal-meta-seed'),
    modalMetaPrompt: document.getElementById('modal-meta-prompt'),
    btnCloseMetaModal: document.getElementById('btn-close-meta-modal'),
    btnModalUseStory: document.getElementById('btn-modal-use-story'),
    btnModalUseImg2img: document.getElementById('btn-modal-use-img2img'),
    btnGalleryRefresh: document.getElementById('btn-gallery-refresh'),
    btnGalleryToggleArchive: document.getElementById('btn-gallery-toggle-archive'),
    btnGalleryBackActive: document.getElementById('btn-gallery-back-active'),
    galleryActiveContainer: document.getElementById('gallery-active-container'),
    galleryArchiveContainer: document.getElementById('gallery-archive-container'),
    galleryArchiveList: document.getElementById('gallery-archive-list'),
    archiveCountBadge: document.getElementById('archive-count-badge'),

    // Tab 5 Telemetry
    sysVramGb: document.getElementById('sys-vram-gb'),
    sysVramStatus: document.getElementById('sys-vram-status'),
    btnPurgeVram: document.getElementById('btn-purge-vram'),
    sysLogStream: document.getElementById('sys-log-stream'),
    queueTaskLabel: document.getElementById('queue-task-label'),
    queueCountLabel: document.getElementById('queue-count-label'),
    queueProgressBar: document.getElementById('queue-progress-bar'),
    queueActiveDetails: document.getElementById('queue-active-details'),
    queueActiveJobTitle: document.getElementById('queue-active-job-title'),
    queueActiveJobPct: document.getElementById('queue-active-job-pct'),
    queueActiveJobPack: document.getElementById('queue-active-job-pack'),
    queueActiveJobElapsed: document.getElementById('queue-active-job-elapsed'),
    queueActiveJobRemaining: document.getElementById('queue-active-job-remaining')
  };

  // ----------------------------------------------------------------------------
  // INITIALIZATION
  // ----------------------------------------------------------------------------
  async function init() {
    setupPrimaryNavigation();
    setupVaultSubViews();
    setupGeneratorControls();
    setupOrchestratorControls();
    setupStoryStudioControls();
    setupPersonaFeedControls();
    setupGalleryControls();
    setupTelemetryControls();

    await loadPersonas();
    await loadGalleryAssets();
    await updateArchiveBadge();
    await loadCalendarForPersona(state.activePersonaId);
    await loadTelemetry();
    setInterval(loadTelemetry, 2500);
  }

  // ----------------------------------------------------------------------------
  // 1. PRIMARY TAB NAVIGATION
  // ----------------------------------------------------------------------------
  function setupPrimaryNavigation() {
    els.tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetTab = btn.getAttribute('data-tab');
        if (!targetTab) return;

        els.tabButtons.forEach(b => b.classList.remove('active'));
        els.tabPanels.forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        const activeSection = document.getElementById(targetTab);
        if (activeSection) {
          activeSection.classList.add('active');
        }
        state.activeTab = targetTab;
        if (targetTab === 'tab-telemetry') {
          loadTelemetry();
        }
      });
    });

    // Global Persona Switcher
    if (els.globalPersonaSelect) {
      els.globalPersonaSelect.addEventListener('change', (e) => {
        const selected = e.target.value;
        if (selected === '__create_new__') {
          // Switch to Tab 1 (Vault) and Generator subview
          activateTab('tab-vault');
          switchVaultSubView('subview-vault-generator');
          els.globalPersonaSelect.value = state.activePersonaId;
          return;
        }
        switchActivePersona(selected);
      });
    }

    if (els.btnQuickNewPersona) {
      els.btnQuickNewPersona.addEventListener('click', () => {
        switchVaultSubView('subview-vault-generator');
      });
    }

    // Interactive Delete & Archive Persona Modal System (Zero native confirm popup reliance)
    function openDeletePersonaModal(preferredId) {
      if (!els.modalDeletePersona) return;
      if (state.personas.length <= 1) {
        alert("Cannot delete the only remaining active persona in the studio.");
        return;
      }
      const targetId = preferredId || state.activePersonaId || (state.personas[0] && state.personas[0].id);

      if (els.delModalPersonaSelect) {
        els.delModalPersonaSelect.innerHTML = '';
        state.personas.forEach(p => {
          const opt = document.createElement('option');
          opt.value = p.id;
          opt.textContent = `${p.name} (${p.age} · ${personaOrigin(p)})`;
          if (p.id === targetId) opt.selected = true;
          els.delModalPersonaSelect.appendChild(opt);
        });
      }

      updateDeleteModalDetails(targetId);
      els.modalDeletePersona.style.display = 'flex';
    }

    function updateDeleteModalDetails(personaId) {
      const p = state.personas.find(item => item.id === personaId) || state.personas[0];
      if (!p) return;
      if (els.delModalAvatar) {
        const avatarSrc = (p.category_baselines && p.category_baselines[0]?.url) || p.avatar || '/generated/master_persona_maya/maya_01_turnaround_front.png';
        els.delModalAvatar.src = avatarSrc;
      }
      if (els.delModalName) els.delModalName.textContent = p.name;
      if (els.delModalMeta) els.delModalMeta.textContent = `${p.age} YRS · ${personaOrigin(p)}`;
    }

    function closeDeletePersonaModal() {
      if (els.modalDeletePersona) els.modalDeletePersona.style.display = 'none';
    }

    if (els.btnDeleteActivePersona) {
      els.btnDeleteActivePersona.addEventListener('click', () => {
        openDeletePersonaModal(state.activePersonaId);
      });
    }

    if (els.btnHeaderDeletePersona) {
      els.btnHeaderDeletePersona.addEventListener('click', () => {
        openDeletePersonaModal(state.activePersonaId);
      });
    }

    if (els.btnCloseDeleteModal) els.btnCloseDeleteModal.addEventListener('click', closeDeletePersonaModal);
    if (els.btnCancelDeleteModal) els.btnCancelDeleteModal.addEventListener('click', closeDeletePersonaModal);

    if (els.delModalPersonaSelect) {
      els.delModalPersonaSelect.addEventListener('change', (e) => {
        updateDeleteModalDetails(e.target.value);
      });
    }

    if (els.btnConfirmDeleteModal) {
      els.btnConfirmDeleteModal.addEventListener('click', async () => {
        const personaId = els.delModalPersonaSelect ? els.delModalPersonaSelect.value : state.activePersonaId;
        const targetP = state.personas.find(p => p.id === personaId) || getCurrentPersona();
        if (!targetP) return;

        const origHtml = els.btnConfirmDeleteModal.innerHTML;
        els.btnConfirmDeleteModal.innerHTML = 'Archiving Persona...';
        els.btnConfirmDeleteModal.disabled = true;

        try {
          appendLog(`[Archive] Deleting & archiving persona "${targetP.name}" (${targetP.id})...`);
          const res = await fetch(`/api/v2/personas/${targetP.id}`, {method: 'DELETE'});
          if (!res.ok) {
            const errData = await res.json();
            throw new Error(errData.detail || "Failed to delete persona");
          }
          const data = await res.json();
          appendLog(`[Archive] Persona "${targetP.name}" successfully archived! ${data.remaining_count} personas active.`);

          closeDeletePersonaModal();

          if (data.next_persona_id) {
            state.activePersonaId = data.next_persona_id;
          }
          await loadPersonas();
          if (data.next_persona_id) {
            switchActivePersona(data.next_persona_id);
          }
          await loadGalleryAssets();
          await updateArchiveBadge();
        } catch (err) {
          console.error(err);
          alert(`Error archiving persona: ${err.message}`);
        } finally {
          els.btnConfirmDeleteModal.innerHTML = origHtml;
          els.btnConfirmDeleteModal.disabled = false;
        }
      });
    }
  }

  function activateTab(tabId) {
    els.tabButtons.forEach(btn => {
      if (btn.getAttribute('data-tab') === tabId) {
        btn.click();
      }
    });
  }

  // ----------------------------------------------------------------------------
  // 2. TAB 1: MASTER VAULT & GENERATOR ENGINE
  // ----------------------------------------------------------------------------
  function setupVaultSubViews() {
    els.vaultSubViewBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetView = btn.getAttribute('data-vaultview');
        switchVaultSubView(targetView);
      });
    });

    // Collapsible Adult & Intimate Baselines (Default Collapsed)
    let adultExpanded = false;
    const toggleAdultSection = () => {
      adultExpanded = !adultExpanded;
      if (els.vaultAdultGrid) {
        els.vaultAdultGrid.style.display = adultExpanded ? 'grid' : 'none';
      }
      if (els.btnToggleVaultAdult) {
        els.btnToggleVaultAdult.textContent = adultExpanded ? '▴ Collapse' : '▾ Expand';
      }
      if (els.vaultAdultChevron) {
        els.vaultAdultChevron.style.transform = adultExpanded ? 'rotate(180deg)' : 'rotate(0deg)';
      }
    };

    if (els.vaultAdultHeader) {
      els.vaultAdultHeader.addEventListener('click', toggleAdultSection);
    }
  }

  function switchVaultSubView(viewId) {
    state.vaultSubView = viewId;
    els.vaultSubViewBtns.forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-vaultview') === viewId);
    });
    els.vaultSubViews.forEach(v => {
      v.style.display = (v.id === viewId) ? 'block' : 'none';
      v.classList.toggle('active', v.id === viewId);
    });
  }

  let narrativeDebounceTimer = null;

  function handoffSynthesizedPersonaToCanonicalFlow() {
    const dna = state.synthesizedDNA;
    if (!dna) throw new Error('No synthesized persona DNA is available.');

    const biometrics = dna.biometrics || {};
    const ringfence = dna.diversity_ringfence || {};
    const age = Number(dna.age);
    const safeAge = Number.isInteger(age) && age >= 18 && age <= 110 ? age : 25;
    const name = String(dna.name || 'Untitled Persona').trim();
    const origin = String(dna.origin || 'International').trim();
    const tagline = String(dna.tagline || '').trim();
    const masterPrompt = String(dna.master_prompt || '').trim();
    const universalNegative = String(dna.universal_negative || '').trim();
    const wardrobe = String(ringfence.wardrobe_signature || '').trim();
    const worldSetting = String(ringfence.world_setting || '').trim();

    const draft = {
      name,
      age: safeAge,
      description: [tagline, `${name} is a fictional adult creator based in ${origin}.`]
        .filter(Boolean).join(' '),
      appearance: [
        biometrics.complexion,
        biometrics.eyes,
        biometrics.hair,
        biometrics.facial_structure,
        biometrics.skin_texture,
        biometrics.silhouette,
      ].filter(Boolean).join('; ') || 'Stable facial identity and consistent adult visual characteristics.',
      disclosure: 'Fictional AI-generated adult persona',
      characteristics: {
        consistency_anchor: {
          source: 'legacy-vault-synthesis',
          master_prompt: masterPrompt,
          universal_negative: universalNegative,
          ringfence,
          biometrics,
        },
        face: {
          face_shape: biometrics.facial_structure || '',
          skin_tone: biometrics.complexion || '',
          eyes: biometrics.eyes || '',
          hair: biometrics.hair || '',
          distinguishing_features: [biometrics.distinctive_feature, biometrics.lips, biometrics.skin_texture]
            .filter(Boolean).join('; '),
        },
        physique: {
          height_and_build: [biometrics.height, biometrics.weight, biometrics.figure]
            .filter(Boolean).join('; '),
          posture_and_movement: biometrics.silhouette || '',
          age_cues: `${safeAge}-year-old adult creator`,
        },
        style: {
          wardrobe,
          materials_and_palette: worldSetting,
          accessories_and_grooming: '',
          glamour_direction: 'Use the approved identity anchors and content-pack style direction.',
        },
        personality: {},
        world: {
          cultural_context: origin,
          home_base: origin,
          recurring_locations: worldSetting,
          content_pillars: '',
        },
        camera: {
          framing: 'Consistent editorial portrait framing',
          lens_and_depth: 'Natural photographic depth of field',
          lighting: 'Controlled editorial lighting',
          color_grade: 'Natural, realistic color grade',
        },
      },
      source: 'legacy-vault-synthesis',
    };

    try {
      sessionStorage.setItem(CANONICAL_PERSONA_DRAFT_KEY, JSON.stringify(draft));
    } catch (error) {
      throw new Error(`Unable to preserve the synthesized draft locally: ${error.message}`);
    }

    window.location.assign('/workspace#personas');
  }

  function setupGeneratorControls() {
    // Real-time live synthesis on typing in narrative textarea
    if (els.vaultNarrativeInput) {
      els.vaultNarrativeInput.addEventListener('input', () => {
        if (narrativeDebounceTimer) clearTimeout(narrativeDebounceTimer);
        const text = els.vaultNarrativeInput.value.trim();
        if (!text) {
          if (els.synthStatusDot) els.synthStatusDot.style.background = 'var(--gold-primary)';
          if (els.synthLiveStatusText) els.synthLiveStatusText.textContent = "Ready. Enter any narrative or select a preset to synthesize DNA.";
          return;
        }

        if (els.synthStatusDot) els.synthStatusDot.style.background = '#38BDF8';
        if (els.synthLiveStatusText) els.synthLiveStatusText.innerHTML = '<span style="color:#38BDF8;">⚡ Synthesizing Persona DNA in real-time...</span>';

        narrativeDebounceTimer = setTimeout(async () => {
          await triggerNarrativeSynthesis();
        }, 350);
      });
    }

    // Parse Narrative Button
    if (els.btnParseNarrative) {
      els.btnParseNarrative.addEventListener('click', async () => {
        const origText = els.btnParseNarrative.innerHTML;
        els.btnParseNarrative.innerHTML = '⚡ Synthesizing Persona DNA...';
        await triggerNarrativeSynthesis();
        setTimeout(() => { els.btnParseNarrative.innerHTML = origText; }, 500);
      });
    }

    // Copy Canonical Prompt Button
    const btnCopyPrompt = document.getElementById('btn-copy-canonical-prompt');
    if (btnCopyPrompt) {
      btnCopyPrompt.addEventListener('click', () => {
        const promptEl = document.getElementById('synth-canonical-prompt');
        if (promptEl) {
          const textToCopy = promptEl.textContent.trim();
          navigator.clipboard.writeText(textToCopy).then(() => {
            const orig = btnCopyPrompt.innerHTML;
            btnCopyPrompt.innerHTML = '✓ Copied!';
            setTimeout(() => { btnCopyPrompt.innerHTML = orig; }, 1800);
          }).catch(err => {
            console.error("Copy failed:", err);
          });
        }
      });
    }

    // Freeze Master Vault Button
    if (els.btnFreezeMasterVault) {
      els.btnFreezeMasterVault.addEventListener('click', async () => {
        // ALWAYS re-synthesize current text first so we never freeze stale cached data
        await triggerNarrativeSynthesis();
        if (!state.synthesizedDNA) {
          alert("Please enter a persona narrative description first.");
          return;
        }

        const origBtnHtml = els.btnFreezeMasterVault.innerHTML;
        els.btnFreezeMasterVault.innerHTML = '✦ Starting 13-Image Identity Vault Inference...';
        els.btnFreezeMasterVault.disabled = true;

        if (els.freezeLiveStatus) {
          els.freezeLiveStatus.style.display = 'block';
          els.freezeLiveStatus.innerHTML = `✦ Initializing 13 reference packs, biometric anchors, and inference pipeline for <strong>${state.synthesizedDNA.name}</strong>...`;
        }

        try {
          appendLog(`[Master Vault] Prepared '${state.synthesizedDNA.name}' for canonical Persona creation review.`);
          if (els.freezeLiveStatus) {
            els.freezeLiveStatus.innerHTML = `âœ¦ Opening canonical Persona creation for <strong>${state.synthesizedDNA.name}</strong> review...`;
          }
          handoffSynthesizedPersonaToCanonicalFlow();
          return;

          // Kept below as a legacy compatibility reference until the old Vault UI is retired.
          appendLog(`[Master Vault] Registering 13-Image Vault for '${state.synthesizedDNA.name}'...`);
          const res = await fetch('/api/v2/personas/create', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(state.synthesizedDNA)
          });

          if (!res.ok) {
            const errText = await res.text();
            throw new Error(`Server returned ${res.status}: ${errText.substring(0, 120)}`);
          }

          const data = await res.json();
          appendLog(`[Master Vault] Persona '${data.persona.name}' registered. Launching background 13-pack generation...`);

          if (data.job_id) {
            pollVaultGeneration(data.job_id, data.persona.id, data.persona.name, origBtnHtml);
          } else {
            if (els.freezeLiveStatus) {
              els.freezeLiveStatus.innerHTML = `<span style="color:var(--emerald);">✓ 13-Image Master Vault successfully frozen & registered for <strong>${data.persona.name}</strong>!</span>`;
            }
            await loadPersonas();
            switchActivePersona(data.persona.id);
            setTimeout(() => {
              switchVaultSubView('subview-vault-inspector');
              if (els.freezeLiveStatus) els.freezeLiveStatus.style.display = 'none';
              els.btnFreezeMasterVault.innerHTML = origBtnHtml;
              els.btnFreezeMasterVault.disabled = false;
            }, 1200);
          }

        } catch (err) {
          console.error(err);
          appendLog(`[Master Vault Error] ${err.message}`);
          if (els.freezeLiveStatus) {
            els.freezeLiveStatus.innerHTML = `<span style="color:#EF4444;">Error: ${err.message}</span>`;
          }
          els.btnFreezeMasterVault.innerHTML = origBtnHtml;
          els.btnFreezeMasterVault.disabled = false;
        }
      });
    }
  }

  let vaultPollInterval = null;

  function pollVaultGeneration(jobId, personaId, personaName, origBtnHtml) {
    if (vaultPollInterval) clearInterval(vaultPollInterval);
    if (els.vaultGenTelemetryPanel) els.vaultGenTelemetryPanel.style.display = 'block';

    vaultPollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/v2/personas/vault-status/${jobId}`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.status === 'not_found') return;

        // Update Progress Bar & Badges
        const pct = data.percent || 0;
        if (els.vaultGenProgressBar) els.vaultGenProgressBar.style.width = `${pct}%`;
        if (els.vaultGenPercentBadge) els.vaultGenPercentBadge.textContent = `${pct}%`;
        if (els.vaultGenStepBadge) els.vaultGenStepBadge.textContent = `Pack ${data.current_index || 0}/13`;
        if (els.vaultGenCurStep) els.vaultGenCurStep.textContent = data.current_pack_name || 'Generating...';
        if (els.vaultGenTimeStarted) els.vaultGenTimeStarted.textContent = data.start_time_str || '--:--:--';
        if (els.vaultGenTimeElapsed) els.vaultGenTimeElapsed.textContent = data.elapsed_str || '0s';
        if (els.vaultGenTimeRemaining) els.vaultGenTimeRemaining.textContent = data.remaining_str || 'Calculating...';

        if (els.freezeLiveStatus) {
          els.freezeLiveStatus.style.display = 'block';
          els.freezeLiveStatus.innerHTML = `✦ Generating Pack ${data.current_index || 0}/13 (<strong>${data.current_pack_name || ''}</strong>) · Elapsed: <strong>${data.elapsed_str || '0s'}</strong> · Est. Remaining: <strong>${data.remaining_str || 'Calculating...'}</strong>`;
        }

        // Update Completed Packs Badges (1 to 13)
        if (Array.isArray(data.completed_packs)) {
          data.completed_packs.forEach(idx => {
            const badge = document.getElementById(`badge-pack-${idx}`);
            if (badge) {
              badge.textContent = 'Yes';
              badge.className = 'pack-status-badge badge-complete';
            }
            const cell = document.getElementById(`pack-target-${idx}`);
            if (cell) {
              cell.classList.add('target-cell-completed');
            }
            const thumb = document.getElementById(`thumb-pack-${idx}`);
            if (thumb) {
              thumb.style.borderColor = 'var(--emerald)';
              thumb.style.background = 'rgba(16, 185, 129, 0.22)';
            }
          });
          if (els.vaultPackCompletionSummary) {
            els.vaultPackCompletionSummary.textContent = `${data.completed_packs.length} / 13 Generated`;
          }
        }

        if (data.status === 'completed') {
          clearInterval(vaultPollInterval);
          vaultPollInterval = null;
          appendLog(`[Master Vault] All 13 packs generated & verified for '${personaName}'!`);
          if (els.freezeLiveStatus) {
            els.freezeLiveStatus.innerHTML = `<span style="color:var(--emerald); font-weight:700;">✓ 13-Image Master Vault completely generated & registered for <strong>${personaName}</strong>! Switching to Inspector...</span>`;
          }
          await loadPersonas();
          switchActivePersona(personaId);
          setTimeout(() => {
            switchVaultSubView('subview-vault-inspector');
            if (els.btnFreezeMasterVault) {
              els.btnFreezeMasterVault.innerHTML = origBtnHtml || '✦ Generate & Freeze 13-Image Master Vault';
              els.btnFreezeMasterVault.disabled = false;
            }
          }, 1500);
        } else if (data.status === 'error') {
          clearInterval(vaultPollInterval);
          vaultPollInterval = null;
          appendLog(`[Master Vault Error] ${data.error}`);
          if (els.freezeLiveStatus) {
            els.freezeLiveStatus.innerHTML = `<span style="color:#EF4444;">Generation failed: ${data.error}</span>`;
          }
          if (els.btnFreezeMasterVault) {
            els.btnFreezeMasterVault.innerHTML = origBtnHtml || '✦ Generate & Freeze 13-Image Master Vault';
            els.btnFreezeMasterVault.disabled = false;
          }
        }
      } catch (err) {
        console.error("Vault polling error:", err);
      }
    }, 1500);
  }

  async function triggerNarrativeSynthesis() {
    if (!els.vaultNarrativeInput) return;
    const text = els.vaultNarrativeInput.value.trim();
    if (!text) {
      state.synthesizedDNA = null;
      return;
    }
    state.synthesizedDNA = null;
    try {
      if (els.synthStatusDot) els.synthStatusDot.style.background = '#38BDF8';
      if (els.synthLiveStatusText) {
        els.synthLiveStatusText.innerHTML = '<span style="color:#38BDF8;">⚡ Parsing narrative DNA & calculating biometrics...</span>';
      }
      appendLog(`[Synthesizer] Parsing narrative DNA: "${text.substring(0, 50)}..."`);
      
      const res = await fetch('/api/v2/personas/synthesize', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({narrative: text})
      });
      const data = await res.json();
      renderSynthesizedDNA(data);

      if (els.synthStatusDot) els.synthStatusDot.style.background = '#10B981';
      if (els.synthLiveStatusText) {
        els.synthLiveStatusText.innerHTML = `<span style="color:#10B981;">✓ Live DNA Synthesized for <strong>${data.name}</strong> (${data.age} · ${data.origin || 'Origin not recorded'})</span>`;
      }
      appendLog(`[Synthesizer] Successfully synthesized DNA for '${data.name}' (${data.biometrics.figure}, ${data.biometrics.bust}).`);
    } catch (err) {
      console.error(err);
      if (els.synthStatusDot) els.synthStatusDot.style.background = '#EF4444';
      if (els.synthLiveStatusText) {
        els.synthLiveStatusText.innerHTML = `<span style="color:#EF4444;">Synthesis failed: ${err.message}</span>`;
      }
    }
  }

  function renderSynthesizedDNA(data) {
    state.synthesizedDNA = data;
    if (els.synthBioHeader) {
      els.synthBioHeader.textContent = `${data.name.toUpperCase()} | ${data.age} YRS | ${data.biometrics.height} | ${String(data.origin || 'Unknown').split(',')[0]}`;
    }
    if (els.synthValFigure) els.synthValFigure.textContent = data.biometrics.figure;
    if (els.synthValBust) els.synthValBust.textContent = data.biometrics.bust;
    if (els.synthValWaist) els.synthValWaist.textContent = `${data.biometrics.waist} / ${data.biometrics.hips}`;
    if (els.synthValComplexion) els.synthValComplexion.textContent = data.biometrics.complexion;
    if (els.synthValEyes) els.synthValEyes.textContent = data.biometrics.eyes;
    if (els.synthValHair) els.synthValHair.textContent = data.biometrics.hair;
    if (els.synthValFacial) els.synthValFacial.textContent = data.biometrics.facial_structure || "Sculpted high cheekbones with a defined elegant jawline";
    if (els.synthValLips) els.synthValLips.textContent = data.biometrics.lips || "Naturally full lips with defined cupid's bow";
    if (els.synthValSkin) els.synthValSkin.textContent = data.biometrics.skin_texture || "Natural epidermal micro-pores, fine skin texture";
    if (els.synthValSilhouette) els.synthValSilhouette.textContent = data.biometrics.silhouette || "Sculpted athletic hourglass, toned collarbones";

    if (els.rfWardrobeSig && data.diversity_ringfence) {
      els.rfWardrobeSig.textContent = data.diversity_ringfence.wardrobe_signature;
    }
    if (els.rfWorldSig && data.diversity_ringfence) {
      els.rfWorldSig.textContent = data.diversity_ringfence.world_setting;
    }
    if (els.synthCanonicalPrompt) {
      els.synthCanonicalPrompt.textContent = data.master_prompt;
    }

    // Reset 13-pack badges to pending "No"
    for (let i = 1; i <= 13; i++) {
      const b = document.getElementById(`badge-pack-${i}`);
      if (b) {
        b.textContent = 'No';
        b.className = 'pack-status-badge badge-pending';
      }
    }
    if (els.vaultPackCompletionSummary) {
      els.vaultPackCompletionSummary.textContent = '0 / 13 Generated';
    }
  }

  // ----------------------------------------------------------------------------
  // 3. TAB 2: PHOTOSHOOT ORCHESTRATOR
  // ----------------------------------------------------------------------------
  function setupOrchestratorControls() {
    // Mode Switch (txt2img vs img2img)
    if (els.btnOrchModeTxt && els.btnOrchModeImg) {
      els.btnOrchModeTxt.addEventListener('click', () => {
        state.orchMode = 'txt2img';
        els.btnOrchModeTxt.classList.add('active');
        els.btnOrchModeImg.classList.remove('active');
        if (els.orchImg2imgBox) els.orchImg2imgBox.style.display = 'none';
      });
      els.btnOrchModeImg.addEventListener('click', () => {
        state.orchMode = 'img2img';
        els.btnOrchModeImg.classList.add('active');
        els.btnOrchModeTxt.classList.remove('active');
        if (els.orchImg2imgBox) els.orchImg2imgBox.style.display = 'block';
      });
    }

    // Denoising slider
    if (els.orchDenoisingSlider && els.denoisingValLbl) {
      els.orchDenoisingSlider.addEventListener('input', (e) => {
        els.denoisingValLbl.textContent = parseFloat(e.target.value).toFixed(2);
      });
    }

    // Aspect Ratio Presets
    els.aspectButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        els.aspectButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.orchAspectRatio = btn.getAttribute('data-ar') || '9:16';
      });
    });

    // AI Scene Variations
    if (els.btnSuggestScenes) {
      els.btnSuggestScenes.addEventListener('click', async () => {
        const p = getCurrentPersona();
        const pName = p ? p.name : "Model";
        appendLog(`[Scene Engine] Generating 3 diverse scene variations for ${pName}...`);
        
        try {
          const res = await fetch('/api/v2/orchestrator/suggest-scenes', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              narrative: els.orchPromptInput.value,
              framing: els.orchFramingSelect.value,
              lens: els.orchLensSelect.value,
              lighting: els.orchLightingSelect.value,
              persona_name: pName
            })
          });
          const data = await res.json();
          renderSceneChips(data.scenes);
        } catch (err) {
          console.error(err);
        }
      });
    }

    // Generate Render Button
    if (els.btnOrchGenerate) {
      els.btnOrchGenerate.addEventListener('click', async () => {
        appendLog("[Orchestrator] Queuing photoshoot render on Apple MPS...");
        els.btnOrchGenerate.textContent = "⏳ Generating 4K Visual...";
        els.btnOrchGenerate.disabled = true;

        try {
          const res = await fetch('/api/v2/orchestrator/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              persona_id: state.activePersonaId,
              prompt: els.orchPromptInput.value,
              aspect_ratio: state.orchAspectRatio,
              model: els.orchModelSelect.value,
              mode: state.orchMode
            })
          });
          const data = await res.json();
          if (els.orchCanvasImage && data.image_url) {
            els.orchCanvasImage.src = data.image_url;
          }
          appendLog(`[Orchestrator] 4K render complete for ${data.persona_name || 'Persona'} in ${data.elapsed_seconds}s (Seed: ${data.seed}).`);
          // Automatically update gallery so new render is immediately accessible
          await loadGalleryAssets();
        } catch (err) {
          console.error(err);
        } finally {
          els.btnOrchGenerate.textContent = "✦ Queue High-Res Photoshoot Render";
          els.btnOrchGenerate.disabled = false;
        }
      });
    }

    // Download Orchestrator 4K Render
    if (els.btnDownloadOrchRender) {
      els.btnDownloadOrchRender.addEventListener('click', () => {
        const src = els.orchCanvasImage ? els.orchCanvasImage.src : null;
        if (src) {
          triggerDownload(src, `photoshoot_render_${Date.now()}.png`);
          appendLog("[Download] Photoshoot 4K visual asset downloaded.");
        }
      });
    }

    // Clean vs Editorial Comparison
    if (els.btnCanvasToggleClean && els.btnCanvasToggleEditorial) {
      els.btnCanvasToggleClean.addEventListener('click', () => {
        els.btnCanvasToggleClean.classList.add('active');
        els.btnCanvasToggleEditorial.classList.remove('active');
        if (els.orchCanvasEditorialOverlay) els.orchCanvasEditorialOverlay.style.display = 'none';
      });
      els.btnCanvasToggleEditorial.addEventListener('click', () => {
        els.btnCanvasToggleEditorial.classList.add('active');
        els.btnCanvasToggleClean.classList.remove('active');
        if (els.orchCanvasEditorialOverlay) els.orchCanvasEditorialOverlay.style.display = 'flex';
      });
    }
  }

  function renderSceneChips(scenes) {
    if (!els.orchSceneChipsContainer) return;
    els.orchSceneChipsContainer.innerHTML = '';
    scenes.forEach(s => {
      const chip = document.createElement('div');
      chip.className = 'hook-card-opt1';
      chip.style.padding = '0.65rem 0.85rem';
      chip.innerHTML = `
        <span class="hook-badge-opt1" style="font-size: 0.68rem;">${s.title}</span>
        <p style="font-size: 0.78rem; color: #FFFFFF; margin-top: 0.25rem;">${s.description}</p>
      `;
      chip.addEventListener('click', () => {
        els.orchPromptInput.value = s.prompt;
        appendLog(`[Scene Adopted] Applied: "${s.title}"`);
      });
      els.orchSceneChipsContainer.appendChild(chip);
    });
  }

  // ----------------------------------------------------------------------------
  // 4. TAB 3: STORY & DIGITAL BLOG STUDIO
  // ----------------------------------------------------------------------------
  function setupStoryStudioControls() {
    // 3-Way Subview toggles
    els.storySubViewBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        const targetView = btn.getAttribute('data-subview');
        switchStorySubView(targetView);
      });
    });

    // Single vs Carousel
    if (els.btnFormatSingle && els.btnFormatCarousel) {
      els.btnFormatSingle.addEventListener('click', () => {
        state.storyFormat = 'single';
        els.btnFormatSingle.classList.add('active');
        els.btnFormatCarousel.classList.remove('active');
        if (els.carouselNavWrap) els.carouselNavWrap.style.display = 'none';
      });
      els.btnFormatCarousel.addEventListener('click', () => {
        state.storyFormat = 'carousel';
        els.btnFormatCarousel.classList.add('active');
        els.btnFormatSingle.classList.remove('active');
        if (els.carouselNavWrap) els.carouselNavWrap.style.display = 'flex';
        state.carouselSlide = 1;
        updateCarouselSlide();
      });
    }

    // Personal vs Commercial Mode Toggle
    if (els.btnModePersonal && els.btnModeCommercial) {
      els.btnModePersonal.addEventListener('click', () => {
        state.storyMode = 'personal';
        els.btnModePersonal.classList.add('active');
        els.btnModeCommercial.classList.remove('active');
        if (els.commercialFieldsWrap) els.commercialFieldsWrap.style.display = 'none';
        generateStoryHooks();
      });

      els.btnModeCommercial.addEventListener('click', () => {
        state.storyMode = 'commercial';
        els.btnModeCommercial.classList.add('active');
        els.btnModePersonal.classList.remove('active');
        if (els.commercialFieldsWrap) els.commercialFieldsWrap.style.display = 'block';
        generateStoryHooks();
      });
    }

    if (els.btnGenerateHooks) {
      els.btnGenerateHooks.addEventListener('click', generateStoryHooks);
    }

    // Hook card selections
    const hookCards = document.querySelectorAll('.hook-card-opt1');
    hookCards.forEach(card => {
      card.addEventListener('click', () => {
        hookCards.forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        const idx = parseInt(card.getAttribute('data-hook-idx') || '0', 10);
        state.selectedHookIdx = idx;
        const textEl = document.getElementById(`hook-text-${idx}`);
        if (textEl && els.overlayHookDisplay) {
          els.overlayHookDisplay.textContent = textEl.textContent.trim();
        }
      });
    });

    // Carousel buttons
    if (els.btnPrevSlide && els.btnNextSlide) {
      els.btnPrevSlide.addEventListener('click', () => {
        if (state.carouselSlide > 1) {
          state.carouselSlide--;
          updateCarouselSlide();
        }
      });
      els.btnNextSlide.addEventListener('click', () => {
        if (state.carouselSlide < 4) {
          state.carouselSlide++;
          updateCarouselSlide();
        }
      });
    }

    // Schedule This Post
    if (els.btnScheduleThisPost) {
      els.btnScheduleThisPost.addEventListener('click', async () => {
        const p = getCurrentPersona();
        const pId = p ? p.id : state.activePersonaId;
        const hookText = els.overlayHookDisplay ? els.overlayHookDisplay.textContent.trim() : "New Story Post";

        try {
          const res = await fetch('/api/v2/calendar/schedule', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              persona_id: pId,
              title: hookText.substring(0, 40) + "...",
              format: state.storyFormat,
              slides_count: state.storyFormat === 'carousel' ? 4 : 1,
              mode: state.storyMode,
              niche_or_theme: state.storyMode === 'personal' ? 'Personal Lifestyle' : (els.storyNicheSelect ? els.storyNicheSelect.value : 'Campaign'),
              scheduled_date: '2026-10-25',
              scheduled_time: '19:00',
              thumbnail: els.stageMainImage ? els.stageMainImage.src : '/generated/master_persona_maya/maya_06_baseline_fashion.png',
              caption: els.captionPreviewText ? els.captionPreviewText.textContent.trim() : '',
              hook: hookText
            })
          });
          const data = await res.json();
          appendLog(`[Calendar] Scheduled post: "${data.event.title}"`);
          await loadCalendarForPersona(pId);
          switchStorySubView('subview-calendar');
        } catch (err) {
          console.error(err);
        }
      });
    }

    // Download Clean Story Visual
    if (els.btnDownloadClean) {
      els.btnDownloadClean.addEventListener('click', () => {
        const src = els.stageMainImage ? els.stageMainImage.src : null;
        if (src) {
          triggerDownload(src, `story_clean_${Date.now()}.png`);
          appendLog("[Download] Clean story visual downloaded.");
        }
      });
    }

    // Download Editorial Story Visual
    if (els.btnDownloadEditorial) {
      els.btnDownloadEditorial.addEventListener('click', () => {
        const src = els.stageMainImage ? els.stageMainImage.src : null;
        if (src) {
          triggerDownload(src, `story_editorial_${Date.now()}.png`);
          appendLog("[Download] Editorial story visual downloaded.");
        }
      });
    }

    // Copy Caption to Clipboard
    if (els.btnCopyCaption) {
      els.btnCopyCaption.addEventListener('click', async () => {
        const text = els.captionPreviewText ? els.captionPreviewText.textContent.trim() : '';
        if (text) {
          try {
            await navigator.clipboard.writeText(text);
            const orig = els.btnCopyCaption.textContent;
            els.btnCopyCaption.textContent = "✓ Copied!";
            setTimeout(() => { els.btnCopyCaption.textContent = orig; }, 1800);
            appendLog("[Story Studio] Caption & hashtags copied to clipboard.");
          } catch (e) {
            // Fallback
            appendLog("[Story Studio] Caption copied.");
          }
        }
      });
    }
  }

  function switchStorySubView(viewId) {
    state.storySubView = viewId;
    els.storySubViewBtns.forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-subview') === viewId);
    });
    els.storySubViews.forEach(v => {
      v.style.display = (v.id === viewId) ? 'block' : 'none';
      v.classList.toggle('active', v.id === viewId);
    });

    if (viewId === 'subview-feed') {
      renderPersonaFeed();
    }
  }

  async function generateStoryHooks() {
    const p = getCurrentPersona();
    const pId = p ? p.id : state.activePersonaId;
    try {
      appendLog(`[Story Engine] Generating ${state.storyMode.toUpperCase()} viral hooks...`);
      const res = await fetch('/api/v2/story/hooks', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          persona_id: pId,
          format: state.storyFormat,
          mode: state.storyMode,
          theme_or_niche: els.storyNicheSelect ? els.storyNicheSelect.value : "Fashion",
          brand_name: els.storyBrandName ? els.storyBrandName.value : null,
          promo_code: els.storyPromoCode ? els.storyPromoCode.value : null
        })
      });
      const data = await res.json();
      state.currentHooksData = data;

      // Update Hooks
      data.hooks.forEach((hook, i) => {
        if (els.hookTexts[i]) {
          els.hookTexts[i].textContent = `"${hook}"`;
        }
      });

      if (els.overlayHookDisplay) {
        els.overlayHookDisplay.textContent = `"${data.hooks[state.selectedHookIdx || 0]}"`;
      }
      if (els.captionPreviewText) {
        els.captionPreviewText.textContent = data.caption;
      }
    } catch (err) {
      console.error(err);
    }
  }

  function updateCarouselSlide() {
    if (!els.carouselSlideIndicator) return;
    els.carouselSlideIndicator.textContent = `Slide ${state.carouselSlide} of 4`;
    const p = getCurrentPersona();
    if (!p) return;
    
    // Switch images for carousel preview
    const slides = [
      p.category_baselines[0]?.url || p.avatar,
      p.category_baselines[1]?.url || p.avatar,
      p.category_baselines[2]?.url || p.avatar,
      p.category_baselines[3]?.url || p.avatar
    ];
    if (els.stageMainImage && slides[state.carouselSlide - 1]) {
      els.stageMainImage.src = slides[state.carouselSlide - 1];
    }
  }

  // ----------------------------------------------------------------------------
  // 5. TAB 3 SUB-VIEW 2: PERSONA FEED & ARCHIVE
  // ----------------------------------------------------------------------------
  function setupPersonaFeedControls() {
    els.feedFilterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        els.feedFilterBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        state.feedFilter = btn.getAttribute('data-feedfilter') || 'all';
        renderPersonaFeed();
      });
    });
  }

  function renderPersonaFeed() {
    if (!els.personaFeedGrid) return;
    const p = getCurrentPersona();
    if (els.feedPersonaName && p) {
      els.feedPersonaName.textContent = p.name.toUpperCase();
    }

    const events = (state.calendarData && state.calendarData.events) ? state.calendarData.events : [];
    let filtered = events;
    if (state.feedFilter === 'single') filtered = filtered.filter(e => e.format === 'single');
    else if (state.feedFilter === 'carousel') filtered = filtered.filter(e => e.format === 'carousel');
    else if (state.feedFilter === 'personal') filtered = filtered.filter(e => e.mode === 'personal');
    else if (state.feedFilter === 'commercial') filtered = filtered.filter(e => e.mode === 'commercial');

    els.personaFeedGrid.innerHTML = '';
    if (filtered.length === 0) {
      els.personaFeedGrid.innerHTML = `<div style="grid-column: 1/-1; padding: 2rem; text-align: center; color: var(--text-muted);">No posts found for this filter. Create and schedule new posts in Creator Studio!</div>`;
      return;
    }

    filtered.forEach(post => {
      const card = document.createElement('div');
      card.className = 'feed-card-opt';
      const isPersonal = post.mode === 'personal';
      card.innerHTML = `
        <div class="feed-card-thumb-wrap">
          <img src="${post.thumbnail}" alt="${post.title}" class="feed-card-thumb"/>
          <span class="feed-card-badge-top ${isPersonal ? 'personal' : 'commercial'}">
            ${isPersonal ? '🟣 Personal' : '🟡 Commercial'}
          </span>
        </div>
        <div class="feed-card-content">
          <div>
            <strong style="font-size: 0.85rem; color: #FFFFFF; display: block;">${post.title}</strong>
            <small style="color: var(--text-dim); font-size: 0.72rem;">${post.theme || post.niche || 'Lifestyle'}</small>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 0.5rem; margin-top: 0.5rem; font-size: 0.75rem;">
            <span style="color: var(--text-muted);">${post.scheduled_date}</span>
            <button class="btn-glass" style="padding: 0.25rem 0.5rem; font-size: 0.7rem;">Inspect</button>
          </div>
        </div>
      `;
      els.personaFeedGrid.appendChild(card);
    });
  }

  // ----------------------------------------------------------------------------
  // 6. TAB 4: MEDIA GALLERY & METADATA INSPECTOR
  // ----------------------------------------------------------------------------
  function setupGalleryControls() {
    if (els.galleryFilterPersona) {
      els.galleryFilterPersona.addEventListener('change', renderGalleryGrid);
    }
    if (els.galleryFilterCategory) {
      els.galleryFilterCategory.addEventListener('change', renderGalleryGrid);
    }
    if (els.galleryFilterAr) {
      els.galleryFilterAr.addEventListener('change', renderGalleryGrid);
    }
    if (els.btnGalleryRefresh) {
      els.btnGalleryRefresh.addEventListener('click', loadGalleryAssets);
    }
    if (els.btnCloseMetaModal && els.galleryMetaModal) {
      els.btnCloseMetaModal.addEventListener('click', () => {
        els.galleryMetaModal.style.display = 'none';
      });
    }

    if (els.btnModalUseStory) {
      els.btnModalUseStory.addEventListener('click', () => {
        if (els.galleryMetaModal) els.galleryMetaModal.style.display = 'none';
        activateTab('tab-story');
      });
    }

    if (els.btnModalUseImg2img) {
      els.btnModalUseImg2img.addEventListener('click', () => {
        if (els.galleryMetaModal) els.galleryMetaModal.style.display = 'none';
        activateTab('tab-orchestrator');
        if (els.btnOrchModeImg) els.btnOrchModeImg.click();
      });
    }

    if (els.btnGalleryToggleArchive) {
      els.btnGalleryToggleArchive.addEventListener('click', async () => {
        if (els.galleryActiveContainer) els.galleryActiveContainer.style.display = 'none';
        if (els.galleryArchiveContainer) els.galleryArchiveContainer.style.display = 'block';
        await loadGalleryArchive();
      });
    }

    if (els.btnGalleryBackActive) {
      els.btnGalleryBackActive.addEventListener('click', () => {
        if (els.galleryActiveContainer) els.galleryActiveContainer.style.display = 'grid';
        if (els.galleryArchiveContainer) els.galleryArchiveContainer.style.display = 'none';
      });
    }
  }

  async function loadGalleryAssets() {
    try {
      const res = await fetch('/api/v2/gallery/assets');
      const data = await res.json();
      state.galleryAssets = data.assets || [];
      renderGalleryGrid();
    } catch (err) {
      console.error(err);
    }
  }

  function renderGalleryGrid() {
    if (!els.galleryGrid) return;
    let list = state.galleryAssets;

    const pFilter = els.galleryFilterPersona ? els.galleryFilterPersona.value : 'all';
    const cFilter = els.galleryFilterCategory ? els.galleryFilterCategory.value : 'all';
    const arFilter = els.galleryFilterAr ? els.galleryFilterAr.value : 'all';

    if (pFilter !== 'all') list = list.filter(a => a.persona_id === pFilter);
    if (cFilter !== 'all') list = list.filter(a => a.category === cFilter);
    if (arFilter !== 'all') list = list.filter(a => a.aspect_ratio === arFilter);

    els.galleryGrid.innerHTML = '';
    list.forEach(item => {
      const card = document.createElement('div');
      card.className = 'gallery-card-item';
      const reviewPersonaId = item.persona_id || state.activePersonaId || '';
      const reviewQuery = reviewPersonaId ? `?persona_id=${encodeURIComponent(reviewPersonaId)}` : '';
      card.innerHTML = `
        <div class="gallery-card-thumb-wrap">
          <img src="${item.clean_url}" alt="${item.title}" class="gallery-card-thumb"/>
        </div>
        <div class="gallery-card-info">
          <div class="gallery-card-title">${item.title}</div>
          <div class="gallery-card-meta">
            <span>${item.category}</span>
            <span style="color: var(--gold-light);">${item.aspect_ratio}</span>
          </div>
          <div class="gallery-card-actions">
            <a class="btn-glass canonical-asset-review-link" data-canonical-asset-review data-canonical-persona-id="${reviewPersonaId}" href="/workspace${reviewQuery}#assets">Open canonical review</a>
          </div>
        </div>
      `;
      card.addEventListener('click', (event) => {
        if (event.target.closest('a')) return;
        openMetadataModal(item);
      });
      els.galleryGrid.appendChild(card);
    });
  }

  function openMetadataModal(item) {
    if (!els.galleryMetaModal) return;
    if (els.modalMetaTitle) els.modalMetaTitle.textContent = item.title;
    if (els.modalMetaThumb) els.modalMetaThumb.src = item.clean_url;
    if (els.modalMetaPersona) els.modalMetaPersona.textContent = item.persona_name;
    if (els.modalMetaModel) els.modalMetaModel.textContent = item.model;
    if (els.modalMetaSeed) els.modalMetaSeed.textContent = `${item.sampler} · Seed ${item.seed} · Steps ${item.steps} (CFG ${item.cfg})`;
    if (els.modalMetaPrompt) els.modalMetaPrompt.textContent = item.prompt;
    els.galleryMetaModal.style.display = 'flex';
  }

  async function updateArchiveBadge() {
    try {
      const res = await fetch('/api/v2/gallery/archive');
      const data = await res.json();
      if (els.archiveCountBadge) {
        els.archiveCountBadge.textContent = data.total_archived_personas || 0;
      }
      return data;
    } catch (err) {
      console.error(err);
      return null;
    }
  }

  async function loadGalleryArchive() {
    const data = await updateArchiveBadge();
    if (!data || !els.galleryArchiveList) return;

    const list = data.archived_personas || [];
    els.galleryArchiveList.innerHTML = '';

    if (list.length === 0) {
      els.galleryArchiveList.innerHTML = `
        <div style="background: rgba(14, 20, 32, 0.5); border: 1px dashed rgba(255,255,255,0.1); border-radius: 12px; padding: 3rem; text-align: center; color: var(--text-muted);">
          No personas in the archive. When you delete a persona from Master Vault, it is preserved here.
        </div>
      `;
      return;
    }

    list.forEach(item => {
      const card = document.createElement('div');
      card.className = 'archived-persona-card';
      card.style.cssText = "background: rgba(14, 20, 32, 0.85); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 14px; padding: 1.5rem; display: flex; flex-direction: column; gap: 1.25rem;";

      const avatarSrc = item.avatar || '/generated/master_persona_maya/maya_01_turnaround_front.png';
      
      let thumbsHtml = '';
      (item.assets || []).slice(0, 8).forEach(a => {
        thumbsHtml += `
          <div style="width: 72px; height: 96px; border-radius: 6px; overflow: hidden; background: #000; border: 1px solid rgba(255,255,255,0.08); flex-shrink: 0;" title="${a.title}">
            <img src="${a.clean_url}" alt="${a.title}" style="width: 100%; height: 100%; object-fit: cover;"/>
          </div>
        `;
      });

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 1rem;">
          <div style="display: flex; align-items: center; gap: 1rem;">
            <img src="${avatarSrc}" alt="${item.name}" style="width: 54px; height: 54px; border-radius: 50%; object-fit: cover; border: 2px solid var(--gold-light);"/>
            <div>
              <h4 style="font-size: 1.05rem; color: #FFFFFF; font-family: var(--font-title);">${item.name}</h4>
              <span style="font-size: 0.75rem; color: var(--text-muted);">${item.origin} · Archived: ${item.archived_at}</span>
            </div>
          </div>
          <div style="display: flex; gap: 0.75rem; align-items: center;">
            <span style="font-size: 0.75rem; color: var(--gold-light);">${item.total_assets} Preserved Assets</span>
            <button class="btn-gold btn-restore-persona" data-pid="${item.persona_id}" style="padding: 0.45rem 1rem; font-size: 0.78rem;">
              ↺ Retrieve Persona
            </button>
          </div>
        </div>

        <div>
          <span style="font-size: 0.75rem; color: var(--text-dim); display: block; margin-bottom: 0.5rem;">Archived Reference & Render Assets:</span>
          <div style="display: flex; gap: 0.65rem; flex-wrap: wrap;">
            ${thumbsHtml || '<span style="color: var(--text-muted); font-size: 0.75rem;">No image assets in record</span>'}
          </div>
        </div>
      `;

      card.querySelector('.btn-restore-persona').addEventListener('click', async () => {
        const pid = item.persona_id;
        try {
          appendLog(`[Archive] Retrieving persona "${item.name}" from archive...`);
          const res = await fetch(`/api/v2/personas/${pid}/restore`, {method: 'POST'});
          if (!res.ok) {
            const err = await res.json();
            alert(err.detail || "Failed to restore persona");
            return;
          }
          const resp = await res.json();
          appendLog(`[Archive] Persona "${item.name}" restored to active master studio!`);
          
          await loadPersonas();
          switchActivePersona(pid);
          await loadGalleryAssets();
          await updateArchiveBadge();
          
          // Switch view back to active
          if (els.galleryActiveContainer) els.galleryActiveContainer.style.display = 'grid';
          if (els.galleryArchiveContainer) els.galleryArchiveContainer.style.display = 'none';
        } catch (err) {
          console.error(err);
          alert(`Failed to restore: ${err.message}`);
        }
      });

      els.galleryArchiveList.appendChild(card);
    });
  }

  // ----------------------------------------------------------------------------
  // 7. TAB 5: SYSTEM TELEMETRY
  // ----------------------------------------------------------------------------
  function setupTelemetryControls() {
    if (els.btnPurgeVram) {
      els.btnPurgeVram.addEventListener('click', async () => {
        try {
          appendLog("[Hardware] Purging MPS Unified Memory cache...");
          const res = await fetch('/api/v2/system/purge-cache', {method: 'POST'});
          const data = await res.json();
          appendLog(`[Hardware] ${data.message}`);
          await loadTelemetry();
        } catch (err) {
          console.error(err);
        }
      });
    }
  }

  async function loadTelemetry() {
    try {
      const res = await fetch('/api/v2/system/telemetry');
      const data = await res.json();
      if (els.sysVramGb) {
        els.sysVramGb.textContent = `${data.vram.used_gb} / ${data.vram.total_gb} GB`;
      }
      if (els.headerVramText) {
        els.headerVramText.textContent = `GPU VRAM: ${data.vram.used_gb} / ${data.vram.total_gb} GB (${data.vram.percentage}% used)`;
      }

      // Active Inference Task Queue binding
      if (data.active_queue) {
        const q = data.active_queue;
        if (q.running > 0 && q.active_task) {
          if (els.queueTaskLabel) {
            els.queueTaskLabel.innerHTML = `<span class="telemetry-dot" style="background:#F59E0B; display:inline-block; margin-right:6px; animation: pulse 1.5s infinite;"></span><strong style="color:#F59E0B;">RUNNING</strong> · ${q.active_task.name}`;
          }
          if (els.queueCountLabel) {
            els.queueCountLabel.textContent = `${q.running} Task Running (${q.queued} Packs Queued)`;
            els.queueCountLabel.style.color = 'var(--gold-primary)';
          }
          if (els.queueProgressBar) {
            els.queueProgressBar.style.width = `${q.active_task.percent || 0}%`;
            els.queueProgressBar.style.background = 'var(--gold-primary)';
          }
          if (els.queueActiveDetails) {
            els.queueActiveDetails.style.display = 'block';
          }
          if (els.queueActiveJobTitle) {
            els.queueActiveJobTitle.textContent = q.active_task.name;
          }
          if (els.queueActiveJobPct) {
            els.queueActiveJobPct.textContent = `${q.active_task.percent || 0}%`;
          }
          if (els.queueActiveJobPack) {
            els.queueActiveJobPack.textContent = `Current: ${q.active_task.detail}`;
          }
          if (els.queueActiveJobElapsed) {
            els.queueActiveJobElapsed.textContent = q.active_task.elapsed || '0s';
          }
          if (els.queueActiveJobRemaining) {
            els.queueActiveJobRemaining.textContent = q.active_task.remaining || '--';
          }
        } else {
          if (els.queueTaskLabel) {
            els.queueTaskLabel.innerHTML = 'IDLE · Ready to generate';
          }
          if (els.queueCountLabel) {
            els.queueCountLabel.textContent = '0 Tasks in Queue';
            els.queueCountLabel.style.color = 'var(--emerald)';
          }
          if (els.queueProgressBar) {
            els.queueProgressBar.style.width = '0%';
          }
          if (els.queueActiveDetails) {
            els.queueActiveDetails.style.display = 'none';
          }
        }
      }
    } catch (err) {
      console.error(err);
    }
  }

  function appendLog(msg) {
    if (!els.sysLogStream) return;
    const timeStr = new Date().toLocaleTimeString();
    els.sysLogStream.textContent += `\n[${timeStr}] ${msg}`;
    els.sysLogStream.scrollTop = els.sysLogStream.scrollHeight;
  }

  // ----------------------------------------------------------------------------
  // 8. DATA LOADING & PERSONA BINDING
  // ----------------------------------------------------------------------------
  async function loadPersonas() {
    try {
      const res = await fetch('/api/v2/personas');
      const data = await res.json();
      state.personas = data.personas || [];
      renderPersonaSelect();
      renderActivePersona();
    } catch (err) {
      console.error(err);
    }
  }

  function syncCanonicalSurfaceLinks(personaId = state.activePersonaId) {
    const targetPersonaId = String(personaId || '').trim();
    document.querySelectorAll('[data-canonical-workspace-link]').forEach((link) => {
      const query = targetPersonaId ? `?persona_id=${encodeURIComponent(targetPersonaId)}` : '';
      link.setAttribute('href', `/workspace${query}`);
    });
    document.querySelectorAll('[data-canonical-target]').forEach((link) => {
      const target = link.getAttribute('data-canonical-target');
      if (!target) return;
      const query = targetPersonaId ? `?persona_id=${encodeURIComponent(targetPersonaId)}` : '';
      link.setAttribute('href', `/workspace${query}#${encodeURIComponent(target)}`);
    });
  }

  function renderPersonaSelect() {
    if (!els.globalPersonaSelect) return;
    els.globalPersonaSelect.innerHTML = '';
    state.personas.forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = `${p.name} (${p.age} · ${personaOrigin(p)})`;
      if (p.id === state.activePersonaId) opt.selected = true;
      els.globalPersonaSelect.appendChild(opt);
    });

    const createOpt = document.createElement('option');
    createOpt.value = '__create_new__';
    createOpt.textContent = '+ ✦ Synthesize New Persona...';
    els.globalPersonaSelect.appendChild(createOpt);

    // Also populate Gallery Persona Filter dynamically from database
    if (els.galleryFilterPersona) {
      els.galleryFilterPersona.innerHTML = '<option value="all">All Personas (Database)</option>';
      state.personas.forEach(p => {
        const gOpt = document.createElement('option');
        gOpt.value = p.id;
        gOpt.textContent = `${p.name} (${personaOrigin(p)})`;
        els.galleryFilterPersona.appendChild(gOpt);
      });
    }
    syncCanonicalSurfaceLinks();
  }

  function switchActivePersona(personaId) {
    state.activePersonaId = personaId;
    if (els.globalPersonaSelect) els.globalPersonaSelect.value = personaId;
    syncCanonicalSurfaceLinks(personaId);
    renderActivePersona();
    loadCalendarForPersona(personaId);
    generateStoryHooks();
  }

  function getCurrentPersona() {
    return state.personas.find(p => p.id === state.activePersonaId) || state.personas[0];
  }

  function personaOrigin(persona) {
    return String(persona?.origin || persona?.location || persona?.world?.location || 'Origin not recorded').split(',')[0].trim();
  }

  function renderActivePersona() {
    const p = getCurrentPersona();
    if (!p) return;

    if (els.headerPersonaAvatar) els.headerPersonaAvatar.src = p.avatar;
    if (els.vaultActiveAnchorLbl) els.vaultActiveAnchorLbl.textContent = p.name;
    if (els.vaultPersonaName) els.vaultPersonaName.textContent = p.name.toUpperCase();
    if (els.vaultPersonaDesc) els.vaultPersonaDesc.textContent = `${p.age}-year-old · ${personaOrigin(p)}`;
    if (els.storyActivePersonaLbl) els.storyActivePersonaLbl.textContent = p.name;
    if (els.stageOverlayPersona) els.stageOverlayPersona.textContent = p.name;
    if (els.feedPersonaName) els.feedPersonaName.textContent = p.name.toUpperCase();

    // Dynamically update stage canvases & prompt workspace to active persona
    const defaultVisual = (p.category_baselines && p.category_baselines[0]?.url) || p.avatar;
    if (els.stageMainImage) els.stageMainImage.src = defaultVisual;
    if (els.orchCanvasImage) els.orchCanvasImage.src = defaultVisual;
    if (els.orchPromptInput) {
      const city = p.origin ? p.origin.split(',')[0] : 'Downtown';
      els.orchPromptInput.value = `8k raw photo, waist-up portrait of ${p.name} from ${city}, stylish contemporary couture outfit, natural soft light, 50mm portrait lens`;
    }

    // Biometrics Card
    if (els.bioHeaderLine) {
      els.bioHeaderLine.textContent = `${p.name.toUpperCase()} | ${p.age} YRS | ${p.biometrics.height} | ${personaOrigin(p)}`;
    }
    if (els.bioValHeight) els.bioValHeight.textContent = p.biometrics.height;
    if (els.bioValEthnicity) els.bioValEthnicity.textContent = p.ethnicity || personaOrigin(p);
    if (els.bioValFigure) els.bioValFigure.textContent = p.biometrics.figure;
    if (els.bioValSkin) els.bioValSkin.textContent = p.biometrics.complexion;
    if (els.bioValWeight) els.bioValWeight.textContent = p.biometrics.weight;
    if (els.bioValHair) els.bioValHair.textContent = p.biometrics.hair;

    // 1. Turnaround Pack (4 Angles: 01-04)
    if (els.vaultTurnaroundGrid && p.turnaround_pack) {
      els.vaultTurnaroundGrid.innerHTML = '';
      p.turnaround_pack.forEach(angle => {
        const card = document.createElement('div');
        card.className = 'turnaround-card-opt3';
        card.innerHTML = `
          <div class="turnaround-thumb-wrap-opt3">
            <img src="${angle.url}" alt="${angle.label}" class="turnaround-img-opt3"/>
          </div>
          <div class="turnaround-footer-opt3">
            <div class="angle-tag-opt3">${angle.label}</div>
            <div class="degree-badge-opt3">${angle.angle}</div>
          </div>
        `;
        els.vaultTurnaroundGrid.appendChild(card);
      });
    }

    // 2. Micro-Detailing Macro Card (Image 05)
    if (els.vaultMacroCard && p.micro_detailing) {
      els.vaultMacroCard.style.display = 'flex';
      if (els.vaultMacroImg) els.vaultMacroImg.src = p.micro_detailing.url;
      if (els.vaultMacroTitle) els.vaultMacroTitle.textContent = p.micro_detailing.title || `${p.name} · Eyes & Lips Macro`;
      if (els.vaultMacroDesc) els.vaultMacroDesc.textContent = `Shot on ${p.micro_detailing.lens || '100mm f/2.8 Macro'} · Natural catchlights & epidermal micro-pores`;
    } else if (els.vaultMacroCard) {
      els.vaultMacroCard.style.display = 'none';
    }

    // 3. Category Baselines (06, 07, 08, 09)
    if (els.vaultCategoriesGrid && p.category_baselines) {
      els.vaultCategoriesGrid.innerHTML = '';
      p.category_baselines.forEach((cat, idx) => {
        const num = String(6 + idx).padStart(2, '0');
        const card = document.createElement('div');
        card.className = `category-option-card-opt3 ${idx % 2 === 0 ? 'accent-gold' : 'accent-purple'}`;
        card.innerHTML = `
          <div class="category-header-row-opt3">
            <span class="category-numeral-opt3">${num}</span>
            <span class="category-badge-pill-opt3">${cat.category}</span>
          </div>
          <div class="category-option-img-wrap-opt3">
            <img src="${cat.url}" alt="${cat.title}" class="category-option-img-opt3"/>
          </div>
          <div class="category-option-footer-opt3">
            <div class="category-option-name-opt3">${cat.title}</div>
            <div class="category-option-meta-opt3">APPROVED BASELINE · SEED ${8824 + idx * 4}</div>
          </div>
        `;
        els.vaultCategoriesGrid.appendChild(card);
      });
    }

    // 4. Adult & Boudoir Baselines (10, 11, 12, 13)
    if (els.vaultAdultGrid) {
      els.vaultAdultGrid.innerHTML = '';
      if (p.adult_baselines && p.adult_baselines.length > 0) {
        p.adult_baselines.forEach((adult, idx) => {
          const num = String(10 + idx).padStart(2, '0');
          const card = document.createElement('div');
          card.className = 'category-option-card-opt3 accent-purple';
          card.innerHTML = `
            <div class="category-header-row-opt3">
              <span class="category-numeral-opt3">${num}</span>
              <span class="category-badge-pill-opt3" style="background: rgba(168, 85, 247, 0.2); color: var(--purple-light);">${adult.category}</span>
            </div>
            <div class="category-option-img-wrap-opt3">
              <img src="${adult.url}" alt="${adult.title}" class="category-option-img-opt3"/>
            </div>
            <div class="category-option-footer-opt3">
              <div class="category-option-name-opt3">${adult.title}</div>
              <div class="category-option-meta-opt3">APPROVED MASTER NUDE · SEED ${9104 + idx}</div>
            </div>
          `;
          els.vaultAdultGrid.appendChild(card);
        });
      } else {
        els.vaultAdultGrid.innerHTML = `<div style="grid-column: 1/-1; padding: 1.5rem; text-align: center; color: var(--text-dim); font-size: 0.8rem;">No adult baselines configured for this persona.</div>`;
      }
    }
  }

  function triggerDownload(url, filename) {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  // ----------------------------------------------------------------------------
  // 9. CONTENT CALENDAR (OPTION 2)
  // ----------------------------------------------------------------------------
  async function loadCalendarForPersona(personaId) {
    try {
      const res = await fetch(`/api/v2/calendar/events?persona_id=${personaId}`);
      const data = await res.json();
      state.calendarData = data;
      renderCalendar();
    } catch (err) {
      console.error(err);
    }
  }

  function renderCalendar() {
    if (!state.calendarData || !els.calendarDaysColumns) return;

    // 70/30 Content Balance Tracker
    const b = state.calendarData.balance_metric || state.calendarData.balance;
    if (b) {
      const pPct = b.personal_percentage !== undefined ? b.personal_percentage : b.personal_pct;
      const cPct = b.commercial_percentage !== undefined ? b.commercial_percentage : b.commercial_pct;
      if (els.gaugeRatioText) {
        els.gaugeRatioText.textContent = `${pPct}% Personal / ${cPct}% Commercial`;
      }
      if (els.gaugeFillPersonal) els.gaugeFillPersonal.style.width = `${pPct}%`;
      if (els.gaugeFillCommercial) els.gaugeFillCommercial.style.width = `${cPct}%`;
      if (els.gaugeStatusMsg) {
        els.gaugeStatusMsg.textContent = b.status_message;
        els.gaugeStatusMsg.style.color = b.is_optimal ? 'var(--emerald)' : 'var(--gold-light)';
      }
    }

    // Days Columns Grid
    els.calendarDaysColumns.innerHTML = '';
    const days = [
      {date: '2026-10-19', label: 'MON 19'},
      {date: '2026-10-20', label: 'TUE 20'},
      {date: '2026-10-21', label: 'WED 21'},
      {date: '2026-10-22', label: 'THU 22'},
      {date: '2026-10-23', label: 'FRI 23'},
      {date: '2026-10-24', label: 'SAT 24'},
      {date: '2026-10-25', label: 'SUN 25'}
    ];

    days.forEach(day => {
      const col = document.createElement('div');
      col.className = 'cal-day-column-opt2';
      
      const dayEvents = (state.calendarData.events || []).filter(e => e.scheduled_date === day.date);
      
      let eventsHtml = '';
      dayEvents.forEach(evt => {
        const isPersonal = evt.mode === 'personal';
        eventsHtml += `
          <div class="calendar-post-card-opt2 ${isPersonal ? 'mode-personal' : 'mode-commercial'}" data-event-id="${evt.id}">
            <div class="post-card-badge-opt2 ${isPersonal ? 'badge-personal' : 'badge-commercial'}">
              ${isPersonal ? '🟣 Personal' : '🟡 Commercial'}
            </div>
            <div class="post-card-thumb-wrap-opt2">
              <img src="${evt.thumbnail}" alt="${evt.title}" class="post-card-thumb-opt2"/>
            </div>
            <div class="post-card-details-opt2">
              <strong style="font-size: 0.78rem; color: #FFFFFF; display: block; margin-bottom: 0.2rem;">${evt.title}</strong>
              <small style="color: var(--text-dim); font-size: 0.7rem;">${evt.scheduled_time || '18:00'} · ${evt.format}</small>
            </div>
          </div>
        `;
      });

      col.innerHTML = `
        <div class="cal-day-header-opt2">
          <span>${day.label}</span>
          <small style="color: var(--text-dim); font-size: 0.7rem;">${dayEvents.length} posts</small>
        </div>
        <div class="cal-day-slots-opt2">
          ${eventsHtml || '<div style="padding: 1rem 0; text-align: center; color: var(--text-dim); font-size: 0.72rem;">No posts</div>'}
        </div>
      `;

      // Click to inspect
      col.querySelectorAll('.calendar-post-card-opt2').forEach(card => {
        card.addEventListener('click', () => {
          const evtId = card.getAttribute('data-event-id');
          const found = (state.calendarData.events || []).find(e => e.id === evtId);
          if (found) {
            if (els.inspThumbSide) els.inspThumbSide.src = found.thumbnail;
            if (els.inspSideName) els.inspSideName.textContent = found.title;
            if (els.inspSidePrompt) els.inspSidePrompt.textContent = found.caption;
            if (els.inspSideHooks) {
              els.inspSideHooks.innerHTML = `<li>"${found.hook || found.title}"</li>`;
            }
          }
        });
      });

      els.calendarDaysColumns.appendChild(col);
    });
  }

  // Start app
  init();
});

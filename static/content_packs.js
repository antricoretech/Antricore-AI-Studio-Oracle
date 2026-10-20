import { api } from './modules/api.js';

const state = {
  personas: [],
  referencePacks: [],
  contentPacks: [],
  personaId: "",
  sourcePackId: "",
  requestController: null,
};

const $ = (selector) => document.querySelector(selector);
const adultClasses = new Set(["adult_glamour", "lingerie", "boudoir", "nude_editorial"]);

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  }[character]));
}

function setStatus(message, tone = "") {
  const status = $("#status");
  status.textContent = message;
  status.className = `status ${tone}`.trim();
}

function selectedSource() {
  return state.referencePacks.find((pack) => pack.id === state.sourcePackId) || null;
}

function canonicalItems(pack) {
  return (pack?.items || []).filter((item) => Boolean(item.canonical_selected) && item.asset_id);
}

function sourceReady(pack) {
  return Boolean(pack && pack.review === "approved" && pack.canonical_selected && canonicalItems(pack).length);
}

function badge(label, className = "") {
  return `<span class="badge ${className}">${escapeHtml(label)}</span>`;
}

function renderPersonaSelect() {
  const select = $("#persona-select");
  select.innerHTML = state.personas.length
    ? state.personas.map((persona) => `<option value="${escapeHtml(persona.id)}">${escapeHtml(persona.name || persona.id)} · ${escapeHtml(persona.id)}</option>`).join("")
    : `<option value="">No Master Personas available</option>`;
  select.value = state.personaId;
  select.disabled = !state.personas.length;
}

function renderReferencePacks() {
  $("#source-count").textContent = String(state.referencePacks.length);
  const target = $("#reference-packs");
  if (!state.referencePacks.length) {
    target.innerHTML = `<div class="empty">No ReferencePacks are available for this PersonaVersion yet.</div>`;
    return;
  }
  target.innerHTML = state.referencePacks.map((pack) => {
    const items = canonicalItems(pack);
    const ready = sourceReady(pack);
    const selected = pack.id === state.sourcePackId;
    const className = selected ? "card selected" : "card";
    const classBadge = pack.content_class === "adult_glamour" || adultClasses.has(pack.content_class) ? badge("Identity + style", "core") : "";
    return `<article class="${className}" role="listitem">
      <div class="card-top"><h3>${escapeHtml(pack.name || pack.pack_type)}</h3>${badge(pack.review || "pending", pack.review || "pending")}</div>
      <div class="card-meta">${badge(pack.content_class || "identity")}${classBadge}${badge(`${items.length} canonical anchor${items.length === 1 ? "" : "s"}`)}</div>
      <p>${ready ? "Ready to author a ContentPack from this canonical source." : "Needs approved pack/item review, rights confirmation, and canonical selection."}</p>
      <div class="card-actions"><button class="button small ${ready ? "secondary" : ""}" type="button" data-source-id="${escapeHtml(pack.id)}" ${ready ? "" : "disabled"}>${selected ? "Selected source" : "Use as source"}</button></div>
    </article>`;
  }).join("");
}

function renderSelectedSource() {
  const target = $("#selected-source");
  const pack = selectedSource();
  const ready = sourceReady(pack);
  if (!pack) {
    target.textContent = "Choose an eligible canonical source pack.";
    target.className = "selected-source";
    $("#create-button").disabled = true;
    return;
  }
  target.innerHTML = ready
    ? `<strong>${escapeHtml(pack.name || pack.pack_type)}</strong> selected · ${canonicalItems(pack).length} canonical anchor(s) will be linked without copying media.`
    : `<strong>${escapeHtml(pack.name || pack.pack_type)}</strong> is not eligible yet. Return to ReferencePack review before creating this ContentPack.`;
  target.className = `selected-source ${ready ? "ready" : ""}`;
  $("#create-button").disabled = !ready;
}

function renderContentPacks() {
  $("#pack-count").textContent = String(state.contentPacks.length);
  const target = $("#content-packs");
  if (!state.contentPacks.length) {
    target.innerHTML = `<div class="empty">No ContentPacks have been authored for this persona. Select a canonical source above to begin.</div>`;
    return;
  }
  target.innerHTML = state.contentPacks.map((pack) => {
    const adult = adultClasses.has(pack.content_class);
    return `<article class="card" role="listitem">
      <div class="card-top"><h3>${escapeHtml(pack.name)}</h3>${badge(pack.review || "pending", pack.review || "pending")}</div>
      <div class="card-meta">${badge(pack.content_class)}${adult || pack.identity_core ? badge("Identity Core", "core") : ""}${badge(pack.identity_authority)}</div>
      <p>${escapeHtml(pack.items?.length || 0)} linked canonical anchor(s) · PersonaVersion ${escapeHtml(pack.persona_version_id || "unknown")}</p>
      <div class="card-actions">
        ${pack.review !== "approved" ? `<button class="button small secondary" type="button" data-review="approved" data-pack-id="${escapeHtml(pack.id)}">Approve</button>` : ""}
        ${pack.review !== "rejected" ? `<button class="button small danger" type="button" data-review="rejected" data-pack-id="${escapeHtml(pack.id)}">Reject</button>` : ""}
        <button class="button small secondary" type="button" data-resolve-id="${escapeHtml(pack.id)}" ${pack.review === "approved" ? "" : "disabled"}>Resolve anchors</button>
      </div>
    </article>`;
  }).join("");
}

function renderAll() {
  renderPersonaSelect();
  renderReferencePacks();
  renderSelectedSource();
  renderContentPacks();
}

async function loadPersonas() {
  const payload = await api("/api/personas");
  state.personas = Array.isArray(payload) ? payload : payload?.personas || [];
  const requested = new URLSearchParams(window.location.search).get("persona_id");
  if (requested && state.personas.some((persona) => persona.id === requested)) {
    state.personaId = requested;
  } else if (!state.personaId || !state.personas.some((persona) => persona.id === state.personaId)) {
    state.personaId = state.personas[0]?.id || "";
  }
}

async function loadWorkspace() {
  if (!state.personaId) {
    state.referencePacks = [];
    state.contentPacks = [];
    state.sourcePackId = "";
    renderAll();
    setStatus("Create a Master Persona before authoring ContentPacks.");
    return;
  }
  state.requestController?.abort();
  state.requestController = new AbortController();
  const signal = state.requestController.signal;
  setStatus("Loading canonical sources and ContentPacks…");
  try {
    const [references, contentPacks] = await Promise.all([
      api(`/api/personas/${encodeURIComponent(state.personaId)}/reference-packs`, { signal }),
      api(`/api/personas/${encodeURIComponent(state.personaId)}/content-packs`, { signal }),
    ]);
    if (signal.aborted) return;
    state.referencePacks = Array.isArray(references) ? references : references?.packs || [];
    state.contentPacks = Array.isArray(contentPacks) ? contentPacks : contentPacks?.content_packs || [];
    if (!sourceReady(selectedSource())) state.sourcePackId = "";
    renderAll();
    setStatus(`${state.referencePacks.length} reference source(s) and ${state.contentPacks.length} ContentPack(s) loaded.`, "success");
  } catch (error) {
    if (error.name === "AbortError") return;
    setStatus(error.message, "error");
  }
}

function syncAdultControls() {
  const contentClass = $("#content-class").value;
  const adult = adultClasses.has(contentClass);
  const authority = $("#identity-authority");
  const core = $("#identity-core");
  if (adult) {
    authority.value = "identity_and_style";
    authority.disabled = true;
    core.checked = true;
    core.disabled = true;
  } else {
    authority.disabled = false;
    core.disabled = false;
  }
}

async function createContentPack(event) {
  event.preventDefault();
  const source = selectedSource();
  if (!sourceReady(source)) {
    setStatus("Select an approved ReferencePack with canonical anchors first.", "error");
    return;
  }
  const form = event.currentTarget;
  let style;
  let metadata;
  try {
    style = JSON.parse($("#style-json").value || "{}");
    metadata = JSON.parse($("#metadata-json").value || "{}");
  } catch (error) {
    setStatus(`Style and metadata must be valid JSON: ${error.message}`, "error");
    return;
  }
  const contentClass = $("#content-class").value;
  const payload = {
    reference_pack_id: source.id,
    pack_type: $("#pack-type").value.trim(),
    name: $("#pack-name").value.trim(),
    content_class: contentClass,
    identity_authority: adultClasses.has(contentClass) ? "identity_and_style" : $("#identity-authority").value,
    identity_core: adultClasses.has(contentClass) || $("#identity-core").checked,
    style,
    metadata,
    reference_item_ids: canonicalItems(source).map((item) => item.id),
  };
  if (!payload.name || !payload.pack_type) {
    setStatus("Pack name and pack type are required.", "error");
    return;
  }
  const button = $("#create-button");
  button.disabled = true;
  setStatus("Creating ContentPack…");
  try {
    await api(`/api/personas/${encodeURIComponent(state.personaId)}/content-packs`, { method: "POST", body: JSON.stringify(payload) });
    form.reset();
    $("#metadata-json").value = "{}";
    syncAdultControls();
    setStatus("ContentPack created in pending review. Approve it after the identity/style review.", "success");
    await loadWorkspace();
  } catch (error) {
    setStatus(error.message, "error");
    renderSelectedSource();
  }
}

async function reviewContentPack(packId, review) {
  setStatus(`${review === "approved" ? "Approving" : "Rejecting"} ContentPack…`);
  try {
    await api(`/api/personas/${encodeURIComponent(state.personaId)}/content-packs/${encodeURIComponent(packId)}/review`, { method: "PATCH", body: JSON.stringify({ review }) });
    setStatus(`ContentPack ${review}.`, "success");
    await loadWorkspace();
  } catch (error) {
    setStatus(error.message, "error");
  }
}

async function resolveContentPack(packId) {
  setStatus("Resolving approved canonical anchors…");
  try {
    const resolved = await api(`/api/personas/${encodeURIComponent(state.personaId)}/content-packs/${encodeURIComponent(packId)}/resolve`);
    const anchors = (resolved.anchors || []).map((anchor) => `<a href="${escapeHtml(anchor.url)}" target="_blank" rel="noreferrer"><img src="${escapeHtml(anchor.url)}" alt="Canonical identity anchor"></a>`).join("");
    $("#resolution").hidden = false;
    $("#resolution").innerHTML = `<h3 id="resolution-heading">Resolved canonical identity</h3><p>Authority: <strong>${escapeHtml(resolved.identity_authority)}</strong> · Identity Core: <strong>${resolved.identity_core ? "yes" : "no"}</strong></p><div class="anchor-list">${anchors || "No anchors returned"}</div><pre>${escapeHtml(JSON.stringify(resolved.style || {}, null, 2))}</pre>`;
    setStatus("Approved ContentPack resolved successfully.", "success");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

$("#persona-select").addEventListener("change", async (event) => {
  state.personaId = event.target.value;
  state.sourcePackId = "";
  $("#resolution").hidden = true;
  await loadWorkspace();
});
$("#refresh-button").addEventListener("click", loadWorkspace);
$("#content-pack-form").addEventListener("submit", createContentPack);
$("#content-class").addEventListener("change", syncAdultControls);
$("#reference-packs").addEventListener("click", (event) => {
  const button = event.target.closest("[data-source-id]");
  if (!button) return;
  state.sourcePackId = button.dataset.sourceId;
  renderReferencePacks();
  renderSelectedSource();
});
$("#content-packs").addEventListener("click", (event) => {
  const review = event.target.closest("[data-review]");
  if (review) {
    reviewContentPack(review.dataset.packId, review.dataset.review);
    return;
  }
  const resolve = event.target.closest("[data-resolve-id]");
  if (resolve) resolveContentPack(resolve.dataset.resolveId);
});

syncAdultControls();
loadPersonas().then(() => { renderAll(); return loadWorkspace(); }).catch((error) => setStatus(error.message, "error"));

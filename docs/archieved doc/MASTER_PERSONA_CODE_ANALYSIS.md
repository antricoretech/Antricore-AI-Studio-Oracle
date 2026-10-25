# Master Persona Code Analysis

**Reviewed:** 2026-10-21  
**Project:** AI Influencer Studio  
**Scope:** Read-only code and architecture analysis. No implementation changes are included.

## Executive assessment

The project has a strong master-persona concept, but the code currently implements it through three different systems:

1. The `/api/v2` Master Persona Vault.
2. The SQLite persona/reference/generation pipeline.
3. The Orchestrator persona/anchor pipeline.

Because these systems do not share one canonical persona record, the UI may show a persona as master locked while generation, asset, provenance, and review systems do not necessarily refer to the same identity object.

The main issue is architectural consistency rather than the creative concept.

## Current master-persona process

### 1. Narrative-based persona synthesis

The main Vault UI accepts a freeform persona narrative and sends it to:

```text
POST /api/v2/personas/synthesize
```

The frontend debounces synthesis while typing and displays:

- Name
- Age
- Origin
- Body measurements
- Complexion
- Eyes
- Hair
- Lips
- Skin texture
- Silhouette
- Wardrobe signature
- World setting
- Canonical prompt

The backend synthesis is primarily regex and keyword based. It extracts names, age, regions, skin descriptions, hair, eyes, body shape, style, and other traits from text. It is deterministic text parsing and default selection rather than an AI reasoning layer.

### 2. Master vault creation

When the user clicks **Generate & Freeze 13-Image Master Vault**, the frontend:

1. Re-synthesizes the current narrative.
2. Sends the synthesized DNA to `/api/v2/personas/create`.
3. Receives a persona object and background job ID.
4. Starts polling vault progress.

The backend then:

1. Creates a `PersonaSpecification`.
2. Builds 13 image prompt specifications.
3. Creates `generated/master_persona_<persona_id>/`.
4. Stores the persona in `data/personas_v2.json`.
5. Starts a daemon background thread.
6. Generates the 13 images sequentially.
7. Copies each rendered image into the persona folder.
8. Stores progress in `_vault_jobs_cache.json`.

Relevant implementation areas:

- `static/app.js` — Vault UI synthesis, freeze action, and polling.
- `studio/api_v2.py` — v2 persona synthesis, persistence, vault creation, and background generation.
- `studio/master_persona_engine.py` — 13-pack prompt specification builder.
- `studio/diffusion_engine.py` — local image generation and asset registration.

### 3. The 13-image vault

The 13 images are divided into:

- Four turnaround images: front, left profile, right profile, and back.
- One eyes/lips macro.
- Four standard lifestyle/category baselines.
- Four adult/intimate baselines.

The design attempts to provide:

- Face and hair continuity.
- Body and silhouette references.
- Clothing and style references.
- Macro eye and lip details.
- Multiple camera angles.
- Category-specific visual anchors.
- Deterministic seed offsets.

This is a useful visual reference-vault strategy and aligns with `docs/MASTER_PERSONA_ENGINEERING_SPEC.md`.

### 4. Downstream generation

The normal SQLite generation path builds prompts from:

- Persona name.
- Age.
- Appearance.
- Description.
- Structured characteristics.
- Scene prompt.
- Selected reference image or approved source asset.

The standalone CLI works differently. It does not load the stored database persona directly. It reads a JSON generation brief and flattens the persona capsule into a prompt suffix for image and video generation.

## Strengths

### Strong identity-capsule structure

The project separates stable identity information from scene-specific instructions. Structured fields exist for face, physique, style, personality, world, and camera.

### Good freeze concept

The SQLite workflow prevents new references from being added after identity freeze and prevents repeatable series from being created before freezing.

### Good provenance direction

The standard asset workflow records persona ID, job ID, prompt, seed, reference ID, workflow, persona version, SHA-256, disclosure, and quality metadata.

### Good separation between identity and scene

Series episodes inherit a shared continuity prompt while retaining separate episode prompts and motion prompts.

### Good local-first workflow

The project supports local persona storage, local references, local generation, manual review, local JSON handoff, ComfyUI, and direct CLI workflows.

## Main architectural problems

### 1. No single master-persona source of truth

The project currently has multiple identity stores:

```text
data/personas_v2.json
SQLite personas table
SQLite reference_images table
SQLite assets table
Orchestrator persona routes
Generation brief JSON files
```

The main Vault reads `/api/v2/personas`, which comes from `personas_v2.json`.

The Orchestrator reads `/api/orchestrator/personas`, which comes from SQLite.

The standard generation flow reads `/api/personas`, also from SQLite.

Therefore, the same visual persona can exist in one system but not another.

### 2. The 13-image vault is not actually review-approved

The Vault UI uses language such as generated, verified, and frozen. However, `diffusion_engine.generate_render()` inserts rendered images into SQLite with `review='approved'` and `rights_confirmed=1` automatically.

There is no manual review step for each vault image, no identity-quality score, and no visual comparison against a canonical reference.

The conceptual lifecycle should instead be:

```text
generated → pending_review → approved / rejected
```

Generated should not mean approved master identity.

### 3. Vault output and SQLite asset paths are inconsistent

The diffusion engine writes files to `generated/renders/`, while the normal asset API looks for files in `data/outputs/`.

This can leave SQLite asset records pointing to files that the normal asset file, manifest, or package endpoints cannot locate.

### 4. Identity locking differs between paths

The SQLite path has `identity_locked`, `identity_version`, and `locked_at`.

The `/api/v2` Vault persona does not persist the same lock and version fields in its JSON persona object.

The Orchestrator sets `identity_locked` when locking an anchor but does not update `identity_version`.

The standard freeze route keeps the version at a minimum of `1`; it does not create a new immutable identity snapshot.

The current implementation is therefore closer to a lock flag than a true versioned identity system.

### 5. The Orchestrator can lock the wrong asset

The lock-anchor route looks up the asset by `asset_id` without verifying that the asset belongs to the selected persona.

It also does not verify that the asset is:

- An image.
- Approved.
- Rights-confirmed.
- Quality-checked.
- Owned by the selected persona.

This creates a risk of assigning Persona B's image as Persona A's master anchor.

### 6. Photo Studio can bypass the identity process

The Photo Studio route automatically marks generated images as approved, copies them into the reference directory, and creates a reference image. It does not consistently enforce the frozen identity state.

This allows a downstream creative tool to affect the reference vault without following the canonical identity-freeze process.

### 7. The synthesizer uses too many hardcoded defaults

The synthesis layer frequently fills in fixed values for body measurements, bust/waist/hip values, weight, height, body type, wardrobe, and facial traits.

In the custom JSON path, supplied values can be replaced by hardcoded values such as `36-24-30` and `36D`.

This makes the system appear flexible while silently normalizing different personas toward similar visual traits.

### 8. The full persona is currently mostly visual

The specification includes personality, speech style, mannerisms, cultural context, content pillars, recurring locations, and camera language.

The v2 Vault mainly persists visual biometrics, wardrobe signature, world setting, and image prompt specifications. Personality, voice, behavior, and content strategy are not strongly represented in the persisted Vault object.

The current Master Persona is therefore primarily a visual identity vault rather than a complete influencer persona.

### 9. Direct API validation is weaker than the UI suggests

The v2 persona creation model uses plain fields for name, age, and origin without the same strict validation as the standard persona schema.

The UI guides the user toward fictional adult personas, but direct API requests can bypass some of those constraints. Persona names are also used to form IDs and folders, so strict safe-slug validation is important.

### 10. Vault recovery is approximate

The recovery logic assumes that the number of PNG files equals the number of completed packs. It does not verify that the correct pack exists, that the file matches the expected prompt, or that the content hash is correct.

The progress cache is also separate from the main database and uses daemon threads, so process shutdown can still interrupt generation.

## Important future recommendations

### Define one canonical persona aggregate

The project should eventually have one authoritative identity object containing:

- Persona identity.
- Structured characteristics.
- Disclosure and content boundaries.
- Current identity version.
- Canonical reference ID.
- Master vault pack records.
- Approved/rejected status per pack.
- Prompt specification hash.
- Seed policy.
- Provenance metadata.

JSON should remain an import/export format, not a second live database.

### Separate persona versions from generated assets

Use a conceptual structure such as:

```text
Persona
  └── PersonaVersion
        ├── Identity capsule
        ├── Canonical reference
        ├── Master vault packs
        ├── Prompt hash
        └── Review status
```

Editing a frozen persona should create a new version rather than modifying the existing identity.

### Make the canonical reference explicit

Do not select the newest reference automatically. The persona should have an explicit `canonical_reference_id`. Other references may exist, but generation should use the canonical reference unless the user deliberately selects another approved reference.

### Add pack-level review

Each of the 13 images should eventually have a pack ID, file path, hash, prompt, seed, model, status, review decision, reviewer timestamp, and rejection reason.

### Centralize prompt construction

The following contain overlapping identity logic:

- `master_persona_engine.py`
- `orchestrator.py`
- `brief.py`
- `free_cli.py`
- `app.py`

They should conceptually use one identity-prompt service so the same persona does not receive different identity descriptions depending on the generation path.

### Test the actual Vault path

The current tests cover the SQLite persona workflow, but the main `/api/v2` Vault workflow lacks equivalent coverage.

Important future tests should cover:

- Narrative synthesis.
- Custom persona creation.
- 13-pack specification generation.
- Vault job persistence.
- Resume behavior.
- Pack-level failure.
- Duplicate persona creation.
- Identity lock behavior.
- Vault-to-SQLite asset linkage.
- Persona deletion and restoration.
- Invalid name/path input.
- Age and safety validation.

## Final assessment

The creative identity model is promising and the 13-image vault is a useful visual-identity strategy.

The current implementation is best described as:

```text
A strong master-persona UI and prompt-generation prototype
with multiple partially overlapping persistence systems.
```

It is not yet a fully reliable canonical identity system.

The most important future direction is to consolidate the identity lifecycle:

```text
Draft persona
  → reviewed identity capsule
  → frozen PersonaVersion
  → approved canonical reference
  → approved 13-pack vault
  → downstream generation
  → reviewed assets
```

Until that lifecycle is unified, there is a risk of persona drift, incorrect reference selection, incomplete provenance, false approved states, and inconsistent behavior between the Vault, Orchestrator, SQLite dashboard, and CLI.

This document records analysis and recommendations only. No code, dependencies, configuration, or installations were changed.

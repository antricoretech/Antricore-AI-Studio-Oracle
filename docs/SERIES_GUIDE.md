# Persona consistency and series workflow

The dashboard now treats a persona as a reusable production record instead of a one-off prompt. Use this sequence for a single video or a repeatable series.

## 1. Build the canonical persona

1. Open **Create → Persona library**.
2. Create the original fictional adult identity or import a validated persona JSON from ChatGPT.
3. Fill the identity capsule: face, physique, wardrobe/glamour direction, personality, world, camera language and the traits that must never change.
4. Add one or more rights-cleared master references. Use an original synthetic reference or material for which you have documented permission.
5. Review the appearance and references, then click **Freeze identity**.

Freezing creates an immutable continuity checkpoint (`identity_version`). New series plans and queued episodes require this checkpoint. Editing a persona later should be treated as a new version or a new persona, so an existing series is not silently changed.

## 2. Make one video

1. Go to **Produce → Image studio** and select the frozen persona.
2. Choose the approved master reference, then select a verified local video workflow.
3. Add the scene prompt and a separate motion direction (action, expression, camera movement and pacing).
4. Choose a vertical or landscape canvas, seed and optional narration/audio.
5. Confirm fictional identity, rights-cleared inputs and AI disclosure, then queue the render.
6. Open **Media Review**. Inspect the face, body, hands, motion, text, audio and disclosure before approving or rejecting the export.

The stored persona profile is appended to the generation prompt automatically. Identity continuity remains probabilistic: a frozen record improves repeatability but never replaces manual review.

## 3. Make a series

1. Open **Produce → Series studio** from the sidebar.
2. Select a frozen persona.
3. Write a short series description and a shared continuity bible. Include the fixed identity anchor, wardrobe rules, palette, camera grade, recurring locations, voice and disclosure language.
4. Add one episode per line using:

   `Episode title | visual direction | motion direction`

5. Select a verified video graph and confirm the rights/disclosure checkbox.
6. Create the series plan. Every episode stores the shared bible plus its own visual and motion direction.
7. Queue episodes one at a time, review each result, and approve only clean exports. The newest rights-cleared reference (or approved master image) is used automatically when an episode does not specify one.

The series library keeps the episode number, prompts, status and linked render job. Completed and failed jobs update the episode status, so a long-running character series can be resumed without losing its plan.

## 4. Bring direct-Python outputs back into the dashboard

When the local pipeline finishes, open **Review & export → Media review → Import a completed pipeline output**. Select the frozen persona, choose video/image/audio, upload the generated file, describe the episode, and keep the AI disclosure text. The imported asset starts as **pending**; approve it only after checking the media and disclosure. This closes the loop for files rendered outside the optional ComfyUI bridge.

## Direct CLI versus dashboard queue

The **Copy CLI handoff JSON** button includes the series plan and one valid generation brief per episode. Save an individual entry from `briefs` as a JSON file and run `python -m studio.free_cli brief --file episode.json`; the brief path automatically carries the frozen identity capsule into both the master-image and Wan2.2 prompts. The catalog displays the local FLUX, Wan, Kokoro and FFmpeg recipes so the intended path is visible. Catalog entries are setup guidance, not installed graphs. The dashboard queue accepts only a verified imported ComfyUI API-format graph. The direct Python CLI remains the no-credit path for the local/cloud GPU pipeline; import the completed output for review.

Keep model and dependency licenses, source permissions and the AI disclosure with every export. Do not use real-person likenesses, minors, explicit sexual acts, non-consensual content or deceptive impersonation.

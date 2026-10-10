# Studio navigation and connected production flow

The dashboard uses a grouped menu so the visible navigation matches the production order without splitting the underlying pipeline into disconnected tools.

Groups are collapsed by default to keep the sidebar compact. Select a group heading to expand its submenu; the open state is remembered in the browser, and navigating to a submenu opens its group automatically.

Overview includes a recent generated library for image and video outputs. Persona cards also show that character's latest generated media, so the identity record and its production history stay visible together.

## Menu

### Workspace

- **Overview** — current pipeline state, recent jobs and the recommended next action.

### Create

- **Persona library** — create, import, freeze and maintain the canonical fictional adult identity.
- **New persona** — shortcut directly to the identity form.
- **Reference vault** — add and review rights-cleared master references for continuity.
- **Generation brief** — load a ChatGPT JSON handoff containing persona, image, motion, voice and review fields.

### Produce

- **Image studio** — create or vary an approved master image.
- **Video studio** — use an approved image with a verified motion workflow.
- **Voice & narration** — create optional synthetic narration with Kokoro.
- **Series studio** — plan repeatable episodes that inherit the frozen persona.

### Review & export

- **Media review** — inspect, approve or reject generated images, videos and audio.
- **Approval queue** — shortcut to the pending/approved review gallery.
- **Export packages** — shortcut to reviewed assets and their download/disclosure records.
- **Link tracking** — maintain controlled testing links after review.

### Operations

- **Workflow manager** — import and inspect verified ComfyUI API graphs; this is an advanced configuration area.
- **Monitoring** — check the API, connections, model files, runtimes, GPU, workflows, queue and storage before a render session.

## Connected hand-off

The blue pipeline rail at the top of the dashboard is the canonical route:

`Persona → Brief → Master image → Motion video → Voice (optional) → Review & export → Series reuse`

Each step opens the existing panel and focuses the relevant control. The persona record and generation brief remain the source of truth; approved references and media are offered as the next stage's selectable inputs. Series episodes store the frozen identity version and shared continuity brief so later episodes do not silently drift.

Workflow Manager and Monitoring are intentionally separate from creative production: users can render through a verified graph or the direct Python CLI, while the monitoring page reports whether the selected environment is ready. No new API credits or hosted inference path is introduced by this navigation layer.

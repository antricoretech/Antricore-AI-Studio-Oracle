# Instagram Publishing Integration Research

**Reviewed:** 2026-10-20  
**Project:** AI Influencer Studio  
**Scope:** Research and recommendations only. No implementation is included in this document.

## Executive recommendation

Keep AI Influencer Studio as the master system for personas, generated assets, provenance, review, and approval. When implementation is approved, add a dedicated Instagram publishing adapter that uses Meta's official Instagram Platform API.

Recommended open-source references:

1. **Best long-term fit:** a native official Meta API adapter inside this application.
2. **Best off-the-shelf repository:** [Postiz](https://github.com/gitroomhq/postiz-app).
3. **Best reliability architecture reference:** [Postline](https://github.com/adeel1608/social-media-scheduler).
4. **Not recommended for production:** unofficial private API libraries such as [instagrapi](https://github.com/subzeroid/instagrapi).

The current project does not contain online social publishing. The existing application should remain the source of truth rather than duplicating persona and asset ownership in a separate scheduler.

## Official Instagram API constraints

Instagram's official publishing API has several important requirements:

- Publishing is intended for Instagram Professional accounts: Business or Creator.
- Personal Instagram accounts are not supported by the official publishing API.
- The normal publishing sequence is:
  1. Create a media container.
  2. Poll the container processing status.
  3. Publish the completed container.
- Instagram must be able to download the media from a publicly reachable HTTPS URL.
- A local file path, `127.0.0.1`, private LAN URL, or local-only `generated/` directory cannot be used as the media URL.
- Meta OAuth, permissions, app configuration, and possibly review or business verification are required depending on the authentication path and account ownership.
- Platform limits, supported media types, permissions, and review requirements can change; verify the current Meta documentation before implementation.

Primary references:

- [Meta Instagram API documentation collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api)
- [Instagram content publishing documentation](https://developers.facebook.com/docs/instagram-platform/content-publishing)
- [Instagram API with Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login)
- [Meta developer resources](https://developers.meta.com/resources/)

## Persona-to-account model

Each master persona should have an explicit Instagram account assignment:

```text
Master Persona
   └── Instagram Account
         ├── Instagram user ID
         ├── username
         ├── account type
         ├── OAuth credentials
         ├── token expiry/status
         └── publishing history
```

Example:

```text
Mira Persona  →  @mira.example
Aria Persona  →  @aria.example
Nora Persona  →  @nora.example
```

The destination account should be permanently recorded on the publication record when the content is approved. It should not be re-selected dynamically at send time.

Suggested conceptual records:

- `persona`
- `social_account`
- `persona_social_account`
- `publication`
- `publication_attempt`
- `media_delivery`
- `oauth_token_status`

The initial design can support one Instagram account per persona while allowing multiple accounts later.

## Recommended publishing flow

```text
Generate asset
   ↓
Manual review and rights confirmation
   ↓
Confirm persona and Instagram account
   ↓
Create caption and disclosure
   ↓
Upload approved media to temporary HTTPS storage
   ↓
Create Instagram media container
   ↓
Poll processing status
   ↓
Publish to selected Instagram account
   ↓
Save Instagram media ID and result
```

The existing project already provides useful foundations:

- Persona records.
- Asset records.
- Review and approval state.
- Disclosure metadata.
- SHA-256 hashes.
- Provenance manifests.
- Local generated media.

The missing conceptual layer is the publication system.

## Media delivery recommendation

Do not expose the complete local `generated/` folder publicly.

Use a restricted staging process:

1. Upload only approved assets.
2. Generate a short-lived signed HTTPS URL.
3. Allow Meta to fetch the media.
4. Expire or remove the staged copy after the publishing window.
5. Preserve the original asset locally for provenance and audit.

Possible storage options include Cloudflare R2, Amazon S3, Backblaze B2, or another restricted object-storage service. A tunnel may help during development, but it should not be treated as the permanent production media architecture.

## Repository comparison

| Repository | Strengths | Limitations | Recommendation |
|---|---|---|---|
| [Postiz](https://github.com/gitroomhq/postiz-app) | Approximately 37k stars, self-hosted, Instagram support, public API, scheduling, multiple channels, official OAuth approach | Large TypeScript/NestJS/PostgreSQL/Redis/Temporal stack; AGPL-3.0 | Best off-the-shelf option |
| [Postline](https://github.com/adeel1608/social-media-scheduler) | Focused design, official APIs, signed media URLs, queues, idempotency, leases, explicit ambiguous-result handling | Small project; repository states live social publishing has not yet been verified | Best architecture reference |
| [Mixpost](https://github.com/inovector/mixpost) | Mature, MIT licensed, scheduling and account management, approximately 3.8k stars | PHP/Laravel stack; Instagram capability depends on the selected edition or fork | Good general scheduler |
| [MixpostMCP](https://github.com/ZenFrogStudio/MixpostMCP) | Desktop mode, SQLite, Instagram support, local scheduling | Requires the desktop app to remain open; requires public media URLs; limited built-in authentication | Suitable for experimentation, not preferred as the production core |
| [instagrapi](https://github.com/subzeroid/instagrapi) | Popular Python library, approximately 7k stars, supports private Instagram endpoints | Unofficial private API, session challenges, account checkpoints, breakage and policy risks | Avoid for production publishing |
| [n8n](https://github.com/n8n-io/n8n) | Strong workflow orchestration and scheduling | Source-available/fair-code rather than OSI open source; adds another service | Optional orchestration layer only |

Postiz documents self-hosting, Instagram support, public API integration, official OAuth flows, and no scraping-based publishing. It requires its own database, Redis, storage, provider applications, and maintenance.

Postline is useful as a design reference because it separates platform targets and uses stable idempotency keys, signed media delivery, leases, queues, and manual handling of ambiguous outcomes. Its own repository states that production social publishing has not yet been live-verified, so it should be treated primarily as an architecture reference.

Private API automation is not a good foundation. The instagrapi project itself warns that private API automation is fragile because device state, challenges, proxies, trust signals, and rate limits can change independently of the library.

## Architecture options

### Option A: Native adapter inside AI Influencer Studio — recommended

Keep this application as the master production system and add a dedicated official Instagram publisher later.

Advantages:

- Persona and account mapping remain in one database.
- Generated assets remain connected to provenance.
- Review and approval stay inside the existing dashboard.
- No duplicated media library.
- Lower risk of publishing the wrong persona to the wrong account.
- Easier future support for additional platforms.

The publisher should be isolated from image/video generation code and should communicate only with Meta's official endpoints.

### Option B: Postiz sidecar

Run Postiz beside this application:

1. AI Influencer Studio generates and approves content.
2. The approved media is uploaded to staging storage.
3. The local application calls Postiz's API.
4. The selected account and schedule are passed to Postiz.
5. Publication status is returned through API or webhook.
6. The original asset and provenance stay in AI Influencer Studio.

This may be faster to prototype, but it creates two systems that understand accounts, media, scheduling, and publication. Review the AGPL-3.0 license before embedding or redistributing modified Postiz code.

### Option C: Local-only desktop scheduler

A desktop scheduler can run on the MacBook, but scheduled posts will not be sent while the computer is asleep, offline, or shut down. This is suitable for supervised workflows, not dependable unattended publishing.

## Reliability requirements

The publisher should not be treated as a simple file-upload button. It should eventually include:

- Persistent publication queue.
- UTC scheduling.
- Per-account rate limiting.
- Token expiry monitoring.
- Account connection health.
- Idempotency keys.
- Locking or lease ownership for each job.
- Retry only for clearly retryable failures.
- Manual review for ambiguous outcomes.
- Remote Instagram media ID storage.
- Error history and audit log.
- Publish cancellation.
- Duplicate detection.

An API call may succeed even if the local connection fails immediately afterward. Blind retries can therefore create duplicate posts. A strong pattern is to mark ambiguous outcomes as `needs_review` rather than automatically retrying.

Suggested publication state machine:

```text
draft
  → approved
  → queued
  → media_staged
  → container_created
  → processing
  → published

Failure states:
  failed
  needs_review
  cancelled
```

## Security recommendations

Do not store Instagram passwords.

Use OAuth authorization for each account and protect:

- Access tokens.
- Token expiry information.
- Instagram user IDs.
- Granted permissions.
- Account connection status.
- Last successful API call.

For local macOS operation, OS Keychain-backed secret storage is preferable to plaintext tokens in SQLite or `.env` files. In a server deployment, use encrypted storage backed by a dedicated secret manager where possible.

The server should validate this relationship before publishing:

```text
approved asset
  → belongs to persona
  → persona is linked to selected Instagram account
  → account is authorized
```

The client should not be trusted to submit an arbitrary persona/account pair.

## AI persona and publication policy

The project's existing fictional-adult-persona, disclosure, rights-confirmation, and manual-review gates should remain mandatory before automatic publication.

Before queueing an Instagram post, require confirmation of:

- Persona identity.
- Destination Instagram account.
- Asset approval.
- Rights confirmation.
- AI/synthetic disclosure.
- Caption approval.
- Commercial or brand claim review.
- No real-person impersonation.
- No deceptive endorsement.

Automation should publish approved content; it should not be responsible for deciding whether generated content is safe, lawful, or suitable for publication.

## MacBook Air considerations

The Instagram publishing worker itself is lightweight compared with local AI image/video generation. The main limitations are operational:

- The Mac must be awake and online for a local worker to publish.
- The Mac's local files must be staged to public HTTPS storage.
- Running a large scheduler stack alongside local generation may consume memory.
- A small remote worker can provide reliable scheduling while the Mac remains the generation workstation.

Recommended deployment direction:

```text
MacBook Air
  ├── AI generation
  ├── persona library
  ├── review and approval
  └── publication queue

Small always-on worker or VPS
  ├── media staging
  ├── scheduled publication
  └── status polling/webhooks
```

## Final recommendation

Do not use an unofficial private Instagram client as the foundation.

The preferred future design is:

1. Keep AI Influencer Studio as the master persona and asset system.
2. Use official Instagram APIs only.
3. Add explicit persona-to-account mapping.
4. Use temporary signed HTTPS media delivery.
5. Add a persistent publication queue and state machine.
6. Use Postiz as the leading open-source reference or optional sidecar.
7. Borrow Postline's idempotency, queue, lease, and ambiguous-result handling.
8. Keep manual approval before automatic posting.
9. Use a small always-on worker if publishing must happen while the MacBook is asleep.

This document is a future implementation reference only. No code, configuration, dependencies, or installations are changed by this research.

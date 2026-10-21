import os
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.getenv("DATA_DIR") or ROOT / "data").resolve()
DB = DATA / "studio.db"
UPLOADS = DATA / "references"
OUTPUTS = DATA / "outputs"
WORKFLOWS = DATA / "workflows"


def initialize():
    for directory in [DATA, UPLOADS, OUTPUTS, WORKFLOWS]:
        directory.mkdir(parents=True, exist_ok=True)
    with connection() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS personas (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL,
            description TEXT NOT NULL, appearance TEXT NOT NULL,
            disclosure TEXT NOT NULL, created_at TEXT NOT NULL,
            characteristics_json TEXT NOT NULL DEFAULT '{}',
            identity_locked INTEGER NOT NULL DEFAULT 0,
            identity_version INTEGER NOT NULL DEFAULT 1,
            locked_at TEXT
        );
        CREATE TABLE IF NOT EXISTS persona_versions (
            id TEXT PRIMARY KEY,
            persona_id TEXT NOT NULL,
            version_no INTEGER NOT NULL,
            state TEXT NOT NULL DEFAULT 'draft',
            snapshot_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL DEFAULT 'created',
            created_at TEXT NOT NULL,
            frozen_at TEXT,
            superseded_at TEXT,
            UNIQUE(persona_id, version_no),
            FOREIGN KEY(persona_id) REFERENCES personas(id)
        );
        CREATE TABLE IF NOT EXISTS reference_images (
            id TEXT PRIMARY KEY, persona_id TEXT NOT NULL,
            filename TEXT NOT NULL, label TEXT NOT NULL, created_at TEXT NOT NULL,
            asset_id TEXT,
            persona_version_id TEXT,
            role TEXT NOT NULL DEFAULT 'supporting',
            content_class TEXT NOT NULL DEFAULT 'identity',
            review TEXT NOT NULL DEFAULT 'pending',
            rights_confirmed INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(persona_id) REFERENCES personas(id)
        );
        CREATE TABLE IF NOT EXISTS reference_packs (
            id TEXT PRIMARY KEY,
            persona_id TEXT NOT NULL,
            persona_version_id TEXT,
            pack_type TEXT NOT NULL,
            name TEXT NOT NULL,
            content_class TEXT NOT NULL DEFAULT 'identity',
            identity_authority TEXT NOT NULL DEFAULT 'identity',
            review TEXT NOT NULL DEFAULT 'pending',
            canonical_eligible INTEGER NOT NULL DEFAULT 0,
            canonical_selected INTEGER NOT NULL DEFAULT 0,
            reviewed_at TEXT,
            source TEXT NOT NULL DEFAULT 'operator',
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            UNIQUE(persona_id, pack_type, persona_version_id),
            FOREIGN KEY(persona_id) REFERENCES personas(id)
        );
        CREATE TABLE IF NOT EXISTS reference_pack_items (
            id TEXT PRIMARY KEY,
            pack_id TEXT NOT NULL,
            asset_id TEXT,
            filename TEXT,
            source_url TEXT NOT NULL,
            label TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'supporting_reference',
            content_class TEXT NOT NULL DEFAULT 'identity',
            review TEXT NOT NULL DEFAULT 'pending',
            rights_confirmed INTEGER NOT NULL DEFAULT 0,
            canonical_eligible INTEGER NOT NULL DEFAULT 0,
            canonical_selected INTEGER NOT NULL DEFAULT 0,
            reviewed_at TEXT,
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(pack_id) REFERENCES reference_packs(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS content_packs (
            id TEXT PRIMARY KEY,
            persona_id TEXT NOT NULL,
            persona_version_id TEXT NOT NULL,
            reference_pack_id TEXT NOT NULL,
            pack_type TEXT NOT NULL,
            name TEXT NOT NULL,
            content_class TEXT NOT NULL DEFAULT 'identity',
            identity_authority TEXT NOT NULL DEFAULT 'identity',
            identity_core INTEGER NOT NULL DEFAULT 0,
            review TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            style_json TEXT NOT NULL DEFAULT '{}',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            UNIQUE(persona_id, persona_version_id, pack_type, name),
            FOREIGN KEY(persona_id) REFERENCES personas(id),
            FOREIGN KEY(reference_pack_id) REFERENCES reference_packs(id)
        );
        CREATE TABLE IF NOT EXISTS content_pack_items (
            id TEXT PRIMARY KEY,
            content_pack_id TEXT NOT NULL,
            reference_pack_item_id TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'canonical_anchor',
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            UNIQUE(content_pack_id, reference_pack_item_id),
            FOREIGN KEY(content_pack_id) REFERENCES content_packs(id) ON DELETE CASCADE,
            FOREIGN KEY(reference_pack_item_id) REFERENCES reference_pack_items(id),
            FOREIGN KEY(asset_id) REFERENCES assets(id)
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, persona_id TEXT NOT NULL, workflow_id TEXT NOT NULL,
            type TEXT NOT NULL, prompt TEXT NOT NULL, status TEXT NOT NULL,
            error TEXT, comfy_prompt_id TEXT, created_at TEXT NOT NULL, finished_at TEXT,
            request_json TEXT NOT NULL DEFAULT '{}', updated_at TEXT,
            lineage_json TEXT NOT NULL DEFAULT '{}', attempt INTEGER NOT NULL DEFAULT 1,
            cancel_requested INTEGER NOT NULL DEFAULT 0,
            idempotency_key TEXT,
            result_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS assets (
            id TEXT PRIMARY KEY, persona_id TEXT NOT NULL, persona_version_id TEXT, job_id TEXT,
            filename TEXT NOT NULL, kind TEXT NOT NULL, prompt TEXT NOT NULL,
            review TEXT NOT NULL DEFAULT 'pending', rights_confirmed INTEGER NOT NULL DEFAULT 0,
            disclosure TEXT NOT NULL DEFAULT 'Fictional adult character. AI-generated synthetic media.',
            created_at TEXT NOT NULL, sha256 TEXT, metadata_json TEXT NOT NULL DEFAULT '{}',
            quality_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS links (
            code TEXT PRIMARY KEY, label TEXT NOT NULL,
            destination TEXT NOT NULL, clicks INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS series (
            id TEXT PRIMARY KEY, persona_id TEXT NOT NULL, title TEXT NOT NULL,
            description TEXT NOT NULL, shared_prompt TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned', created_at TEXT NOT NULL,
            persona_version_id TEXT,
            FOREIGN KEY(persona_id) REFERENCES personas(id)
        );
        CREATE TABLE IF NOT EXISTS series_episodes (
            id TEXT PRIMARY KEY, series_id TEXT NOT NULL, episode_no INTEGER NOT NULL,
            title TEXT NOT NULL, prompt TEXT NOT NULL, video_prompt TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned', job_id TEXT, created_at TEXT NOT NULL,
            FOREIGN KEY(series_id) REFERENCES series(id),
            FOREIGN KEY(job_id) REFERENCES jobs(id)
        );
        CREATE TABLE IF NOT EXISTS schema_meta (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        );
        """)
        columns = {row[1] for row in con.execute("PRAGMA table_info(personas)").fetchall()}
        if "characteristics_json" not in columns:
            con.execute("ALTER TABLE personas ADD COLUMN characteristics_json TEXT NOT NULL DEFAULT '{}'")
        if "identity_locked" not in columns:
            con.execute("ALTER TABLE personas ADD COLUMN identity_locked INTEGER NOT NULL DEFAULT 0")
        if "identity_version" not in columns:
            con.execute("ALTER TABLE personas ADD COLUMN identity_version INTEGER NOT NULL DEFAULT 1")
        if "locked_at" not in columns:
            con.execute("ALTER TABLE personas ADD COLUMN locked_at TEXT")
        series_columns = {row[1] for row in con.execute("PRAGMA table_info(series)").fetchall()}
        if "persona_version_id" not in series_columns:
            con.execute("ALTER TABLE series ADD COLUMN persona_version_id TEXT")
        reference_columns = {row[1] for row in con.execute("PRAGMA table_info(reference_images)").fetchall()}
        if "asset_id" not in reference_columns:
            con.execute("ALTER TABLE reference_images ADD COLUMN asset_id TEXT")
        if "persona_version_id" not in reference_columns:
            con.execute("ALTER TABLE reference_images ADD COLUMN persona_version_id TEXT")
        if "role" not in reference_columns:
            con.execute("ALTER TABLE reference_images ADD COLUMN role TEXT NOT NULL DEFAULT 'supporting'")
        if "content_class" not in reference_columns:
            con.execute("ALTER TABLE reference_images ADD COLUMN content_class TEXT NOT NULL DEFAULT 'identity'")
        if "review" not in reference_columns:
            con.execute("ALTER TABLE reference_images ADD COLUMN review TEXT NOT NULL DEFAULT 'pending'")
        if "rights_confirmed" not in reference_columns:
            con.execute("ALTER TABLE reference_images ADD COLUMN rights_confirmed INTEGER NOT NULL DEFAULT 0")
        if "metadata_json" not in reference_columns:
            con.execute("ALTER TABLE reference_images ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'")
        pack_columns = {row[1] for row in con.execute("PRAGMA table_info(reference_packs)").fetchall()}
        if "canonical_selected" not in pack_columns:
            con.execute("ALTER TABLE reference_packs ADD COLUMN canonical_selected INTEGER NOT NULL DEFAULT 0")
        if "reviewed_at" not in pack_columns:
            con.execute("ALTER TABLE reference_packs ADD COLUMN reviewed_at TEXT")
        pack_item_columns = {row[1] for row in con.execute("PRAGMA table_info(reference_pack_items)").fetchall()}
        if "asset_id" not in pack_item_columns:
            con.execute("ALTER TABLE reference_pack_items ADD COLUMN asset_id TEXT")
        if "canonical_selected" not in pack_item_columns:
            con.execute("ALTER TABLE reference_pack_items ADD COLUMN canonical_selected INTEGER NOT NULL DEFAULT 0")
        if "reviewed_at" not in pack_item_columns:
            con.execute("ALTER TABLE reference_pack_items ADD COLUMN reviewed_at TEXT")
        asset_columns = {row[1] for row in con.execute("PRAGMA table_info(assets)").fetchall()}
        if "persona_version_id" not in asset_columns:
            con.execute("ALTER TABLE assets ADD COLUMN persona_version_id TEXT")
        if "disclosure" not in asset_columns:
            con.execute("ALTER TABLE assets ADD COLUMN disclosure TEXT NOT NULL DEFAULT 'Fictional adult character. AI-generated synthetic media.'")
        if "sha256" not in asset_columns:
            con.execute("ALTER TABLE assets ADD COLUMN sha256 TEXT")
        if "metadata_json" not in asset_columns:
            con.execute("ALTER TABLE assets ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'")
        if "quality_json" not in asset_columns:
            con.execute("ALTER TABLE assets ADD COLUMN quality_json TEXT NOT NULL DEFAULT '{}'")
        job_columns = {row[1] for row in con.execute("PRAGMA table_info(jobs)").fetchall()}
        if "request_json" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN request_json TEXT NOT NULL DEFAULT '{}'")
        if "updated_at" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN updated_at TEXT")
        if "lineage_json" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN lineage_json TEXT NOT NULL DEFAULT '{}'")
        if "attempt" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN attempt INTEGER NOT NULL DEFAULT 1")
        if "cancel_requested" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN cancel_requested INTEGER NOT NULL DEFAULT 0")
        if "idempotency_key" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN idempotency_key TEXT")
        if "result_json" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN result_json TEXT NOT NULL DEFAULT '{}'")
        if "worker_id" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN worker_id TEXT")
        if "started_at" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN started_at TEXT")
        if "heartbeat_at" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN heartbeat_at TEXT")
        if "lease_expires_at" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN lease_expires_at TEXT")
        if "next_retry_at" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN next_retry_at TEXT")
        if "progress_stage" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN progress_stage TEXT NOT NULL DEFAULT 'queued'")
        if "progress_percent" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN progress_percent INTEGER NOT NULL DEFAULT 0")
        if "progress_detail" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN progress_detail TEXT")
        if "progress_json" not in job_columns:
            con.execute("ALTER TABLE jobs ADD COLUMN progress_json TEXT NOT NULL DEFAULT '{}'")
        # Give pre-progress jobs a truthful terminal snapshot instead of the
        # migration default of queued/0.
        con.execute(
            "UPDATE jobs SET progress_stage=CASE status "
            "WHEN 'completed' THEN 'completed' WHEN 'failed' THEN 'failed' "
            "WHEN 'cancelled' THEN 'cancelled' WHEN 'interrupted' THEN 'interrupted' "
            "WHEN 'running' THEN 'running' WHEN 'submitted' THEN 'submitted' ELSE 'queued' END, "
            "progress_percent=CASE status WHEN 'completed' THEN 100 WHEN 'failed' THEN 100 "
            "WHEN 'cancelled' THEN 100 WHEN 'interrupted' THEN 0 ELSE progress_percent END "
            "WHERE progress_stage='queued' AND status<>'queued'"
        )
        # Backfill one deterministic version for legacy personas before the
        # repository starts creating new canonical PersonaVersion records.
        legacy_personas = con.execute(
            "SELECT id, name, age, description, appearance, disclosure, created_at, characteristics_json, identity_locked, identity_version, locked_at FROM personas"
        ).fetchall()
        for persona in legacy_personas:
            exists = con.execute(
                "SELECT 1 FROM persona_versions WHERE persona_id=? LIMIT 1", (persona[0],)
            ).fetchone()
            if exists:
                continue
            version_no = int(persona[9] or 1)
            state = "frozen" if persona[8] else "draft"
            try:
                characteristics = json.loads(persona[7] or "{}")
            except (TypeError, json.JSONDecodeError):
                characteristics = {}
            snapshot = {
                "name": persona[1],
                "age": persona[2],
                "description": persona[3],
                "appearance": persona[4],
                "disclosure": persona[5],
                "characteristics": characteristics,
            }
            con.execute(
                "INSERT INTO persona_versions (id, persona_id, version_no, state, snapshot_json, source, created_at, frozen_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (f"{persona[0]}-v{version_no}", persona[0], version_no, state,
                 json.dumps(snapshot, ensure_ascii=False, sort_keys=True), "legacy_backfill",
                 persona[6], persona[10] if state == "frozen" else None),
            )
        # Foreign-key and queue lookups are the hot paths for the control plane.
        con.executescript("""
        CREATE INDEX IF NOT EXISTS idx_reference_images_persona ON reference_images(persona_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_reference_images_version ON reference_images(persona_version_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_reference_images_role ON reference_images(persona_id, role, review);
        CREATE INDEX IF NOT EXISTS idx_reference_packs_persona ON reference_packs(persona_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_reference_packs_version ON reference_packs(persona_version_id, pack_type);
        CREATE INDEX IF NOT EXISTS idx_reference_pack_items_pack ON reference_pack_items(pack_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_reference_pack_items_asset ON reference_pack_items(asset_id);
        CREATE INDEX IF NOT EXISTS idx_content_packs_persona_version ON content_packs(persona_id, persona_version_id, review);
        CREATE INDEX IF NOT EXISTS idx_content_pack_items_pack ON content_pack_items(content_pack_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_content_pack_items_asset ON content_pack_items(asset_id);
        CREATE INDEX IF NOT EXISTS idx_persona_versions_persona ON persona_versions(persona_id, version_no);
        CREATE INDEX IF NOT EXISTS idx_persona_versions_state ON persona_versions(state, created_at);
        CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at);
        CREATE INDEX IF NOT EXISTS idx_jobs_dispatch ON jobs(status, next_retry_at, created_at);
        CREATE INDEX IF NOT EXISTS idx_jobs_persona_created ON jobs(persona_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_assets_persona_created ON assets(persona_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_assets_review_kind ON assets(review, kind);
        CREATE INDEX IF NOT EXISTS idx_assets_sha256 ON assets(sha256);
        CREATE INDEX IF NOT EXISTS idx_assets_persona_version ON assets(persona_id, persona_version_id, kind, review);
        CREATE INDEX IF NOT EXISTS idx_series_persona_created ON series(persona_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_series_persona_version ON series(persona_version_id);
        CREATE INDEX IF NOT EXISTS idx_series_episodes_job ON series_episodes(job_id);
        """)
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_idempotency_key ON jobs(idempotency_key) WHERE idempotency_key IS NOT NULL")
        con.execute("INSERT INTO schema_meta(key,value) VALUES('schema_version','12') ON CONFLICT(key) DO UPDATE SET value=excluded.value")
        # A durable queued row is safe to dispatch after restart. Only work
        # that may already have reached ComfyUI is interrupted and requires
        # prompt reconciliation or explicit operator retry.
        con.execute("UPDATE jobs SET status='interrupted', error='App restarted during job; retry from Studio', updated_at=?, worker_id=NULL, heartbeat_at=NULL, lease_expires_at=NULL WHERE status IN ('running','submitted','cancelling')", (datetime_now(),))


@contextmanager
def connection():
    con = sqlite3.connect(DB, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def all_rows(sql: str, args=()):
    with connection() as con:
        return [dict(x) for x in con.execute(sql, args).fetchall()]


def row(sql: str, args=()):
    with connection() as con:
        result = con.execute(sql, args).fetchone()
        return dict(result) if result is not None else None


def write(sql: str, args=()):
    with connection() as con:
        con.execute(sql, args)


def write_many(statements):
    """Run a group of writes in one transaction.

    The route layer uses this for series creation and queue state changes so a
    partial write cannot leave the control plane with an orphaned episode.
    """

    with connection() as con:
        for sql, args in statements:
            con.execute(sql, args)


def datetime_now():
    """UTC timestamp helper kept local to avoid importing the route module."""

    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")

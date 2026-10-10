import os
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
        CREATE TABLE IF NOT EXISTS reference_images (
            id TEXT PRIMARY KEY, persona_id TEXT NOT NULL,
            filename TEXT NOT NULL, label TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(persona_id) REFERENCES personas(id)
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, persona_id TEXT NOT NULL, workflow_id TEXT NOT NULL,
            type TEXT NOT NULL, prompt TEXT NOT NULL, status TEXT NOT NULL,
            error TEXT, comfy_prompt_id TEXT, created_at TEXT NOT NULL, finished_at TEXT
        );
        CREATE TABLE IF NOT EXISTS assets (
            id TEXT PRIMARY KEY, persona_id TEXT NOT NULL, job_id TEXT,
            filename TEXT NOT NULL, kind TEXT NOT NULL, prompt TEXT NOT NULL,
            review TEXT NOT NULL DEFAULT 'pending', rights_confirmed INTEGER NOT NULL DEFAULT 0,
            disclosure TEXT NOT NULL DEFAULT 'Fictional adult character. AI-generated synthetic media.',
            created_at TEXT NOT NULL
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
            FOREIGN KEY(persona_id) REFERENCES personas(id)
        );
        CREATE TABLE IF NOT EXISTS series_episodes (
            id TEXT PRIMARY KEY, series_id TEXT NOT NULL, episode_no INTEGER NOT NULL,
            title TEXT NOT NULL, prompt TEXT NOT NULL, video_prompt TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned', job_id TEXT, created_at TEXT NOT NULL,
            FOREIGN KEY(series_id) REFERENCES series(id),
            FOREIGN KEY(job_id) REFERENCES jobs(id)
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
        asset_columns = {row[1] for row in con.execute("PRAGMA table_info(assets)").fetchall()}
        if "disclosure" not in asset_columns:
            con.execute("ALTER TABLE assets ADD COLUMN disclosure TEXT NOT NULL DEFAULT 'Fictional adult character. AI-generated synthetic media.'")
        con.execute("UPDATE jobs SET status='interrupted', error='App restarted during job; retry from Studio' WHERE status IN ('running','submitted','queued')")


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

"""Small persistence boundary for route handlers.

This is deliberately a light repository layer rather than a new ORM. SQLite is
still the right fit for a single local/cloud worker, while keeping SQL out of
the orchestration paths makes the next storage migration straightforward.
"""

from __future__ import annotations

import json

from . import database as db


class PersonaRepository:
    @staticmethod
    def get(persona_id: str):
        return db.row("SELECT * FROM personas WHERE id=?", (persona_id,))

    @staticmethod
    def list():
        return db.all_rows("SELECT * FROM personas ORDER BY created_at DESC")

    @staticmethod
    def create(*, persona_id: str, name: str, age: int, description: str, appearance: str, disclosure: str, created_at: str, characteristics: dict):
        db.write(
            "INSERT INTO personas (id,name,age,description,appearance,disclosure,created_at,characteristics_json) VALUES (?,?,?,?,?,?,?,?)",
            (persona_id, name, age, description, appearance, disclosure, created_at, json.dumps(characteristics)),
        )
        return PersonaRepository.get(persona_id)


class SeriesRepository:
    @staticmethod
    def create(*, series_id: str, persona_id: str, title: str, description: str, shared_prompt: str, created_at: str, episodes: list[tuple]):
        statements = [(
            "INSERT INTO series (id,persona_id,title,description,shared_prompt,status,created_at) VALUES (?,?,?,?,?,?,?)",
            (series_id, persona_id, title, description, shared_prompt, "planned", created_at),
        )]
        for episode in episodes:
            statements.append((
                "INSERT INTO series_episodes (id,series_id,episode_no,title,prompt,video_prompt,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (episode[0], series_id, episode[1], episode[2], episode[3], episode[4], "planned", episode[5]),
            ))
        db.write_many(statements)
        return db.row("SELECT * FROM series WHERE id=?", (series_id,))


class JobRepository:
    @staticmethod
    def create(*, job_id: str, persona_id: str, workflow_id: str, kind: str, prompt: str, request_json: str, lineage_json: str = "{}", created_at: str):
        db.write(
            "INSERT INTO jobs (id,persona_id,workflow_id,type,prompt,status,created_at,request_json,updated_at,lineage_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (job_id, persona_id, workflow_id, kind, prompt, "queued", created_at, request_json, created_at, lineage_json),
        )


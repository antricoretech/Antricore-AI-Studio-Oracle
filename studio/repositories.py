"""Small persistence boundary for route handlers.

This is deliberately a light repository layer rather than a new ORM. SQLite is
still the right fit for a single local/cloud worker, while keeping SQL out of
the orchestration paths makes the next storage migration straightforward.
"""

from __future__ import annotations

import json
import uuid

from . import database as db


class PersonaRepository:
    @staticmethod
    def get(persona_id: str):
        return db.row("SELECT * FROM personas WHERE id=?", (persona_id,))

    @staticmethod
    def list():
        return db.all_rows("SELECT * FROM personas ORDER BY created_at DESC")

    @staticmethod
    def current_version(persona_id: str):
        return db.row(
            "SELECT * FROM persona_versions WHERE persona_id=? ORDER BY version_no DESC LIMIT 1",
            (persona_id,),
        )

    @staticmethod
    def versions(persona_id: str):
        return db.all_rows(
            "SELECT * FROM persona_versions WHERE persona_id=? ORDER BY version_no DESC",
            (persona_id,),
        )

    @staticmethod
    def version(persona_id: str, version_id: str):
        return db.row(
            "SELECT * FROM persona_versions WHERE persona_id=? AND id=?",
            (persona_id, version_id),
        )

    @staticmethod
    def create(*, persona_id: str, name: str, age: int, description: str, appearance: str, disclosure: str, created_at: str, characteristics: dict):
        snapshot = {
            "name": name,
            "age": age,
            "description": description,
            "appearance": appearance,
            "disclosure": disclosure,
            "characteristics": characteristics,
        }
        db.write_many([
            (
                "INSERT INTO personas (id,name,age,description,appearance,disclosure,created_at,characteristics_json) VALUES (?,?,?,?,?,?,?,?)",
                (persona_id, name, age, description, appearance, disclosure, created_at, json.dumps(characteristics)),
            ),
            (
                "INSERT INTO persona_versions (id,persona_id,version_no,state,snapshot_json,source,created_at) VALUES (?,?,?,?,?,?,?)",
                (uuid.uuid4().hex, persona_id, 1, "draft", json.dumps(snapshot, ensure_ascii=False, sort_keys=True), "created", created_at),
            ),
        ])
        return PersonaRepository.get(persona_id)

    @staticmethod
    def freeze(persona_id: str, frozen_at: str):
        version = PersonaRepository.current_version(persona_id)
        if not version:
            return None
        if version["state"] != "frozen":
            db.write_many([
                (
                    "UPDATE persona_versions SET state='frozen', frozen_at=? WHERE id=?",
                    (frozen_at, version["id"]),
                ),
                (
                    "UPDATE personas SET identity_locked=1, identity_version=?, locked_at=? WHERE id=?",
                    (version["version_no"], frozen_at, persona_id),
                ),
            ])
        return PersonaRepository.version(persona_id, version["id"])


class ReferencePackRepository:
    @staticmethod
    def list(persona_id: str):
        packs = db.all_rows(
            "SELECT * FROM reference_packs WHERE persona_id=? ORDER BY created_at, pack_type",
            (persona_id,),
        )
        for pack in packs:
            pack["items"] = db.all_rows(
                "SELECT reference_pack_items.*, assets.kind AS asset_kind, assets.review AS asset_review, "
                "assets.persona_version_id AS asset_persona_version_id, assets.filename AS asset_filename "
                "FROM reference_pack_items LEFT JOIN assets ON assets.id=reference_pack_items.asset_id "
                "WHERE reference_pack_items.pack_id=? ORDER BY reference_pack_items.created_at, reference_pack_items.id",
                (pack["id"],),
            )
        return packs

    @staticmethod
    def get(persona_id: str, pack_id: str):
        pack = db.row(
            "SELECT * FROM reference_packs WHERE id=? AND persona_id=?",
            (pack_id, persona_id),
        )
        if not pack:
            return None
        pack["items"] = db.all_rows(
            "SELECT reference_pack_items.*, assets.kind AS asset_kind, assets.review AS asset_review, "
            "assets.persona_version_id AS asset_persona_version_id, assets.filename AS asset_filename "
            "FROM reference_pack_items LEFT JOIN assets ON assets.id=reference_pack_items.asset_id "
            "WHERE reference_pack_items.pack_id=? ORDER BY reference_pack_items.created_at, reference_pack_items.id",
            (pack_id,),
        )
        return pack

    @staticmethod
    def review_pack(*, persona_id: str, pack_id: str, review: str, rights_confirmed: bool | None, reviewed_at: str):
        if review not in {"approved", "rejected", "pending"}:
            raise ValueError("Review must be approved, rejected, or pending")
        pack = ReferencePackRepository.get(persona_id, pack_id)
        if not pack:
            raise LookupError("Reference pack not found")
        if rights_confirmed is not None:
            db.write(
                "UPDATE reference_pack_items SET rights_confirmed=? WHERE pack_id=?",
                (int(rights_confirmed), pack_id),
            )
            pack = ReferencePackRepository.get(persona_id, pack_id)
        if review == "approved":
            if not pack["items"]:
                raise ValueError("A reference pack must contain at least one item before approval")
            if any(item["review"] != "approved" for item in pack["items"]):
                raise ValueError("Approve every reference-pack item before approving the pack")
            if any(not item["rights_confirmed"] for item in pack["items"]):
                raise ValueError("Confirm rights for every reference-pack item before approving the pack")
        db.write_many([
            (
                "UPDATE reference_packs SET review=?, reviewed_at=? WHERE id=? AND persona_id=?",
                (review, reviewed_at, pack_id, persona_id),
            ),
            *([(
                "UPDATE reference_packs SET canonical_selected=0 WHERE id=? AND persona_id=?",
                (pack_id, persona_id),
            ), (
                "UPDATE reference_pack_items SET canonical_selected=0 WHERE pack_id=?",
                (pack_id,),
            )] if review != "approved" else []),
        ])
        return ReferencePackRepository.get(persona_id, pack_id)

    @staticmethod
    def review_item(*, persona_id: str, pack_id: str, item_id: str, review: str, rights_confirmed: bool | None, reviewed_at: str):
        if review not in {"approved", "rejected", "pending"}:
            raise ValueError("Review must be approved, rejected, or pending")
        pack = ReferencePackRepository.get(persona_id, pack_id)
        if not pack:
            raise LookupError("Reference pack not found")
        item = next((item for item in pack["items"] if item["id"] == item_id), None)
        if not item:
            raise LookupError("Reference pack item not found")
        effective_rights = item["rights_confirmed"] if rights_confirmed is None else int(rights_confirmed)
        if review == "approved" and not effective_rights:
            raise ValueError("Confirm rights for the reference-pack item before approval")
        statements = [(
            "UPDATE reference_pack_items SET review=?, rights_confirmed=?, reviewed_at=? WHERE id=? AND pack_id=?",
            (review, effective_rights, reviewed_at, item_id, pack_id),
        )]
        if review != "approved" or not effective_rights:
            statements.extend([
                ("UPDATE reference_packs SET review='pending', canonical_selected=0 WHERE id=? AND persona_id=?", (pack_id, persona_id)),
                ("UPDATE reference_pack_items SET canonical_selected=0 WHERE pack_id=?", (pack_id,)),
            ])
        db.write_many(statements)
        return ReferencePackRepository.get(persona_id, pack_id)

    @staticmethod
    def link_asset(*, persona_id: str, pack_id: str, item_id: str, asset_id: str):
        pack = ReferencePackRepository.get(persona_id, pack_id)
        if not pack:
            raise LookupError("Reference pack not found")
        if not any(item["id"] == item_id for item in pack["items"]):
            raise LookupError("Reference pack item not found")
        asset = db.row(
            "SELECT id, persona_id, persona_version_id, kind, filename FROM assets WHERE id=? AND persona_id=?",
            (asset_id, persona_id),
        )
        if not asset:
            raise LookupError("Asset not found for this persona")
        if asset["kind"] != "image":
            raise ValueError("Only image assets can be linked as reference-pack media")
        if not pack["persona_version_id"]:
            raise ValueError("Reference pack has no PersonaVersion lineage")
        if not asset["persona_version_id"]:
            raise ValueError("Asset has no PersonaVersion lineage; regenerate or explicitly re-import it under the current version")
        if asset["persona_version_id"] != pack["persona_version_id"]:
            raise ValueError("Asset PersonaVersion does not match the reference pack")
        db.write_many([
            ("UPDATE reference_pack_items SET asset_id=?, canonical_selected=0 WHERE id=? AND pack_id=?", (asset_id, item_id, pack_id)),
            ("UPDATE reference_packs SET canonical_selected=0 WHERE id=? AND persona_id=?", (pack_id, persona_id)),
        ])
        return ReferencePackRepository.get(persona_id, pack_id)

    @staticmethod
    def select_canonical(*, persona_id: str, pack_id: str, selected: bool, item_ids: list[str]):
        pack = ReferencePackRepository.get(persona_id, pack_id)
        if not pack:
            raise LookupError("Reference pack not found")
        if not selected:
            db.write_many([
                ("UPDATE reference_packs SET canonical_selected=0 WHERE id=? AND persona_id=?", (pack_id, persona_id)),
                ("UPDATE reference_pack_items SET canonical_selected=0 WHERE pack_id=?", (pack_id,)),
            ])
            return ReferencePackRepository.get(persona_id, pack_id)
        item_ids = list(dict.fromkeys(item_ids))
        if not item_ids:
            raise ValueError("Select at least one pack item as a canonical anchor")
        if pack["review"] != "approved" or not pack["canonical_eligible"]:
            raise ValueError("Approve the eligible reference pack before selecting canonical anchors")
        items = {item["id"]: item for item in pack["items"]}
        if any(item_id not in items for item_id in item_ids):
            raise ValueError("Every canonical item must belong to the selected reference pack")
        for item_id in item_ids:
            item = items[item_id]
            if item["review"] != "approved" or not item["rights_confirmed"]:
                raise ValueError("Canonical items must be approved and rights-confirmed")
            if not item["canonical_eligible"] or not item["asset_id"]:
                raise ValueError("Canonical items must be eligible and linked to a media asset")
            asset = db.row(
                "SELECT id, persona_version_id, kind, review, rights_confirmed, filename FROM assets WHERE id=? AND persona_id=?",
                (item["asset_id"], persona_id),
            )
            if not asset or asset["kind"] != "image" or asset["review"] != "approved" or not asset["rights_confirmed"]:
                raise ValueError("Every canonical item requires an approved, rights-confirmed image asset")
            if not pack["persona_version_id"] or asset["persona_version_id"] != pack["persona_version_id"]:
                raise ValueError("Canonical asset and reference pack must share the same PersonaVersion")
            if not (db.OUTPUTS / asset["filename"]).is_file():
                raise ValueError("Canonical asset file is missing from local media storage")
        with db.connection() as con:
            con.execute("UPDATE reference_pack_items SET canonical_selected=0 WHERE pack_id=?", (pack_id,))
            placeholders = ",".join("?" for _ in item_ids)
            con.execute(
                f"UPDATE reference_pack_items SET canonical_selected=1 WHERE pack_id=? AND id IN ({placeholders})",
                (pack_id, *item_ids),
            )
            con.execute("UPDATE reference_packs SET canonical_selected=1 WHERE id=? AND persona_id=?", (pack_id, persona_id))
        return ReferencePackRepository.get(persona_id, pack_id)

    @staticmethod
    def invalidate_canonical_for_asset(asset_id: str):
        db.write_many([
            ("UPDATE reference_pack_items SET canonical_selected=0 WHERE asset_id=?", (asset_id,)),
            ("UPDATE reference_packs SET canonical_selected=0 WHERE id IN (SELECT pack_id FROM reference_pack_items WHERE asset_id=?)", (asset_id,)),
        ])

    @staticmethod
    def import_legacy(*, persona_id: str, persona_version_id: str, packs: list[dict], created_at: str):
        statements = []
        imported = []
        for spec in packs:
            pack_type = spec["pack_type"]
            pack_id = uuid.uuid5(uuid.NAMESPACE_URL, f"ai-influencer-studio:{persona_id}:{persona_version_id}:{pack_type}").hex
            if not db.row("SELECT id FROM reference_packs WHERE id=?", (pack_id,)):
                statements.append((
                    "INSERT INTO reference_packs (id,persona_id,persona_version_id,pack_type,name,content_class,identity_authority,review,canonical_eligible,source,created_at,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (pack_id, persona_id, persona_version_id, pack_type, spec["name"], spec["content_class"], spec["identity_authority"], "pending", 1, "v2_json_import", created_at, json.dumps(spec.get("metadata", {}), ensure_ascii=False, sort_keys=True)),
                ))
            for index, item in enumerate(spec.get("items", [])):
                item_id = uuid.uuid5(uuid.NAMESPACE_URL, f"ai-influencer-studio:{pack_id}:{index}:{item.get('source_url', '')}").hex
                if db.row("SELECT id FROM reference_pack_items WHERE id=?", (item_id,)):
                    continue
                statements.append((
                    "INSERT INTO reference_pack_items (id,pack_id,filename,source_url,label,role,content_class,review,rights_confirmed,canonical_eligible,created_at,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (item_id, pack_id, item.get("filename"), item.get("source_url", ""), item.get("label", "Reference"), item.get("role", "supporting_reference"), spec["content_class"], "pending", 0, 1, created_at, json.dumps(item.get("metadata", {}), ensure_ascii=False, sort_keys=True)),
                ))
            imported.append(pack_id)
        if statements:
            db.write_many(statements)
        return imported

    @staticmethod
    def restore(persona_id: str, packs: list[dict]):
        statements = []
        current_version = PersonaRepository.current_version(persona_id)
        current_version_id = current_version["id"] if current_version else None
        for pack in packs:
            pack_type = pack.get("pack_type", "legacy")
            pack_id = uuid.uuid5(uuid.NAMESPACE_URL, f"ai-influencer-studio:{persona_id}:{current_version_id}:{pack_type}").hex
            raw_pack_metadata = pack.get("metadata")
            if raw_pack_metadata is None:
                raw_pack_metadata = pack.get("metadata_json", "{}")
            pack_metadata = raw_pack_metadata if isinstance(raw_pack_metadata, str) else json.dumps(raw_pack_metadata, ensure_ascii=False, sort_keys=True)
            statements.append((
                "INSERT OR REPLACE INTO reference_packs (id,persona_id,persona_version_id,pack_type,name,content_class,identity_authority,review,canonical_eligible,source,created_at,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (pack_id, persona_id, current_version_id, pack_type, pack.get("name", "Reference Pack"), pack.get("content_class", "identity"), pack.get("identity_authority", "identity"), pack.get("review", "pending"), int(bool(pack.get("canonical_eligible", 0))), pack.get("source", "archive_restore"), pack.get("created_at") or "", pack_metadata),
            ))
            for index, item in enumerate(pack.get("items", [])):
                source_url = item.get("source_url", "")
                item_id = uuid.uuid5(uuid.NAMESPACE_URL, f"ai-influencer-studio:{pack_id}:{index}:{source_url}").hex
                raw_item_metadata = item.get("metadata")
                if raw_item_metadata is None:
                    raw_item_metadata = item.get("metadata_json", "{}")
                item_metadata = raw_item_metadata if isinstance(raw_item_metadata, str) else json.dumps(raw_item_metadata, ensure_ascii=False, sort_keys=True)
                statements.append((
                    "INSERT OR REPLACE INTO reference_pack_items (id,pack_id,filename,source_url,label,role,content_class,review,rights_confirmed,canonical_eligible,created_at,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (item_id, pack_id, item.get("filename"), source_url, item.get("label", "Reference"), item.get("role", "supporting_reference"), item.get("content_class", pack.get("content_class", "identity")), item.get("review", "pending"), int(bool(item.get("rights_confirmed", 0))), int(bool(item.get("canonical_eligible", 0))), item.get("created_at") or "", item_metadata),
                ))
        if statements:
            db.write_many(statements)

    @staticmethod
    def delete_for_persona(persona_id: str):
        db.write_many([
            ("DELETE FROM reference_pack_items WHERE pack_id IN (SELECT id FROM reference_packs WHERE persona_id=?)", (persona_id,)),
            ("DELETE FROM reference_packs WHERE persona_id=?", (persona_id,)),
        ])


class SeriesRepository:
    @staticmethod
    def create(*, series_id: str, persona_id: str, persona_version_id: str | None, title: str, description: str, shared_prompt: str, created_at: str, episodes: list[tuple]):
        statements = [(
            "INSERT INTO series (id,persona_id,persona_version_id,title,description,shared_prompt,status,created_at) VALUES (?,?,?,?,?,?,?,?)",
            (series_id, persona_id, persona_version_id, title, description, shared_prompt, "planned", created_at),
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


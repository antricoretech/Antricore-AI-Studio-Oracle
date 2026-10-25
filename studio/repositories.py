"""Small persistence boundary for route handlers.

This is deliberately a light repository layer rather than a new ORM. SQLite is
still the right fit for a single local/cloud worker, while keeping SQL out of
the orchestration paths makes the next storage migration straightforward.
"""

from __future__ import annotations

import json
import uuid

from . import database as db
from .identity_conditioning import (
    BENCHMARK_STATUSES,
    CASE_STATUSES,
    normalize_selection,
    summarize_cases,
    validate_completed_metrics,
    validate_metrics,
)

ADULT_GLAMOUR_CONTENT_CLASSES = frozenset({
    "adult_glamour",
    "lingerie",
    "boudoir",
    "nude_editorial",
})


def is_adult_glamour_content_class(content_class: str) -> bool:
    return content_class.strip().lower() in ADULT_GLAMOUR_CONTENT_CLASSES


class CreatorProfileRepository:
    JSON_FIELDS = ("personality_json", "audience_json", "content_pillars_json", "brand_json", "voice_json", "metadata_json")

    @staticmethod
    def _decode(profile: dict | None):
        if not profile:
            return None
        result = dict(profile)
        for field in CreatorProfileRepository.JSON_FIELDS:
            raw = result.pop(field, "{}")
            try:
                result[field.removesuffix("_json")] = json.loads(raw or ("[]" if field == "content_pillars_json" else "{}"))
            except (TypeError, json.JSONDecodeError):
                result[field.removesuffix("_json")] = [] if field == "content_pillars_json" else {}
        return result

    @staticmethod
    def get(persona_id: str, persona_version_id: str | None = None):
        version = PersonaRepository.version(persona_id, persona_version_id) if persona_version_id else PersonaRepository.current_version(persona_id)
        if not version:
            return None
        return CreatorProfileRepository._decode(db.row(
            "SELECT * FROM creator_profiles WHERE persona_id=? AND persona_version_id=?",
            (persona_id, version["id"]),
        ))

    @staticmethod
    def _normalize_pillars(pillars: list[dict]) -> list[dict]:
        normalized = []
        for index, raw in enumerate(pillars):
            name = str(raw.get("name") or "").strip()
            if len(name) < 2:
                raise ValueError("Every content pillar requires a name")
            content_classes = list(dict.fromkeys(
                str(value).strip().lower() for value in (raw.get("content_classes") or ["identity"]) if str(value).strip()
            )) or ["identity"]
            adult_glamour = any(is_adult_glamour_content_class(value) for value in content_classes)
            identity_authority = str(raw.get("identity_authority") or "style").strip().lower()
            if identity_authority not in {"identity", "style", "identity_and_style"}:
                raise ValueError(f"Unsupported identity authority for content pillar '{name}'")
            if adult_glamour:
                identity_authority = "identity_and_style"
            key = str(raw.get("key") or "").strip().lower()
            if not key:
                key = "".join(character if character.isalnum() else "_" for character in name).strip("_").lower()[:80]
            normalized.append({
                "key": key or f"pillar_{index + 1}",
                "name": name,
                "description": str(raw.get("description") or "").strip()[:500],
                "formats": list(dict.fromkeys(str(value).strip() for value in (raw.get("formats") or []) if str(value).strip()))[:12],
                "content_classes": content_classes[:12],
                "identity_authority": identity_authority,
                "identity_core": bool(raw.get("identity_core")) or adult_glamour,
                "audience_goal": str(raw.get("audience_goal") or "").strip()[:300],
                "style_directives": dict(raw.get("style_directives") or {}),
                "metadata": dict(raw.get("metadata") or {}),
            })
        return normalized

    @staticmethod
    def upsert(*, persona_id: str, persona_version_id: str | None, personality: dict,
               audience: dict, content_pillars: list[dict], brand: dict, voice: dict,
               disclosure: str, metadata: dict, updated_at: str):
        version = PersonaRepository.version(persona_id, persona_version_id) if persona_version_id else PersonaRepository.current_version(persona_id)
        if not version:
            raise LookupError("PersonaVersion not found")
        if version["state"] != "draft":
            raise ValueError("Create a new draft PersonaVersion before editing the Creator Profile")
        disclosure = disclosure.strip()
        if len(disclosure) < 20:
            raise ValueError("Creator Profile disclosure must be at least 20 characters")
        normalized_pillars = CreatorProfileRepository._normalize_pillars(content_pillars)
        existing = db.row(
            "SELECT id, created_at FROM creator_profiles WHERE persona_id=? AND persona_version_id=?",
            (persona_id, version["id"]),
        )
        profile_id = existing["id"] if existing else uuid.uuid4().hex
        created_at = existing["created_at"] if existing else updated_at
        db.write(
            "INSERT INTO creator_profiles "
            "(id,persona_id,persona_version_id,status,personality_json,audience_json,content_pillars_json,brand_json,voice_json,disclosure,metadata_json,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(persona_version_id) DO UPDATE SET status=excluded.status, personality_json=excluded.personality_json, "
            "audience_json=excluded.audience_json, content_pillars_json=excluded.content_pillars_json, brand_json=excluded.brand_json, "
            "voice_json=excluded.voice_json, disclosure=excluded.disclosure, metadata_json=excluded.metadata_json, updated_at=excluded.updated_at",
            (
                profile_id, persona_id, version["id"], "draft",
                json.dumps(dict(personality or {}), ensure_ascii=False, sort_keys=True),
                json.dumps(dict(audience or {}), ensure_ascii=False, sort_keys=True),
                json.dumps(normalized_pillars, ensure_ascii=False, sort_keys=True),
                json.dumps(dict(brand or {}), ensure_ascii=False, sort_keys=True),
                json.dumps(dict(voice or {}), ensure_ascii=False, sort_keys=True),
                disclosure, json.dumps(dict(metadata or {}), ensure_ascii=False, sort_keys=True),
                created_at, updated_at,
            ),
        )
        return CreatorProfileRepository.get(persona_id, version["id"])


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
    def resolve_canonical_asset(persona_id: str, persona_version_id: str | None = None):
        sql = (
            "SELECT assets.*, reference_packs.id AS reference_pack_id, reference_packs.pack_type AS reference_pack_type, "
            "reference_packs.content_class AS reference_content_class "
            "FROM reference_pack_items "
            "JOIN reference_packs ON reference_packs.id=reference_pack_items.pack_id "
            "JOIN assets ON assets.id=reference_pack_items.asset_id "
            "WHERE reference_packs.persona_id=? AND reference_packs.review='approved' "
            "AND reference_packs.canonical_selected=1 AND reference_pack_items.canonical_selected=1 "
            "AND reference_pack_items.review='approved' AND reference_pack_items.rights_confirmed=1 "
            "AND assets.kind='image' AND assets.review='approved' AND assets.rights_confirmed=1"
        )
        args: list[str] = [persona_id]
        if persona_version_id:
            sql += " AND reference_packs.persona_version_id=? AND assets.persona_version_id=?"
            args.extend([persona_version_id, persona_version_id])
        sql += " ORDER BY CASE WHEN reference_packs.content_class='adult_glamour' THEN 0 ELSE 1 END, reference_pack_items.created_at DESC LIMIT 1"
        return db.row(sql, tuple(args))

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


class ContentPackRepository:
    @staticmethod
    def _decode(pack: dict | None):
        if not pack:
            return None
        result = dict(pack)
        for field in ("style_json", "metadata_json"):
            raw = result.pop(field, "{}")
            try:
                result[field.removesuffix("_json")] = json.loads(raw or "{}")
            except (TypeError, json.JSONDecodeError):
                result[field.removesuffix("_json")] = {}
        result["items"] = db.all_rows(
            "SELECT content_pack_items.*, reference_pack_items.role AS reference_role, "
            "assets.kind AS asset_kind, assets.review AS asset_review, assets.persona_version_id AS asset_persona_version_id, "
            "assets.filename AS asset_filename "
            "FROM content_pack_items "
            "JOIN reference_pack_items ON reference_pack_items.id=content_pack_items.reference_pack_item_id "
            "JOIN assets ON assets.id=content_pack_items.asset_id "
            "WHERE content_pack_items.content_pack_id=? ORDER BY content_pack_items.created_at, content_pack_items.id",
            (result["id"],),
        )
        return result

    @staticmethod
    def list(persona_id: str):
        return [ContentPackRepository._decode(row) for row in db.all_rows(
            "SELECT * FROM content_packs WHERE persona_id=? ORDER BY created_at, pack_type, name",
            (persona_id,),
        )]

    @staticmethod
    def get(persona_id: str, pack_id: str):
        return ContentPackRepository._decode(db.row(
            "SELECT * FROM content_packs WHERE id=? AND persona_id=?",
            (pack_id, persona_id),
        ))

    @staticmethod
    def _validate_source(*, persona_id: str, persona_version_id: str, reference_pack_id: str, item_ids: list[str]):
        source = ReferencePackRepository.get(persona_id, reference_pack_id)
        if not source:
            raise LookupError("Reference pack not found")
        if source["persona_version_id"] != persona_version_id:
            raise ValueError("Reference pack and ContentPack must share the same PersonaVersion")
        if source["review"] != "approved" or not source["canonical_selected"]:
            raise ValueError("ContentPack requires an approved reference pack with selected canonical anchors")
        canonical_items = {
            item["id"]: item for item in source["items"]
            if item["canonical_selected"] and item["review"] == "approved" and item["rights_confirmed"] and item["asset_id"]
        }
        selected_ids = list(dict.fromkeys(item_ids)) or list(canonical_items)
        if not selected_ids:
            raise ValueError("ContentPack requires at least one canonical reference item")
        if any(item_id not in canonical_items for item_id in selected_ids):
            raise ValueError("ContentPack items must be selected canonical items from the reference pack")
        for item_id in selected_ids:
            item = canonical_items[item_id]
            asset = db.row(
                "SELECT id, persona_version_id, kind, review, rights_confirmed, filename FROM assets WHERE id=? AND persona_id=?",
                (item["asset_id"], persona_id),
            )
            if not asset or asset["kind"] != "image" or asset["review"] != "approved" or not asset["rights_confirmed"]:
                raise ValueError("ContentPack anchors require approved, rights-confirmed image assets")
            if asset["persona_version_id"] != persona_version_id:
                raise ValueError("ContentPack anchor asset does not match the PersonaVersion")
            if not (db.OUTPUTS / asset["filename"]).is_file():
                raise ValueError("ContentPack anchor asset file is missing from local media storage")
        return source, selected_ids

    @staticmethod
    def create(*, persona_id: str, persona_version_id: str, reference_pack_id: str, pack_type: str,
               name: str, content_class: str, identity_authority: str, identity_core: bool,
               style: dict, metadata: dict, item_ids: list[str], created_at: str):
        if is_adult_glamour_content_class(content_class):
            identity_core = True
            identity_authority = "identity_and_style"
        if identity_authority not in {"identity", "style", "identity_and_style"}:
            raise ValueError("Unsupported ContentPack identity authority")
        source, selected_ids = ContentPackRepository._validate_source(
            persona_id=persona_id, persona_version_id=persona_version_id,
            reference_pack_id=reference_pack_id, item_ids=item_ids,
        )
        if is_adult_glamour_content_class(content_class) and not is_adult_glamour_content_class(source["content_class"]):
            raise ValueError("Adult/glamour ContentPacks must use an adult/glamour reference pack")
        content_pack_id = uuid.uuid4().hex
        statements = [(
            "INSERT INTO content_packs (id,persona_id,persona_version_id,reference_pack_id,pack_type,name,content_class,identity_authority,identity_core,review,created_at,style_json,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (content_pack_id, persona_id, persona_version_id, reference_pack_id, pack_type, name, content_class, identity_authority, int(identity_core), "pending", created_at, json.dumps(style, ensure_ascii=False, sort_keys=True), json.dumps(metadata, ensure_ascii=False, sort_keys=True)),
        )]
        source_items = {item["id"]: item for item in source["items"]}
        for item_id in selected_ids:
            item = source_items[item_id]
            statements.append((
                "INSERT INTO content_pack_items (id,content_pack_id,reference_pack_item_id,asset_id,role,created_at,metadata_json) VALUES (?,?,?,?,?,?,?)",
                (uuid.uuid4().hex, content_pack_id, item_id, item["asset_id"], "canonical_anchor", created_at, json.dumps({"source": "reference_pack"}, sort_keys=True)),
            ))
        db.write_many(statements)
        return ContentPackRepository.get(persona_id, content_pack_id)

    @staticmethod
    def review(*, persona_id: str, pack_id: str, review: str, reviewed_at: str):
        if review not in {"approved", "rejected", "pending"}:
            raise ValueError("Review must be approved, rejected, or pending")
        pack = ContentPackRepository.get(persona_id, pack_id)
        if not pack:
            raise LookupError("ContentPack not found")
        if review == "approved":
            ContentPackRepository._validate_source(
                persona_id=persona_id,
                persona_version_id=pack["persona_version_id"],
                reference_pack_id=pack["reference_pack_id"],
                item_ids=[item["reference_pack_item_id"] for item in pack["items"]],
            )
        db.write(
            "UPDATE content_packs SET review=? WHERE id=? AND persona_id=?",
            (review, pack_id, persona_id),
        )
        return ContentPackRepository.get(persona_id, pack_id)

    @staticmethod
    def resolve(persona_id: str, pack_id: str):
        pack = ContentPackRepository.get(persona_id, pack_id)
        if not pack:
            raise LookupError("ContentPack not found")
        if pack["review"] != "approved":
            raise ValueError("Approve the ContentPack before using it for generation")
        source, selected_ids = ContentPackRepository._validate_source(
            persona_id=persona_id,
            persona_version_id=pack["persona_version_id"],
            reference_pack_id=pack["reference_pack_id"],
            item_ids=[item["reference_pack_item_id"] for item in pack["items"]],
        )
        anchors = [
            {
                "reference_pack_item_id": item["reference_pack_item_id"],
                "asset_id": item["asset_id"],
                "url": f"/api/assets/{item['asset_id']}/file",
            }
            for item in pack["items"] if item["reference_pack_item_id"] in selected_ids
        ]
        return {
            "id": pack["id"],
            "persona_id": pack["persona_id"],
            "persona_version_id": pack["persona_version_id"],
            "content_class": pack["content_class"],
            "identity_authority": pack["identity_authority"],
            "identity_core": bool(pack["identity_core"]),
            "style": pack["style"],
            "anchors": anchors,
            "reference_pack_id": source["id"],
        }


class ContentBriefRepository:
    JSON_FIELDS = ("metadata_json",)
    STATUSES = frozenset({"draft", "approved", "archived"})

    @staticmethod
    def _decode(brief: dict | None):
        if not brief:
            return None
        result = dict(brief)
        raw = result.pop("metadata_json", "{}")
        try:
            result["metadata"] = json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            result["metadata"] = {}
        return result

    @staticmethod
    def list(persona_id: str):
        return [
            ContentBriefRepository._decode(row)
            for row in db.all_rows(
                "SELECT * FROM content_briefs WHERE persona_id=? ORDER BY updated_at DESC, created_at DESC",
                (persona_id,),
            )
        ]

    @staticmethod
    def get(persona_id: str, brief_id: str):
        return ContentBriefRepository._decode(db.row(
            "SELECT * FROM content_briefs WHERE id=? AND persona_id=?",
            (brief_id, persona_id),
        ))

    @staticmethod
    def _bindings(*, persona_id: str, persona_version_id: str, creator_profile_id: str | None,
                  content_pack_id: str | None, content_class: str, pillar_key: str,
                  require_approved_pack: bool = False):
        version = PersonaRepository.version(persona_id, persona_version_id)
        if not version:
            raise LookupError("PersonaVersion not found")
        profile = CreatorProfileRepository.get(persona_id, persona_version_id)
        if not profile:
            raise ValueError("Create the Creator System for this PersonaVersion before authoring a ContentBrief")
        if creator_profile_id and profile["id"] != creator_profile_id:
            raise ValueError("ContentBrief Creator Profile must match its PersonaVersion")
        pillars = profile.get("content_pillars") or []
        pillar = next((item for item in pillars if item.get("key") == pillar_key), None) if pillar_key else None
        if pillar_key and not pillar:
            raise ValueError("ContentBrief pillar_key must reference a Creator System content pillar")
        if is_adult_glamour_content_class(content_class):
            if not pillar or not any(is_adult_glamour_content_class(value) for value in pillar.get("content_classes", [])):
                raise ValueError("Adult/glamour ContentBriefs must use the adult/glamour Creator System pillar")
            if not pillar.get("identity_core") or pillar.get("identity_authority") != "identity_and_style":
                raise ValueError("Adult/glamour pillar must remain an Identity Core and style authority")
        content_pack = None
        if content_pack_id:
            content_pack = ContentPackRepository.get(persona_id, content_pack_id)
            if not content_pack:
                raise LookupError("ContentPack not found")
            if content_pack["persona_version_id"] != persona_version_id:
                raise ValueError("ContentBrief and ContentPack must share the same PersonaVersion")
            if require_approved_pack and content_pack["review"] != "approved":
                raise ValueError("Approve the selected ContentPack before approving this ContentBrief")
            if is_adult_glamour_content_class(content_class) and not is_adult_glamour_content_class(content_pack["content_class"]):
                raise ValueError("Adult/glamour ContentBriefs must use an adult/glamour ContentPack")
        return version, profile, pillar, content_pack

    @staticmethod
    def _normalized_fields(*, title: str, format: str, content_class: str, pillar_key: str,
                           audience_goal: str, emotional_objective: str, story_direction: str,
                           visual_direction: str, motion_direction: str, caption_direction: str,
                           script_direction: str, disclosure: str, metadata: dict):
        return {
            "title": title.strip(),
            "format": format.strip().lower(),
            "content_class": content_class.strip().lower(),
            "pillar_key": pillar_key.strip().lower(),
            "audience_goal": audience_goal.strip(),
            "emotional_objective": emotional_objective.strip(),
            "story_direction": story_direction.strip(),
            "visual_direction": visual_direction.strip(),
            "motion_direction": motion_direction.strip(),
            "caption_direction": caption_direction.strip(),
            "script_direction": script_direction.strip(),
            "disclosure": disclosure.strip(),
            "metadata": dict(metadata or {}),
        }

    @staticmethod
    def create(*, persona_id: str, persona_version_id: str, creator_profile_id: str | None,
               content_pack_id: str | None, title: str, format: str, content_class: str,
               pillar_key: str, audience_goal: str, emotional_objective: str, story_direction: str,
               visual_direction: str, motion_direction: str, caption_direction: str,
               script_direction: str, disclosure: str, metadata: dict, created_at: str):
        fields = ContentBriefRepository._normalized_fields(
            title=title, format=format, content_class=content_class, pillar_key=pillar_key,
            audience_goal=audience_goal, emotional_objective=emotional_objective,
            story_direction=story_direction, visual_direction=visual_direction,
            motion_direction=motion_direction, caption_direction=caption_direction,
            script_direction=script_direction, disclosure=disclosure, metadata=metadata,
        )
        if len(fields["disclosure"]) < 20:
            raise ValueError("ContentBrief disclosure must be at least 20 characters")
        _version, profile, _pillar, _pack = ContentBriefRepository._bindings(
            persona_id=persona_id, persona_version_id=persona_version_id,
            creator_profile_id=creator_profile_id, content_pack_id=content_pack_id,
            content_class=fields["content_class"], pillar_key=fields["pillar_key"],
        )
        brief_id = uuid.uuid4().hex
        db.write(
            "INSERT INTO content_briefs (id,persona_id,persona_version_id,creator_profile_id,content_pack_id,title,status,format,content_class,pillar_key,audience_goal,emotional_objective,story_direction,visual_direction,motion_direction,caption_direction,script_direction,disclosure,metadata_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                brief_id, persona_id, persona_version_id, profile["id"], content_pack_id,
                fields["title"], "draft", fields["format"], fields["content_class"],
                fields["pillar_key"], fields["audience_goal"], fields["emotional_objective"],
                fields["story_direction"], fields["visual_direction"], fields["motion_direction"],
                fields["caption_direction"], fields["script_direction"], fields["disclosure"],
                json.dumps(fields["metadata"], ensure_ascii=False, sort_keys=True), created_at, created_at,
            ),
        )
        return ContentBriefRepository.get(persona_id, brief_id)

    @staticmethod
    def update(*, persona_id: str, brief_id: str, creator_profile_id: str | None,
               content_pack_id: str | None, title: str, format: str, content_class: str,
               pillar_key: str, audience_goal: str, emotional_objective: str, story_direction: str,
               visual_direction: str, motion_direction: str, caption_direction: str,
               script_direction: str, disclosure: str, metadata: dict, updated_at: str):
        existing = ContentBriefRepository.get(persona_id, brief_id)
        if not existing:
            raise LookupError("ContentBrief not found")
        if existing["status"] != "draft":
            raise ValueError("Approved or archived ContentBriefs are immutable; create a new draft")
        fields = ContentBriefRepository._normalized_fields(
            title=title, format=format, content_class=content_class, pillar_key=pillar_key,
            audience_goal=audience_goal, emotional_objective=emotional_objective,
            story_direction=story_direction, visual_direction=visual_direction,
            motion_direction=motion_direction, caption_direction=caption_direction,
            script_direction=script_direction, disclosure=disclosure, metadata=metadata,
        )
        if len(fields["disclosure"]) < 20:
            raise ValueError("ContentBrief disclosure must be at least 20 characters")
        _version, profile, _pillar, _pack = ContentBriefRepository._bindings(
            persona_id=persona_id, persona_version_id=existing["persona_version_id"],
            creator_profile_id=creator_profile_id or existing["creator_profile_id"],
            content_pack_id=content_pack_id, content_class=fields["content_class"],
            pillar_key=fields["pillar_key"],
        )
        db.write(
            "UPDATE content_briefs SET creator_profile_id=?, content_pack_id=?, title=?, revision=revision+1, format=?, content_class=?, pillar_key=?, audience_goal=?, emotional_objective=?, story_direction=?, visual_direction=?, motion_direction=?, caption_direction=?, script_direction=?, disclosure=?, metadata_json=?, updated_at=? WHERE id=? AND persona_id=? AND status='draft'",
            (
                profile["id"], content_pack_id, fields["title"], fields["format"], fields["content_class"],
                fields["pillar_key"], fields["audience_goal"], fields["emotional_objective"],
                fields["story_direction"], fields["visual_direction"], fields["motion_direction"],
                fields["caption_direction"], fields["script_direction"], fields["disclosure"],
                json.dumps(fields["metadata"], ensure_ascii=False, sort_keys=True), updated_at,
                brief_id, persona_id,
            ),
        )
        return ContentBriefRepository.get(persona_id, brief_id)

    @staticmethod
    def approve(*, persona_id: str, brief_id: str, reviewed_at: str):
        brief = ContentBriefRepository.get(persona_id, brief_id)
        if not brief:
            raise LookupError("ContentBrief not found")
        if brief["status"] == "archived":
            raise ValueError("Archived ContentBriefs cannot be approved")
        version, _profile, _pillar, _pack = ContentBriefRepository._bindings(
            persona_id=persona_id, persona_version_id=brief["persona_version_id"],
            creator_profile_id=brief["creator_profile_id"], content_pack_id=brief["content_pack_id"],
            content_class=brief["content_class"], pillar_key=brief["pillar_key"],
            require_approved_pack=True,
        )
        if version["state"] != "frozen":
            raise ValueError("Freeze the PersonaVersion before approving a ContentBrief")
        if not brief["story_direction"] and not brief["visual_direction"]:
            raise ValueError("ContentBrief needs story or visual direction before approval")
        db.write(
            "UPDATE content_briefs SET status='approved', updated_at=? WHERE id=? AND persona_id=?",
            (reviewed_at, brief_id, persona_id),
        )
        return ContentBriefRepository.get(persona_id, brief_id)

    @staticmethod
    def resolve(persona_id: str, brief_id: str):
        brief = ContentBriefRepository.get(persona_id, brief_id)
        if not brief:
            raise LookupError("ContentBrief not found")
        if brief["status"] != "approved":
            raise ValueError("Approve the ContentBrief before handing it to production")
        version, profile, pillar, content_pack = ContentBriefRepository._bindings(
            persona_id=persona_id, persona_version_id=brief["persona_version_id"],
            creator_profile_id=brief["creator_profile_id"], content_pack_id=brief["content_pack_id"],
            content_class=brief["content_class"], pillar_key=brief["pillar_key"],
            require_approved_pack=True,
        )
        if version["state"] != "frozen":
            raise ValueError("ContentBrief production handoff requires a frozen PersonaVersion")
        approved_artifacts = [
            {
                "id": artifact["id"],
                "artifact_type": artifact["artifact_type"],
                "status": artifact["status"],
                "revision": artifact["revision"],
                "content": artifact["content"],
                "disclosure": artifact["disclosure"],
                "source": artifact["source"],
                "quality": artifact.get("quality") or {},
                "persona_version_id": artifact["persona_version_id"],
                "content_brief_id": artifact["content_brief_id"],
            }
            for artifact in ContentArtifactRepository.list_for_brief(persona_id, brief_id)
            if artifact["status"] == "approved"
        ]
        return {
            "id": brief["id"],
            "persona_id": persona_id,
            "persona_version_id": version["id"],
            "status": brief["status"],
            "brief": brief,
            "creator_profile": profile,
            "content_pillar": pillar,
            "content_pack": ContentPackRepository.resolve(persona_id, content_pack["id"]) if content_pack else None,
            "content_artifacts": approved_artifacts,
            "production_handoff": {
                "format": brief["format"],
                "content_class": brief["content_class"],
                "audience_goal": brief["audience_goal"],
                "emotional_objective": brief["emotional_objective"],
                "story_direction": brief["story_direction"],
                "visual_direction": brief["visual_direction"],
                "motion_direction": brief["motion_direction"],
                "caption_direction": brief["caption_direction"],
                "script_direction": brief["script_direction"],
                "disclosure": brief["disclosure"],
            },
        }


class ContentArtifactRepository:
    ARTIFACT_TYPES = frozenset({"caption", "script"})
    STATUSES = frozenset({"draft", "approved", "rejected", "archived"})

    @staticmethod
    def _decode(artifact: dict | None):
        if not artifact:
            return None
        result = dict(artifact)
        raw = result.pop("metadata_json", "{}")
        try:
            result["metadata"] = json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            result["metadata"] = {}
        quality_raw = result.pop("quality_json", "{}")
        try:
            result["quality"] = json.loads(quality_raw or "{}")
        except (TypeError, json.JSONDecodeError):
            result["quality"] = {}
        return result

    @staticmethod
    def list(persona_id: str):
        return [
            ContentArtifactRepository._decode(row)
            for row in db.all_rows(
                "SELECT * FROM content_artifacts WHERE persona_id=? ORDER BY updated_at DESC, created_at DESC",
                (persona_id,),
            )
        ]

    @staticmethod
    def list_for_brief(persona_id: str, brief_id: str):
        return [
            ContentArtifactRepository._decode(row)
            for row in db.all_rows(
                "SELECT * FROM content_artifacts WHERE persona_id=? AND content_brief_id=? ORDER BY artifact_type, updated_at DESC",
                (persona_id, brief_id),
            )
        ]

    @staticmethod
    def get(persona_id: str, artifact_id: str):
        return ContentArtifactRepository._decode(db.row(
            "SELECT * FROM content_artifacts WHERE id=? AND persona_id=?",
            (artifact_id, persona_id),
        ))

    @staticmethod
    def _template(brief: dict, artifact_type: str):
        if artifact_type == "caption":
            return "\n\n".join(filter(None, [
                "[Caption draft template]",
                brief["caption_direction"],
                f"Audience objective: {brief['audience_goal']}" if brief["audience_goal"] else "",
                f"Emotional objective: {brief['emotional_objective']}" if brief["emotional_objective"] else "",
                f"Disclosure: {brief['disclosure']}",
            ]))
        return "\n\n".join(filter(None, [
            "[Script draft template]",
            f"Opening / hook: {brief['story_direction']}" if brief["story_direction"] else "",
            f"Visual direction: {brief['visual_direction']}" if brief["visual_direction"] else "",
            f"Motion and delivery: {brief['motion_direction']}" if brief["motion_direction"] else "",
            f"Emotional objective: {brief['emotional_objective']}" if brief["emotional_objective"] else "",
            f"Disclosure: {brief['disclosure']}",
        ]))

    @staticmethod
    def _validate_type(artifact_type: str):
        artifact_type = artifact_type.strip().lower()
        if artifact_type not in ContentArtifactRepository.ARTIFACT_TYPES:
            raise ValueError("Content artifact type must be caption or script")
        return artifact_type

    @staticmethod
    def _quality(artifact: dict, evaluated_at: str):
        checks = []

        def add(key: str, status: str, detail: str):
            checks.append({"key": key, "status": status, "detail": detail})

        content = (artifact.get("content") or "").strip()
        if content:
            add("content_present", "passed", "Artifact contains reviewable copy.")
        else:
            add("content_present", "failed", "Artifact copy cannot be empty.")

        disclosure = (artifact.get("disclosure") or "").strip()
        if len(disclosure) >= 20:
            add("disclosure", "passed", "Disclosure metadata is present.")
        else:
            add("disclosure", "failed", "Disclosure metadata must contain at least 20 characters.")

        resolved = None
        try:
            resolved = ContentBriefRepository.resolve(artifact["persona_id"], artifact["content_brief_id"])
            if resolved["persona_version_id"] == artifact["persona_version_id"]:
                add("lineage", "passed", "Approved ContentBrief and PersonaVersion lineage are aligned.")
            else:
                add("lineage", "failed", "Artifact PersonaVersion no longer matches its approved ContentBrief.")
        except (LookupError, ValueError) as exc:
            add("lineage", "failed", str(exc))

        if artifact.get("source") == "deterministic_template" or any(
            token in content for token in ("[Caption draft template]", "[Script draft template]", "TODO", "{{", "}}")
        ):
            add("operator_review", "warning", "Template or placeholder markers remain; complete human copy review before publishing.")
        else:
            add("operator_review", "passed", "No template or placeholder markers were detected.")

        limit = 2200 if artifact.get("artifact_type") == "caption" else 5000
        if len(content) <= limit:
            add("length", "passed", f"Copy is within the {limit}-character {artifact.get('artifact_type')} limit.")
        else:
            add("length", "warning", f"Copy exceeds the {limit}-character {artifact.get('artifact_type')} limit and needs editing.")

        if resolved and is_adult_glamour_content_class(resolved["brief"]["content_class"]):
            pillar = resolved.get("content_pillar") or {}
            if pillar.get("identity_core") and pillar.get("identity_authority") == "identity_and_style":
                add("adult_identity_core", "passed", "Adult/glamour content remains bound to Identity Core and style authority.")
            else:
                add("adult_identity_core", "failed", "Adult/glamour content must retain Identity Core and identity_and_style authority.")

        status = "failed" if any(item["status"] == "failed" for item in checks) else (
            "needs_review" if any(item["status"] == "warning" for item in checks) else "passed"
        )
        return {
            "status": status,
            "checks": checks,
            "evaluated_at": evaluated_at,
            "blocking": status == "failed",
        }

    @staticmethod
    def assess(*, persona_id: str, artifact_id: str, evaluated_at: str):
        artifact = ContentArtifactRepository.get(persona_id, artifact_id)
        if not artifact:
            raise LookupError("Content artifact not found")
        quality = ContentArtifactRepository._quality(artifact, evaluated_at)
        db.write(
            "UPDATE content_artifacts SET quality_status=?, quality_json=?, updated_at=? WHERE id=? AND persona_id=?",
            (quality["status"], json.dumps(quality, ensure_ascii=False, sort_keys=True), evaluated_at, artifact_id, persona_id),
        )
        return ContentArtifactRepository.get(persona_id, artifact_id)

    @staticmethod
    def create(*, persona_id: str, brief_id: str, artifact_type: str, content: str,
               metadata: dict, created_at: str):
        artifact_type = ContentArtifactRepository._validate_type(artifact_type)
        resolved = ContentBriefRepository.resolve(persona_id, brief_id)
        brief = resolved["brief"]
        existing = db.row(
            "SELECT id FROM content_artifacts WHERE persona_id=? AND content_brief_id=? AND artifact_type=? AND status <> 'archived'",
            (persona_id, brief_id, artifact_type),
        )
        if existing:
            raise ValueError(f"A non-archived {artifact_type} artifact already exists for this ContentBrief")
        operator_content = content.strip()
        content = operator_content or ContentArtifactRepository._template(brief, artifact_type)
        if not content:
            raise ValueError("Content artifact cannot be empty")
        artifact_id = uuid.uuid4().hex
        db.write(
            "INSERT INTO content_artifacts (id,persona_id,persona_version_id,content_brief_id,artifact_type,status,revision,content,disclosure,source,quality_status,quality_json,metadata_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                artifact_id, persona_id, resolved["persona_version_id"], brief_id, artifact_type,
                "draft", 1, content, brief["disclosure"],
                "operator" if operator_content else "deterministic_template", "pending", "{}",
                json.dumps(dict(metadata or {}), ensure_ascii=False, sort_keys=True), created_at, created_at,
            ),
        )
        return ContentArtifactRepository.assess(persona_id=persona_id, artifact_id=artifact_id, evaluated_at=created_at)

    @staticmethod
    def update(*, persona_id: str, artifact_id: str, content: str, metadata: dict, updated_at: str):
        artifact = ContentArtifactRepository.get(persona_id, artifact_id)
        if not artifact:
            raise LookupError("Content artifact not found")
        if artifact["status"] != "draft":
            raise ValueError("Approved, rejected, or archived content artifacts are immutable")
        content = content.strip()
        if not content:
            raise ValueError("Content artifact cannot be empty")
        db.write(
            "UPDATE content_artifacts SET revision=revision+1, content=?, source='operator', quality_status='pending', quality_json='{}', metadata_json=?, updated_at=? WHERE id=? AND persona_id=? AND status='draft'",
            (content, json.dumps(dict(metadata or {}), ensure_ascii=False, sort_keys=True), updated_at, artifact_id, persona_id),
        )
        return ContentArtifactRepository.assess(persona_id=persona_id, artifact_id=artifact_id, evaluated_at=updated_at)

    @staticmethod
    def review(*, persona_id: str, artifact_id: str, review: str, reviewed_at: str):
        if review not in {"approved", "rejected", "pending"}:
            raise ValueError("Artifact review must be approved, rejected, or pending")
        artifact = ContentArtifactRepository.get(persona_id, artifact_id)
        if not artifact:
            raise LookupError("Content artifact not found")
        if review == "approved":
            artifact = ContentArtifactRepository.assess(persona_id=persona_id, artifact_id=artifact_id, evaluated_at=reviewed_at)
            if artifact["quality_status"] == "failed":
                failed = next((item["detail"] for item in artifact["quality"].get("checks", []) if item["status"] == "failed"), "Content artifact quality check failed")
                raise ValueError(f"Resolve content artifact quality failure before approval: {failed}")
        db.write(
            "UPDATE content_artifacts SET status=?, updated_at=? WHERE id=? AND persona_id=?",
            (review, reviewed_at, artifact_id, persona_id),
        )
        return ContentArtifactRepository.get(persona_id, artifact_id)

    @staticmethod
    def resolve(persona_id: str, artifact_id: str):
        artifact = ContentArtifactRepository.get(persona_id, artifact_id)
        if not artifact:
            raise LookupError("Content artifact not found")
        if artifact["status"] != "approved":
            raise ValueError("Approve the content artifact before using it downstream")
        brief = ContentBriefRepository.resolve(persona_id, artifact["content_brief_id"])
        if brief["persona_version_id"] != artifact["persona_version_id"]:
            raise ValueError("Content artifact lineage is stale")
        if artifact.get("quality_status") == "failed":
            raise ValueError("Content artifact quality check failed")
        return {
            "id": artifact["id"],
            "persona_id": artifact["persona_id"],
            "persona_version_id": artifact["persona_version_id"],
            "content_brief_id": artifact["content_brief_id"],
            "artifact_type": artifact["artifact_type"],
            "status": artifact["status"],
            "revision": artifact["revision"],
            "content": artifact["content"],
            "disclosure": artifact["disclosure"],
            "source": artifact["source"],
            "quality": artifact.get("quality") or {},
        }


class IdentityBenchmarkRepository:
    @staticmethod
    def _decode_case(case: dict):
        result = dict(case)
        raw = result.pop("metrics_json", "{}")
        try:
            result["metrics"] = json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            result["metrics"] = {}
        return result

    @staticmethod
    def _decode(benchmark: dict | None):
        if not benchmark:
            return None
        result = dict(benchmark)
        raw = result.pop("metadata_json", "{}")
        try:
            result["metadata"] = json.loads(raw or "{}")
        except (TypeError, json.JSONDecodeError):
            result["metadata"] = {}
        result["cases"] = [
            IdentityBenchmarkRepository._decode_case(case)
            for case in db.all_rows(
                # Case IDs are UUIDs, so ordering by id makes the visible
                # benchmark sequence random when several cases share a
                # timestamp. SQLite's rowid preserves the insert order and
                # keeps the planned method/scenario matrix deterministic.
                "SELECT * FROM identity_benchmark_cases WHERE benchmark_id=? ORDER BY created_at, rowid",
                (result["id"],),
            )
        ]
        result["summary"] = summarize_cases(result["cases"])
        return result

    @staticmethod
    def list(persona_id: str):
        return [
            IdentityBenchmarkRepository._decode(row)
            for row in db.all_rows(
                "SELECT * FROM identity_benchmarks WHERE persona_id=? ORDER BY created_at DESC",
                (persona_id,),
            )
        ]

    @staticmethod
    def get(persona_id: str, benchmark_id: str):
        return IdentityBenchmarkRepository._decode(
            db.row(
                "SELECT * FROM identity_benchmarks WHERE id=? AND persona_id=?",
                (benchmark_id, persona_id),
            )
        )

    @staticmethod
    def create(*, persona_id: str, persona_version_id: str, anchor: dict,
               base_model_id: str | None, methods: list[str] | None,
               scenario_ids: list[str] | None, metadata: dict | None,
               created_at: str):
        selected_methods, scenarios = normalize_selection(methods, scenario_ids)
        benchmark_id = uuid.uuid4().hex
        benchmark_metadata = dict(metadata or {})
        benchmark_metadata.update({
            "methods": selected_methods,
            "scenarios": [scenario["id"] for scenario in scenarios],
            "execution": "deferred_until_final_model_gate",
        })
        statements = [(
            "INSERT INTO identity_benchmarks "
            "(id,persona_id,persona_version_id,anchor_asset_id,anchor_reference_pack_id,anchor_content_class,"
            "base_model_id,status,created_at,updated_at,metadata_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                benchmark_id,
                persona_id,
                persona_version_id,
                anchor["id"],
                anchor.get("reference_pack_id"),
                anchor.get("reference_content_class") or anchor.get("content_class") or "identity",
                base_model_id,
                "planned",
                created_at,
                created_at,
                json.dumps(benchmark_metadata, ensure_ascii=False, sort_keys=True),
            ),
        )]
        for method in selected_methods:
            for scenario in scenarios:
                statements.append((
                    "INSERT INTO identity_benchmark_cases "
                    "(id,benchmark_id,method,scenario_id,scenario_label,content_class,prompt,status,created_at,updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        uuid.uuid4().hex,
                        benchmark_id,
                        method,
                        scenario["id"],
                        scenario["label"],
                        scenario["content_class"],
                        scenario["prompt"],
                        "planned",
                        created_at,
                        created_at,
                    ),
                ))
        db.write_many(statements)
        return IdentityBenchmarkRepository.get(persona_id, benchmark_id)

    @staticmethod
    def record_case_result(*, persona_id: str, benchmark_id: str, case_id: str,
                           status: str, metrics: dict | None, notes: str,
                           error: str | None, output_asset_id: str | None,
                           updated_at: str):
        if status not in CASE_STATUSES:
            raise ValueError("Unsupported identity benchmark case status")
        benchmark = db.row(
            "SELECT * FROM identity_benchmarks WHERE id=? AND persona_id=?",
            (benchmark_id, persona_id),
        )
        if not benchmark:
            raise LookupError("Identity benchmark not found")
        case = db.row(
            "SELECT * FROM identity_benchmark_cases WHERE id=? AND benchmark_id=?",
            (case_id, benchmark_id),
        )
        if not case:
            raise LookupError("Identity benchmark case not found")
        normalized_metrics = validate_metrics(metrics)
        if status == "completed":
            validate_completed_metrics(normalized_metrics)
        if output_asset_id:
            asset = db.row(
                "SELECT id, persona_id, persona_version_id, kind, filename FROM assets WHERE id=? AND persona_id=?",
                (output_asset_id, persona_id),
            )
            if not asset:
                raise LookupError("Benchmark output asset not found for this persona")
            if asset["kind"] != "image":
                raise ValueError("Identity benchmark output must be an image asset")
            if asset["persona_version_id"] != benchmark["persona_version_id"]:
                raise ValueError("Benchmark output asset must match the benchmark PersonaVersion")
            if not (db.OUTPUTS / asset["filename"]).is_file():
                raise ValueError("Benchmark output asset file is missing from local media storage")
        started_at = updated_at if status == "running" and not case.get("started_at") else case.get("started_at")
        completed_at = updated_at if status in {"completed", "blocked", "failed"} else None
        db.write(
            "UPDATE identity_benchmark_cases SET status=?, output_asset_id=?, metrics_json=?, notes=?, error=?, "
            "updated_at=?, started_at=?, completed_at=? WHERE id=? AND benchmark_id=?",
            (
                status,
                output_asset_id,
                json.dumps(normalized_metrics, ensure_ascii=False, sort_keys=True),
                notes,
                error,
                updated_at,
                started_at,
                completed_at,
                case_id,
                benchmark_id,
            ),
        )
        remaining = db.row(
            "SELECT COUNT(*) AS count FROM identity_benchmark_cases WHERE benchmark_id=? AND status NOT IN ('completed','blocked','failed')",
            (benchmark_id,),
        )["count"]
        if remaining:
            benchmark_status = "in_progress" if status != "planned" else "planned"
        else:
            completed = db.row(
                "SELECT COUNT(*) AS count FROM identity_benchmark_cases WHERE benchmark_id=? AND status='completed'",
                (benchmark_id,),
            )["count"]
            benchmark_status = "completed" if completed else "blocked"
        if benchmark_status not in BENCHMARK_STATUSES:
            raise ValueError("Invalid derived identity benchmark status")
        db.write(
            "UPDATE identity_benchmarks SET status=?, updated_at=? WHERE id=? AND persona_id=?",
            (benchmark_status, updated_at, benchmark_id, persona_id),
        )
        return IdentityBenchmarkRepository.get(persona_id, benchmark_id)


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


class PublishingRepository:
    @staticmethod
    def _decode_account(row):
        if not row:
            return None
        result = dict(row)
        try:
            result["metadata"] = json.loads(result.pop("metadata_json", "{}") or "{}")
        except (TypeError, json.JSONDecodeError):
            result["metadata"] = {}
        result.pop("token_ref", None)
        return result

    @staticmethod
    def account(account_id: str, persona_id: str | None = None):
        sql = "SELECT * FROM publishing_accounts WHERE id=?"
        args = [account_id]
        if persona_id:
            sql += " AND persona_id=?"
            args.append(persona_id)
        return PublishingRepository._decode_account(db.row(sql, tuple(args)))

    @staticmethod
    def accounts(persona_id: str):
        return [PublishingRepository._decode_account(row) for row in db.all_rows(
            "SELECT * FROM publishing_accounts WHERE persona_id=? ORDER BY created_at DESC", (persona_id,)
        )]

    @staticmethod
    def create_account(*, account_id: str, persona_id: str, platform: str, account_label: str,
                       account_type: str, handle: str | None, external_account_id: str | None,
                       metadata: dict, created_at: str):
        db.write(
            "INSERT INTO publishing_accounts (id,persona_id,platform,account_label,account_type,handle,external_account_id,status,metadata_json,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (account_id, persona_id, platform, account_label, account_type, handle, external_account_id,
             "unverified", json.dumps(metadata, ensure_ascii=False), created_at, created_at),
        )
        return PublishingRepository.account(account_id, persona_id)

    @staticmethod
    def attempt(attempt_id: str):
        row = db.row("SELECT * FROM publish_attempts WHERE id=?", (attempt_id,))
        return PublishingRepository._decode_attempt(row)

    @staticmethod
    def attempt_by_key(key: str):
        row = db.row("SELECT * FROM publish_attempts WHERE idempotency_key=?", (key,))
        return PublishingRepository._decode_attempt(row)

    @staticmethod
    def _decode_attempt(row):
        if not row:
            return None
        result = dict(row)
        for field in ("request_json", "response_json"):
            try:
                result[field.removesuffix("_json")] = json.loads(result.pop(field, "{}") or "{}")
            except (TypeError, json.JSONDecodeError):
                result[field.removesuffix("_json")] = {}
        result["dry_run"] = bool(result.get("dry_run"))
        return result

    @staticmethod
    def create_attempt(*, attempt_id: str, persona_id: str, persona_version_id: str | None,
                       asset_id: str, content_artifact_id: str | None, account_id: str,
                       platform: str, format_name: str, idempotency_key: str, status: str,
                       request: dict, response: dict, error: str | None, created_at: str):
        db.write(
            "INSERT INTO publish_attempts (id,persona_id,persona_version_id,asset_id,content_artifact_id,account_id,platform,format,idempotency_key,status,dry_run,request_json,response_json,error,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (attempt_id, persona_id, persona_version_id, asset_id, content_artifact_id, account_id,
             platform, format_name, idempotency_key, status, 1, json.dumps(request, ensure_ascii=False),
             json.dumps(response, ensure_ascii=False), error, created_at, created_at),
        )
        return PublishingRepository.attempt(attempt_id)

    @staticmethod
    def _decode_auth_session(row):
        if not row:
            return None
        result = dict(row)
        try:
            result["scopes"] = json.loads(result.pop("scopes_json", "[]") or "[]")
        except (TypeError, json.JSONDecodeError):
            result["scopes"] = []
        result.pop("state_hash", None)
        result.pop("verifier_hash", None)
        return result

    @staticmethod
    def auth_sessions(account_id: str):
        return [PublishingRepository._decode_auth_session(row) for row in db.all_rows(
            "SELECT * FROM publishing_auth_sessions WHERE account_id=? ORDER BY created_at DESC", (account_id,)
        )]

    @staticmethod
    def auth_session_by_state_hash(state_hash: str):
        return PublishingRepository._decode_auth_session(db.row(
            "SELECT * FROM publishing_auth_sessions WHERE state_hash=?", (state_hash,)
        ))

    @staticmethod
    def consume_auth_session(*, session_id: str, status: str, consumed_at: str,
                             error: str | None = None):
        updated = db.write(
            "UPDATE publishing_auth_sessions SET status=?,consumed_at=?,error=? WHERE id=? AND status='planned' AND consumed_at IS NULL",
            (status, consumed_at, error, session_id),
        )
        if updated != 1:
            return None
        return PublishingRepository._decode_auth_session(db.row(
            "SELECT * FROM publishing_auth_sessions WHERE id=?", (session_id,)
        ))

    @staticmethod
    def create_auth_session(*, session_id: str, account_id: str, provider: str,
                            auth_mode: str,
                            state_hash: str, verifier_hash: str, redirect_uri: str,
                            scopes: list[str], status: str, expires_at: str,
                            error: str | None, created_at: str):
        db.write(
            "INSERT INTO publishing_auth_sessions (id,account_id,provider,auth_mode,state_hash,verifier_hash,redirect_uri,scopes_json,status,expires_at,error,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (session_id, account_id, provider, auth_mode, state_hash, verifier_hash, redirect_uri,
             json.dumps(scopes, ensure_ascii=False), status, expires_at, error, created_at),
        )
        return PublishingRepository._decode_auth_session(db.row(
            "SELECT * FROM publishing_auth_sessions WHERE id=?", (session_id,)
        ))


class JobRepository:
    @staticmethod
    def create(*, job_id: str, persona_id: str, workflow_id: str, kind: str, prompt: str, request_json: str, lineage_json: str = "{}", created_at: str, idempotency_key: str | None = None, status: str = "queued"):
        db.write(
            "INSERT INTO jobs (id,persona_id,workflow_id,type,prompt,status,created_at,request_json,updated_at,lineage_json,idempotency_key) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (job_id, persona_id, workflow_id, kind, prompt, status, created_at, request_json, created_at, lineage_json, idempotency_key),
        )

    @staticmethod
    def by_idempotency_key(key: str):
        return db.row("SELECT * FROM jobs WHERE idempotency_key=?", (key,))


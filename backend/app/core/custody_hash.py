"""Version 1 canonical custody hashing. Changing this format needs a new schema version."""
import hashlib
import json
from datetime import timezone


def timestamp(value):
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def event_payload(event):
    return {
        "schema_version": event.schema_version, "id": str(event.id), "evidence_id": str(event.evidence_id),
        "sequence": event.sequence, "event_type": event.event_type, "actor_type": event.actor_type,
        "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
        "actor_agent_id": str(event.actor_agent_id) if event.actor_agent_id else None,
        "system_actor": event.system_actor, "actor_label": event.actor_label,
        "recorded_at": timestamp(event.recorded_at), "source_at": timestamp(event.source_at),
        "operation_id": str(event.operation_id), "details": event.details, "previous_hash": event.previous_hash,
    }


def hash_event(event):
    encoded = json.dumps(event_payload(event), sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

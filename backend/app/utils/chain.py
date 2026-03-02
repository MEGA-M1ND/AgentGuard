"""Cryptographic audit log chaining utilities.

Each audit log entry stores a SHA-256 hash that covers the previous entry's
log_id + timestamp + the current entry's log_id + action. A tampered row
produces a hash mismatch detectable by GET /logs/verify.
"""
import hashlib
from datetime import datetime


def compute_hash(
    prev_log_id: str,
    prev_timestamp: datetime,
    current_log_id: str,
    current_action: str,
) -> str:
    """Return SHA-256 hex digest linking the current entry to the previous one.

    The input is a pipe-delimited string of the four values so the components
    are unambiguous even if individual values contain special characters.

    Args:
        prev_log_id:       log_id of the immediately preceding entry.
        prev_timestamp:    timestamp of the immediately preceding entry.
        current_log_id:    log_id of the entry being inserted.
        current_action:    action field of the entry being inserted.

    Returns:
        64-character lowercase hex digest.
    """
    raw = f"{prev_log_id}|{prev_timestamp.isoformat()}|{current_log_id}|{current_action}"
    return hashlib.sha256(raw.encode()).hexdigest()


def genesis_hash() -> str:
    """Return the fixed hash used for the very first log entry of an agent.

    Having a deterministic genesis value means the first entry is also
    verifiable — any implementation can recompute SHA-256("GENESIS").
    """
    return hashlib.sha256(b"GENESIS").hexdigest()

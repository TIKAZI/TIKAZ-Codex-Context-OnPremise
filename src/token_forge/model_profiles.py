"""Capability-first local model profiles with explicit verification boundaries."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any


def load_model_profiles(path: Path | None = None) -> dict[str, Any]:
    resource = path if path is not None else files("token_forge").joinpath("data/model-profiles.json")
    data = json.loads(resource.read_text(encoding="utf-8"))
    if data.get("schema_version") != "model-profiles/v1":
        raise ValueError("model profiles must use schema_version model-profiles/v1")
    profiles = data.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("model profiles must contain profiles")
    ids = [profile.get("id") for profile in profiles]
    if any(not isinstance(model_id, str) or not model_id for model_id in ids) or len(set(ids)) != len(ids):
        raise ValueError("model profile ids must be unique strings")
    return data


def describe_model(model: str, path: Path | None = None) -> dict[str, Any]:
    """Return a profile without treating a name match as runtime validation."""
    model = str(model or "").strip()
    if not model:
        return {"model": None, "status": "not-configured", "verified": False}
    try:
        data = load_model_profiles(path)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return {"model": model, "status": "registry-unavailable", "verified": False, "reason": str(error)}
    for profile in data["profiles"]:
        if profile["id"] == model:
            return {
                "model": model, **profile,
                "historically_fixture_validated": profile.get("validation") == "fixture-validated",
                "verified": False,
                "actual_model": "UNVERIFIED",
                "reason": "Registry metadata is historical; current verification requires a matching runtime report.",
            }
    return {
        "model": model,
        "status": "unknown-unverified",
        "verified": False,
        "reason": "model name is not in the checked-in registry; configure and validate it explicitly",
    }



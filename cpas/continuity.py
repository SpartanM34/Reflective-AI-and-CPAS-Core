"""Explicit reporting for CPAS's four forms of continuity."""

from __future__ import annotations

from typing import Any, Mapping

from .identity import identity_digest


FORMS = ("declarative", "contextual", "epistemic", "persistent_system")


def build_activation_report(
    declaration: Mapping[str, Any],
    *,
    runtime_negotiation: Mapping[str, Any] | None = None,
    rehydration_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    declared = declaration["continuity"]["forms"]
    forms = {
        name: {
            "active": bool(declared[name]["active"]),
            "source": declared[name].get("source"),
        }
        for name in FORMS
    }
    if rehydration_manifest:
        if rehydration_manifest.get("included"):
            forms["epistemic"] = {
                "active": True,
                "source": "verified DKA-E rehydration manifest",
            }
        if rehydration_manifest.get("persistent_round_trip_verified"):
            forms["persistent_system"] = {
                "active": True,
                "source": "verified external CPAS store round trip",
            }

    warnings: list[str] = []
    if forms["persistent_system"]["active"] and not forms["epistemic"]["active"]:
        warnings.append("persistent-system continuity is active without restored epistemic state")
    negotiation = dict(runtime_negotiation or {"mode": "unbound"})
    return {
        "instance_id": declaration["instance_id"],
        "identity_digest": identity_digest(declaration),
        "runtime_mode": negotiation.get("mode", "unbound"),
        "continuity_forms": forms,
        "state_layers": declaration["continuity"]["state_layers"],
        "rehydration": dict(rehydration_manifest or {}),
        "warnings": warnings,
    }


def compare_declared_continuity(
    previous: Mapping[str, Any], current: Mapping[str, Any]
) -> dict[str, Any]:
    left = identity_digest(previous)
    right = identity_digest(current)
    return {
        "compatible": left == right,
        "previous_identity_digest": left,
        "current_identity_digest": right,
        "runtime_changed": previous.get("runtime_binding") != current.get("runtime_binding"),
    }

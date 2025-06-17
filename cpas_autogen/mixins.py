from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from .seed_token import SeedToken
from .prompt_wrapper import wrap_with_seed_token
from .epistemic_fingerprint import generate_fingerprint
from .continuity_check import continuity_check
from .metrics_monitor import periodic_metrics_check
from .drift_monitor import latest_metrics
from .realignment_trigger import should_realign


class EpistemicAgentMixin:
    """Mixin providing CPAS epistemic hooks for AutoGen agents."""

    idp_metadata: dict
    seed_token: SeedToken
    last_fingerprint: dict | None
    _last_metrics_check: datetime | None

    def conversable_setup(self) -> None:
        """Initialise seed token and metadata."""
        if not getattr(self, "idp_metadata", None):
            raise AttributeError("idp_metadata missing on agent")
        self.seed_token = SeedToken.generate(self.idp_metadata)
        self.last_fingerprint = None
        self._last_metrics_check = None

    def generate_reply(self, messages, *args, thread_token: str = "", **kwargs):
        """Wrap prompt with seed token and perform drift checks."""
        if not messages:
            return super().generate_reply(messages, *args, **kwargs)
        prompt = messages[-1]["content"]
        wrapped = wrap_with_seed_token(prompt, self.seed_token.to_dict())
        self.last_fingerprint = generate_fingerprint(wrapped, self.seed_token.to_dict())
        if not continuity_check(self.seed_token.to_dict(), thread_token):
            logging.warning("Continuity check failed for thread token %s", thread_token)
        metrics = latest_metrics()
        if metrics:
            periodic_metrics_check(self, metrics)
            if should_realign(metrics):
                logging.info("Realignment triggered for %s", self.idp_metadata.get("instance_name"))
                self.seed_token = SeedToken.generate(self.idp_metadata)
        messages[-1]["content"] = wrapped
        return super().generate_reply(messages, *args, **kwargs)

    def get_epistemic_fingerprint(self) -> str:
        """Return SHA256 hash of IDP metadata."""
        import hashlib
        sha = hashlib.sha256()
        sha.update(str(sorted(self.idp_metadata.items())).encode("utf-8"))
        return sha.hexdigest()

__all__ = ["EpistemicAgentMixin"]

from __future__ import annotations

"""Python implementation of the T-BEEP messaging utilities."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import re


@dataclass
class TBeepMessage:
    """Structured representation of a T-BEEP message."""

    thread_token: str
    instance: str
    reasoning_level: str
    confidence: str
    collaboration_mode: str
    timestamp: str
    version: str
    resources: List[str] = field(default_factory=list)
    handoff: List[str] = field(default_factory=list)
    content: str = ""
    seed_token: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        msg = {
            "threadToken": self.thread_token,
            "instance": self.instance,
            "reasoningLevel": self.reasoning_level,
            "confidence": self.confidence,
            "collaborationMode": self.collaboration_mode,
            "timestamp": self.timestamp,
            "version": self.version,
            "resources": list(self.resources),
            "handoff": list(self.handoff),
            "content": self.content,
        }
        if self.seed_token is not None:
            msg["seedToken"] = self.seed_token
        return msg

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TBeepMessage":
        return cls(
            thread_token=data.get("threadToken", ""),
            instance=data.get("instance", ""),
            reasoning_level=data.get("reasoningLevel", ""),
            confidence=data.get("confidence", ""),
            collaboration_mode=data.get("collaborationMode", ""),
            timestamp=data.get("timestamp", ""),
            version=data.get("version", ""),
            resources=data.get("resources", []) or [],
            handoff=data.get("handoff", []) or [],
            content=data.get("content", ""),
            seed_token=data.get("seedToken"),
        )


class TBeepMessenger:
    """Utility for generating and parsing T-BEEP messages."""

    THREAD_RE = re.compile(r"^#[A-Z_]+\d{3,4}\.\d+$")

    def __init__(self, instance_name: str, **base_config: Any) -> None:
        self.instance_name = instance_name
        self.message_history: List[TBeepMessage] = []
        self.config = {
            "reasoningLevel": "Detailed",
            "confidence": "Medium",
            "collaborationMode": "Discussion",
        }
        self.config.update(base_config)

    # Message creation -------------------------------------------------
    def create_message(
        self,
        *,
        thread_token: Optional[str] = None,
        reasoning_level: Optional[str] = None,
        confidence: Optional[str] = None,
        collaboration_mode: Optional[str] = None,
        resources: Optional[List[str]] = None,
        handoff: Optional[List[str]] = None,
        content: str = "",
        seed_token: Optional[Dict[str, Any]] = None,
    ) -> TBeepMessage:
        ts = datetime.utcnow().isoformat() + "Z"
        token = thread_token or self.generate_thread_token()
        msg = TBeepMessage(
            thread_token=token,
            instance=self.instance_name,
            reasoning_level=reasoning_level or self.config["reasoningLevel"],
            confidence=confidence or self.config["confidence"],
            collaboration_mode=collaboration_mode or self.config["collaborationMode"],
            timestamp=ts,
            version=self.generate_version(token),
            resources=resources or [],
            handoff=handoff or [],
            content=content,
            seed_token=seed_token,
        )
        self.message_history.append(msg)
        return msg

    def generate_thread_token(self, project_name: str = "COLLAB") -> str:
        num = str(int(datetime.utcnow().timestamp() * 1000) % 1000).zfill(3)
        return f"#{project_name}_{num}.0"

    def generate_version(self, thread_token: str) -> str:
        base = thread_token.split(".")[0].lstrip("#")
        count = sum(1 for m in self.message_history if m.thread_token.startswith(base))
        return f"#{base}.v{count + 1}.0"

    def continue_thread(
        self, thread_token: str, **options: Any
    ) -> TBeepMessage:
        base, version = thread_token.split(".")
        new_token = f"{base}.{int(version) + 1}"
        return self.create_message(thread_token=new_token, **options)

    # Formatting -------------------------------------------------------
    def format_for_mobile(self, message: TBeepMessage) -> str:
        return (
            f"\uD83D\uDD39 Thread Token: {message.thread_token}\n"
            f"\uD83D\uDD39 Instance: {message.instance}\n"
            f"\U0001F9E0 Reasoning Level: {message.reasoning_level}\n"
            f"\U0001F4CA Confidence: {message.confidence}\n"
            f"\U0001F91D Collaboration Mode: {message.collaboration_mode}\n"
            f"\u23F0 Timestamp: {message.timestamp}\n"
            f"\uD83D\uDD17 Version: {message.version}\n"
            f"\U0001F4CE Resources: [{', '.join(message.resources)}]\n"
            f"\uD83D\uDD01 Handoff: {', '.join(message.handoff)}\n\n"
            f"{message.content}"
        )

    # Parsing ----------------------------------------------------------
    def parse_mobile_format(self, text: str) -> TBeepMessage:
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        mapping = {}
        content_lines: List[str] = []
        for line in lines:
            if line.startswith("\uD83D\uDD39 Thread Token:"):
                mapping["threadToken"] = line.split(":", 1)[1].strip()
            elif line.startswith("\uD83D\uDD39 Instance:"):
                mapping["instance"] = line.split(":", 1)[1].strip()
            elif line.startswith("\U0001F9E0 Reasoning Level:"):
                mapping["reasoningLevel"] = line.split(":", 1)[1].strip()
            elif line.startswith("\U0001F4CA Confidence:"):
                mapping["confidence"] = line.split(":", 1)[1].strip()
            elif line.startswith("\U0001F91D Collaboration Mode:"):
                mapping["collaborationMode"] = line.split(":", 1)[1].strip()
            elif line.startswith("\u23F0 Timestamp:"):
                mapping["timestamp"] = line.split(":", 1)[1].strip()
            elif line.startswith("\uD83D\uDD17 Version:"):
                mapping["version"] = line.split(":", 1)[1].strip()
            elif line.startswith("\U0001F4CE Resources:"):
                resources = line.split(":", 1)[1].strip().strip("[]")
                mapping["resources"] = [r.strip() for r in resources.split(",") if r.strip()] if resources else []
            elif line.startswith("\uD83D\uDD01 Handoff:"):
                handoff = line.split(":", 1)[1].strip()
                mapping["handoff"] = [h.strip() for h in handoff.split(",") if h.strip()] if handoff else []
            else:
                content_lines.append(line)
        mapping["content"] = "\n".join(content_lines)
        return TBeepMessage.from_dict(mapping)

    # Validation -------------------------------------------------------
    def validate_message(self, message: TBeepMessage) -> Dict[str, Any]:
        missing = [
            field
            for field in [
                "thread_token",
                "instance",
                "reasoning_level",
                "confidence",
            ]
            if not getattr(message, field)
        ]
        warnings = self._validation_warnings(message)
        return {"valid": not missing, "missing": missing, "warnings": warnings}

    def _validation_warnings(self, message: TBeepMessage) -> List[str]:
        warnings = []
        if not message.handoff:
            warnings.append("No handoff specified - conversation may stall")
        if not message.resources:
            warnings.append("No resources listed - context may be unclear")
        if len(message.content) < 10:
            warnings.append("Very short content - may need more detail")
        return warnings


__all__ = ["TBeepMessenger", "TBeepMessage"]


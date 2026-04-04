# guardrails.py
# Limits and safe paths for the course autonomous agent (used by loop.py)
# Tim Fraser

import os
import re
from pathlib import Path

# Topic: AI for Data Management — keep guardrails obvious and readable for systems engineers.

MAX_AUTONOMOUS_TURNS = 10
MAX_WEB_SEARCHES_PER_REQUEST = 3
MAX_SKILL_READS_PER_REQUEST = 8

# Activity root: parent of this package (AGENT.md, skills/, logs/ live here).
_SKILLS_DIR_NAME = "skills"

# Skill files: basename only, alphanumeric, underscore, hyphen, .md
_SKILL_BASENAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+\.md$")


def agent_root() -> Path:
    """Directory containing AGENT.md and skills/ (parent of the app/ package)."""
    return Path(__file__).resolve().parent.parent


def skills_dir() -> Path:
    """Directory containing markdown skill files loaded via read_skill."""
    return agent_root() / _SKILLS_DIR_NAME


def read_skill_file(basename: str) -> str:
    """
    Read skills/{basename} if basename matches ^[a-zA-Z0-9_-]+\\.md$.
    Raises ValueError if invalid or file missing.
    """
    if not basename or not isinstance(basename, str):
        raise ValueError("Skill name must be a non-empty string.")
    if not _SKILL_BASENAME_PATTERN.fullmatch(basename):
        raise ValueError("Invalid skill filename (use basename like evidence_brief.md).")
    full = (skills_dir() / basename).resolve()
    try:
        full.relative_to(skills_dir().resolve())
    except ValueError as exc:
        raise ValueError("Skill path must stay inside skills/.") from exc
    if not full.is_file():
        raise ValueError(f"Skill not found: {basename}")
    return full.read_text(encoding="utf-8")


def clamp_turns(requested: int | None) -> int:
    """Clamp requested max turns to [1, MAX_AUTONOMOUS_TURNS]."""
    if requested is None:
        return MAX_AUTONOMOUS_TURNS
    try:
        n = int(requested)
    except (TypeError, ValueError):
        return MAX_AUTONOMOUS_TURNS
    return max(1, min(n, MAX_AUTONOMOUS_TURNS))


def min_completion_turns() -> int:
    """
    Minimum LLM /api/chat rounds (each counts toward the turn budget) before END_BRIEF is accepted.

    - Set **AGENT_MIN_COMPLETION_TURNS** to a positive integer (capped at **MAX_AUTONOMOUS_TURNS**).
    - If unset: **2** when **SERPER_API_KEY** is set (nudge verification against search), else **1**.
    """
    raw = (os.getenv("AGENT_MIN_COMPLETION_TURNS") or "").strip()
    if raw.isdigit():
        n = int(raw)
        return max(1, min(n, MAX_AUTONOMOUS_TURNS))
    if (os.getenv("SERPER_API_KEY") or "").strip():
        return min(2, MAX_AUTONOMOUS_TURNS)
    return 1


def task_size_ok(task: str, max_chars: int | None = None) -> bool:
    """Optional coarse limit on prompt injection / huge payloads."""
    limit = max_chars if max_chars is not None else int(os.getenv("AGENT_MAX_TASK_CHARS", "8000"))
    return isinstance(task, str) and 0 < len(task) <= limit

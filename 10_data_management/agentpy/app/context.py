# context.py
# Load AGENT.md and enumerate skill files for the system prompt
# Tim Fraser

import os

from .guardrails import agent_root, skills_dir

_FALLBACK_AGENT = """You assist disaster response coordinators with brief open-source situational summaries.

Produce markdown sections:
## Question restatement (incident, geography, time window if any)
## Key points (3 bullets max; never invent numbers or quotes; tie claims to retrieved text only)
## References (numbered list: verbatim URLs only from Retrieved URLs for References blocks, or state no URLs retrieved)
## Confidence (low/medium/high + one sentence)

End with a line containing only: END_BRIEF

Use read_skill and web_search when available. Never invent URLs."""


def load_agent_instructions() -> str:
    """Read AGENT.md in the activity root; fall back if missing (e.g. incomplete Connect bundle)."""
    path = agent_root() / "AGENT.md"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return _FALLBACK_AGENT


def list_skill_basenames() -> list[str]:
    """Basenames of *.md in skills/, excluding README.md (documentation only)."""
    root = skills_dir()
    if not root.is_dir():
        return []
    out: list[str] = []
    for name in sorted(os.listdir(root)):
        if not name.endswith(".md"):
            continue
        if name == "README.md":
            continue
        out.append(name)
    return out


def build_system_prompt() -> str:
    """Full system message: AGENT.md plus an appendix listing loadable skill files."""
    base = load_agent_instructions().strip()
    skills = list_skill_basenames()
    if not skills:
        appendix = "\n\n## Available skills\n\n_No skill `.md` files found under `skills/`._"
    else:
        lines = "\n".join(f"- `{s}`" for s in skills)
        appendix = (
            "\n\n## Available skills (load with read_skill)\n\n"
            f"{lines}\n\nCall `read_skill` with the **filename** exactly as listed (e.g. `disaster_situational_brief.md`)."
        )
    return base + appendix

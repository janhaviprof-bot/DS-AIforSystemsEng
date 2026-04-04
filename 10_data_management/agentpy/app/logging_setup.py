# logging_setup.py
# Optional file logging for agent turn trace (see AGENT_LOG_FILE).
# Tim Fraser

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from .guardrails import agent_root

_LOGGER_NAME = "agent"
_CONFIGURED = False


def configure_agent_logging() -> None:
    """
    Attach a FileHandler to logger 'agent' if enabled.

    - **AGENT_LOG_FILE** unset: write to **logs/agent.log** under activity root.
    - **AGENT_LOG_FILE** set to empty, 0, off, false, no: disable file logging.
    - Otherwise: path; relative paths are resolved under activity root.
    - **AGENT_LOG_LEVEL**: default INFO.

    Idempotent; on OSError (e.g. read-only deploy) logs a warning to stderr and skips the file.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    raw = os.getenv("AGENT_LOG_FILE")
    if raw is not None:
        stripped = raw.strip()
        if stripped.lower() in ("", "0", "off", "false", "no"):
            _CONFIGURED = True
            return
        path = Path(stripped)
    else:
        path = agent_root() / "logs" / "agent.log"

    if not path.is_absolute():
        path = agent_root() / path

    level_name = (os.getenv("AGENT_LOG_LEVEL") or "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(path, encoding="utf-8")
    except OSError as exc:
        print(f"agent logging: could not open {path}: {exc}", file=sys.stderr)
        _CONFIGURED = True
        return

    fh.setLevel(level)
    fh.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"),
    )
    logger.addHandler(fh)
    _CONFIGURED = True

"""Adaptador de sólo lectura al oráculo C estricto de BolgeForge."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess


def run_mb_ref(executable: Path, program: Path, payload: bytes, max_steps: int, timeout: float = 120.0) -> dict:
    completed = subprocess.run(
        [str(executable), str(program), str(max_steps)],
        input=payload,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    status_by_rc = {0: "HALT", 2: "MAX_STEPS", 3: "STALL", 4: "IO_ERROR"}
    return {
        "returncode": completed.returncode,
        "terminal": status_by_rc.get(completed.returncode, "ERROR"),
        "output_hex": completed.stdout.hex(),
        "output_sha256": hashlib.sha256(completed.stdout).hexdigest(),
        "stderr_utf8": completed.stderr.decode("utf-8", "backslashreplace"),
        "command": [str(executable), str(program), str(max_steps)],
    }

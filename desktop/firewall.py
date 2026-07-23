"""Windows Firewall bootstrap — makes casting plug-and-play.

The Hub fetches the Deck page over the LAN, so inbound TCP on our port must be
allowed. The prompt Windows shows on first bind creates a program-scoped rule
that has proven unreliable; a port-scoped rule works. Creating one needs
elevation, so on first launch (or after a port change) we trigger a single UAC
prompt. Declining it never breaks the app — only the Hub's access.
"""

from __future__ import annotations

import re
import subprocess
import sys

RULE_NAME = "NestDeck"


def _rule_matches(port: int) -> bool:
    """True if our rule already exists for this port (no elevation needed)."""
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "show", "rule", f"name={RULE_NAME}"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if result.returncode != 0:
        return False
    # Labels are localised; the port number itself is not.
    return re.search(rf"\b{port}\b", result.stdout) is not None


def ensure_rule(port: int) -> None:
    """Create (or move to a new port) the inbound allow rule, via one UAC
    prompt. Best-effort: a refusal leaves the app fully usable locally."""
    if sys.platform != "win32":
        return
    if _rule_matches(port):
        return

    import ctypes

    # Recreate atomically: drop any stale rule (old port), then add the new
    # one. `&` keeps going when the delete finds nothing to delete.
    script = (
        f'netsh advfirewall firewall delete rule name="{RULE_NAME}" & '
        f'netsh advfirewall firewall add rule name="{RULE_NAME}" '
        f"dir=in action=allow protocol=TCP localport={port}"
    )
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f"/c {script}", None, 0)
    except OSError:
        pass

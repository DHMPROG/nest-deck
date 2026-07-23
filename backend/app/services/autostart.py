"""Start-with-Windows, via the per-user Run registry key.

Only meaningful for the packaged .exe: the command registered is the running
executable (``sys.executable`` when frozen). From source there's no stable exe
to point at, so it reports unsupported rather than registering a python command
that would break the moment the checkout moves.
"""

from __future__ import annotations

import sys

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE = "NestDeck"


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def supported() -> bool:
    return sys.platform == "win32" and _frozen()


def _command() -> str:
    # Quoted so a path with spaces survives.
    return f'"{sys.executable}"'


def is_enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, _VALUE)
            return bool(value)
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable() -> bool:
    if not supported():
        return False
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
        winreg.SetValueEx(key, _VALUE, 0, winreg.REG_SZ, _command())
    return True


def disable() -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, _VALUE)
    except FileNotFoundError:
        pass
    return True

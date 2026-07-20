"""Action handlers.

Every handler is ``async def handle(action: Action) -> dict`` and returns
``{"status": "ok"|"error", "message": str}``. Handlers must never raise — a
misconfigured or offline service degrades to an error tile, not a 500.
"""

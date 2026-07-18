"""Async i3ipc transport wrapper for the MCP server.

This module isolates *all* i3/Sway communication behind :class:`I3Backend`. The
rest of the server never imports :mod:`i3ipc` directly, which keeps the tool
layer testable: tests inject a fake connection factory instead of talking to a
real window manager.

Design notes:
- A single :class:`i3ipc.aio.Connection` is created lazily and cached. It is
  opened with ``auto_reconnect=True`` so an ``i3 restart`` does not permanently
  break the server.
- Every mutation goes through :meth:`I3Backend.run`, which normalises the i3
  ``RUN_COMMAND`` reply (a list of ``{success, error}`` records) into a single
  :class:`CommandResult`. Callers therefore always see per-command success and
  the first error message, never a raw i3ipc object.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from .models import CommandOutcome, CommandResult

# A factory that yields a connected i3ipc async Connection. Injectable for tests.
ConnectionFactory = Callable[[], Awaitable[Any]]


async def _default_connection_factory() -> Any:  # pragma: no cover - needs a live WM
    """Open a real connection to the running i3/Sway IPC socket.

    Imported lazily so that importing this module (e.g. during test collection
    or ``--help``) does not require a running window manager or the i3ipc event
    loop machinery. Excluded from coverage: it can only run against a real i3/
    Sway session, which CI does not provide.
    """
    from i3ipc.aio import Connection  # local import: keeps import side-effects out

    return await Connection(auto_reconnect=True).connect()


class I3Backend:
    """Cached, lazily-connected gateway to the i3/Sway IPC interface."""

    def __init__(self, connection_factory: ConnectionFactory | None = None) -> None:
        """Store the connection factory; do not connect yet.

        Parameters
        ----------
        connection_factory:
            Coroutine returning a connected i3ipc ``Connection``. Defaults to a
            real i3/Sway connection; tests pass a fake to avoid needing a WM.
        """
        self._factory: ConnectionFactory = connection_factory or _default_connection_factory
        self._conn: Any | None = None

    async def connection(self) -> Any:
        """Return the cached connection, creating it on first use."""
        if self._conn is None:
            self._conn = await self._factory()
        return self._conn

    # -- Mutations ---------------------------------------------------------

    async def run(self, payload: str) -> CommandResult:
        """Run one or more i3 commands and summarise the per-command outcome.

        i3 returns one ``{success, error}`` record per command in the payload
        (commands are separated by ``;`` or ``,``). We surface all of them plus
        a single roll-up so tool callers can react to partial failures.
        """
        conn = await self.connection()
        replies = await conn.command(payload)
        outcomes = [
            CommandOutcome(success=bool(r.success), error=getattr(r, "error", None))
            for r in replies
        ]
        first_error = next((o.error for o in outcomes if not o.success), None)
        return CommandResult(
            success=all(o.success for o in outcomes) if outcomes else True,
            error=first_error,
            outcomes=outcomes,
        )

    # -- Queries -----------------------------------------------------------

    async def get_tree(self) -> Any:
        """Return the root :class:`i3ipc.Con` of the layout tree."""
        conn = await self.connection()
        return await conn.get_tree()

    async def get_workspaces(self) -> list[Any]:
        """Return the list of workspace reply objects."""
        conn = await self.connection()
        return list(await conn.get_workspaces())

    async def get_outputs(self) -> list[Any]:
        """Return the list of output (monitor) reply objects."""
        conn = await self.connection()
        return list(await conn.get_outputs())

    async def get_version(self) -> Any:
        """Return the i3/Sway version reply object."""
        conn = await self.connection()
        return await conn.get_version()

    async def get_config(self) -> Any:
        """Return the loaded configuration reply object."""
        conn = await self.connection()
        return await conn.get_config()

    async def get_binding_modes(self) -> list[str]:
        """Return the names of all configured binding modes."""
        conn = await self.connection()
        return list(await conn.get_binding_modes())

    async def get_binding_state(self) -> str | None:
        """Return the currently active binding mode name, if the WM reports it.

        ``GET_BINDING_STATE`` is a newer message; older i3/Sway builds omit it,
        so we degrade gracefully to ``None`` rather than raising.
        """
        conn = await self.connection()
        getter = getattr(conn, "get_binding_state", None)
        if getter is None:  # pragma: no cover - depends on i3ipc/WM version
            return None
        state = await getter()
        return getattr(state, "name", None)

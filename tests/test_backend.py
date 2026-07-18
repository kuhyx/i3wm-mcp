"""Tests for the i3ipc transport wrapper (:mod:`i3wm_mcp.backend`)."""

from __future__ import annotations

from tests.conftest import (
    FakeBindingState,
    FakeCommandReply,
    FakeConnection,
    make_backend,
)

from i3wm_mcp.backend import I3Backend


async def test_connection_is_cached() -> None:
    """The connection factory is invoked exactly once, then cached."""
    calls = {"n": 0}
    conn = FakeConnection()

    async def factory() -> FakeConnection:
        calls["n"] += 1
        return conn

    backend = I3Backend(connection_factory=factory)
    first = await backend.connection()
    second = await backend.connection()
    assert first is second is conn
    assert calls["n"] == 1


async def test_run_all_success() -> None:
    """A single successful command yields success with no error."""
    conn = FakeConnection(command_replies=[FakeCommandReply(True, None)])
    result = await make_backend(conn).run("focus left")
    assert result.success is True
    assert result.error is None
    assert len(result.outcomes) == 1


async def test_run_reports_first_error() -> None:
    """A failing command in the payload surfaces as the roll-up error."""
    replies = [FakeCommandReply(True, None), FakeCommandReply(False, "boom")]
    conn = FakeConnection(command_replies=replies)
    result = await make_backend(conn).run("a; b")
    assert result.success is False
    assert result.error == "boom"
    assert [o.success for o in result.outcomes] == [True, False]


async def test_run_empty_reply_is_success() -> None:
    """An empty reply list is treated as success (nothing failed)."""
    conn = FakeConnection(command_replies=[])
    result = await make_backend(conn).run("nop")
    assert result.success is True
    assert result.outcomes == []


async def test_query_passthroughs() -> None:
    """Each query method returns the connection's corresponding value."""
    conn = FakeConnection(binding_modes=["default", "resize"])
    backend = make_backend(conn)
    assert await backend.get_tree() is None
    assert await backend.get_workspaces() == []
    assert await backend.get_outputs() == []
    assert (await backend.get_version()).human_readable == "4.25.1"
    assert (await backend.get_config()).config == "bar {}\n"
    assert await backend.get_binding_modes() == ["default", "resize"]


async def test_binding_state_present_and_absent() -> None:
    """binding-state returns the mode name, or None when unset."""
    with_state = make_backend(FakeConnection(binding_state=FakeBindingState("resize")))
    assert await with_state.get_binding_state() == "resize"

    without_state = make_backend(FakeConnection(binding_state=None))
    assert await without_state.get_binding_state() is None

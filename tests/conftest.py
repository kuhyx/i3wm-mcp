"""Shared test fixtures wiring the fakes in :mod:`tests.fakes` into the server.

Each test builds a :class:`~tests.fakes.FakeConnection` (optionally with a fake
layout tree) and installs it via the ``set_backend`` fixture, which swaps
``i3wm_mcp.runtime.backend`` -- the one name every tool module resolves at call
time -- for a backend wired to the fake.

The fake classes are re-exported here so ``from tests.conftest import FakeCon``
keeps working alongside ``from tests.fakes import FakeCon``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from tests.fakes import (
    FakeBindingState,
    FakeCommandReply,
    FakeCon,
    FakeConfig,
    FakeConnection,
    FakeOutput,
    FakeRect,
    FakeVersion,
    FakeWorkspace,
)

from i3wm_mcp import runtime
from i3wm_mcp.backend import I3Backend

__all__ = [
    "FakeBindingState",
    "FakeCommandReply",
    "FakeCon",
    "FakeConfig",
    "FakeConnection",
    "FakeOutput",
    "FakeRect",
    "FakeVersion",
    "FakeWorkspace",
    "build_deep_tree",
    "make_backend",
    "sample_tree",
    "set_backend",
]


def make_backend(conn: FakeConnection) -> I3Backend:
    """Wrap a fake connection in an :class:`I3Backend`."""

    async def factory() -> FakeConnection:
        return conn

    return I3Backend(connection_factory=factory)


@pytest.fixture
def set_backend(monkeypatch: pytest.MonkeyPatch) -> Callable[[FakeConnection], FakeConnection]:
    """Install a fake connection as the module-level backend; return the connection."""

    def _set(conn: FakeConnection) -> FakeConnection:
        monkeypatch.setattr(runtime, "backend", make_backend(conn))
        return conn

    return _set


@pytest.fixture
def sample_tree() -> FakeCon:
    """A small but realistic i3 tree: two outputs, workspaces, windows, a dock."""
    firefox = FakeCon(
        id=10,
        name="Mozilla Firefox",
        window=100,
        window_class="firefox",
        window_instance="Navigator",
        window_role="browser",
        focused=True,
        rect=FakeRect(),
        pid=1234,
        layout="splith",
    )
    terminal = FakeCon(
        id=11,
        name="term",
        window=101,
        window_class="Alacritty",
        floating="user_on",
        marks=["scratch"],
        urgent=True,
    )
    wayland = FakeCon(id=12, name="wl", app_id="foot", fullscreen_mode=1)
    ws1 = FakeCon(id=2, type="workspace", name="1", nodes=[firefox], floating_nodes=[terminal])
    ws2 = FakeCon(id=3, type="workspace", name="2", nodes=[wayland])
    dock = FakeCon(
        id=4, type="dockarea", nodes=[FakeCon(id=5, name="i3bar", window=200, window_class="i3bar")]
    )
    content = FakeCon(id=6, type="con", nodes=[ws1, ws2])
    output = FakeCon(id=7, type="output", name="DP-0", nodes=[content, dock])
    return FakeCon(id=1, type="root", name="root", nodes=[output])


def build_deep_tree(window_count: int) -> FakeCon:
    """A single workspace holding ``window_count`` windows (for truncation tests)."""
    windows: list[Any] = [
        FakeCon(id=1000 + i, name=f"w{i}", window=i, window_class="X") for i in range(window_count)
    ]
    ws = FakeCon(id=2, type="workspace", name="1", nodes=windows)
    output = FakeCon(id=7, type="output", name="DP-0", nodes=[ws])
    return FakeCon(id=1, type="root", name="root", nodes=[output])

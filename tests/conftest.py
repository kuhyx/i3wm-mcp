"""Shared test fixtures: lightweight fakes that stand in for i3ipc objects.

The backend never sees a real window manager in tests. Instead each test builds
a :class:`FakeConnection` (optionally with a fake layout tree) and installs it
via the ``set_backend`` fixture, which swaps ``server.backend`` for one wired to
the fake. The fakes are deliberately duck-typed to match only the attributes the
production code reads.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from i3wm_mcp import server
from i3wm_mcp.backend import I3Backend


class FakeCommandReply:
    """Mimics an i3ipc CommandReply (result of one RUN_COMMAND entry)."""

    def __init__(self, success: bool = True, error: str | None = None) -> None:
        self.success = success
        self.error = error


class FakeRect:
    """Mimics an i3ipc Rect."""

    def __init__(self, x: int = 0, y: int = 0, width: int = 1920, height: int = 1080) -> None:
        self.x, self.y, self.width, self.height = x, y, width, height


class FakeCon:
    """Mimics an i3ipc Con tree node with only the fields we consume."""

    def __init__(
        self,
        *,
        id: int = 1,
        type: str = "con",
        name: str | None = None,
        window: int | None = None,
        app_id: str | None = None,
        window_class: str | None = None,
        window_instance: str | None = None,
        window_role: str | None = None,
        marks: list[str] | None = None,
        focused: bool = False,
        urgent: bool = False,
        floating: str | None = None,
        fullscreen_mode: int = 0,
        layout: str | None = None,
        pid: int | None = None,
        rect: FakeRect | None = None,
        nodes: list[FakeCon] | None = None,
        floating_nodes: list[FakeCon] | None = None,
    ) -> None:
        self.id = id
        self.type = type
        self.name = name
        self.window = window
        self.app_id = app_id
        self.window_class = window_class
        self.window_instance = window_instance
        self.window_role = window_role
        self.marks = marks or []
        self.focused = focused
        self.urgent = urgent
        self.floating = floating
        self.fullscreen_mode = fullscreen_mode
        self.layout = layout
        self.pid = pid
        self.rect = rect
        self.nodes = nodes or []
        self.floating_nodes = floating_nodes or []


class FakeWorkspace:
    """Mimics an i3ipc workspace reply."""

    def __init__(
        self,
        num: int = 1,
        name: str = "1",
        visible: bool = True,
        focused: bool = True,
        urgent: bool = False,
        output: str | None = "DP-0",
    ) -> None:
        self.num, self.name, self.visible = num, name, visible
        self.focused, self.urgent, self.output = focused, urgent, output


class FakeOutput:
    """Mimics an i3ipc output reply."""

    def __init__(
        self,
        name: str = "DP-0",
        active: bool = True,
        primary: bool = True,
        current_workspace: str | None = "1",
        rect: FakeRect | None = None,
    ) -> None:
        self.name, self.active, self.primary = name, active, primary
        self.current_workspace, self.rect = current_workspace, rect


class FakeVersion:
    """Mimics an i3ipc version reply."""

    def __init__(
        self,
        human_readable: str = "4.25.1",
        loaded_config_file_name: str | None = "/home/user/.config/i3/config",
    ) -> None:
        self.human_readable = human_readable
        self.loaded_config_file_name = loaded_config_file_name


class FakeConfig:
    """Mimics an i3ipc config reply."""

    def __init__(self, config: str = "bar {}\n") -> None:
        self.config = config


class FakeBindingState:
    """Mimics an i3ipc binding-state reply."""

    def __init__(self, name: str = "default") -> None:
        self.name = name


class FakeConnection:
    """Mimics enough of an i3ipc async Connection for the backend."""

    def __init__(
        self,
        *,
        tree: FakeCon | None = None,
        workspaces: list[FakeWorkspace] | None = None,
        outputs: list[FakeOutput] | None = None,
        version: FakeVersion | None = None,
        config: FakeConfig | None = None,
        binding_modes: list[str] | None = None,
        binding_state: FakeBindingState | None = None,
        command_replies: list[FakeCommandReply] | None = None,
    ) -> None:
        self._tree = tree
        self._workspaces = workspaces or []
        self._outputs = outputs or []
        self._version = version or FakeVersion()
        self._config = config or FakeConfig()
        self._binding_modes = binding_modes if binding_modes is not None else ["default"]
        self._binding_state = binding_state
        self._command_replies = command_replies
        self.commands: list[str] = []

    async def command(self, payload: str) -> list[FakeCommandReply]:
        self.commands.append(payload)
        if self._command_replies is not None:
            return self._command_replies
        return [FakeCommandReply(True, None)]

    async def get_tree(self) -> FakeCon | None:
        return self._tree

    async def get_workspaces(self) -> list[FakeWorkspace]:
        return self._workspaces

    async def get_outputs(self) -> list[FakeOutput]:
        return self._outputs

    async def get_version(self) -> FakeVersion:
        return self._version

    async def get_config(self) -> FakeConfig:
        return self._config

    async def get_binding_modes(self) -> list[str]:
        return self._binding_modes

    async def get_binding_state(self) -> FakeBindingState | None:
        return self._binding_state


def make_backend(conn: FakeConnection) -> I3Backend:
    """Wrap a fake connection in an :class:`I3Backend`."""

    async def factory() -> FakeConnection:
        return conn

    return I3Backend(connection_factory=factory)


@pytest.fixture
def set_backend(monkeypatch: pytest.MonkeyPatch) -> Callable[[FakeConnection], FakeConnection]:
    """Install a fake connection as the module-level backend; return the connection."""

    def _set(conn: FakeConnection) -> FakeConnection:
        monkeypatch.setattr(server, "backend", make_backend(conn))
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

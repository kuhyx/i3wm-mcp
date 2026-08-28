"""Lightweight fakes that stand in for i3ipc objects.

The backend never sees a real window manager in tests. These fakes are
deliberately duck-typed to match only the attributes the production code reads,
so adding a field to i3ipc does not ripple through the suite.

Kept out of ``conftest.py`` so that file stays a short list of fixtures;
``conftest`` re-exports every name here, and tests may import from either.
"""

from __future__ import annotations


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

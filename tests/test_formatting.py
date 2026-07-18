"""Tests for the pure shaping helpers (:mod:`i3wm_mcp.formatting`)."""

from __future__ import annotations

from tests.conftest import (
    FakeCon,
    FakeOutput,
    FakeRect,
    FakeWorkspace,
    build_deep_tree,
)

from i3wm_mcp.formatting import (
    MAX_WINDOWS,
    collect_windows,
    con_to_window,
    find_focused,
    output_to_info,
    workspace_to_info,
)


def test_con_to_window_maps_fields() -> None:
    """A rich container maps every surfaced field, including floating/fullscreen."""
    con = FakeCon(
        id=10,
        name="t",
        window_class="firefox",
        app_id=None,
        marks=["m"],
        focused=True,
        urgent=True,
        floating="user_on",
        fullscreen_mode=1,
        layout="splith",
        pid=99,
        rect=FakeRect(1, 2, 3, 4),
    )
    win = con_to_window(con, workspace="1", output="DP-0")
    assert win.id == 10
    assert win.floating is True
    assert win.fullscreen is True
    assert win.marks == ["m"]
    assert win.workspace == "1" and win.output == "DP-0"
    assert win.rect == {"x": 1, "y": 2, "width": 3, "height": 4}


def test_floating_variants_and_no_rect() -> None:
    """auto_off is not floating; a con with no rect yields rect=None."""
    tiled = con_to_window(FakeCon(floating="auto_off"))
    assert tiled.floating is False
    assert tiled.rect is None


def test_collect_windows_filters_and_excludes_docks(sample_tree: FakeCon) -> None:
    """All application windows are returned; dock (i3bar) windows are excluded."""
    windows, truncated = collect_windows(sample_tree, {})
    classes = {w.window_class or w.app_id for w in windows}
    assert "i3bar" not in classes
    assert classes == {"firefox", "Alacritty", "foot"}
    assert truncated is False
    # workspace/output context is threaded down the walk
    firefox = next(w for w in windows if w.window_class == "firefox")
    assert firefox.workspace == "1" and firefox.output == "DP-0"


def test_collect_windows_each_filter(sample_tree: FakeCon) -> None:
    """Each filter narrows the set as expected."""
    assert len(collect_windows(sample_tree, {"window_class": "firefox"})[0]) == 1
    assert len(collect_windows(sample_tree, {"title": "term"})[0]) == 1
    assert len(collect_windows(sample_tree, {"instance": "Navigator"})[0]) == 1
    assert len(collect_windows(sample_tree, {"role": "browser"})[0]) == 1
    assert len(collect_windows(sample_tree, {"workspace": "2"})[0]) == 1
    assert len(collect_windows(sample_tree, {"floating": True})[0]) == 1
    assert len(collect_windows(sample_tree, {"floating": False})[0]) == 2
    assert len(collect_windows(sample_tree, {"urgent": True})[0]) == 1
    # A non-matching class filter yields nothing.
    assert collect_windows(sample_tree, {"window_class": "nope"})[0] == []


def test_collect_windows_truncates() -> None:
    """More than MAX_WINDOWS matches sets the truncated flag and caps the list."""
    tree = build_deep_tree(MAX_WINDOWS + 5)
    windows, truncated = collect_windows(tree, {})
    assert len(windows) == MAX_WINDOWS
    assert truncated is True


def test_find_focused(sample_tree: FakeCon) -> None:
    """find_focused returns the focused window, or None when none is focused."""
    focused = find_focused(sample_tree)
    assert focused is not None and focused.window_class == "firefox"

    empty = FakeCon(type="root", name="root", nodes=[])
    assert find_focused(empty) is None

    # Several windows, none focused: the loop iterates through all and returns None.
    ws = FakeCon(
        type="workspace",
        name="1",
        nodes=[
            FakeCon(id=1, window=1, window_class="A"),
            FakeCon(id=2, window=2, window_class="B"),
        ],
    )
    unfocused_tree = FakeCon(
        type="root",
        name="root",
        nodes=[FakeCon(type="output", name="DP-0", nodes=[ws])],
    )
    assert find_focused(unfocused_tree) is None


def test_workspace_and_output_mappers() -> None:
    """Workspace/output replies map to their info models."""
    ws = workspace_to_info(FakeWorkspace(num=3, name="dev", visible=False, focused=False))
    assert ws.num == 3 and ws.name == "dev" and ws.visible is False

    out = output_to_info(FakeOutput(name="HDMI-0", primary=False, rect=FakeRect(0, 0, 800, 600)))
    assert out.name == "HDMI-0" and out.primary is False
    assert out.rect == {"x": 0, "y": 0, "width": 800, "height": 600}

# tests/indexer/test_watcher.py
import asyncio
import pytest
from context_engine.indexer.watcher import FileWatcher


@pytest.mark.asyncio
async def test_watcher_detects_new_file(tmp_path):
    events = []

    async def on_change(path: str):
        events.append(path)

    watcher = FileWatcher(
        watch_dir=str(tmp_path), on_change=on_change,
        debounce_ms=100, ignore_patterns=[".git"],
    )
    watcher.start()
    test_file = tmp_path / "hello.py"
    test_file.write_text("print('hello')")
    await asyncio.sleep(0.5)
    watcher.stop()
    assert len(events) > 0
    assert any("hello.py" in e for e in events)


@pytest.mark.asyncio
async def test_watcher_ignores_patterns(tmp_path):
    events = []

    async def on_change(path: str):
        events.append(path)

    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    watcher = FileWatcher(
        watch_dir=str(tmp_path), on_change=on_change,
        debounce_ms=100, ignore_patterns=[".git"],
    )
    watcher.start()
    (git_dir / "config").write_text("test")
    await asyncio.sleep(0.5)
    watcher.stop()
    assert not any(".git" in e for e in events)


@pytest.mark.asyncio
async def test_watcher_ignore_matches_component_not_substring(tmp_path):
    """Ignore pattern 'vendor' should not match 'vendor-utils' directory."""
    events = []

    async def on_change(path: str):
        events.append(path)

    # Create dirs: 'vendor' (should be ignored) and 'vendor-utils' (should NOT be ignored)
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor-utils").mkdir()

    watcher = FileWatcher(
        watch_dir=str(tmp_path), on_change=on_change,
        debounce_ms=100, ignore_patterns=["vendor"],
    )
    watcher.start()
    (tmp_path / "vendor" / "lib.py").write_text("ignored")
    (tmp_path / "vendor-utils" / "helper.py").write_text("not ignored")
    await asyncio.sleep(0.5)
    watcher.stop()
    assert not any("vendor/lib.py" in e or "vendor\\lib.py" in e for e in events)
    assert any("helper.py" in e for e in events)


@pytest.mark.asyncio
async def test_watcher_always_ignores_cce_dirs(tmp_path):
    """'.cce' is always ignored even without explicit patterns."""
    events = []

    async def on_change(path: str):
        events.append(path)

    (tmp_path / ".cce").mkdir()

    watcher = FileWatcher(
        watch_dir=str(tmp_path), on_change=on_change,
        debounce_ms=100, ignore_patterns=[],
    )
    watcher.start()
    (tmp_path / ".cce" / "commands.yaml").write_text("test")
    (tmp_path / "real.py").write_text("should be seen")
    await asyncio.sleep(0.5)
    watcher.stop()
    assert not any(".cce" in e for e in events)
    assert any("real.py" in e for e in events)


@pytest.mark.asyncio
async def test_watcher_debounces(tmp_path):
    events = []

    async def on_change(path: str):
        events.append(path)

    watcher = FileWatcher(
        watch_dir=str(tmp_path), on_change=on_change,
        debounce_ms=300, ignore_patterns=[],
    )
    watcher.start()
    test_file = tmp_path / "rapid.py"
    for i in range(5):
        test_file.write_text(f"version {i}")
        await asyncio.sleep(0.05)
    await asyncio.sleep(0.8)
    watcher.stop()
    assert len(events) < 5


# ─── Issue #66 regression coverage: event-type filtering ────────────────


class _FakeEvent:
    def __init__(self, src_path, *, is_directory=False, dest_path=None):
        self.src_path = src_path
        self.is_directory = is_directory
        if dest_path is not None:
            self.dest_path = dest_path


def _make_handler(tmp_path, queued):
    from context_engine.indexer.watcher import _DebouncedHandler
    # A loop is required by the handler constructor but never used here —
    # _enqueue is monkey-patched below, so on_change is never scheduled.
    loop = asyncio.new_event_loop()
    handler = _DebouncedHandler(
        on_change=lambda p: None,
        debounce_ms=10,
        ignore_patterns=[],
        watch_dir=str(tmp_path),
        loop=loop,
    )
    # Swap in a recorder so we can assert what was enqueued without timing
    # out on the real debounce timer.
    handler._enqueue = lambda path: queued.append(path)
    return handler


def test_watcher_ignores_read_only_events(tmp_path):
    """Read-only `opened`/`closed_no_write` events from a sibling `cce index`
    must not enqueue work. This is the trigger half of the #66 leak —
    without this, hundreds of read events per `cce index --path X` cascade
    into the reindex worker and spawn embed pools.
    """
    queued: list[str] = []
    handler = _make_handler(tmp_path, queued)

    # Read-only events flow through the base FileSystemEventHandler stubs,
    # which are no-ops on our subclass. They must NOT result in anything
    # being enqueued.
    for read_only in ("on_opened", "on_closed", "on_closed_no_write"):
        method = getattr(handler, read_only, None)
        if method is None:
            continue
        try:
            method(_FakeEvent(str(tmp_path / f"{read_only}.py")))
        except TypeError:
            # Some watchdog versions require the event to have specific
            # attributes — that's still proof the method isn't ours.
            pass
    assert queued == [], (
        "Read-only events leaked into the reindex queue: %s" % queued
    )

    # The four content-changing types DO fire.
    handler.on_modified(_FakeEvent(str(tmp_path / "a.py")))
    handler.on_created(_FakeEvent(str(tmp_path / "b.py")))
    handler.on_deleted(_FakeEvent(str(tmp_path / "c.py")))
    handler.on_moved(_FakeEvent(
        str(tmp_path / "old.py"), dest_path=str(tmp_path / "new.py"),
    ))
    assert str(tmp_path / "a.py") in queued
    assert str(tmp_path / "b.py") in queued
    assert str(tmp_path / "c.py") in queued
    assert str(tmp_path / "old.py") in queued
    assert str(tmp_path / "new.py") in queued


def test_watcher_skips_directory_events(tmp_path):
    queued: list[str] = []
    handler = _make_handler(tmp_path, queued)
    handler.on_modified(_FakeEvent(str(tmp_path / "subdir"), is_directory=True))
    handler.on_created(_FakeEvent(str(tmp_path / "subdir2"), is_directory=True))
    handler.on_deleted(_FakeEvent(str(tmp_path / "subdir3"), is_directory=True))
    handler.on_moved(_FakeEvent(
        str(tmp_path / "old_dir"), is_directory=True,
        dest_path=str(tmp_path / "new_dir"),
    ))
    assert queued == []


def test_watcher_move_with_same_src_and_dest(tmp_path):
    """Spurious move events sometimes report src == dest; queue only once."""
    queued: list[str] = []
    handler = _make_handler(tmp_path, queued)
    handler.on_moved(_FakeEvent(
        str(tmp_path / "x.py"), dest_path=str(tmp_path / "x.py"),
    ))
    assert queued == [str(tmp_path / "x.py")]

"""Tests for the heuristic decision extractor."""
from __future__ import annotations

import pytest
from context_engine.memory.decision_extractor import extract_decisions
from context_engine.memory import db as memory_db
from context_engine.memory.compressor import compress_turn, _auto_capture_decisions


def _decisions(text):
    return [d for d, _ in extract_decisions(text)]


def _reasons(text):
    return [r for _, r in extract_decisions(text)]


# ---------------------------------------------------------------------------
# Pattern coverage
# ---------------------------------------------------------------------------

def test_chose_over_because():
    results = extract_decisions("I chose PostgreSQL over MySQL because it has better JSON support.")
    assert len(results) == 1
    assert "PostgreSQL" in results[0][0]
    assert "JSON" in results[0][1]


def test_decided_to_because():
    results = extract_decisions("We decided to use Redis because the data needs to expire automatically.")
    assert len(results) == 1
    assert "Redis" in results[0][0]
    assert "expire" in results[0][1]


def test_went_with_because():
    results = extract_decisions("Went with goroutines because a worker pool would add unnecessary complexity.")
    assert len(results) == 1
    assert "goroutines" in results[0][0]


def test_going_with_because():
    results = extract_decisions("Going with SQLite because it requires no separate server process.")
    assert len(results) == 1
    assert "SQLite" in results[0][0]


def test_use_because():
    results = extract_decisions("Use chi instead of gin because chi is stdlib-compatible.")
    assert len(results) >= 1


def test_instead_of_because():
    results = extract_decisions("Using interfaces instead of structs because it makes testing easier.")
    assert len(results) == 1
    assert "testing" in results[0][1]


def test_prefer_because():
    results = extract_decisions("Preferred uv over pip because it resolves dependencies faster.")
    assert len(results) == 1
    assert "uv" in results[0][0]


def test_switched_to_because():
    results = extract_decisions("Switched to aiohttp because requests blocks the event loop.")
    assert len(results) == 1
    assert "aiohttp" in results[0][0]


def test_will_use_because():
    results = extract_decisions("Will use tree-sitter because it handles syntax errors gracefully.")
    assert len(results) == 1
    assert "tree-sitter" in results[0][0]


def test_opted_for_because():
    results = extract_decisions("Opted for a single goroutine because concurrency wasn't needed here.")
    assert len(results) == 1


def test_since_reason_clause():
    r1 = extract_decisions("Decided to use WAL mode since it allows concurrent reads.")
    assert len(r1) == 1


def test_as_not_a_reason_clause():
    # "as" was dropped — "use chi as the router" is not a decision
    assert extract_decisions("Use chi as the router for all API endpoints.") == []


# ---------------------------------------------------------------------------
# Multi-sentence text
# ---------------------------------------------------------------------------

def test_multiple_decisions_in_paragraph():
    text = (
        "We decided to use Go because the team knows it well. "
        "Went with chi over gin because chi has no external dependencies. "
        "This keeps the binary small."
    )
    results = extract_decisions(text)
    assert len(results) == 2


def test_deduplication():
    text = (
        "Decided to use Redis because it supports expiry. "
        "Decided to use Redis because it's fast."
    )
    results = extract_decisions(text)
    assert len(results) == 1


# ---------------------------------------------------------------------------
# No false positives
# ---------------------------------------------------------------------------

def test_no_match_on_plain_code():
    code = "func (r *Router) Use(middlewares ...func(http.Handler) http.Handler) {}"
    assert extract_decisions(code) == []


def test_no_match_on_short_sentence():
    assert extract_decisions("Use Redis.") == []


def test_no_match_without_reason_clause():
    assert extract_decisions("We decided to use PostgreSQL.") == []
    assert extract_decisions("Chose Go over Python.") == []


def test_empty_string():
    assert extract_decisions("") == []


def test_no_match_on_bash_output():
    output = "PASS\nok  \tgithub.com/go-chi/chi\t0.004s\n"
    assert extract_decisions(output) == []


# ---------------------------------------------------------------------------
# Integration tests for _auto_capture_decisions
# ---------------------------------------------------------------------------

def _make_db(tmp_path):
    return memory_db.connect(tmp_path / "memory.db")


def _seed_session(conn, session_id):
    import time
    epoch = int(time.time())
    conn.execute(
        "INSERT OR IGNORE INTO sessions (id, project, started_at_epoch, started_at) "
        "VALUES (?, 'test', ?, ?)",
        (session_id, epoch, "2026-01-01T00:00:00"),
    )
    conn.commit()


def test_auto_capture_inserts_with_source_auto(tmp_path):
    conn = _make_db(tmp_path)
    _seed_session(conn, "s1")
    text = "Decided to use Redis because it supports key expiry natively."
    count = _auto_capture_decisions(conn, text, session_id="s1", prompt_number=1, embedder=None)
    assert count == 1
    rows = conn.execute("SELECT source FROM decisions WHERE session_id = 's1'").fetchall()
    assert len(rows) == 1
    assert rows[0]["source"] == "auto"


def test_auto_capture_idempotent_on_retry(tmp_path):
    conn = _make_db(tmp_path)
    _seed_session(conn, "s1")
    text = "Went with goroutines because a worker pool adds unnecessary complexity."
    _auto_capture_decisions(conn, text, session_id="s1", prompt_number=1, embedder=None)
    _auto_capture_decisions(conn, text, session_id="s1", prompt_number=1, embedder=None)
    rows = conn.execute("SELECT id FROM decisions WHERE session_id = 's1'").fetchall()
    assert len(rows) == 1


def test_auto_capture_embedder_none_does_not_raise(tmp_path):
    conn = _make_db(tmp_path)
    _seed_session(conn, "s1")
    text = "Switched to aiohttp because requests blocks the event loop."
    count = _auto_capture_decisions(conn, text, session_id="s1", prompt_number=1, embedder=None)
    assert count == 1


def test_auto_capture_no_insert_on_no_match(tmp_path):
    conn = _make_db(tmp_path)
    _seed_session(conn, "s1")
    text = "func (r *Router) Use(middlewares ...func(http.Handler) http.Handler) {}"
    count = _auto_capture_decisions(conn, text, session_id="s1", prompt_number=1, embedder=None)
    assert count == 0
    rows = conn.execute("SELECT id FROM decisions").fetchall()
    assert len(rows) == 0

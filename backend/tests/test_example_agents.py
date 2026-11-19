"""Tests for the example agents (M7).

Covers the pure logic of ``examples/search_server.py``.  The full agent
loops (filesystem_agent, search_agent) require a live subprocess and are
exercised by ``just demo`` instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make ``examples/`` importable from within the backend test suite.
_EXAMPLES_DIR = Path(__file__).parent.parent.parent / "examples"
if str(_EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES_DIR))

from search_server import KNOWLEDGE_BASE, _fetch_page, _get_topics, _search  # noqa: E402


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------


def test_search_server_search_returns_matching_results():
    """search() returns results containing at least one query keyword."""
    results = _search("MCP protocol")
    assert len(results) >= 1
    for item in results:
        combined = (
            item["title"] + " " + item["body"] + " " + " ".join(item["tags"])
        ).lower()
        assert "mcp" in combined or "protocol" in combined


def test_search_server_search_result_count_cap():
    """search() returns at most 3 results regardless of how many match."""
    # A very broad query that likely matches everything
    results = _search("the a and or is in")
    assert len(results) <= 3


def test_search_server_search_no_match():
    """search() returns an empty list when no items match."""
    results = _search("zzznomatchxxx")
    assert results == []


# ---------------------------------------------------------------------------
# fetch_page()
# ---------------------------------------------------------------------------


def test_search_server_fetch_page_hit():
    """fetch_page() returns a non-empty body for a known URL."""
    url = KNOWLEDGE_BASE[0]["url"]
    body = _fetch_page(url)
    assert isinstance(body, str)
    assert len(body) > 0
    # Should NOT be an error message
    assert not body.startswith("error:")


def test_search_server_fetch_page_miss():
    """fetch_page() returns an error string (not an exception) for unknown URLs."""
    result = _fetch_page("https://example.com/does-not-exist")
    assert isinstance(result, str)
    assert "error" in result.lower()


# ---------------------------------------------------------------------------
# get_topics()
# ---------------------------------------------------------------------------


def test_search_server_get_topics_returns_list():
    """get_topics() returns a non-empty list of strings."""
    topics = _get_topics()
    assert isinstance(topics, list)
    assert len(topics) >= 1
    for t in topics:
        assert isinstance(t, str)


def test_search_server_get_topics_sorted():
    """get_topics() returns topics in sorted order."""
    topics = _get_topics()
    assert topics == sorted(topics)


def test_search_server_get_topics_covers_known_tags():
    """get_topics() includes tags present in the knowledge base."""
    topics = _get_topics()
    assert "mcp" in topics
    assert "tracing" in topics

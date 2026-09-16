from scwiki.cache.entry import Entry
from scwiki.cache.keys import make_key
from scwiki.cache.policy import expires_for
from scwiki.core.families import FAMILIES, SEARCH
from scwiki.core.requests import Query


def test_key_is_stable_across_include_order() -> None:
    a = make_key("vehicles", "x", Query(include=("ports", "components")))
    b = make_key("vehicles", "x", Query(include=("components", "ports")))
    assert a == b


def test_key_changes_with_version_and_identifier() -> None:
    base = Query(version="4.10.0")
    assert make_key("vehicles", "x", base) != make_key("vehicles", "x", Query(version="4.9.0"))
    assert make_key("vehicles", "x", base) != make_key("vehicles", "y", base)


def test_key_uses_star_for_lists_and_includes_filters_and_page() -> None:
    key = make_key("vehicles", None, Query(filter={"name": "Arrow"}, page=2))
    assert key.startswith("vehicles|*|")
    assert "name=Arrow" in key
    assert key != make_key("vehicles", None, Query(filter={"name": "Arrow"}, page=3))


def test_expires_for_versioned_is_none() -> None:
    assert expires_for(FAMILIES["vehicles"], is_list=False, now=100.0) is None
    assert expires_for(FAMILIES["vehicles"], is_list=True, now=100.0) is None


def test_expires_for_timed_families() -> None:
    week = 7 * 24 * 3600
    assert expires_for(FAMILIES["comm_links"], is_list=False, now=100.0) == 100.0 + week
    assert expires_for(FAMILIES["comm_links"], is_list=True, now=100.0) == 100.0 + 3600
    assert expires_for(SEARCH, is_list=True, now=0.0) == 300.0


def test_entry_freshness() -> None:
    assert Entry({}, stored_at=0.0, expires_at=None, version="v").is_fresh(10**9)
    e = Entry({}, stored_at=0.0, expires_at=50.0, version=None)
    assert e.is_fresh(49.9)
    assert not e.is_fresh(50.0)

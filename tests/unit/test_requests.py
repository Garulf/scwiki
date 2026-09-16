from datetime import timedelta

from scwiki.core.families import FAMILIES, Family
from scwiki.core.requests import Query, build_request, detail_path, list_path

BASE = "https://api.star-citizen.wiki/api"
UA = "scwiki/test"


def test_detail_url_with_include_and_version() -> None:
    fam = FAMILIES["vehicles"]
    q = Query(include=("ports",), version="4.10.0-LIVE.12519617")
    req = build_request(BASE, detail_path(fam, "aegs-avenger-stalker"), q, user_agent=UA)
    assert req.method == "GET"
    assert req.url == (
        f"{BASE}/vehicles/aegs-avenger-stalker?include=ports&version=4.10.0-LIVE.12519617"
    )


def test_list_url_encodes_filter_and_page_brackets() -> None:
    fam = FAMILIES["vehicles"]
    q = Query(filter={"name": "Arrow"}, page=2, page_size=200)
    req = build_request(BASE, list_path(fam), q, user_agent=UA)
    assert req.url == (
        f"{BASE}/vehicles?filter%5Bname%5D=Arrow&page%5Bnumber%5D=2&page%5Bsize%5D=200"
    )


def test_identifier_is_percent_encoded() -> None:
    fam = FAMILIES["celestial_objects"]
    path = detail_path(fam, "STANTON.PLANETS/ODD NAME")
    assert path == "celestial-objects/STANTON.PLANETS%2FODD%20NAME"


def test_headers_include_accept_and_user_agent() -> None:
    req = build_request(BASE, "stats/latest", Query(), user_agent=UA)
    assert req.headers["Accept"] == "application/json"
    assert req.headers["User-Agent"] == UA
    assert req.url == f"{BASE}/stats/latest"


def test_include_is_comma_joined_and_sort_and_locale_pass_through() -> None:
    q = Query(include=("ports", "components"), sort="-name", locale="de_DE")
    req = build_request(BASE, "vehicles", q, user_agent=UA)
    assert req.url == f"{BASE}/vehicles?include=ports%2Ccomponents&locale=de_DE&sort=-name"


def test_family_table_shape() -> None:
    assert FAMILIES["vehicles"].versioned is True
    assert FAMILIES["comm_links"].versioned is False
    assert FAMILIES["shipmatrix_vehicles"].path == "shipmatrix/vehicles"
    for fam in FAMILIES.values():
        assert isinstance(fam, Family)
        if fam.versioned:
            assert fam.detail_ttl is None and fam.list_ttl is None
        else:
            assert fam.detail_ttl is not None and fam.detail_ttl > timedelta(0)
            assert fam.list_ttl is not None and fam.list_ttl > timedelta(0)

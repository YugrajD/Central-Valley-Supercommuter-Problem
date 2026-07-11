"""API contract tests. Data-dependent cases skip cleanly on a fresh clone."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from repositories.base import get_repository

client = TestClient(app)
repo = get_repository()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.skipif(not repo.exists("sj_tracts"), reason="pipeline not run")
def test_baseline_geojson_shape():
    r = client.get("/baseline")
    assert r.status_code == 200
    gj = r.json()
    assert gj["type"] == "FeatureCollection"
    assert len(gj["features"]) == 174  # SJ County tracts
    props = gj["features"][0]["properties"]
    assert "geoid" in props
    assert "supercommuter_share" in props


def test_scenarios_catalog():
    r = client.get("/scenarios")
    assert r.status_code == 200
    ids = {s["id"] for s in r.json()}
    assert {"manteca_ace", "valley_link", "ace_double"} <= ids


def test_unknown_scenario_404():
    r = client.post("/scenario", json={"scenario_id": "not_a_thing"})
    assert r.status_code == 404


@pytest.mark.skipif(
    not (repo.exists("baseline_access") and repo.exists("scenario_access_valley_link")),
    reason="scenario cache not built",
)
def test_scenario_diff_payload():
    r = client.post("/scenario", json={"scenario_id": "valley_link", "cutoff_min": 60})
    assert r.status_code == 200
    body = r.json()
    assert body["scenario_id"] == "valley_link"
    assert {"total_delta", "tracts_improved", "top_gainers"} <= set(body["headline"])
    assert body["geojson"]["type"] == "FeatureCollection"
    props = body["geojson"]["features"][0]["properties"]
    assert {"baseline", "scenario", "delta"} <= set(props)

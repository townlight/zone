import copy
import json
import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from civiczone.geo_import import (
    GeoImportError,
    import_geojson,
    lookup_parcel,
    readiness,
)

FIXTURE = Path(__file__).parent / "fixtures" / "z1-town.json"
DB_URL = os.environ.get("CIVICZONE_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DB_URL, reason="CIVICZONE_TEST_DATABASE_URL is not set; skipping real-DB tests"
)

BOWTIE = [
    [-105.0005, 39.9997],
    [-105.0002, 39.9999],
    [-105.0005, 39.9999],
    [-105.0002, 39.9997],
    [-105.0005, 39.9997],
]


def _make_engine():
    return create_engine(DB_URL)


@pytest.fixture(scope="session")
def engine():
    e = _make_engine()
    yield e
    e.dispose()


@pytest.fixture
def setup_jur(engine):
    base = json.loads(FIXTURE.read_text())
    created = []

    def _make():
        j = "Z1-Fictional-" + uuid.uuid4().hex[:10]
        created.append(j)
        p = copy.deepcopy(base)
        p["jurisdiction"] = j
        return j, p

    yield _make

    with engine.begin() as conn:
        for j in created:
            conn.execute(
                text(
                    "DELETE FROM civiczone.parcels p USING civiczone.zones z "
                    "WHERE p.zone_id=z.id AND z.jurisdiction=:j"
                ),
                {"j": j},
            )
            for tbl in ("zones", "overlays", "geo_imports"):
                conn.execute(
                    text(f"DELETE FROM civiczone.{tbl} WHERE jurisdiction=:j"),
                    {"j": j},
                )


def test_import_lookup_roundtrip(engine, setup_jur):
    j, payload = setup_jur()
    actor = str(uuid.uuid4())
    assert readiness(engine)
    r = import_geojson(engine, payload, actor)
    assert r["idempotent"] is False
    assert r["is_current"] is True
    assert r["content_sha256"]

    res = lookup_parcel(engine, jurisdiction=j, query="P1")
    assert res.get("status") == "ok"
    zone = res["zone"]
    assert (zone["code"], zone["name"], zone["section_number"]) == (
        "R2",
        "Residential",
        "6.12.040",
    )
    assert "HIST" in {o["code"] for o in res["overlays"]}
    assert lookup_parcel(engine, jurisdiction=j, query="P2")["overlays"] == []
    assert res["source"]["source_id"] == "fictional-file-drop"
    assert res["source"]["version"] == "1"
    assert res["source"]["content_sha256"] == r["content_sha256"]
    assert res["disclaimer"]
    pid = res["parcel_id"]

    with engine.connect() as conn:
        stored = conn.execute(
            text("SELECT actor_id FROM civiczone.geo_imports WHERE id=:i"),
            {"i": r["id"]},
        ).scalar_one()
    assert str(stored) == actor

    e2 = _make_engine()
    try:
        res2 = lookup_parcel(e2, jurisdiction=j, query="P1")
        assert res2["parcel_id"] == pid
    finally:
        e2.dispose()

    again = import_geojson(engine, payload, actor)
    assert again["idempotent"] is True
    assert again["is_current"] is True
    assert again["content_sha256"] == r["content_sha256"]


def test_rejects_changed_identity_and_bowtie(engine, setup_jur):
    j, payload = setup_jur()
    import_geojson(engine, payload, str(uuid.uuid4()))

    altered = copy.deepcopy(payload)
    altered["parcels"]["features"][0]["properties"]["address"] = "CHANGED"
    with pytest.raises(GeoImportError):
        import_geojson(engine, altered, str(uuid.uuid4()))

    bow = copy.deepcopy(payload)
    bow["version"] = "2"
    bow["parcels"]["features"][0]["geometry"]["coordinates"] = [BOWTIE]
    with pytest.raises(GeoImportError):
        import_geojson(engine, bow, str(uuid.uuid4()))

    with engine.connect() as conn:
        n = conn.execute(
            text("SELECT count(*) FROM civiczone.geo_imports WHERE jurisdiction=:j"),
            {"j": j},
        ).scalar_one()
        cur = conn.execute(
            text(
                "SELECT version FROM civiczone.geo_imports "
                "WHERE jurisdiction=:j AND is_current"
            ),
            {"j": j},
        ).scalar_one()
    assert n == 1
    assert cur == "1"


def test_version2_archives_and_replay_no_rollback(engine, setup_jur):
    j, payload = setup_jur()
    r1 = import_geojson(engine, payload, str(uuid.uuid4()))

    p2_id = lookup_parcel(engine, jurisdiction=j, query="P2")["parcel_id"]
    p1_id = lookup_parcel(engine, jurisdiction=j, query="P1")["parcel_id"]

    v2 = copy.deepcopy(payload)
    v2["version"] = "2"
    v2["parcels"]["features"] = [
        f for f in v2["parcels"]["features"]
        if f["properties"]["parcel_number"] != "P2"
    ]
    import_geojson(engine, v2, str(uuid.uuid4()))

    assert lookup_parcel(engine, jurisdiction=j, query="P1")["parcel_id"] == p1_id

    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT is_active FROM civiczone.parcels "
                "WHERE id=:p"
            ),
            {"p": p2_id},
        ).mappings().one()
        old_payload = conn.execute(
            text("SELECT payload FROM civiczone.geo_imports WHERE id=:i"),
            {"i": r1["id"]},
        ).scalar_one()
        cur_ver = conn.execute(
            text(
                "SELECT version FROM civiczone.geo_imports "
                "WHERE jurisdiction=:j AND is_current"
            ),
            {"j": j},
        ).scalar_one()
    assert row["is_active"] is False
    nums = {f["properties"]["parcel_number"] for f in old_payload["parcels"]["features"]}
    assert "P2" in nums
    assert cur_ver == "2"

    replay = import_geojson(engine, payload, str(uuid.uuid4()))
    assert replay["is_current"] is False

    with engine.connect() as conn:
        still = conn.execute(
            text(
                "SELECT version FROM civiczone.geo_imports "
                "WHERE jurisdiction=:j AND is_current"
            ),
            {"j": j},
        ).scalar_one()
    assert still == "2"


def test_lookup_statuses(engine, setup_jur):
    r = lookup_parcel(engine, jurisdiction="Z1-Nope-" + uuid.uuid4().hex[:6], query="P1")
    assert r["status"] == "out_of_jurisdiction"

    j, payload = setup_jur()
    import_geojson(engine, payload, str(uuid.uuid4()))
    assert lookup_parcel(engine, jurisdiction=j, query="100-200-300")["status"] == "not_found"

    j2, payload2 = setup_jur()
    addr = payload2["parcels"]["features"][0]["properties"]["address"]
    payload2["parcels"]["features"][1]["properties"]["address"] = addr
    import_geojson(engine, payload2, str(uuid.uuid4()))
    assert lookup_parcel(engine, jurisdiction=j2, query=addr)["status"] == "ambiguous"


def _outside_boundary(p):
    p["parcels"]["features"][0]["geometry"]["coordinates"] = [
        [
            [-105.002, 39.9995],
            [-105.0015, 39.9995],
            [-105.0015, 39.9998],
            [-105.002, 39.9998],
            [-105.002, 39.9995],
        ]
    ]


def _crossing_two_zones(p):
    p["zones"]["features"][0]["geometry"]["coordinates"] = [
        [
            [-105.0004, 39.9994],
            [-104.9996, 39.9994],
            [-104.9996, 40.0004],
            [-105.0004, 40.0004],
            [-105.0004, 39.9994],
        ]
    ]
    p["zones"]["features"].append(
        {
            "type": "Feature",
            "id": "R3",
            "properties": {"code": "R3", "name": "Other", "section_number": "1.1.1"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-105.0008, 39.9994],
                        [-105.0004, 39.9994],
                        [-105.0004, 40.0004],
                        [-105.0008, 40.0004],
                        [-105.0008, 39.9994],
                    ]
                ],
            },
        }
    )


@pytest.mark.parametrize(
    "mutator",
    [
        lambda p: p.update(crs="EPSG:9999"),
        lambda p: p["parcels"]["features"].append(
            copy.deepcopy(p["parcels"]["features"][0])
        ),
        lambda p: p["zones"]["features"][0]["properties"].pop("section_number"),
        _outside_boundary,
        _crossing_two_zones,
    ],
)
def test_rejects_without_import_rows(engine, setup_jur, mutator):
    j, payload = setup_jur()
    mutator(payload)
    with pytest.raises(GeoImportError):
        import_geojson(engine, payload, str(uuid.uuid4()))
    with engine.connect() as conn:
        n = conn.execute(
            text("SELECT count(*) FROM civiczone.geo_imports WHERE jurisdiction=:j"),
            {"j": j},
        ).scalar_one()
    assert n == 0

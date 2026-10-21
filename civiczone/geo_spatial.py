import json

from sqlalchemy import text
from sqlalchemy.exc import DataError

from .geo_validate import GeoImportError


_ERR = "Invalid spatial data"


def _geom_obj(geom):
    if isinstance(geom, str):
        return json.loads(geom)
    return geom


def _geom_text(geom):
    return json.dumps(_geom_obj(geom), separators=(",", ":"))


def _normalize_items(items):
    normalized = []
    for item in items:
        normalized.append({**item, "geometry": _geom_obj(item["geometry"])})
    return normalized


def _exec(conn, sql, params):
    try:
        return conn.execute(text(sql), params)
    except DataError:
        raise GeoImportError(_ERR) from None


def _validate_geometries(conn, boundary_json, geometries):
    boundary = _exec(
        conn,
        """
        SELECT
          ST_IsValid(g) AS valid,
          ST_IsEmpty(g) AS empty,
          ST_SRID(g) AS srid,
          ST_Area(g) AS area
        FROM (
          SELECT ST_GeomFromGeoJSON(:boundary) AS g
        ) AS b
        """,
        {"boundary": boundary_json},
    ).one()

    if not boundary.valid or boundary.empty or boundary.srid != 4326 or boundary.area <= 0:
        raise GeoImportError(_ERR)

    if not geometries:
        return

    rows = _exec(
        conn,
        """
        WITH elems AS (
          SELECT elem, ord
          FROM jsonb_array_elements(CAST(:geoms AS jsonb)) WITH ORDINALITY AS t(elem, ord)
        ), parsed AS (
          SELECT ord, ST_GeomFromGeoJSON((elem)::text) AS geom
          FROM elems
        )
        SELECT
          ord,
          ST_IsValid(geom) AS valid,
          ST_IsEmpty(geom) AS empty,
          ST_SRID(geom) AS srid,
          ST_Area(geom) AS area,
          ST_CoveredBy(geom, ST_GeomFromGeoJSON(:boundary)) AS covered
        FROM parsed
        """,
        {
            "geoms": json.dumps(geometries),
            "boundary": boundary_json,
        },
    ).all()

    for row in rows:
        if (
            not row.valid
            or row.empty
            or row.srid != 4326
            or row.area <= 0
            or not row.covered
        ):
            raise GeoImportError(_ERR)


def _covering_zone(conn, parcel_json, zones_json):
    rows = _exec(
        conn,
        """
        WITH elems AS (
          SELECT elem, ord
          FROM jsonb_array_elements(CAST(:zones AS jsonb)) WITH ORDINALITY AS t(elem, ord)
        ), z AS (
          SELECT
            ord,
            elem->'properties' AS props,
            ST_GeomFromGeoJSON((elem->'geometry')::text) AS geom
          FROM elems
        )
        SELECT
          ord,
          props->>'code' AS code,
          ST_Covers(geom, ST_GeomFromGeoJSON(:parcel)) AS covers,
          ST_Area(ST_Intersection(geom, ST_GeomFromGeoJSON(:parcel))) AS inter_area
        FROM z
        """,
        {
            "zones": zones_json,
            "parcel": parcel_json,
        },
    ).all()

    covering = [row for row in rows if row.covers]
    positive = [row for row in rows if row.inter_area is not None and row.inter_area > 0]

    if len(covering) != 1:
        raise GeoImportError(_ERR)

    chosen = covering[0]
    if any(row.ord != chosen.ord for row in positive):
        raise GeoImportError(_ERR)

    return chosen.code


def _overlays_for_parcel(conn, parcel_json, overlays_json):
    rows = _exec(
        conn,
        """
        WITH elems AS (
          SELECT elem, ord
          FROM jsonb_array_elements(CAST(:overlays AS jsonb)) WITH ORDINALITY AS t(elem, ord)
        ), o AS (
          SELECT
            ord,
            elem->'properties' AS props,
            ST_GeomFromGeoJSON((elem->'geometry')::text) AS geom
          FROM elems
        )
        SELECT
          props->>'code' AS code,
          props->>'name' AS name,
          props->>'section_number' AS section_number
        FROM o
        WHERE ST_Area(ST_Intersection(geom, ST_GeomFromGeoJSON(:parcel))) > 0
        ORDER BY ord
        """,
        {
            "overlays": overlays_json,
            "parcel": parcel_json,
        },
    ).all()

    return [
        {
            "code": row.code,
            "name": row.name,
            "section_number": row.section_number,
        }
        for row in rows
    ]


def validate_spatial(conn, data):
    boundary = data["boundary"]
    if isinstance(boundary, dict) and "geometry" in boundary and "type" not in boundary:
        boundary = boundary["geometry"]

    zones = _normalize_items(data.get("zones") or [])
    parcels = _normalize_items(data.get("parcels") or [])
    overlays = _normalize_items(data.get("overlays") or [])

    boundary_json = _geom_text(boundary)
    geometries = (
        [zone["geometry"] for zone in zones]
        + [parcel["geometry"] for parcel in parcels]
        + [overlay["geometry"] for overlay in overlays]
    )
    _validate_geometries(conn, boundary_json, geometries)

    zones_json = json.dumps(zones)
    overlays_json = json.dumps(overlays)

    result = {}
    for parcel in parcels:
        properties = parcel.get("properties") or {}
        parcel_number = properties.get("parcel_number")
        parcel_json = _geom_text(parcel["geometry"])

        zone_code = _covering_zone(conn, parcel_json, zones_json)
        found_overlays = _overlays_for_parcel(conn, parcel_json, overlays_json)

        result[parcel_number] = {
            "zone_code": zone_code,
            "overlays": found_overlays,
        }

    return result

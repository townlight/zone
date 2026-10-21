import hashlib
import json
import math
import re
from datetime import date

DISCLAIMER = "Informational only; this is not a zoning determination."
MAX_BYTES = 10 * 1024 * 1024
MAX_FEATURES = 20000
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class GeoImportError(ValueError):
    pass


def _fail(message):
    raise GeoImportError(message)


def _str(obj, key, max_len=None, required=True):
    if key not in obj or obj[key] is None:
        if required:
            _fail("%s is required" % key)
        return ""
    value = obj[key]
    if not isinstance(value, str):
        _fail("%s must be a string" % key)
    value = value.strip()
    if required and not value:
        _fail("%s must be non-empty" % key)
    if max_len is not None and len(value) > max_len:
        _fail("%s exceeds %s characters" % (key, max_len))
    return value


def _point(point):
    if not isinstance(point, list) or len(point) != 2:
        _fail("coordinates must be 2D points")
    for value in point:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            _fail("coordinates must be finite numbers")
    if not (-180 <= point[0] <= 180) or not (-90 <= point[1] <= 90):
        _fail("coordinates outside valid lon/lat range")


def _ring(ring):
    if not isinstance(ring, list) or len(ring) < 4:
        _fail("ring must have at least 4 points")
    for point in ring:
        _point(point)
    if ring[0] != ring[-1]:
        _fail("ring must be closed")


def _polygon(polygon):
    if not isinstance(polygon, list) or not polygon:
        _fail("polygon must have rings")
    for ring in polygon:
        _ring(ring)


def _geometry(geometry):
    if not isinstance(geometry, dict):
        _fail("geometry must be an object")
    geom_type = geometry.get("type")
    if geom_type not in ("Polygon", "MultiPolygon"):
        _fail("geometry must be Polygon or MultiPolygon")
    coordinates = geometry.get("coordinates")
    if geom_type == "Polygon":
        _polygon(coordinates)
    else:
        if not isinstance(coordinates, list) or not coordinates:
            _fail("multipolygon must have polygons")
        for polygon in coordinates:
            _polygon(polygon)
    return geometry


def _zone_props(props, layer_name):
    return {
        "code": _str(props, "code", 80),
        "name": _str(props, "name", 255),
        "section_number": _str(props, "section_number", 255),
    }


def _overlay_props(props, layer_name):
    result = {"code": _str(props, "code", 80), "name": _str(props, "name", 255)}
    if "section_number" in props and props["section_number"] is not None:
        result["section_number"] = _str(props, "section_number", 255, required=False)
    return result


def _parcel_props(props, layer_name):
    return {
        "parcel_number": _str(props, "parcel_number", 120),
        "address": _str(props, "address", 500),
    }


def _layer(payload, name, require_features, build_props, duplicate_key):
    layer = payload.get(name)
    if not isinstance(layer, dict):
        _fail("%s must be an object" % name)
    if layer.get("type") != "FeatureCollection":
        _fail("%s must be a FeatureCollection" % name)
    features = layer.get("features")
    if not isinstance(features, list):
        _fail("%s.features must be a list" % name)
    if require_features and not features:
        _fail("%s must not be empty" % name)
    if len(features) > MAX_FEATURES:
        _fail("%s exceeds %s features" % (name, MAX_FEATURES))
    result = []
    ids = set()
    duplicates = set()
    for feature in features:
        if not isinstance(feature, dict):
            _fail("%s feature must be an object" % name)
        if feature.get("type") != "Feature":
            _fail("%s feature type must be Feature" % name)
        feature_id = _str(feature, "id")
        if feature_id in ids:
            _fail("duplicate feature id in %s" % name)
        ids.add(feature_id)
        props = feature.get("properties")
        if not isinstance(props, dict):
            _fail("properties must be an object")
        normalized_props = build_props(props, name)
        duplicate_value = normalized_props[duplicate_key]
        if duplicate_value in duplicates:
            _fail("duplicate %s in %s" % (duplicate_key, name))
        duplicates.add(duplicate_value)
        geometry = _geometry(feature.get("geometry"))
        result.append({
            "feature_id": feature_id,
            "properties": normalized_props,
            "geometry": geometry,
        })
    return result


def _source_date(payload):
    value = _str(payload, "source_date", 10)
    if not _DATE_RE.match(value):
        _fail("source_date must be YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError:
        _fail("source_date must be a valid date")
    return value


def prepare(payload, actor_id):
    if not isinstance(actor_id, str) or not actor_id.strip():
        _fail("actor_id must be non-empty")
    actor_id = actor_id.strip()
    if not isinstance(payload, dict):
        _fail("payload must be an object")
    try:
        original_json = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise GeoImportError("payload must be JSON serializable") from exc
    if len(original_json.encode("utf-8")) > MAX_BYTES:
        _fail("payload exceeds 10MiB")

    jurisdiction = _str(payload, "jurisdiction", 255)
    source_id = _str(payload, "source_id", 255)
    version = _str(payload, "version", 120)
    source_date = _source_date(payload)
    crs = _str(payload, "crs", 255)
    if crs != "EPSG:4326":
        _fail("crs must be EPSG:4326")

    boundary = _geometry(payload.get("boundary"))
    zones = _layer(payload, "zones", True, _zone_props, "code")
    parcels = _layer(payload, "parcels", True, _parcel_props, "parcel_number")
    overlays = _layer(payload, "overlays", False, _overlay_props, "code")

    return {
        "jurisdiction": jurisdiction,
        "source_id": source_id,
        "version": version,
        "source_date": source_date,
        "crs": crs,
        "boundary": boundary,
        "zones": zones,
        "parcels": parcels,
        "overlays": overlays,
        "payload": original_json,
        "content_sha256": hashlib.sha256(original_json.encode("utf-8")).hexdigest(),
        "actor_id": actor_id,
    }

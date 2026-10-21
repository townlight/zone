from fastapi.testclient import TestClient

from civiczone.main import app

client = TestClient(app)


def test_public_ui_route_returns_accessible_html() -> None:
    response = client.get("/civiczone")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    text = response.text

    assert '<html lang="en">' in text
    assert '<a class="skip-link" href="#main">Skip to main content</a>' in text
    assert '<main id="main" tabindex="-1">' in text
    assert "aria-live=\"polite\"" in text
    assert "v0.2.2 corrective demotion state" in text
    assert '<button id="run" type="submit">Run lookup</button>' in text


def test_public_ui_shows_real_api_workflow_bindings() -> None:
    response = client.get("/civiczone")
    text = response.text

    assert "123 Main St" in text
    assert "100-200-300" in text
    assert "sample city dataset" in text
    assert "R-2" in text
    assert "ADU" in text
    assert "Ã‚Â§" not in text
    assert "fetch(" in text
    assert "/api/v1/civiczone/parcels/lookup" in text
    assert "/api/v1/civiczone/questions/answer" in text


def test_public_ui_keeps_boundaries_actionable_and_honest() -> None:
    response = client.get("/civiczone")
    text = response.text

    assert "does not provide legal advice" in text
    assert "does not make a zoning determination" in text
    assert "does not replace your planning department" in text
    assert "Missing parcels explain" in text
    assert "Staff workspace" in text
    assert "Shipping v0.1.0" not in text
    assert "v0.1.0 public UI foundation" not in text
    assert "zoning determinations are available" not in text


def test_staff_ui_route_returns_browser_shell_without_embedded_staff_data() -> None:
    response = client.get("/civiczone/staff")
    text = response.text

    assert response.status_code == 200
    assert "Townlight Zoning staff workspace" in text
    assert "X-CivicZone-Principal" in text
    assert "X-CivicZone-Role" in text
    assert "/api/v1/civiczone/staff/questions/answer" in text
    assert "staff_only" not in text

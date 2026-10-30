"""Cited variance/CUP standards and process explanation, plus nonconformity flags.

Public-appropriate tests for the beta outcome: a resident question about a
variance or a conditional use permit gets the cited standard, the cited process
and the review path; a stated condition that is short of a cited standard raises
a REVIEW flag and never a determination; anything the loaded rules do not cover
is explicitly unavailable.

Synthetic fixture rules only (the package's own sample dataset).
"""
from fastapi.testclient import TestClient
import pytest
from civiczone.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # A file-backed SQLite rule dataset: real persistence, no city data.
    url = f"sqlite:///{tmp_path / 'rules.db'}"
    monkeypatch.setenv("CIVICZONE_PARCEL_RULE_DB_URL", url)
    # A configured rule database starts EMPTY on purpose: rules are loaded
    # explicitly and never invented. Seed the package's own sample dataset so the
    # cited-standard path can be exercised against real persistence.
    from civiczone.rule_lookup import RuleLookupRepository
    RuleLookupRepository(db_url=url, seed_defaults=True).engine.dispose()
    for name in ("CIVICZONE_PARCEL_DB_URL", "CIVICZONE_QUESTION_LEDGER_DB_URL",
                 "CIVICZONE_STAFF_WORKFLOW_DB_URL"):
        monkeypatch.delenv(name, raising=False)
    from civiczone import main
    def source(section):
        if section == 'synthetic-variance':
            return {'status':'ok','citation':{'section_number':'CMC 18.60 (synthetic)',
                'body_text':'Variance applications require a public hearing and the recorded hardship evidence.'}}
        if section == 'synthetic-cup':
            return {'status':'ok','citation':{'section_number':'CMC 18.64 (synthetic)',
                'body_text':'Conditional use permit applications require discretionary review and conditions may be imposed.'}}
        return None
    monkeypatch.setattr(main,'_process_source',source)
    with TestClient(app) as test_client:
        yield test_client


def explain(client, **body):
    body.setdefault('process_section', 'synthetic-cup' if 'conditional use' in body.get('question','') else 'synthetic-variance')
    response = client.post("/api/v1/civiczone/standards/process-explanation", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_variance_question_gets_the_cited_standard_and_process(client):
    payload = explain(client, question="Can I get a variance from the front setback?",
                      zone_code="R-2", rule_types=["front_setback"],
                      observed={"front_setback": "12 feet"})
    assert payload["status"] == "explained"
    assert payload["process"] == "variance"
    assert payload["standard_citation"].startswith("CMC 18.60")
    assert payload["standards"] == [{"rule_type": "front_setback",
                                     "value": "20 feet minimum",
                                     "citation": "CMC 18.20.050(A)"}]
    assert payload["review_required"] is True
    assert payload["determination_made"] is False
    assert "not a zoning determination" in payload["disclaimer"]
    # 12 ft is still short of the 20 ft minimum: a flag, not a decision.
    assert payload["flags"] and payload["flags"][0]["determination_made"] is False
    assert payload["flags"][0]["citation"] == "CMC 18.20.050(A)"


def test_cup_question_is_explained_as_a_distinct_process(client):
    payload = explain(client, question="Do I need a conditional use permit for a restaurant?",
                      zone_code="R-2", rule_types=[])
    assert payload["process"] == "cup"
    assert payload["label"] == "Conditional use permit"
    assert payload["standard_citation"].startswith("CMC 18.64")
    assert "discretionary review" in payload["what"]
    # No rule type was asked for, so no standard is invented.
    assert payload["standards"] == []
    assert payload["determination_made"] is False


def test_condition_that_meets_the_standard_raises_no_flag(client):
    payload = explain(client, question="Variance question about my side setback",
                      zone_code="R-2", rule_types=["front_setback"],
                      observed={"front_setback": "25 feet"})
    assert payload["status"] == "explained"
    assert payload["flags"] == []


def test_nonconformity_wording_produces_a_review_note_not_a_finding(client):
    payload = explain(client, question="My porch is pre-existing and nonconforming; "
                                       "do I need a variance to rebuild it?",
                      zone_code="R-2", rule_types=["front_setback"],
                      observed={"front_setback": "5 feet"})
    assert payload["process"] == "variance"
    assert payload["nonconformity_note"]
    assert "only staff can determine that status" in payload["nonconformity_note"].casefold() \
        or "only staff" in payload["nonconformity_note"].casefold()
    flag = payload["flags"][0]
    assert flag["review_required"] is True and flag["determination_made"] is False


def test_an_uncited_standard_is_explicitly_unavailable(client):
    payload = explain(client, question="Can I get a variance for my parking spaces?",
                      zone_code="R-2", rule_types=["parking_spaces"])
    assert payload["status"] == "explained"
    assert payload["standards"] == []
    assert any("unavailable, not assumed" in line for line in payload["review"])


def test_a_non_process_question_is_refused_not_answered(client):
    payload = explain(client, question="What is the capital of France?")
    assert payload["status"] == "unavailable"
    assert payload["reason"]
    assert payload["fix"]
    assert payload["review_required"] is True


def test_no_zone_code_states_that_no_standard_could_be_cited(client):
    payload = explain(client, question="Do I need a variance?",
                      rule_types=["front_setback"])
    assert payload["status"] == "explained"
    assert payload["standards"] == []
    assert any("No zone code was supplied" in line for line in payload["review"])


def test_existing_rules_and_parcel_endpoints_still_answer(client):
    use = client.post("/api/v1/civiczone/rules/use",
                      json={"zone_code": "R-2", "use": "adu"})
    assert use.status_code == 200, use.text
    assert use.json()["citation"].startswith("CMC")
    dim = client.post("/api/v1/civiczone/rules/dimensional",
                      json={"zone_code": "R-2", "rule_type": "front_setback"})
    assert dim.status_code == 200, dim.text
    assert dim.json()["value"] == "20 feet minimum"
    parcel = client.post("/api/v1/civiczone/parcels/lookup",
                         json={"parcel_number": "100-200-300"})
    assert parcel.status_code == 200, parcel.text
    # The shipped parcel contract nests zone context: {"zone": {"code", "name"}}.
    assert parcel.json()["zone"]["code"] == "R-2"
    missing = client.post("/api/v1/civiczone/parcels/lookup",
                          json={"parcel_number": "999-999-999"})
    assert missing.status_code == 404


def test_public_page_states_the_process_boundary(client):
    page = client.get("/civiczone")
    assert page.status_code == 200
    text = page.text
    assert "Variance, conditional use and nonconformity" in text
    assert "possible nonconformity review flag" in text.lower()
    assert "never declares" in text.lower()
    assert "No standard is estimated" in text


def test_process_source_is_required_even_without_dimensional_rules():
    from civiczone.discretionary import explain as domain_explain, Unavailable
    result=domain_explain('variance',repository=None,zone_code='AUDIT-ZONE')
    assert isinstance(result,Unavailable)


def test_two_jurisdictions_changed_missing_and_unrelated_process_sources():
    from civiczone.discretionary import explain as domain_explain, Unavailable
    for section,text in [('A 6','Variance review by the synthetic A board.'),('B 9','Variance review by the synthetic B council.')]:
        result=domain_explain('variance',repository=None,process_source={
            'status':'ok','citation':{'section_number':section,'body_text':text}})
        assert result.standard_citation==section and result.what==text
    for source in [None,{'status':'refused'}, {'status':'ok','citation':{'section_number':'Library 1','body_text':'Library opens at nine.'}}]:
        assert isinstance(domain_explain('variance',repository=None,process_source=source),Unavailable)

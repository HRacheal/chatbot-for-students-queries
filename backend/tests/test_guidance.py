"""Degree guidance: upload validation, grade extraction and transparent recommendations.

All results slips here are synthetic. Programme requirements are synthetic test records,
not real USIU-Africa requirements.
"""

import io

import pytest

from services.guidance_service import GRADE_POINTS, GuidanceService, extract_grades, validate_grades

SLIP = """KENYA CERTIFICATE OF SECONDARY EDUCATION (SYNTHETIC TEST)
CANDIDATE NAME: TEST CANDIDATE   INDEX NO: 00000000000
101 ENGLISH            B+
102 KISWAHILI          B
121 MATHEMATICS ALT A  A-
231 BIOLOGY            B
233 CHEMISTRY          C+
311 HISTORY & GOVERNMENT  A
443 AGRICULTURE        B-
MEAN GRADE: B+
"""

PROGRAMME_URL = "https://www.usiu.ac.ke/synthetic-programme/"


def requirement(**changes):
    return {"programme": "Synthetic Science Programme", "level": "undergraduate", "url": PROGRAMME_URL,
            "min_mean_grade": "C+", "subject_requirements": [{"subjects": ["Mathematics"], "min_grade": "C+"}],
            "verified": True, **changes}


def upload(client, name, data, content_type="application/octet-stream"):
    return client.post("/api/guidance/extract", data={"file": (io.BytesIO(data), name, content_type)},
                       content_type="multipart/form-data")


def test_grades_are_extracted_without_personal_details():
    result = extract_grades(SLIP)
    grades = {s["subject"]: s["grade"] for s in result["subjects"]}
    assert grades == {"English": "B+", "Kiswahili": "B", "Mathematics": "A-", "Biology": "B",
                      "Chemistry": "C+", "History and Government": "A", "Agriculture": "B-"}
    assert result["mean_grade"] == "B+"
    assert "TEST CANDIDATE" not in str(result) and "00000000000" not in str(result)


def test_unrecognised_text_asks_for_manual_entry():
    result = extract_grades("This is a letter with no grades in it.")
    assert result["subjects"] == [] and "enter them manually" in result["warnings"][0]


def test_text_upload_is_processed(client):
    response = upload(client, "results.txt", SLIP.encode())
    assert response.status_code == 200
    body = response.get_json()
    assert body["needs_confirmation"] is True and len(body["subjects"]) == 7
    assert "not stored" in body["message"]


def test_pdf_upload_is_processed(client):
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    for i, line in enumerate(SLIP.splitlines()):
        pdf.drawString(50, 800 - 16 * i, line)
    pdf.save()
    response = upload(client, "slip.pdf", buffer.getvalue(), "application/pdf")
    assert response.status_code == 200
    assert {s["subject"] for s in response.get_json()["subjects"]} >= {"English", "Mathematics"}


@pytest.mark.parametrize("name,data,message", [
    ("photo.jpg", b"\xff\xd8\xff\xe0 fake jpeg", "Photos and scanned images"),
    ("slip.docx", b"PK\x03\x04", "Unsupported file type"),
    ("slip.exe", b"MZ", "Unsupported file type"),
    ("fake.pdf", b"this is not a pdf", "not a valid PDF"),
    ("empty.txt", b"", "empty"),
    ("binary.txt", b"\x00\x01\x02", "not valid"),
])
def test_invalid_uploads_are_rejected(client, name, data, message):
    response = upload(client, name, data)
    assert response.status_code == 400 and message in response.get_json()["error"]


def test_missing_file_and_oversized_file(make_app):
    client = make_app(GUIDANCE_MAX_UPLOAD_MB=1).test_client()
    assert client.post("/api/guidance/extract", data={}, content_type="multipart/form-data").status_code == 400
    response = upload(client, "big.txt", b"a" * (1024 * 1024 + 10))
    assert response.status_code == 400 and "too large" in response.get_json()["error"]


def test_grade_validation():
    with pytest.raises(ValueError):
        validate_grades({"subjects": []})
    with pytest.raises(ValueError):
        validate_grades({"subjects": [{"subject": "Astrology", "grade": "A"}]})
    with pytest.raises(ValueError):
        validate_grades({"subjects": [{"subject": "English", "grade": "F"}]})
    subjects, mean, estimated = validate_grades({"subjects": [{"subject": "eng", "grade": "b+"}]})
    assert subjects == {"English": "B+"} and mean is None and estimated
    seven = [{"subject": s, "grade": "B"} for s in ("English", "Kiswahili", "Mathematics", "Biology",
                                                    "Chemistry", "Geography", "Agriculture")]
    assert validate_grades({"subjects": seven})[1:] == ("B", True)
    assert GRADE_POINTS["A"] == 12 and GRADE_POINTS["E"] == 1


def test_no_verified_requirements_means_no_recommendations(client, admin_headers):
    # An unverified requirement record is not used.
    client.post("/api/admin/programme-requirements", json=requirement(verified=False), headers=admin_headers)
    body = client.post("/api/guidance/recommend", json={"subjects": [{"subject": "Mathematics", "grade": "A"}],
                                                        "mean_grade": "A"}).get_json()
    assert body["status"] == "no_verified_requirements" and body["recommendations"] == []
    assert "not an admission decision" in body["disclaimer"]
    assert all(p["verified"] is False for p in body["places_to_look"])


def test_recommendations_use_verified_requirements_with_reasons(client, admin_headers):
    created = client.post("/api/admin/programme-requirements", json=requirement(), headers=admin_headers)
    assert created.status_code == 201
    client.post("/api/admin/programme-requirements", headers=admin_headers, json=requirement(
        programme="Synthetic Arts Programme", min_mean_grade="A", subject_requirements=[]))
    client.post("/api/admin/programme-requirements", headers=admin_headers, json=requirement(
        programme="Synthetic Lab Programme", min_mean_grade=None,
        subject_requirements=[{"subjects": ["Physics"], "min_grade": "C"}]))

    body = client.post("/api/guidance/recommend", json={
        "subjects": [{"subject": "Mathematics", "grade": "B"}, {"subject": "English", "grade": "B+"}],
        "mean_grade": "B+"}).get_json()
    assert body["status"] == "ok"
    outcomes = {r["programme"]: r["outcome"] for r in body["recommendations"]}
    assert outcomes == {"Synthetic Science Programme": "meets_listed_requirements",
                        "Synthetic Lab Programme": "incomplete_information",
                        "Synthetic Arts Programme": "below_listed_requirements"}
    assert [r["outcome"] for r in body["recommendations"]][0] == "meets_listed_requirements"
    science = body["recommendations"][0]
    assert science["url"] == PROGRAMME_URL
    assert any("Mathematics B meets" in reason for reason in science["reasons"])
    assert "not an admission decision" in body["disclaimer"]


def test_requirement_records_are_validated_and_admin_only(client, admin_headers, user_headers):
    url = "/api/admin/programme-requirements"
    assert client.post(url, json=requirement()).status_code == 401
    assert client.post(url, json=requirement(), headers=user_headers).status_code == 403
    assert client.get(url, headers=user_headers).status_code == 403
    for bad in (requirement(url="https://cx.usiu.ac.ke/ics/"), requirement(url="https://example.com/"),
                requirement(min_mean_grade="Z"), requirement(min_mean_grade=None, subject_requirements=[]),
                requirement(subject_requirements=[{"subjects": ["Astrology"], "min_grade": "C"}]),
                requirement(programme="")):
        assert client.post(url, json=bad, headers=admin_headers).status_code == 400
    created = client.post(url, json=requirement(verified=False), headers=admin_headers).get_json()["requirement"]
    updated = client.put(f"{url}/{created['id']}", json=requirement(), headers=admin_headers).get_json()["requirement"]
    assert updated["verified"] is True and updated["verified_at"]
    assert client.delete(f"{url}/{created['id']}", headers=admin_headers).status_code == 200
    assert client.delete(f"{url}/{created['id']}", headers=admin_headers).status_code == 404


def test_evaluate_uses_best_of_alternative_subjects():
    outcome, reasons = GuidanceService.evaluate(
        {"subject_requirements": [{"subjects": ["Physics", "Chemistry"], "min_grade": "C+"}]},
        {"Physics": "C", "Chemistry": "B"}, None)
    assert outcome == "meets_listed_requirements" and "Chemistry B" in reasons[0]


def test_options_endpoint(client):
    body = client.get("/api/guidance/options").get_json()
    assert "Mathematics" in body["subjects"] and body["grades"][0] == "A"
    assert body["verified_programmes"] == 0

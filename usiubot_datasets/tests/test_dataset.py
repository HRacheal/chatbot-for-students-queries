"""Tests for the USIUBOT dataset. Run from the project root:

    backend/.venv/Scripts/python.exe -m pytest usiubot_datasets/tests -q -p no:cacheprovider
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

D = Path(__file__).resolve().parents[1]
SCRIPTS = D / "extraction_scripts"
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPTS))
import web_common as C  # noqa: E402


def rows(rel):
    with open(D / rel, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def test_validator_has_no_blocking_failures():
    r = subprocess.run([sys.executable, str(SCRIPTS / "validate_dataset.py")], capture_output=True, text=True,
                       encoding="utf-8", env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1",
                                              "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, r.stdout[-3000:]


def test_bank_details_are_never_confirmed():
    for r in rows("04_fees_and_payments/official/web_bank_and_mobile_payment_details.csv"):
        assert r["risk_level"].startswith("HIGH") and "Finance Office" in r["risk_level"]
        assert r["approval_status"] == "not_approved"
    for r in rows("04_fees_and_payments/official/bank_details_comparison.csv"):
        assert r["status"].startswith("UNCONFIRMED")


def test_external_records_are_labelled():
    files = list(D.glob("0*/external/external_records.csv"))
    assert files
    for f in files:
        for r in rows(f.relative_to(D)):
            assert r["source_type"] == "external"
            assert "not USIU-Africa policy" in r["external_label"]
            assert "usiu.ac.ke" not in r["source_url"]


def test_web_chunks_keep_heading_and_size():
    for f in D.glob("0*/*/web_knowledge_chunks.json"):
        for c in json.loads(f.read_text(encoding="utf-8")):
            assert c["content_chars"] <= 1000
            assert c["content"].startswith(c["heading_path"][0])
            assert c["source_url"].startswith("https://")
            assert c["approval_status"] == "not_approved"


def test_fee_tables_add_up():
    checks = rows("validation_reports/fee_table_checks.csv")
    assert checks and all(c["arithmetic_check"] == "pass" for c in checks)


def test_conflicts_keep_both_versions():
    reg = {r["issue_id"]: r for r in rows("validation_reports/conflict_and_verification_register.csv")}
    w11 = reg["W11"]["website_evidence"]
    assert "49%" in w11 and "90 trimester units" in w11
    tr = rows("07_academic_documents_results_and_verified_eligibility/official/web_transfer_credit_rules.csv")
    assert {"TRF-WEB-01", "TRF-WEB-02"} <= {r["record_id"] for r in tr}


def test_expired_deadlines_are_marked():
    aid = {r["record_id"]: r for r in rows("04_fees_and_payments/official/web_financial_aid_programmes.csv")}
    for rid in ("AID-WEB-17", "AID-WEB-18"):
        assert "Deadline passed" in aid[rid]["validity_note"]


def test_category_08_has_no_invented_enquiries():
    for r in rows("08_questions_answers_and_unresolved_enquiries/official/open_questions_register.csv"):
        assert "NOT a real student enquiry" in r["record_origin"]
    for r in rows("08_questions_answers_and_unresolved_enquiries/official/official_faq_pairs.csv"):
        assert r["source_url"].startswith("https://www.usiu.ac.ke/")


def test_original_pdfs_unchanged():
    integ = json.loads((D / "validation_reports/pdf_integrity.json").read_text(encoding="utf-8"))["files"]
    for name, v in integ.items():
        assert C.sha256_file(C.PROJECT / name) == v["baseline_sha256"]


def test_every_web_record_has_traceability_fields():
    required = ["record_id", "category_id", "topic", "information", "source_title", "source_url", "date_collected",
                "publication_date", "source_type", "verification_status", "last_checked"]
    for f in D.glob("0*/*/web_*.csv"):
        if f.name.endswith("sections_index.csv"):
            continue
        for r in rows(f.relative_to(D)):
            for k in required:
                assert r.get(k), f"{f.name} {r.get('record_id')} missing {k}"

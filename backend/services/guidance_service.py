"""Degree guidance from a results slip (admissions-guidance agent).

1. ``extract`` reads subjects and grades from an uploaded text-based PDF or text file.
   The file is processed in memory and never stored, logged or sent to any external
   service. Names, index numbers and other identifiers are not returned. Scanned
   images and photos cannot be read (no OCR is installed), so the user is asked to
   enter grades manually instead.
2. The user checks and corrects the extracted grades.
3. ``recommend`` compares the confirmed grades with programme entry requirements that
   an administrator has recorded *and verified* against an official USIU-Africa page.
   Each programme gets a transparent result with the reasons. Without verified
   requirements no programme is recommended; the user is pointed to official pages.

Recommendations are guidance only, never an admission decision.

Grade points use the 12-point KCSE scale (A = 12 ... E = 1).
"""

import datetime
import logging
import re

from models.models import to_object_id
from services.sources import tokenize

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "This is guidance only, not an admission decision. Only USIU-Africa Admissions can confirm "
    "eligibility. Please check the official programme page and contact Admissions before applying."
)

GRADES = ("A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "E")
GRADE_POINTS = {g: 12 - i for i, g in enumerate(GRADES)}
POINTS_GRADE = {p: g for g, p in GRADE_POINTS.items()}

# KCSE subject names and common abbreviations on results slips.
SUBJECTS = {
    "English": ["english", "eng"],
    "Kiswahili": ["kiswahili", "kis", "kisw"],
    "Mathematics": ["mathematics", "maths", "math", "mat", "mathematics alt a", "mathematics alt b"],
    "Biology": ["biology", "bio"],
    "Physics": ["physics", "phy"],
    "Chemistry": ["chemistry", "che", "chem"],
    "General Science": ["general science", "gsc"],
    "History and Government": ["history and government", "history & government", "history", "hag", "hist"],
    "Geography": ["geography", "geo"],
    "Christian Religious Education": ["christian religious education", "cre", "c.r.e"],
    "Islamic Religious Education": ["islamic religious education", "ire", "i.r.e"],
    "Hindu Religious Education": ["hindu religious education", "hre"],
    "Home Science": ["home science", "hsc"],
    "Art and Design": ["art and design", "art & design", "art"],
    "Agriculture": ["agriculture", "agr", "agric"],
    "Computer Studies": ["computer studies", "computer", "comp"],
    "Business Studies": ["business studies", "business", "bst"],
    "French": ["french", "fre"],
    "German": ["german", "ger"],
    "Arabic": ["arabic", "ara"],
    "Music": ["music", "mus"],
    "Kenya Sign Language": ["kenya sign language", "ksl"],
    "Woodwork": ["woodwork"],
    "Metalwork": ["metalwork"],
    "Building Construction": ["building construction"],
    "Power Mechanics": ["power mechanics"],
    "Electricity": ["electricity"],
    "Drawing and Design": ["drawing and design"],
    "Aviation Technology": ["aviation technology", "aviation"],
}
_ALIASES = sorted(((alias, name) for name, aliases in SUBJECTS.items() for alias in aliases),
                  key=lambda item: -len(item[0]))
GRADE_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])(A-|A|B\+|B-|B|C\+|C-|C|D\+|D-|D|E)(?![A-Za-z0-9+])")
MEAN_GRADE_RE = re.compile(r"mean\s*grade\W{0,5}(?:[0-9.]+\s*)?(A-|A|B\+|B-|B|C\+|C-|C|D\+|D-|D|E)(?![A-Za-z0-9+])",
                           re.IGNORECASE)

ALLOWED_EXTENSIONS = {".pdf": "pdf", ".txt": "text"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".heic", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
LEVELS = ("undergraduate", "postgraduate", "diploma")


class GuidanceError(ValueError):
    """Invalid upload or input. The message is safe to show to users."""


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def normalise_grade(value):
    if not isinstance(value, str):
        return None
    value = value.strip().upper().replace(" ", "").replace("PLAIN", "")
    return value if value in GRADE_POINTS else None


def normalise_subject(value):
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    for name in SUBJECTS:
        if text == name.lower():
            return name
    for alias, name in _ALIASES:
        if text == alias:
            return name
    return None


# --- extraction ---------------------------------------------------------------------
def read_upload(filename, data, max_bytes):
    """Validate an upload and return its text. Raises GuidanceError."""
    from utils.pdf_utils import extract_pdf_text, is_pdf_bytes

    name = (filename or "").lower()
    ext = name[name.rfind("."):] if "." in name else ""
    if ext in IMAGE_EXTENSIONS:
        raise GuidanceError("Photos and scanned images can't be read automatically yet. "
                            "Please enter your subjects and grades manually.")
    if ext not in ALLOWED_EXTENSIONS:
        raise GuidanceError("Unsupported file type. Upload a PDF or a .txt file, or enter your grades manually.")
    if not data:
        raise GuidanceError("The file is empty.")
    if len(data) > max_bytes:
        raise GuidanceError(f"The file is too large (limit {max_bytes // (1024 * 1024)} MB).")
    if ALLOWED_EXTENSIONS[ext] == "pdf":
        if not is_pdf_bytes(data):
            raise GuidanceError("The file is not a valid PDF.")
        try:
            text = extract_pdf_text(data, max_pages=5)
        except Exception:
            raise GuidanceError("The PDF could not be read (it may be damaged or password-protected).")
        if len(text.strip()) < 10:
            raise GuidanceError("This PDF has no readable text (it may be a scan). "
                                "Please enter your subjects and grades manually.")
        return text
    if b"\x00" in data[:4096]:
        raise GuidanceError("The text file is not valid.")
    return data.decode("utf-8", errors="replace")


def extract_grades(text):
    """Return ``{"subjects": [{"subject", "grade"}], "mean_grade", "warnings"}``.

    Only subject names and grades are returned; other content (names, index numbers,
    school details) is ignored and not kept.
    """
    found, warnings = {}, []
    mean_grade = None
    for raw_line in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        mean = MEAN_GRADE_RE.search(line)
        if mean:
            mean_grade = mean.group(1)
            continue
        lowered = line.lower()
        for alias, name in _ALIASES:
            match = re.search(r"(?<![a-z])" + re.escape(alias) + r"(?![a-z])", lowered)
            if not match:
                continue
            grades = GRADE_TOKEN_RE.findall(line[match.end():])
            if grades:
                grade = grades[-1]
                if name in found and found[name] != grade:
                    warnings.append(f"{name} appears more than once with different grades; please check it.")
                found[name] = grade
            break
    if not found:
        warnings.append("No subjects and grades were recognised. Please enter them manually.")
    return {
        "subjects": [{"subject": s, "grade": g} for s, g in found.items()],
        "mean_grade": mean_grade,
        "warnings": warnings,
    }


# --- confirmed grades -----------------------------------------------------------------
def validate_grades(data):
    """Check user-confirmed grades. Returns ``(subjects_dict, mean_grade, mean_is_estimated)``."""
    items = data.get("subjects")
    if not isinstance(items, list) or not items:
        raise GuidanceError("Enter at least one subject and grade.")
    if len(items) > 15:
        raise GuidanceError("Too many subjects.")
    subjects = {}
    for item in items:
        if not isinstance(item, dict):
            raise GuidanceError("Each subject needs a name and a grade.")
        subject = normalise_subject(item.get("subject"))
        grade = normalise_grade(item.get("grade"))
        if not subject:
            raise GuidanceError(f"Unknown subject: {str(item.get('subject'))[:50]}")
        if not grade:
            raise GuidanceError(f"Grade for {subject} must be one of: " + ", ".join(GRADES))
        subjects[subject] = grade
    mean = data.get("mean_grade")
    if mean not in (None, ""):
        mean = normalise_grade(mean)
        if not mean:
            raise GuidanceError("Mean grade must be one of: " + ", ".join(GRADES))
        return subjects, mean, False
    # Estimate from the best seven subjects (rounded down), clearly labelled as an estimate.
    points = sorted((GRADE_POINTS[g] for g in subjects.values()), reverse=True)[:7]
    if len(points) < 7:
        return subjects, None, True
    return subjects, POINTS_GRADE[max(1, int(sum(points) / 7))], True


class GuidanceService:
    def __init__(self, db_getter, settings, catalogue=None, is_trusted=None):
        self._db = db_getter
        self.settings = settings
        self.catalogue = catalogue
        self.is_trusted = is_trusted or (lambda url: False)

    @property
    def collection(self):
        return self._db("programme_requirements")

    # --- requirement records (admin) ------------------------------------------------------
    def _validated_requirement(self, data):
        programme = data.get("programme")
        if not isinstance(programme, str) or not programme.strip() or len(programme) > 200:
            raise GuidanceError("Programme name is required")
        level = data.get("level") or "undergraduate"
        if level not in LEVELS:
            raise GuidanceError("Level must be one of: " + ", ".join(LEVELS))
        url = (data.get("url") or "").strip()
        if not self.is_trusted(url):
            raise GuidanceError("Source URL must be an official https page on a trusted USIU-Africa host")
        source_date = (data.get("source_date") or "").strip()
        if source_date and not re.match(r"^\d{4}(-\d{2}(-\d{2})?)?$", source_date):
            raise GuidanceError("Source date must be YYYY, YYYY-MM or YYYY-MM-DD")
        min_mean = data.get("min_mean_grade") or None
        if min_mean is not None and not normalise_grade(min_mean):
            raise GuidanceError("Minimum mean grade must be one of: " + ", ".join(GRADES))
        rules = []
        for rule in data.get("subject_requirements") or []:
            if not isinstance(rule, dict):
                raise GuidanceError("Each subject requirement needs subjects and a minimum grade")
            names = [normalise_subject(s) for s in (rule.get("subjects") or [])]
            grade = normalise_grade(rule.get("min_grade"))
            if not names or None in names or not grade:
                raise GuidanceError("Each subject requirement needs known subjects and a valid minimum grade")
            rules.append({"subjects": names, "min_grade": grade})
        if not min_mean and not rules:
            raise GuidanceError("Record at least a minimum mean grade or one subject requirement")
        notes = (data.get("notes") or "").strip()[:1000]
        keywords = [str(k).strip()[:40] for k in (data.get("keywords") or []) if str(k).strip()][:20]
        return {
            "programme": programme.strip(), "level": level, "url": url, "source_date": source_date or None,
            "min_mean_grade": normalise_grade(min_mean) if min_mean else None,
            "subject_requirements": rules, "notes": notes, "keywords": keywords,
            "verified": data.get("verified") is True,
        }

    def create_requirement(self, data, actor="admin"):
        doc = self._validated_requirement(data)
        now = utcnow()
        doc.update(created_at=now, updated_at=now, verified_by=actor if doc["verified"] else None,
                   verified_at=now if doc["verified"] else None)
        doc["_id"] = self.collection.insert_one(doc).inserted_id
        return doc

    def update_requirement(self, requirement_id, data, actor="admin"):
        oid = to_object_id(requirement_id)
        if oid is None or not self.collection.find_one({"_id": oid}):
            return None
        doc = self._validated_requirement(data)
        now = utcnow()
        doc.update(updated_at=now, verified_by=actor if doc["verified"] else None,
                   verified_at=now if doc["verified"] else None)
        self.collection.update_one({"_id": oid}, {"$set": doc})
        return self.collection.find_one({"_id": oid})

    def delete_requirement(self, requirement_id):
        oid = to_object_id(requirement_id)
        return bool(oid) and self.collection.delete_one({"_id": oid}).deleted_count > 0

    def list_requirements(self, verified_only=False):
        query = {"verified": True} if verified_only else {}
        return list(self.collection.find(query).sort("programme", 1))

    # --- recommendation ---------------------------------------------------------------------
    @staticmethod
    def evaluate(requirement, subjects, mean_grade):
        """Compare grades with one requirement. Returns ``(outcome, reasons)``."""
        reasons, missing, failed = [], False, False
        if requirement.get("min_mean_grade"):
            needed = requirement["min_mean_grade"]
            if mean_grade is None:
                missing = True
                reasons.append(f"Needs a mean grade of {needed} or above; your mean grade is not known.")
            elif GRADE_POINTS[mean_grade] >= GRADE_POINTS[needed]:
                reasons.append(f"Mean grade {mean_grade} meets the listed minimum of {needed}.")
            else:
                failed = True
                reasons.append(f"Mean grade {mean_grade} is below the listed minimum of {needed}.")
        for rule in requirement.get("subject_requirements", []):
            options = " or ".join(rule["subjects"])
            have = [(s, subjects[s]) for s in rule["subjects"] if s in subjects]
            if not have:
                missing = True
                reasons.append(f"Needs {options} at {rule['min_grade']} or above; not in your results.")
                continue
            best_subject, best_grade = max(have, key=lambda item: GRADE_POINTS[item[1]])
            if GRADE_POINTS[best_grade] >= GRADE_POINTS[rule["min_grade"]]:
                reasons.append(f"{best_subject} {best_grade} meets the listed minimum of {rule['min_grade']}.")
            else:
                failed = True
                reasons.append(f"Needs {options} at {rule['min_grade']} or above; you have {best_subject} {best_grade}.")
        if failed:
            return "below_listed_requirements", reasons
        if missing:
            return "incomplete_information", reasons
        return "meets_listed_requirements", reasons

    def recommend(self, data):
        subjects, mean_grade, estimated = validate_grades(data)
        interests = data.get("interests") if isinstance(data.get("interests"), str) else ""
        interest_terms = set(tokenize(interests[:300]))
        requirements = self.list_requirements(verified_only=True)
        response = {
            "disclaimer": DISCLAIMER,
            "grades": [{"subject": s, "grade": g, "points": GRADE_POINTS[g]} for s, g in subjects.items()],
            "mean_grade": mean_grade,
            "mean_grade_estimated": estimated and mean_grade is not None,
            "criteria": ("Each programme's entry requirements, as recorded by USIU staff from the linked official "
                         "page, are compared with the grades you confirmed (KCSE 12-point scale)."),
        }
        if estimated:
            response["mean_grade_note"] = (
                "Mean grade estimated from your best seven subjects; the official KCSE mean grade on your "
                "certificate takes precedence." if mean_grade else
                "Mean grade not given and fewer than seven subjects were entered, so it could not be estimated.")
        if not requirements:
            response.update(
                status="no_verified_requirements",
                message=("USIUBOT does not yet have verified programme entry requirements, so it cannot recommend "
                         "programmes. These official pages may list programmes and requirements (not checked):"),
                recommendations=[],
                places_to_look=self._places_to_look(interests or "undergraduate programmes admission requirements"),
            )
            return response
        results = []
        for req in requirements:
            outcome, reasons = self.evaluate(req, subjects, mean_grade)
            relevance = len(interest_terms & set(tokenize(req["programme"] + " " + " ".join(req.get("keywords", [])))))
            results.append({
                "programme": req["programme"], "level": req["level"], "url": req["url"],
                "source_date": req.get("source_date"), "outcome": outcome, "reasons": reasons,
                "notes": req.get("notes") or None, "matches_interests": relevance > 0,
                "_rank": ({"meets_listed_requirements": 0, "incomplete_information": 1,
                           "below_listed_requirements": 2}[outcome], -relevance, req["programme"]),
            })
        results.sort(key=lambda r: r.pop("_rank"))
        response.update(status="ok", recommendations=results,
                        message="Programmes compared with the verified entry requirements recorded by USIU staff:")
        return response

    def _places_to_look(self, text):
        if not self.catalogue:
            return []
        return [{"title": e["title"], "url": e["url"], "verified": False}
                for e in self.catalogue.match(text, k=3, min_coverage=0.2)]


def serialize_requirement(doc):
    return {
        "id": str(doc["_id"]), "programme": doc["programme"], "level": doc["level"], "url": doc["url"],
        "source_date": doc.get("source_date"), "min_mean_grade": doc.get("min_mean_grade"),
        "subject_requirements": doc.get("subject_requirements", []), "notes": doc.get("notes") or "",
        "keywords": doc.get("keywords", []), "verified": bool(doc.get("verified")),
        "verified_at": doc["verified_at"].isoformat() if doc.get("verified_at") else None,
        "updated_at": doc["updated_at"].isoformat() if doc.get("updated_at") else None,
    }

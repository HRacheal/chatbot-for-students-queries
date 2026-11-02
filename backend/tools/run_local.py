"""Run USIUBOT locally for manual testing, without MongoDB or any external service.

    python -m tools.run_local

This is NOT the normal development server. For development against the persistent MongoDB
database in backend/.env (MONGO_URI / MONGO_DB_NAME), run ``python app.py`` from backend/.

* Uses an in-memory database (mongomock, a development dependency). Everything is lost
  when the server stops. Never use this for production; it refuses FLASK_ENV=production.
* Listens on 127.0.0.1 only.
* Creates a local test administrator (Super Administrator), a local test student, and
  synthetic staff accounts (an Admissions administrator, Admissions staff and Registrar
  staff, all @usiubot.local) with throwaway passwords (set LOCAL_ADMIN_PASSWORD /
  LOCAL_STUDENT_PASSWORD / LOCAL_STAFF_PASSWORD, or random ones are generated and printed).
  No real user data is involved.
* Uses your backend/.env for everything else, if present (e.g. GROQ_API_KEY). Live website
  retrieval stays disabled unless you enable it there.
"""

import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ADMIN_EMAIL = "admin@usiubot.local"
STUDENT_USERNAME = "test_student"
STUDENT_EMAIL = "student@usiubot.local"
# Synthetic accounts for trying the role-based dashboard (in-memory database only).
LOCAL_STAFF = (
    ("admissions.admin@usiubot.local", "Local Admissions Admin", "department_admin", ["admissions"]),
    ("admissions.staff@usiubot.local", "Local Admissions Staff", "department_staff", ["admissions"]),
    ("registrar.staff@usiubot.local", "Local Registrar Staff", "department_staff", ["registrar"]),
)


def main():
    if os.getenv("FLASK_ENV") == "production":
        sys.exit("run_local is for local testing only (FLASK_ENV=production refused).")
    try:
        import mongomock
    except ImportError:
        sys.exit("mongomock is not installed: pip install -r requirements-dev.txt")

    admin_password = os.getenv("LOCAL_ADMIN_PASSWORD") or secrets.token_urlsafe(12)
    student_password = os.getenv("LOCAL_STUDENT_PASSWORD") or secrets.token_urlsafe(12)
    staff_password = os.getenv("LOCAL_STAFF_PASSWORD") or (secrets.token_urlsafe(10) + "A1")
    os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(48))
    os.environ["FLASK_ENV"] = "development"
    os.environ["ADMIN_EMAIL"] = ADMIN_EMAIL
    os.environ["ADMIN_PASSWORD"] = admin_password
    os.environ["MONGO_URI"] = ""

    from app import create_app
    from services.auth_service import AuthService

    app = create_app("development", overrides={"DEBUG": False}, db_client=mongomock.MongoClient())
    with app.app_context():
        AuthService(app).register_user(STUDENT_USERNAME, STUDENT_EMAIL, student_password)
        staff = app.extensions["staff_service"]
        for email, name, role, departments in LOCAL_STAFF:
            staff.create({"email": email, "name": name, "role": role, "departments": departments,
                          "must_change_password": False}, actor="run_local", password=staff_password)

    port = int(os.getenv("PORT", "5000"))
    print("\nUSIUBOT local test server (in-memory database; data is lost on exit)")
    print("  For the persistent MongoDB database in backend/.env, stop this and run: python app.py")
    print(f"  API:      http://127.0.0.1:{port}")
    print(f"  Admin:    {ADMIN_EMAIL} / {admin_password}")
    print(f"  Student:  {STUDENT_USERNAME} / {student_password}")
    print(f"  Staff (password {staff_password}): " + ", ".join(f"{e} ({r})" for e, _, r, _ in LOCAL_STAFF))
    print(f"  Language model: {'configured' if app.config.get('GROQ_API_KEY') else 'not configured (GROQ_API_KEY empty)'}")
    print(f"  Live website retrieval: {'enabled' if app.config.get('LIVE_RETRIEVAL_ENABLED') else 'disabled'}\n",
          flush=True)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()

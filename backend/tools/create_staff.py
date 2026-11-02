"""Create a USIUBOT staff account from the command line (typically the first Super Administrator).

    python -m tools.create_staff --email you@usiu.ac.ke --name "Your Name" --role super_admin
    python -m tools.create_staff --email staff@usiu.ac.ke --name "A. Person" --role department_staff \\
        --department admissions

The password is typed at a hidden prompt (never on the command line, so it is not kept in
shell history) and is stored only as a bcrypt hash. Further accounts are best created in the
dashboard (Staff Accounts), where the Super Administrator gets a one-time temporary password.
Uses MONGO_URI from backend/.env; nothing else is changed.
"""

import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config  # noqa: E402
from config.database import db_instance  # noqa: E402
from services.sources import DEPARTMENTS  # noqa: E402
from services.staff_service import StaffError, StaffService, validate_staff_password  # noqa: E402
from utils.auth import STAFF_ROLES  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=STAFF_ROLES, default="super_admin")
    parser.add_argument("--department", action="append", choices=DEPARTMENTS, default=[],
                        help="department (repeat for several); required for department roles")
    args = parser.parse_args(argv)

    if not db_instance.connect(Config.MONGODB_URI, Config.MONGO_DB_NAME):
        print(f"Database not available: {db_instance.last_error}")
        return 1
    password = getpass.getpass("Password for the new account (min. 10 characters, letters and numbers): ")
    if password != getpass.getpass("Repeat the password: "):
        print("The passwords do not match; nothing was created.")
        return 1
    try:
        validate_staff_password(password)
        settings = {k: getattr(Config, k) for k in dir(Config) if k.isupper()}
        doc, _ = StaffService(db_instance.get_collection, settings).create(
            {"email": args.email, "name": args.name, "role": args.role, "departments": args.department,
             "must_change_password": False}, actor="tools.create_staff", password=password)
    except StaffError as e:
        print(f"Not created: {e}")
        return 1
    print(f"Created {doc['role']} account for {doc['email']} (id {doc['_id']}). Sign in at /admin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

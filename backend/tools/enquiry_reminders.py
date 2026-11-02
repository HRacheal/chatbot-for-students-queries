"""Remind departments of open enquiries that have had no update for a while.

    python -m tools.enquiry_reminders            # uses ENQUIRY_REMINDER_DAYS (default 3)
    python -m tools.enquiry_reminders --days 5
    python -m tools.enquiry_reminders --dry-run  # only list what would be sent

Run it from a scheduler (e.g. cron or Windows Task Scheduler) once a day. Emails are only
sent when SMTP and the department's staff address are configured; every attempt is
recorded on the enquiries as sent / failed / not_configured. Contact details of enquirers
are never included in reminders.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config  # noqa: E402
from config.database import db_instance  # noqa: E402
from services.department_routing import DepartmentRouting  # noqa: E402
from services.email_service import EmailService  # noqa: E402
from services.enquiry_service import EnquiryService  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--days", type=int, default=Config.ENQUIRY_REMINDER_DAYS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not db_instance.connect(Config.MONGODB_URI, Config.MONGO_DB_NAME):
        print(f"Database not available: {db_instance.last_error}")
        return 1
    settings = {k: getattr(Config, k) for k in dir(Config) if k.isupper()}
    service = EnquiryService(db_instance.get_collection, settings, EmailService(settings),
                             DepartmentRouting(db_instance.get_collection, settings))
    if args.dry_run:
        overdue = service.overdue(args.days)
        counts = {}
        for e in overdue:
            counts[e["department"]] = counts.get(e["department"], 0) + 1
        print(f"{len(overdue)} open enquiries without an update for {args.days}+ days: {counts or 'none'}")
        return 0
    report = service.send_reminders(args.days)
    for department, item in report.items():
        print(f"{department}: {item['count']} overdue, reminder {item['status']}")
    if not report:
        print("No overdue enquiries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

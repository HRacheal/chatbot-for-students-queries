"""Import or refresh the USIUBOT dataset (usiubot_datasets/) as DRAFT sources.

    python -m tools.import_dataset            # dry run: report what would change, write nothing
    python -m tools.import_dataset --apply    # create/refresh draft sources in the app's MongoDB
    python -m tools.import_dataset --apply --contacts   # also copy published contacts (unpublished)

* Uses the application's own settings and MongoDB (backend/.env: MONGO_URI, SECRET_KEY, ...).
  The same import is available to administrators in the admin dashboard (Sources > Dataset).
* Never approves anything. An administrator reviews and approves sources in the admin
  dashboard; only approved sources are used by the chatbot.
* Safe to run again after the dataset is rebuilt: unchanged sections are skipped, an approved
  section whose text changed returns to draft, removed sections are archived.
* Delivery email addresses for enquiries are never set by this tool.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apply", action="store_true", help="write the draft sources (default: dry run)")
    parser.add_argument("--contacts", action="store_true",
                        help="also copy published department contacts into the routing settings (unpublished)")
    parser.add_argument("--dataset-dir", help="default: DATASET_DIR or ../usiubot_datasets")
    args = parser.parse_args(argv)

    try:
        from app import create_app

        app = create_app()
    except Exception as e:
        print(f"Cannot start the application ({type(e).__name__}: {e}). Check backend/.env "
              "(MONGO_URI, SECRET_KEY, ...). Nothing was imported.", file=sys.stderr)
        return 2
    from services.dataset_import import DatasetError, DatasetImporter

    with app.app_context():
        dataset_dir = args.dataset_dir or app.config["DATASET_DIR"]
        importer = DatasetImporter(app.extensions["source_registry"], dataset_dir)
        try:
            report = importer.run(dry_run=not args.apply, actor="tools.import_dataset")
        except DatasetError as e:
            print(str(e), file=sys.stderr)
            return 2
        print(json.dumps(report, indent=2, default=str))
        if args.contacts and args.apply:
            print(json.dumps(app.extensions["department_routing"].import_dataset_contacts(dataset_dir), indent=2))
        print("Dry run: nothing was written." if not args.apply else
              "Draft sources written. Nothing was approved; review them in the admin dashboard.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

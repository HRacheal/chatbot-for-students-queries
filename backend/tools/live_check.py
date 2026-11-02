"""Read-only access check for live retrieval. Run it from the deployment host:

    python -m tools.live_check            # DNS, connection, robots.txt verdict for each catalogue URL
    python -m tools.live_check --fetch 2  # also fetch up to 2 *allowed, reviewed* pages

It never requests a page that robots.txt disallows, never follows links and stores
nothing. Exit code 0 means live retrieval can be enabled (robots.txt allows at least
one reviewed page and a fetch succeeded when --fetch was used); otherwise 1.
"""

import argparse
import os
import socket
import sys
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config  # noqa: E402
from services.live_retrieval import DEFAULT_CATALOGUE, OfficialPageCatalogue  # noqa: E402
from services.web_access import OK, WebsiteAccess  # noqa: E402


def settings_from_config():
    return {key: getattr(Config, key) for key in dir(Config) if key.isupper()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fetch", type=int, default=0, help="fetch up to N allowed, reviewed pages")
    args = parser.parse_args(argv)

    settings = settings_from_config()
    web = WebsiteAccess(settings)
    catalogue = OfficialPageCatalogue.load(settings.get("OFFICIAL_PAGES_FILE") or DEFAULT_CATALOGUE, web.is_trusted)
    print(f"User agent: {web.user_agent}")
    print(f"Trusted hosts: {', '.join(sorted(web.trusted_hosts))}")
    print(f"Catalogue: {len(catalogue.entries)} pages, {catalogue.reviewed_count} reviewed")
    print(f"LIVE_RETRIEVAL_ENABLED={settings.get('LIVE_RETRIEVAL_ENABLED')}")

    ready = True
    for host in sorted(web.trusted_hosts):
        try:
            address = socket.gethostbyname(host)
            print(f"\n[{host}] DNS: {address}")
        except OSError as e:
            print(f"\n[{host}] DNS failed ({type(e).__name__})")
            ready = False
            continue
        try:
            with socket.create_connection((host, 443), timeout=settings.get("LIVE_CONNECT_TIMEOUT", 5)):
                print(f"[{host}] TCP 443: connected")
        except OSError as e:
            print(f"[{host}] TCP 443: failed ({type(e).__name__}); the site is not reachable from this network")
            ready = False
            continue

    allowed_reviewed = []
    for entry in catalogue.entries:
        if urlsplit(entry["url"]).hostname not in web.trusted_hosts:
            continue
        allowed, status = web.robots_status(entry["url"])
        if status != OK and not allowed and status != "robots_disallowed":
            print(f"robots.txt unavailable ({status}); nothing may be fetched")
            ready = False
            break
        mark = "allowed" if allowed else "DISALLOWED"
        print(f"  robots.txt {mark:10} reviewed={str(entry['reviewed']):5}  {entry['url']}")
        if allowed and entry["reviewed"]:
            allowed_reviewed.append(entry)

    if not allowed_reviewed:
        print("\nNo reviewed catalogue page is allowed by robots.txt for this user agent. "
              "Keep LIVE_RETRIEVAL_ENABLED=false.")
        ready = False

    for entry in allowed_reviewed[: max(0, args.fetch)]:
        result = web.fetch_page(entry["url"])
        if result.ok:
            print(f"  fetched {entry['url']} -> {result.page.final_url} ({len(result.page.text)} characters of text)")
        else:
            print(f"  fetch failed {entry['url']}: {result.status} {result.detail}")
            ready = False

    print("\nREADY: live retrieval may be enabled." if ready else "\nNOT READY: keep live retrieval disabled.")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())

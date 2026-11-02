"""Check the MongoDB and Groq connections configured in backend/.env.

    python -m tools.connection_check            # MongoDB ping + collection list, Groq test reply
    python -m tools.connection_check --no-groq  # MongoDB only

Nothing secret is printed: the MongoDB host is masked and the API key is never shown.
The Groq check sends one fixed, generic test sentence (no user or university data).
The MongoDB check only reads (ping, list collection names, count documents) unless
``--write-test`` is given, which inserts and deletes one document in ``_connection_check``.
Exit code 0 when every requested check passed, otherwise 1.
"""

import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config  # noqa: E402
from config.database import explain_mongo_error  # noqa: E402

GROQ_TEST_PROMPT = "Reply with the single word: ready"
# Reasoning models spend part of the budget on hidden reasoning, so the check allows enough
# tokens for a visible answer (a 10-token limit produced empty replies with gpt-oss).
GROQ_TEST_MAX_TOKENS = 300


def mask_uri(uri):
    """mongodb+srv://user:pass@cluster0.abcd.mongodb.net/db -> mongodb+srv://***@cluster0.***.mongodb.net"""
    if not uri:
        return "<not set>"
    scheme, _, rest = uri.partition("://")
    host = rest.rsplit("@", 1)[-1].split("/", 1)[0].split("?", 1)[0]
    parts = host.split(".")
    if len(parts) > 2:
        host = ".".join([parts[0]] + ["***"] + parts[-2:]) if len(parts) > 3 else ".".join([parts[0], "***", parts[-1]])
    return f"{scheme}://***@{host}"


def check_mongo(uri, db_name, write_test=False):
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError

    print(f"MongoDB: {mask_uri(uri)}  database '{db_name}'")
    if not uri:
        print("  FAIL  MONGO_URI is not set in backend/.env")
        return False
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=10000)
        started = time.monotonic()
        client.admin.command("ping")
        print(f"  OK    ping ({(time.monotonic() - started) * 1000:.0f} ms)")
        db = client[db_name]
        names = sorted(db.list_collection_names())
        print(f"  OK    {len(names)} collections" + (": " + ", ".join(names) if names else " (empty database)"))
        for name in ("users", "staff", "sources", "enquiries", "queries", "query_log"):
            if name in names:
                print(f"        {name}: {db[name].estimated_document_count()} documents")
        if write_test:
            col = db["_connection_check"]
            inserted = col.insert_one({"check": True}).inserted_id
            col.delete_one({"_id": inserted})
            db.drop_collection("_connection_check")
            print("  OK    write test (insert + delete)")
        client.close()
        return True
    except PyMongoError as e:
        print("  FAIL  " + explain_mongo_error(e))
        return False


def check_groq(api_key, model, timeout, reasoning_effort=None):
    print(f"Groq: model '{model}'")
    if not api_key:
        print("  FAIL  GROQ_API_KEY is not set in backend/.env")
        return False
    try:
        from langchain_groq import ChatGroq

        from services.chat_service import reasoning_effort_for

        options = {}
        effort = reasoning_effort_for(model, reasoning_effort)
        if effort:
            options["reasoning_effort"] = effort
        llm = ChatGroq(api_key=api_key, model=model, temperature=0, max_tokens=GROQ_TEST_MAX_TOKENS,
                       timeout=timeout, max_retries=0, **options)
        started = time.monotonic()
        reply = llm.invoke(GROQ_TEST_PROMPT)
        elapsed = (time.monotonic() - started) * 1000
        text = re.sub(r"\s+", " ", getattr(reply, "content", "") or "").strip()[:40]
        if not text:
            finish = (getattr(reply, "response_metadata", None) or {}).get("finish_reason")
            print(f"  FAIL  Groq answered in {elapsed:.0f} ms but with no visible text (finish_reason={finish})")
            return False
        print(f"  OK    reply in {elapsed:.0f} ms: {text!r}" + (f" (reasoning_effort={effort})" if effort else ""))
        return True
    except Exception as e:  # noqa: BLE001 - report every failure kind safely
        from services.chat_service import ChatService

        kind = ChatService.classify_ai_error(e)
        hint = {
            "rate_limited": "Groq rate limit or quota reached; try again later.",
            "timeout": "Groq did not answer in time; check the network or raise GROQ_TIMEOUT.",
        }.get(kind)
        text = str(e).lower()
        if not hint and ("401" in text or "invalid api key" in text or "authentication" in text):
            hint = "Groq rejected the API key: check GROQ_API_KEY."
        if not hint and ("model" in text and ("not found" in text or "decommissioned" in text or "404" in text)):
            hint = "The configured GROQ_MODEL is not available to this key."
        print(f"  FAIL  {hint or 'Groq request failed'} ({type(e).__name__})")
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-groq", action="store_true", help="skip the Groq check")
    parser.add_argument("--no-mongo", action="store_true", help="skip the MongoDB check")
    parser.add_argument("--write-test", action="store_true", help="insert and delete one test document")
    args = parser.parse_args(argv)
    ok = True
    if not args.no_mongo:
        ok &= check_mongo(Config.MONGODB_URI, Config.MONGO_DB_NAME, args.write_test)
    if not args.no_groq:
        ok &= check_groq(Config.GROQ_API_KEY, Config.GROQ_MODEL, Config.GROQ_TIMEOUT, Config.GROQ_REASONING_EFFORT)
    print("All checks passed." if ok else "Some checks failed (see above).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

import logging

from pymongo import MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


def explain_mongo_error(error):
    """A safe, actionable explanation of a MongoDB connection failure (never includes credentials)."""
    name = type(error).__name__
    text = str(error).lower()
    if "authentication failed" in text or "bad auth" in text:
        return ("Authentication failed: check the database user and password in MONGO_URI (replace the "
                "<db_password> placeholder; URL-encode special characters such as @ : / ? #).")
    if name in ("ServerSelectionTimeoutError", "NetworkTimeout", "AutoReconnect", "ConnectionFailure"):
        return ("The MongoDB cluster could not be reached: in MongoDB Atlas > Network Access allow this "
                "machine's IP address, and check that the cluster is running and the host name is correct.")
    if name == "InvalidURI":
        return "MONGO_URI is not a valid MongoDB connection string."
    if name == "ConfigurationError" or "dns" in text or "srv" in text:
        return "MONGO_URI could not be resolved: check the cluster host name (mongodb+srv://...)."
    return f"MongoDB connection failed ({name})."


class Database:
    """Database connection and management"""

    def __init__(self):
        self.client = None
        self.db = None
        self.last_error = None

    def connect(self, uri=None, db_name="chatbot", client=None):
        """Initialise the database connection.

        ``client`` lets tests inject an in-memory client (e.g. mongomock).
        """
        try:
            self.last_error = None
            if client is None:
                if not uri:
                    self.last_error = "MONGO_URI is not set in backend/.env."
                    logger.error("MONGO_URI is not configured")
                    return False
                client = MongoClient(uri, serverSelectionTimeoutMS=10000)
                client.admin.command("ping")
            self.client = client
            self.db = self.client[db_name]
            self._create_indexes()
            logger.info("Database connected: %s", self.describe())
            return True
        except PyMongoError as e:
            self.last_error = explain_mongo_error(e)
            logger.error("Database connection failed: %s", self.last_error)
            return False

    def _create_indexes(self):
        """Create indexes. Failures are logged but never delete or alter data."""
        index_specs = [
            ("chat_history", [("user_id", 1)], {}),
            ("chat_history", [("timestamp", -1)], {}),
            ("queries", [("answered", 1), ("timestamp", -1)], {}),
            ("sources", [("url_normalized", 1)], {"unique": True}),
            ("sources", [("status", 1), ("department", 1)], {}),
            ("source_chunks", [("source_id", 1)], {}),
            ("enquiries", [("reference", 1)], {"unique": True}),
            ("enquiries", [("department", 1), ("status", 1), ("created_at", -1)], {}),
            ("enquiries", [("dedupe_key", 1), ("status", 1)], {}),
            ("enquiries", [("user_id", 1)], {}),
            ("query_log", [("timestamp", -1)], {}),
            ("programme_requirements", [("verified", 1), ("programme", 1)], {}),
            ("official_links", [("key", 1)], {"unique": True}),
            ("enquiries", [("assigned_to_id", 1), ("status", 1)], {}),
            ("enquiries", [("resolved_at", -1)], {}),
            ("queries", [("department", 1), ("answered", 1)], {}),
            ("staff", [("email", 1)], {"unique": True}),
            ("staff", [("departments", 1), ("active", 1)], {}),
            ("audit_log", [("at", -1)], {}),
            ("audit_log", [("action", 1), ("at", -1)], {}),
            ("revoked_tokens", [("jti", 1)], {"unique": True}),
            # Revoked tokens are removed automatically once they would have expired anyway.
            ("revoked_tokens", [("expires_at", 1)], {"expireAfterSeconds": 0}),
            # Unique indexes protect against duplicate accounts. If existing data
            # already contains duplicates, index creation fails and is reported
            # so an operator can resolve them manually.
            ("users", [("email", 1)], {"unique": True}),
            ("users", [("username", 1)], {"unique": True}),
        ]
        for collection, keys, options in index_specs:
            try:
                self.db[collection].create_index(keys, **options)
            except PyMongoError as e:
                logger.warning(
                    "Could not create index %s on %s (%s); existing data may contain duplicates",
                    keys, collection, type(e).__name__,
                )

    def describe(self):
        """Which database is in use, without credentials: 'MongoDB cluster0.***.mongodb.net, database chatbot_db
        (persistent)' or 'in-memory mongomock, database chatbot (data is lost on exit)'."""
        if self.db is None:
            return "not connected"
        if type(self.client).__module__.startswith("mongomock"):
            return f"in-memory mongomock, database {self.db.name} (data is lost on exit)"
        try:
            hosts = sorted(f"{h}" for h, _ in self.client.nodes) or ["unknown host"]
            first = hosts[0].split(".")
            host = f"{first[0]}.***.{'.'.join(first[-2:])}" if len(first) > 3 else hosts[0]
        except Exception:
            host = "unknown host"
        return f"MongoDB {host}, database {self.db.name} (persistent)"

    def ping(self):
        """True if the database answers a ping (used by the health check)."""
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            return False

    def get_collection(self, collection_name):
        """Get a specific collection"""
        if self.db is None:
            raise RuntimeError("Database not connected")
        return self.db[collection_name]

    def close_connection(self):
        """Close database connection"""
        if self.client:
            self.client.close()


# Global database instance
db_instance = Database()

import logging

from pymongo import MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


class Database:
    """Database connection and management"""

    def __init__(self):
        self.client = None
        self.db = None

    def connect(self, uri=None, db_name="chatbot", client=None):
        """Initialise the database connection.

        ``client`` lets tests inject an in-memory client (e.g. mongomock).
        """
        try:
            if client is None:
                if not uri:
                    logger.error("MONGO_URI is not configured")
                    return False
                client = MongoClient(uri, serverSelectionTimeoutMS=10000)
                client.admin.command("ping")
            self.client = client
            self.db = self.client[db_name]
            self._create_indexes()
            logger.info("Database connected")
            return True
        except PyMongoError as e:
            logger.error("Database connection failed: %s", type(e).__name__)
            return False

    def _create_indexes(self):
        """Create indexes. Failures are logged but never delete or alter data."""
        index_specs = [
            ("chat_history", [("user_id", 1)], {}),
            ("chat_history", [("timestamp", -1)], {}),
            ("queries", [("answered", 1), ("timestamp", -1)], {}),
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

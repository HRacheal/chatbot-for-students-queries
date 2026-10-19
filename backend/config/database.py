import os
from pymongo import MongoClient
from config.config import Config

class Database:
    """Database connection and management"""
    
    def __init__(self):
        self.client = None
        self.db = None
        
    def connect(self):
        """Initialize database connection"""
        try:
            self.client = MongoClient(Config.MONGODB_URI)
            self.db = self.client["chatbot"]
            self._create_indexes()
            print("Database connected successfully")
            return True
        except Exception as e:
            print(f"Database connection failed: {str(e)}")
            return False
    
    def _create_indexes(self):
        """Create necessary indexes for better performance"""
        try:
            # Create chat_history collection with indexes if it doesn't exist
            if "chat_history" not in self.db.list_collection_names():
                chat_history_collection = self.db.create_collection("chat_history")
                chat_history_collection.create_index([("user_id", 1)])
                chat_history_collection.create_index([("timestamp", -1)])
            
            print("Database indexes created successfully")
        except Exception as e:
            print(f"Error creating indexes: {str(e)}")
    
    def get_collection(self, collection_name):
        """Get a specific collection"""
        if self.db is None:
            raise Exception("Database not connected")
        return self.db[collection_name]
    
    def close_connection(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            print("Database connection closed")

# Global database instance
db_instance = Database()

import os

from pymongo import MongoClient
from pymongo.database import Database

# Module-level cache for database instances
_mongo_db = None
_mongo_log_db = None

def create_mongo_db() -> Database:
    global _mongo_db
    if _mongo_db is not None:
        return _mongo_db
    
    MONGO_URL = os.environ.get("MONGO_URL")
    if not MONGO_URL: raise ValueError("Please set MONGO_URL in your environment variables.")

    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME")
    if not MONGO_DB_NAME: raise ValueError("Please set MONGO_DB_NAME in your environment variables.")

    # Initialize database
    mongo_client = MongoClient(MONGO_URL)
    _mongo_db = mongo_client[MONGO_DB_NAME]
    return _mongo_db

def create_mongo_log_db() -> Database:
    global _mongo_log_db
    if _mongo_log_db is not None:
        return _mongo_log_db
    
    MONGO_URL = os.environ.get("MONGO_URL")
    if not MONGO_URL: raise ValueError("Please set MONGO_URL in your environment variables.")

    MONGO_LOG_DB_NAME = os.environ.get("MONGO_LOG_DB_NAME")
    if not MONGO_LOG_DB_NAME: raise ValueError("Please set MONGO_LOG_DB_NAME in your environment variables.")

    # Initialize database
    mongo_client = MongoClient(MONGO_URL)
    _mongo_log_db = mongo_client[MONGO_LOG_DB_NAME]
    return _mongo_log_db
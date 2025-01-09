from helpers import time, config
from pymongo import MongoClient

MONGODB_CONNECTION_STRING = config.env_var(config.MONGODB_CONNECTION_STRING_KEY)

def get_database():
    """Get MongoDB database instance."""
    client = MongoClient(MONGODB_CONNECTION_STRING)
    return client.spogitify

def update_user_last_export(user_id: str):
    """Update the last export time for a user."""
    db = get_database()
    db.users.update_one(
        {'_id': user_id},
        {
            '$set': {
                'last_export_start': time.now()
            }
        },
        upsert=True
    )

def get_user_last_export(user_id: str):
    """Get the last export time for a user."""
    db = get_database()
    user = db.users.find_one({'_id': user_id})
    return user.get('last_export_start') if user else None

def get_user_config(user_id: str):
    """Get user-specific configuration."""
    db = get_database()
    user = db.users.find_one({'_id': user_id})
    return user.get('config', {}) if user else {}

def update_user_config(user_id: str, config: dict):
    """Update user-specific configuration."""
    db = get_database()
    db.users.update_one(
        {'_id': user_id},
        {'$set': {'config': config}},
        upsert=True
    )

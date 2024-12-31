import os
from helpers import time
from pymongo import MongoClient
from pymongo.database import Database

MONGODB_CONNECTION_STRING = os.environ.get('MONGODB_CONNECTION_STRING')
if not MONGODB_CONNECTION_STRING:
    raise ValueError("MONGODB_CONNECTION_STRING environment variable is not set")

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

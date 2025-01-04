import os
from helpers import database

# Configuration keys
ARCHIVE_DIR_KEY = 'ARCHIVE_DIR'
EXCLUDE_SPOTIFY_PLAYLISTS_KEY = 'EXCLUDE_SPOTIFY_PLAYLISTS'
EXCLUDE_PLAYLISTS_KEY = 'EXCLUDE_PLAYLISTS'
REPO_NAME_KEY = 'REPO_NAME'

global_config = {
    EXCLUDE_SPOTIFY_PLAYLISTS_KEY: True,
    EXCLUDE_PLAYLISTS_KEY: [],
}

def config_for_user(user_id):
    """Get configuration for a specific user, combining global and user-specific config."""
    user_config = database.get_user_config(user_id)
    return {
        **global_config,
        **user_config,
        REPO_NAME_KEY: f"spotify-archive-{user_id}"
    }

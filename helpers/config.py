import os

# Global configuration keys
SPOTIFY_CLIENT_ID_KEY = 'SPOTIFY_CLIENT_ID'
SPOTIFY_CLIENT_SECRET_KEY = 'SPOTIFY_CLIENT_SECRET'
SPOTIFY_REDIRECT_URI_KEY = 'SPOTIFY_REDIRECT_URI'
GITHUB_TOKEN_KEY = 'GITHUB_TOKEN'
MONGODB_CONNECTION_STRING_KEY = 'MONGODB_CONNECTION_STRING'

def env_var(key, default=None):
    value = os.environ.get(key, default)
    if not value:
        raise ValueError(f"Environment variable {key} is not set")
    return value

# User configuration keys
ARCHIVE_DIR_KEY = 'ARCHIVE_DIR'
INCLUDE_LIKED_SONGS_KEY = 'INCLUDE_LIKED_SONGS'
EXCLUDE_PLAYLISTS_KEY = 'EXCLUDE_PLAYLISTS'
REPO_NAME_KEY = 'REPO_NAME'

from helpers.database import get_user_config
def config_for_user(user_id):
    """Get configuration for a specific user, combining global and user-specific config."""
    return {
        INCLUDE_LIKED_SONGS_KEY: True,
        EXCLUDE_PLAYLISTS_KEY: [],
        REPO_NAME_KEY: f"spotify-archive-{user_id}",
        **get_user_config(user_id)
    }

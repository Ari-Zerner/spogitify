import os

# Configuration keys
ARCHIVE_DIR_KEY = 'ARCHIVE_DIR'
PLAYLISTS_DIR_KEY = 'PLAYLISTS_DIR'
PLAYLIST_METADATA_FILENAME_KEY = 'PLAYLIST_METADATA_FILENAME'
EXCLUDE_SPOTIFY_PLAYLISTS_KEY = 'EXCLUDE_SPOTIFY_PLAYLISTS'
EXCLUDE_PLAYLISTS_KEY = 'EXCLUDE_PLAYLISTS'
REPO_NAME_KEY = 'REPO_NAME'
GITHUB_TOKEN_KEY = 'GITHUB_TOKEN'
SPOTIFY_CLIENT_ID_KEY = 'SPOTIFY_CLIENT_ID'
SPOTIFY_CLIENT_SECRET_KEY = 'SPOTIFY_CLIENT_SECRET'
SPOTIFY_REDIRECT_URI_KEY = 'SPOTIFY_REDIRECT_URI'

global_config = {
    PLAYLISTS_DIR_KEY: 'playlists',
    PLAYLIST_METADATA_FILENAME_KEY: 'playlists_metadata.json',
    EXCLUDE_SPOTIFY_PLAYLISTS_KEY: True,
    EXCLUDE_PLAYLISTS_KEY: [],
    GITHUB_TOKEN_KEY: os.environ.get(GITHUB_TOKEN_KEY),
    SPOTIFY_CLIENT_ID_KEY: os.environ.get(SPOTIFY_CLIENT_ID_KEY),
    SPOTIFY_CLIENT_SECRET_KEY: os.environ.get(SPOTIFY_CLIENT_SECRET_KEY),
    SPOTIFY_REDIRECT_URI_KEY: os.environ.get(SPOTIFY_REDIRECT_URI_KEY),
}

def config_for_user(user_id):
    # TODO: use MongoDB to store user-specific config
    return {
        **global_config,
        REPO_NAME_KEY: f"spotify-archive-{user_id}"
    }

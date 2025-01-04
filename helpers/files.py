import json
import os
from helpers.config import ARCHIVE_DIR_KEY

# File structure constants
PLAYLISTS_DIR = 'playlists'
PLAYLIST_METADATA_FILENAME = 'playlists_metadata.json'

def playlist_filename(playlist):
    return playlist['name'].replace('/', '_') + '.json'

def setup_archive_dir(config):
    """
    Creates the archive directory and playlist metadata file if they don't exist.
    Returns True if setup was performed, False if the archive was already set up.
    """
    os.makedirs(f"{config[ARCHIVE_DIR_KEY]}/{PLAYLISTS_DIR}", exist_ok=True)
    metadata_path = f"{config[ARCHIVE_DIR_KEY]}/{PLAYLIST_METADATA_FILENAME}"
    if not os.path.exists(metadata_path):
        json.dump([], open(metadata_path, 'w'))
        return True
    return False

def write_playlists_metadata_json(playlists, config):
    """
    Writes playlist metadata to JSON file.
    """
    yield 'Saving playlist metadata file'
    with open(os.path.join(config[ARCHIVE_DIR_KEY], PLAYLIST_METADATA_FILENAME), 'w', newline='', encoding='utf-8') as jsonfile:
        playlists_without_tracks = [{k: v for k, v in p.items() if k != 'tracks'} for p in playlists]
        json.dump(playlists_without_tracks, jsonfile, indent=2)

def read_playlists_metadata_json(config):
    try:
        with open(os.path.join(config[ARCHIVE_DIR_KEY], PLAYLIST_METADATA_FILENAME), 'r', newline='', encoding='utf-8') as jsonfile:
            return {p['id']: p for p in json.load(jsonfile)}
    except Exception as e:
        return None

def write_playlist_tracks_json(playlists, config):
    """
    Exports each playlist as a separate JSON file in the playlists folder.
    """
    yield 'Saving playlist files'
    playlists_path = os.path.join(config[ARCHIVE_DIR_KEY], PLAYLISTS_DIR)
    
    # Remove any existing playlist files
    for filename in os.listdir(playlists_path):
        file_path = os.path.join(playlists_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    for playlist in playlists:
        with open(os.path.join(playlists_path, playlist_filename(playlist)), 'w', newline='', encoding='utf-8') as jsonfile:
            json.dump(playlist['tracks'], jsonfile, indent=2)

def read_playlist_tracks_json(playlist, config):
    try:
        with open(os.path.join(config[ARCHIVE_DIR_KEY], PLAYLISTS_DIR, playlist_filename(playlist)), 'r', newline='', encoding='utf-8') as jsonfile:
            return json.load(jsonfile)
    except Exception as e:
        return None

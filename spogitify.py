import os
import json
from datetime import datetime, timedelta
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from git import Repo, exc
import yaml
import re

REMOTE_NAME = 'origin'
DEFAULT_BRANCH = 'main'

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

def get_config(base_config={}):
    """
    Merges base configuration with default values and returns a dictionary with configuration values.

    This function takes a base configuration dictionary (typically loaded from config.yaml) and
    merges it with default values for all configuration options. Environment variables are used
    as fallbacks for sensitive values like API credentials.

    Args:
        base_config (dict): Base configuration dictionary, defaults to empty dict if not provided

    Returns:
        dict: Complete configuration dictionary with all required keys
    """
    # Get configuration values with default fallbacks
    return {
        ARCHIVE_DIR_KEY: os.path.expanduser(base_config.get(ARCHIVE_DIR_KEY, 'spotify-archive')),
        PLAYLISTS_DIR_KEY: base_config.get(PLAYLISTS_DIR_KEY, 'playlists'),
        PLAYLIST_METADATA_FILENAME_KEY: base_config.get(PLAYLIST_METADATA_FILENAME_KEY, 'playlists_metadata.json'),
        EXCLUDE_SPOTIFY_PLAYLISTS_KEY: base_config.get(EXCLUDE_SPOTIFY_PLAYLISTS_KEY, True),
        EXCLUDE_PLAYLISTS_KEY: base_config.get(EXCLUDE_PLAYLISTS_KEY, []),
        REPO_NAME_KEY: base_config.get(REPO_NAME_KEY, None),
        GITHUB_TOKEN_KEY: base_config.get(GITHUB_TOKEN_KEY, os.environ.get(GITHUB_TOKEN_KEY)),
        SPOTIFY_CLIENT_ID_KEY: base_config.get(SPOTIFY_CLIENT_ID_KEY, os.environ.get(SPOTIFY_CLIENT_ID_KEY)),
        SPOTIFY_CLIENT_SECRET_KEY: base_config.get(SPOTIFY_CLIENT_SECRET_KEY, os.environ.get(SPOTIFY_CLIENT_SECRET_KEY)),
        SPOTIFY_REDIRECT_URI_KEY: base_config.get(SPOTIFY_REDIRECT_URI_KEY, os.environ.get(SPOTIFY_REDIRECT_URI_KEY))
    }

def get_spotify_client(config):
    """
    Creates a Spotify client object using configuration values for credentials.
    """
    client_id = config[SPOTIFY_CLIENT_ID_KEY]
    client_secret = config[SPOTIFY_CLIENT_SECRET_KEY]
    redirect_uri = config[SPOTIFY_REDIRECT_URI_KEY]

    if not client_id or not client_secret or not redirect_uri:
        raise ValueError(f'{SPOTIFY_CLIENT_ID_KEY}, {SPOTIFY_CLIENT_SECRET_KEY}, and {SPOTIFY_REDIRECT_URI_KEY} must be set in config.yaml.')

    return spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope='user-library-read playlist-read-private'))

def include_playlist(playlist, config):
    """
    Returns True if the playlist should be included in the export.
    """
    if config[EXCLUDE_SPOTIFY_PLAYLISTS_KEY] and playlist['owner']['id'] == 'spotify':
        return False
    if playlist['name'] in config[EXCLUDE_PLAYLISTS_KEY]:
        return False
    return True

def metadata_path(config):
    return os.path.join(config[ARCHIVE_DIR_KEY], config[PLAYLIST_METADATA_FILENAME_KEY])

def playlist_path(playlist, config, include_archive_dir=True):
    path = os.path.join(config[PLAYLISTS_DIR_KEY], playlist['name'].replace('/', '_') + '.json')
    if include_archive_dir:
        path = os.path.join(config[ARCHIVE_DIR_KEY], path)
    return path

def fetch_playlists(sp, config):
    """
    Fetches all playlists for the authenticated user, including track details.
    """
    yield 'Fetching playlists from Spotify...'
    playlists = []
    seen_playlist_ids = set()
    
    # Load existing playlist metadata
    existing_metadata = {}
    try:
        with open(metadata_path(config), 'r') as f:
            existing_metadata =  {p['id']: p for p in json.load(f)}
    except:
        pass  # If metadata file is invalid, proceed as if it doesn't exist
    
    results = sp.current_user_playlists()
    while results:
        for item in results['items']:
            if item and item['id'] not in seen_playlist_ids and include_playlist(item, config):
                
                yield f"Fetching playlist: {item['name']}"
                playlist = {}
                
                if item['id'] in existing_metadata and existing_metadata[item['id']]['snapshot_id'] == item['snapshot_id']:
                    # If the playlist hasn't changed, reuse saved information
                    try:
                        with open(playlist_path(item, config), 'r') as f:
                            playlist = existing_metadata[item['id']]
                            playlist['tracks'] = json.load(f)
                    except:
                        pass
                    
                if 'tracks' not in playlist:
                    playlist = {
                        'id': item['id'],
                        'name': item['name'],
                        'owner': item['owner']['display_name'],
                        'snapshot_id': item['snapshot_id']
                    }
                    total_length_ms = 0
                    
                    # Fetch tracks for the playlist
                    tracks = []
                    track_results = sp.playlist_tracks(playlist['id'])
                    while track_results:
                        for track_item in track_results['items']:
                            track = track_item['track']
                            if track:
                                track_info = {
                                    'name': track['name'],
                                    'artist': artists_string(track['artists']),
                                    'id': track['id'],
                                    'added_at': track_item.get('added_at', ''),
                                    'added_by': track_item.get('added_by', {}).get('id', ''),
                                    'length_seconds': track['duration_ms'] // 1000
                                }
                                tracks.append(track_info)
                                total_length_ms += track['duration_ms']
                        track_results = sp.next(track_results)
                    
                    playlist['tracks'] = tracks
                    playlist['num_songs'] = len(tracks)
                    playlist['total_length_seconds'] = total_length_ms // 1000
                    
                playlists.append(playlist)
                seen_playlist_ids.add(item['id'])
                
        results = sp.next(results)
    
    playlists.sort(key=lambda playlist: playlist['id'])
    return playlists

def artists_string(artists):
    """
    Returns a comma-separated string of artist names or 'Unknown Artist' if no artist names are available.
    """
    if artists:
        artist_names = []
        for artist in artists:
            name = artist.get('name')
            if name:
                artist_names.append(name)
        if artist_names:
            return ', '.join(artist_names)
    return 'Unknown Artist'

def get_remote_url(config, with_token=False):
    """
    Creates or gets GitHub repository URL if github_token and repo_name are set.
    Returns the remote URL if successful, None otherwise.
    """
    if config[REPO_NAME_KEY] and config[GITHUB_TOKEN_KEY]:
        from github import Github
        gh = Github(config[GITHUB_TOKEN_KEY])
        try:
            gh.get_user().get_repo(config[REPO_NAME_KEY])
        except:
            gh.get_user().create_repo(config[REPO_NAME_KEY])
        prefix = f"https://{config[GITHUB_TOKEN_KEY]}@" if with_token else "https://"
        return f"{prefix}github.com/{gh.get_user().login}/{config[REPO_NAME_KEY]}.git"
    return None

def setup_archive(config):
    """
    Sets up the archive directory and initializes or updates the Git repository.

    This function creates the necessary directory structure within the specified archive directory.
    It then either clones a remote Git repository into this directory or initializes a new Git repository if no remote is specified.
    If a repository already exists, it updates the remote configuration and pulls the latest changes.

    Returns the local Git repository object for further operations.
    """
    repo = Repo.init(config[ARCHIVE_DIR_KEY])
    with repo.config_writer() as git_config:
        git_config.set_value('user', 'name', 'Spogitify')
        git_config.set_value('user', 'email', 'spogitify@gmail.com')
        
    remote_url = get_remote_url(config, with_token=True)
    if remote_url:
        try:
            repo.git.fetch(remote_url)
            repo.git.pull(remote_url, DEFAULT_BRANCH)
        except exc.GitCommandError:
            pass
        
    os.makedirs(f"{config[ARCHIVE_DIR_KEY]}/{config[PLAYLISTS_DIR_KEY]}", exist_ok=True)
    if not os.path.exists(os.path.join(repo.working_dir, 'README.md')):
        with open(os.path.join(repo.working_dir, 'README.md'), 'w') as f:
            f.write('Created by Spogitify')
        repo.index.add(['README.md'])
        repo.index.commit('Initial commit')
        
    if DEFAULT_BRANCH not in repo.heads:
        repo.create_head(DEFAULT_BRANCH)
    repo.heads[DEFAULT_BRANCH].checkout()
    
    return repo

def write_playlists_metadata_json(playlists, config):
    """
    Writes playlist metadata to JSON file.
    """
    yield 'Saving playlist metadata file'
    with open(metadata_path(config), 'w', newline='', encoding='utf-8') as jsonfile:
        playlists_without_tracks = [{k: v for k, v in p.items() if k != 'tracks'} for p in playlists]
        json.dump(playlists_without_tracks, jsonfile, indent=2)

def write_playlist_tracks_json(playlists, config):
    """
    Exports each playlist as a separate JSON file in the playlists folder.
    """
    yield 'Saving playlist files'
    playlists_path = f"{config[ARCHIVE_DIR_KEY]}/{config[PLAYLISTS_DIR_KEY]}"
    
    # Remove any existing playlist files
    for filename in os.listdir(playlists_path):
        file_path = os.path.join(playlists_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    for playlist in playlists:
        with open(playlist_path(playlist, config), 'w', newline='', encoding='utf-8') as jsonfile:
            json.dump(playlist['tracks'], jsonfile, indent=2)

def describe_changes(repo, config):
    """
    Returns a human-readable description of the changes made since the last commit
    by comparing current and previous playlist metadata and tracks.
    """
    def display_track(track):
        """
        Returns a string representation of a track. Accepts a track object with 'name' and 'artist' keys or a tuple of (name, artist).
        """
        if isinstance(track, dict):
            return f"{track['name']} by {track['artist']}"
        elif isinstance(track, tuple):
            return f"{track[0]} by {track[1]}"
        else:
            raise ValueError(f"Invalid track object: {track}")
    
    # Load current metadata
    with open(metadata_path(config), 'r') as f:
        current_metadata = {p['id']: p for p in json.load(f)}
    
    # Load previous metadata
    previous_metadata = {}
    try:
        content = repo.git.show(f'HEAD:{config[PLAYLIST_METADATA_FILENAME_KEY]}')
        previous_metadata = {p['id']: p for p in json.loads(content)}
    except Exception as e:
        # If no previous commit, treat as empty
        pass
    
    change_description = "Summary of Changes:\n"
    
    # Find added playlists
    added = set(current_metadata.keys()) - set(previous_metadata.keys())
    removed = set(previous_metadata.keys()) - set(current_metadata.keys())
    
    # Find changed playlists
    changed = set()
    for playlist_id in set(current_metadata.keys()) & set(previous_metadata.keys()):
        if current_metadata[playlist_id]['snapshot_id'] != previous_metadata[playlist_id]['snapshot_id']:
            changed.add(playlist_id)
    
    if added:
        change_description += "  Added playlists:\n"
        for playlist_id in added:
            playlist = current_metadata[playlist_id]
            change_description += f"  + {playlist['name']}\n"
            
    if removed:
        change_description += "\n  Removed playlists:\n"
        for playlist_id in removed:
            playlist = previous_metadata[playlist_id]
            change_description += f"  - {playlist['name']}\n"
            
    if changed:
        change_description += "\n  Changed playlists:\n"
        for playlist_id in changed:
            playlist = current_metadata[playlist_id]
            change_description += f"  ~ {playlist['name']}\n"
            
    # Then show track details for added playlists
    if added:
        change_description += "\n  Tracks in added playlists:\n"
        for playlist_id in added:
            playlist = current_metadata[playlist_id]
            change_description += f"    {playlist['name']}:\n"
            # Load tracks for added playlist
            with open(playlist_path(playlist, config), 'r') as f:
                tracks = json.load(f)
            for track in tracks:
                change_description += f"    + {display_track(track)}\n"
                
    # Then show track changes for modified playlists
    if changed:
        change_description += "\n  Track changes in modified playlists:\n"
        for playlist_id in changed:
            playlist = current_metadata[playlist_id]
            change_description += f"    {playlist['name']}:\n"
            
            # Load current tracks
            with open(playlist_path(playlist, config), 'r') as f:
                current_tracks = set((t['name'], t['artist']) for t in json.load(f))
            
            # Load previous tracks
            try:
                previous_path = playlist_path(previous_metadata[playlist_id], config, include_archive_dir=False)
                content = repo.git.show(f'HEAD:{previous_path}')
                previous_tracks = set((t['name'], t['artist']) for t in json.loads(content))
            except:
                previous_tracks = set()
            
            added_tracks = current_tracks - previous_tracks
            removed_tracks = previous_tracks - current_tracks
            
            if added_tracks:
                change_description += "      Added tracks:\n"
                for track in added_tracks:
                    change_description += f"      + {display_track({'name': track[0], 'artist': track[1]})}\n"
            if removed_tracks:
                change_description += "      Removed tracks:\n"
                for track in removed_tracks:
                    change_description += f"      - {display_track({'name': track[0], 'artist': track[1]})}\n"
    
    return change_description

def commit_and_push_changes(repo, config):
    """
    Commits (and pushes to remote if configured) any changes in `archive_dir`.
    """
    repo.git.add(A=True) # Add all changes including deletions to git index
    if repo.is_dirty(): # Don't commit if there are no changes
        yield 'Committing changes'
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        changelog = describe_changes(repo, config)
        commit_message = f"Archive {timestamp}\n\n{changelog}"
        repo.index.commit(commit_message)
        remote_url = get_remote_url(config, with_token=True)
        if remote_url:
            yield 'Pushing to remote'
            repo.git.push(remote_url, f"{DEFAULT_BRANCH}:{DEFAULT_BRANCH}")
    else:
        yield 'No changes to commit'
            
def run_export(sp, config):
    """
    Executes the main export process for Spotify playlists.

    This function performs the following steps:
    1. Fetches all playlists from the user's Spotify account.
    2. Sets up the archive directory and initializes/updates the Git repository.
    3. Writes metadata for all playlists to a JSON file.
    4. Writes individual JSON files for each playlist's tracks.
    5. Commits all changes to the Git repository.
    6. Pushes changes to the remote repository if configured.

    Args:
        sp (spotipy.Spotify): An authenticated Spotify client object.
        config (dict): A dictionary containing configuration settings.

    Note:
        This function may take a while to complete, especially for users with many playlists.
        
    Returns:
        A generator of status messages.
    """
    try:
        repo = setup_archive(config)
        playlists = yield from fetch_playlists(sp, config)
        # TODO: The metadata/tracks split is legacy from CSV storage, maybe the archive should just be a single JSON file?
        yield from write_playlists_metadata_json(playlists, config)
        yield from write_playlist_tracks_json(playlists, config)
        yield from commit_and_push_changes(repo, config)
    except Exception as e:
        yield f"Error: {str(e)}"
        raise e

def load_config_file():
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file)

def main():
    config = get_config(load_config_file())
    sp = get_spotify_client(config)
    for status in run_export(sp, config):
        print(status)

if __name__ == '__main__':
    main()
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
        'archive_dir': os.path.expanduser(base_config.get('archive_dir', 'spotify-archive')),
        'playlists_dir': base_config.get('playlists_dir', 'playlists'),
        'playlist_metadata_filename': base_config.get('playlist_metadata_filename', 'playlists_metadata.json'),
        'exclude_spotify_playlists': base_config.get('exclude_spotify_playlists', True),
        'exclude_playlists': base_config.get('exclude_playlists', []),
        'repo_name': base_config.get('repo_name', None),
        'github_token': base_config.get('github_token', os.environ.get('GITHUB_TOKEN')),
        'spotify_client_id': base_config.get('spotify_client_id', os.environ.get('SPOTIFY_CLIENT_ID')),
        'spotify_client_secret': base_config.get('spotify_client_secret', os.environ.get('SPOTIFY_CLIENT_SECRET')),
        'spotify_redirect_uri': base_config.get('spotify_redirect_uri', os.environ.get('SPOTIFY_REDIRECT_URI'))
    }

def get_spotify_client(config):
    """
    Creates a Spotify client object using configuration values for credentials.
    """
    client_id = config['spotify_client_id']
    client_secret = config['spotify_client_secret']
    redirect_uri = config['spotify_redirect_uri']

    if not client_id or not client_secret or not redirect_uri:
        raise ValueError('spotify_client_id, spotify_client_secret, and spotify_redirect_uri must be set in config.yaml.')

    return spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope='user-library-read playlist-read-private'))

def include_playlist(playlist, config):
    """
    Returns True if the playlist should be included in the export.
    """
    if config['exclude_spotify_playlists'] and playlist['owner']['id'] == 'spotify':
        return False
    if playlist['name'] in config['exclude_playlists']:
        return False
    return True

def fetch_playlists(sp, config):
    """
    Fetches all playlists for the authenticated user, including track details.
    """
    yield 'Fetching playlists from Spotify...'
    playlists = []
    seen_playlist_ids = set()
    
    # Load existing playlist metadata
    existing_metadata = {}
    metadata_path = os.path.join(config['archive_dir'], config['playlist_metadata_filename'])
    try:
        with open(metadata_path, 'r') as f:
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
                        with open(os.path.join(config['playlists_dir'], item['name'].replace('/', '_') + '.json'), 'r') as f:
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
    if config['repo_name'] and config['github_token']:
        from github import Github
        gh = Github(config['github_token'])
        try:
            gh.get_user().get_repo(config['repo_name'])
        except:
            gh.get_user().create_repo(config['repo_name'])
        prefix = f"https://{config['github_token']}@" if with_token else "https://"
        return f"{prefix}github.com/{gh.get_user().login}/{config['repo_name']}.git"
    return None

def setup_archive(config):
    """
    Sets up the archive directory and initializes or updates the Git repository.

    This function creates the necessary directory structure within the specified archive directory.
    It then either clones a remote Git repository into this directory or initializes a new Git repository if no remote is specified.
    If a repository already exists, it updates the remote configuration and pulls the latest changes.

    Returns the local Git repository object for further operations.
    """
    repo = None
    remote_url = get_remote_url(config, with_token=True)
    if remote_url:
        try:
            repo = Repo.clone_from(remote_url, config['archive_dir'])
        except exc.GitCommandError:
            repo = Repo.init(config['archive_dir'])

        if REMOTE_NAME not in repo.remotes:
            repo.create_remote(REMOTE_NAME, remote_url)
        else:
            repo.remotes[REMOTE_NAME].set_url(remote_url)

        remote = repo.remotes[REMOTE_NAME]
        if remote.refs:
            try:
                remote.fetch()
                remote.pull(remote.refs[0].remote_head)
            except exc.GitCommandError:
                pass
    else:
        repo = Repo.init(config['archive_dir'])
        
    os.makedirs(f"{config['archive_dir']}/{config['playlists_dir']}", exist_ok=True)

    return repo

def write_playlists_metadata_json(playlists, config):
    """
    Writes playlist metadata to JSON file.
    """
    yield 'Saving playlist metadata file'
    with open(f"{config['archive_dir']}/{config['playlist_metadata_filename']}", 'w', newline='', encoding='utf-8') as jsonfile:
        playlists_without_tracks = [{k: v for k, v in p.items() if k != 'tracks'} for p in playlists]
        json.dump(playlists_without_tracks, jsonfile, indent=2)

def write_playlist_tracks_json(playlists, config):
    """
    Exports each playlist as a separate JSON file in the playlists folder.
    """
    yield 'Saving playlist files'
    playlists_path = f"{config['archive_dir']}/{config['playlists_dir']}"
    
    # Remove any existing playlist files
    for filename in os.listdir(playlists_path):
        file_path = os.path.join(playlists_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    
    for playlist in playlists:
        playlist_name = playlist['name'].replace('/', '_')
        filename = f'{playlists_path}/{playlist_name}.json'

        with open(filename, 'w', newline='', encoding='utf-8') as jsonfile:
            json.dump(playlist['tracks'], jsonfile, indent=2)

def describe_changes(repo, config):
    """
    Returns a human-readable description of the changes made since the last commit.
    """
    diff_index = repo.head.commit.diff(None)  # Compare last commit to working directory
    added_playlists = set()
    changed_playlists = set()
    deleted_playlists = set()
    
    prefix_length = len(config['playlists_dir'] + '/')
    
    def display_playlist(filename):
        # Remove prefix and any file extension
        return filename.rsplit('.', 1)[0][prefix_length:]
    
    def display_track(track):
        return f"{track[0]} by {track[1]}"
    
    playlist_groups = [('Added', 'A', added_playlists),
                       ('Changed', 'M', changed_playlists),
                       ('Deleted', 'D', deleted_playlists)]
    
    for (group_name, change_type, collection) in playlist_groups:
        for diff_item in diff_index.iter_change_type(change_type):
            path = diff_item.a_path
            if re.match(f"^{config['playlists_dir']}/.*\.json$", path):
                collection.add(path)
    
    change_description = "Summary of Changes:\n"
    for (group_name, change_type, collection) in playlist_groups:
        if collection:
            change_description += f"  {group_name} playlists:\n"
            for playlist in collection:
                change_description += f"    - {display_playlist(playlist)}\n"
        
    change_description += "\n"
    
    for playlist in added_playlists:
        change_description += f"Added playlist: {display_playlist(playlist)}\n"
        try:
            with open(os.path.join(repo.working_dir, playlist), 'r') as file:
                tracks = json.load(file)
            change_description += "  Tracks:\n"
            for track in tracks:
                change_description += f"    - {display_track(track)}\n"
        except Exception as e:
            change_description += f"Error describing added playlist {display_playlist(playlist)}: {str(e)}\n"
    
    for playlist in changed_playlists:
        change_description += f"Changed playlist: {display_playlist(playlist)}\n"
        try:
            with open(os.path.join(repo.working_dir, playlist), 'r') as file:
                current_tracks = set((track['name'], track['artist']) for track in json.load(file))
                previous_tracks = set((track['name'], track['artist']) for track in json.loads(repo.git.show(f'HEAD~1:{playlist}')))
            
            added_tracks = current_tracks - previous_tracks
            removed_tracks = previous_tracks - current_tracks
            
            if added_tracks:
                change_description += "  Added tracks:\n"
                for track in added_tracks:
                    change_description += f"    - {display_track(track)}\n"
            if removed_tracks:
                change_description += "  Removed tracks:\n"
                for track in removed_tracks:
                    change_description += f"    - {display_track(track)}\n"
        except Exception as e:
            change_description += f"Error describing changes for {display_playlist(playlist)}: {str(e)}\n"
    
    return change_description

def commit_changes(repo, config):
    """
    Commits any changes in `archive_dir`. If there are previous commits, the commit message is "Update <timestamp>".
    If it's the first commit, the message is "Initial sync <timestamp>".
    """
    repo.git.add(A=True) # Add all changes including deletions to git index
    if repo.is_dirty(): # Don't commit if there are no changes
        yield 'Committing changes'
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        has_commits = bool(repo.git.rev_list('--all'))
        if has_commits:
            commit_message = f"Update {timestamp}\n\n{describe_changes(repo, config)}"
        else:
            commit_message = f"Initial sync {timestamp}"
        repo.index.commit(commit_message)
    else:
        yield 'No changes to commit'

def push_to_remote(repo, config):
    """
    Pushes any changes in `archive_dir` to the remote repository if configured.
    """
    if config['repo_name']:
        yield 'Pushing to remote'
        current_branch = repo.head.ref
        if current_branch.tracking_branch():
            repo.remotes[REMOTE_NAME].push()
        else:
            repo.remotes[REMOTE_NAME].push(refspec=f"{current_branch.name}:{DEFAULT_BRANCH}", set_upstream=True)
            
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
        yield from commit_changes(repo, config)
        yield from push_to_remote(repo, config)
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
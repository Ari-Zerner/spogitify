import os
import csv
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from git import Repo, exc
import yaml
import re

# Read configuration from YAML file
try:
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)
except FileNotFoundError:
    config = {}

# Get configuration values with default fallbacks
archive_dir = os.path.expanduser(config.get('archive_dir', 'spotify-archive'))
playlists_dir = config.get('playlists_dir', 'playlists')
playlist_metadata_filename = config.get('playlist_metadata_filename', 'playlists_metadata.csv')
exclude_spotify_playlists = config.get('exclude_spotify_playlists', True)
exclude_playlists = config.get('exclude_playlists', [])
remote_url = config.get('remote_url', None)
remote_name = 'origin'

def get_spotify_client():
    """
    Creates a Spotify client object using configuration values for credentials.
    """
    client_id = config.get('spotify_client_id')
    client_secret = config.get('spotify_client_secret')
    redirect_uri = 'http://localhost:8888/callback'

    if not client_id or not client_secret:
        print('Error: spotify_client_id and spotify_client_secret must be set in config.yaml.')
        exit(1)

    return spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri, scope='user-library-read playlist-read-private'))

def include_playlist(playlist):
    """
    Returns True if the playlist should be included in the export.
    """
    if exclude_spotify_playlists and playlist['owner']['id'] == 'spotify':
        return False
    if playlist['name'] in exclude_playlists:
        return False
    return True

def fetch_playlists(sp):
    """
    Fetches all playlists for the authenticated user.
    """
    playlists = []
    seen_playlist_ids = set()
    results = sp.current_user_playlists()
    while results:
        for item in results['items']:
            if item['id'] not in seen_playlist_ids:
                playlists.append(item)
                seen_playlist_ids.add(item['id'])
        results = sp.next(results)
    playlists = [playlist for playlist in playlists if include_playlist(playlist)]
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

def setup_archive():
    """
    Sets up the archive directory and initializes or updates the Git repository.

    This function creates the necessary directory structure within the specified archive directory.
    It then either clones a remote Git repository into this directory or initializes a new Git repository if no remote is specified.
    If a repository already exists, it updates the remote configuration and pulls the latest changes.

    Returns the local Git repository object for further operations.
    """
    os.makedirs(f'{archive_dir}/{playlists_dir}', exist_ok=True)

    repo = None
    if remote_url:
        try:
            repo = Repo.clone_from(remote_url, archive_dir)
        except exc.GitCommandError:
            repo = Repo.init(archive_dir)

        if remote_name not in repo.remotes:
            repo.create_remote(remote_name, remote_url)
        else:
            repo.remotes[remote_name].set_url(remote_url)

        remote = repo.remotes[remote_name]
        remote.fetch()
        if remote.refs:
            try:
                remote.pull(remote.refs[0].remote_head)
            except exc.GitCommandError:
                pass
    else:
        repo = Repo.init(archive_dir)

    return repo

def export_playlists_metadata(sp, playlists):
    """
    Creates a CSV file with playlist metadata (name, owner, number of songs, and ID).
    """
    with open(f'{archive_dir}/{playlist_metadata_filename}', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['name', 'owner', 'num_songs', 'id'])

        for playlist in playlists:
            name = playlist['name']
            owner = playlist['owner']['display_name']
            length = playlist['tracks']['total']
            id = playlist['id']

            writer.writerow([name, owner, length, id])

def export_playlists(sp, playlists):
    """
    Exports each playlist as a separate CSV file in the playlists folder,
    with fields ['name', 'artist', 'id', 'added_at', 'added_by'].
    """
    playlists_path = f'{archive_dir}/{playlists_dir}'
    
    # Remove any existing playlist files
    for filename in os.listdir(playlists_path):
        file_path = os.path.join(playlists_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            
    for playlist in playlists:
        playlist_name = playlist['name'].replace('/', '_')
        print(f'Exporting playlist: {playlist_name}')
        filename = f'{playlists_path}/{playlist_name}.csv'

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['name', 'artist', 'id', 'added_at', 'added_by'])

            items = []
            results = sp.playlist_tracks(playlist['id'])
            while results:
                items.extend(results['items'])
                results = sp.next(results)

            for item in items:
                track = item['track']
                name = track['name']
                artist = artists_string(track['artists'])
                id = track['id']
                added_at = item.get('added_at', '')
                added_by = item.get('added_by', {}).get('id', '')

                writer.writerow([name, artist, id, added_at, added_by])

def describe_changes(repo):
    """
    Returns a human-readable description of the changes made since the last commit.
    """
    diff_index = repo.head.commit.diff(None)  # Compare last commit to working directory
    added_playlists = set()
    changed_playlists = set()
    deleted_playlists = set()
    
    prefix_length = len(playlists_dir + '/')
    suffix_length = len('.csv')
    
    def display_playlist(filename):
        return filename[prefix_length:-suffix_length]
    
    def display_track(track):
        return f"{track[0]} by {track[1]}"
    
    playlist_groups = [('Added', 'A', added_playlists),
                       ('Changed', 'M', changed_playlists),
                       ('Deleted', 'D', deleted_playlists)]
    
    for (group_name, change_type, collection) in playlist_groups:
        for diff_item in diff_index.iter_change_type(change_type):
            path = diff_item.a_path
            if re.match(f'^{playlists_dir}/.*\.csv$', path):
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
                reader = csv.reader(file)
                next(reader)  # Skip header
                tracks = list(reader)
            change_description += "  Tracks:\n"
            for track in tracks:
                change_description += f"    - {display_track(track)}\n"
        except Exception as e:
            change_description += f"Error describing added playlist {display_playlist(playlist)}: {str(e)}\n"
    
    for playlist in changed_playlists:
        change_description += f"Changed playlist: {display_playlist(playlist)}\n"
        try:
            with open(os.path.join(repo.working_dir, playlist), 'r') as file:
                current_reader = csv.reader(file)
                next(current_reader)  # Skip header
                current_tracks = set(tuple(row) for row in current_reader)
                previous_reader = csv.reader(repo.git.show(f'HEAD~1:{playlist}').splitlines())
                next(previous_reader)  # Skip header
                previous_tracks = set(tuple(row) for row in previous_reader)
            
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

def commit_changes(repo):
    """
    Commits any changes in `archive_dir`. If there are previous commits, the commit message is "Update <timestamp>".
    If it's the first commit, the message is "Initial sync <timestamp>".
    """
    repo.git.add(A=True) # Add all changes including deletions to git index
    if repo.is_dirty(): # Don't commit if there are no changes
        print('Committing changes')
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        has_commits = bool(repo.git.rev_list('--all'))
        if has_commits:
            commit_message = f"Update {timestamp}\n\n{describe_changes(repo)}"
        else:
            commit_message = f"Initial sync {timestamp}"
        repo.index.commit(commit_message)
    else:
        print('No changes to commit')

def push_to_remote(repo):
    """
    Pushes any changes in `archive_dir` to the remote repository if configured.
    """
    if remote_url:
        print('Pushing to remote')
        current_branch = repo.head.ref
        if current_branch.tracking_branch():
            repo.remotes[remote_name].push()
        else:
            repo.remotes[remote_name].push(refspec=f"{current_branch.name}:{current_branch.name}", set_upstream=True)

def main():
    sp = get_spotify_client()
    playlists = fetch_playlists(sp)
    repo = setup_archive()
    export_playlists_metadata(sp, playlists)
    export_playlists(sp, playlists)
    commit_changes(repo)
    push_to_remote(repo)

if __name__ == '__main__':
    main()
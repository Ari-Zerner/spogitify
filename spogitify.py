import os
import csv
from datetime import datetime
from git import Repo, exc
import re

def include_playlist(playlist, config):
    """
    Returns True if the playlist should be included in the export.
    """
    if config['EXCLUDE_SPOTIFY_PLAYLISTS'] and playlist['owner']['id'] == 'spotify':
        return False
    if playlist['name'] in config['EXCLUDE_PLAYLISTS']:
        return False
    return True

def fetch_playlists(sp, config):
    """
    Fetches all playlists for the authenticated user, including track details.
    """
    playlists = []
    seen_playlist_ids = set()
    results = sp.current_user_playlists()
    while results:
        for item in results['items']:
            if item['id'] not in seen_playlist_ids and include_playlist(item, config):
                
                print(f"Fetching playlist: {item['name']}")
                playlist = {
                    'id': item['id'],
                    'name': item['name'],
                    'owner': item['owner']['display_name']
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

def setup_archive(config):
    """
    Sets up the archive directory and initializes or updates the Git repository.

    This function creates the necessary directory structure within the specified archive directory.
    It then either clones a remote Git repository into this directory or initializes a new Git repository if no remote is specified.
    If a repository already exists, it updates the remote configuration and pulls the latest changes.

    Returns the local Git repository object for further operations.
    """
    os.makedirs(f"{config['ARCHIVE_DIR']}/{config['PLAYLISTS_DIR']}", exist_ok=True)

    repo = None
    if config['REMOTE_URL']:
        try:
            repo = Repo.clone_from(config['REMOTE_URL'], config['ARCHIVE_DIR'])
        except exc.GitCommandError:
            repo = Repo.init(config['ARCHIVE_DIR'])

        if config['REMOTE_NAME'] not in repo.remotes:
            repo.create_remote(config['REMOTE_NAME'], config['REMOTE_URL'])
        else:
            repo.remotes[config['REMOTE_NAME']].set_url(config['REMOTE_URL'])

        remote = repo.remotes[config['REMOTE_NAME']]
        remote.fetch()
        if remote.refs:
            try:
                remote.pull(remote.refs[0].remote_head)
            except exc.GitCommandError:
                pass
    else:
        repo = Repo.init(config['ARCHIVE_DIR'])

    return repo

def write_playlists_metadata_csv(playlists, config):
    """
    Writes playlist metadata to CSV file.
    """
    with open(f"{config['ARCHIVE_DIR']}/{config['PLAYLIST_METADATA_FILENAME']}", 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        fields = ['name', 'owner', 'num_songs', 'id', 'total_length_seconds']
        writer.writerow(fields)
        for playlist in playlists:
            writer.writerow([playlist[field] for field in fields])

def write_playlist_tracks_csvs(playlists, config):
    """
    Exports each playlist as a separate CSV file in the playlists folder.
    """
    playlists_path = f"{config['ARCHIVE_DIR']}/{config['PLAYLISTS_DIR']}"
    
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
            writer.writerow(['name', 'artist', 'id', 'added_at', 'added_by', 'length_seconds'])
            for track in playlist['tracks']:
                writer.writerow([track['name'], track['artist'], track['id'], track['added_at'], track['added_by'], track['length_seconds']])

def describe_changes(repo, config):
    """
    Returns a human-readable description of the changes made since the last commit.
    """
    diff_index = repo.head.commit.diff(None)  # Compare last commit to working directory
    added_playlists = set()
    changed_playlists = set()
    deleted_playlists = set()
    
    prefix_length = len(config['PLAYLISTS_DIR'] + '/')
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
            if re.match(f"^{config['PLAYLISTS_DIR']}/.*\.csv$", path):
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

def commit_changes(repo, config):
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
            commit_message = f"Update {timestamp}\n\n{describe_changes(repo, config)}"
        else:
            commit_message = f"Initial sync {timestamp}"
        repo.index.commit(commit_message)
    else:
        print('No changes to commit')

def push_to_remote(repo, config):
    """
    Pushes any changes in `archive_dir` to the remote repository if configured.
    """
    if config['REMOTE_URL']:
        print('Pushing to remote')
        current_branch = repo.head.ref
        if current_branch.tracking_branch():
            repo.remotes[config['REMOTE_NAME']].push()
        else:
            repo.remotes[config['REMOTE_NAME']].push(refspec=f"{current_branch.name}:{current_branch.name}", set_upstream=True)
            
def run_export(sp, config):
    """
    Executes the main export process for Spotify playlists.

    This function performs the following steps:
    1. Fetches all playlists from the user's Spotify account.
    2. Sets up the archive directory and initializes/updates the Git repository.
    3. Writes metadata for all playlists to a CSV file.
    4. Writes individual CSV files for each playlist's tracks.
    5. Commits all changes to the Git repository.
    6. Pushes changes to the remote repository if configured.

    Args:
        sp (spotipy.Spotify): An authenticated Spotify client object.
        config (dict): A dictionary containing configuration settings.

    Note:
        This function may take a while to complete, especially for users with many playlists.
    """
    playlists = fetch_playlists(sp, config)
    repo = setup_archive(config)
    write_playlists_metadata_csv(playlists, config)
    write_playlist_tracks_csvs(playlists, config)
    commit_changes(repo, config)
    push_to_remote(repo, config)
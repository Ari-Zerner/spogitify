from helpers import files, git
from datetime import datetime

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

def track_string(track):
    """
    Returns a string representation of a track. Accepts a track object with 'name' and 'artist' keys or a tuple of (name, artist).
    """
    if isinstance(track, dict):
        return f"{track['name']} by {track['artist']}"
    elif isinstance(track, tuple):
        return f"{track[0]} by {track[1]}"
    else:
        raise ValueError(f"Invalid track object: {track}")

def describe_changes(repo, config):
    """
    Returns a human-readable description of the changes made since the last commit
    by comparing current and previous playlist metadata and tracks.
    """
    previous_metadata = git.read_head_playlists_metadata_json(repo, config) or {}
    current_metadata = files.read_playlists_metadata(config) or {}
    
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
            tracks = files.read_playlist_tracks(playlist, config)
            for track in tracks:
                change_description += f"    + {track_string(track)}\n"
                
    # Then show track changes for modified playlists
    if changed:
        change_description += "\n  Track changes in modified playlists:\n"
        for playlist_id in changed:
            playlist = current_metadata[playlist_id]
            change_description += f"    {playlist['name']}:\n"
            
            # Load current tracks
            current_tracks = set((t['name'], t['artist']) for t in files.read_playlist_tracks(playlist, config))
            
            # Load previous tracks
            previous_tracks = set((t['name'], t['artist']) for t in (git.read_head_playlist_tracks_json(playlist, repo, config) or []))
            
            added_tracks = current_tracks - previous_tracks
            removed_tracks = previous_tracks - current_tracks
            
            if added_tracks:
                change_description += "      Added tracks:\n"
                for track in added_tracks:
                    change_description += f"      + {track_string({'name': track[0], 'artist': track[1]})}\n"
            if removed_tracks:
                change_description += "      Removed tracks:\n"
                for track in removed_tracks:
                    change_description += f"      - {track_string({'name': track[0], 'artist': track[1]})}\n"
    
    return change_description

def commit_message(repo, config):
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    changelog = describe_changes(repo, config)
    return f"Archive {timestamp}\n\n{changelog}"
import json
from git import Repo, exc
from github import Github
from helpers.config import *
from helpers import files, formatting

def update_repository_access(config):
    """
    Updates repository visibility and collaborator access. Assumes that the repository already exists.
    Returns a (possibly empty) list of error messages.
    """
    gh = Github(GITHUB_TOKEN)
    repo = gh.get_user().get_repo(config[REPO_NAME_KEY])
    
    # Update repository visibility
    repo.edit(private=bool(config[GITHUB_VIEWERS_KEY]))
    
    # Get current collaborators
    current_collaborators = set(collab.login for collab in repo.get_collaborators())
    desired_collaborators = set(config[GITHUB_VIEWERS_KEY])
    
    error_messages = []
    
    # Remove collaborators that are no longer in the list
    for git_user in current_collaborators - desired_collaborators:
        try:
            repo.remove_from_collaborators(git_user)
        except:
            error_messages.append(f"Could not remove GitHub user {git_user} as collaborator")
        
    # Add new collaborators
    for git_user in desired_collaborators - current_collaborators:
        try:
            repo.add_to_collaborators(git_user, permission='pull')
        except:
            error_messages.append(f"Could not add GitHub user {git_user} as collaborator")
            
    return error_messages

REMOTE_NAME = 'origin'
DEFAULT_BRANCH = 'main'
GITHUB_TOKEN = env_var(GITHUB_TOKEN_KEY)

def get_remote_url(config, with_token=False):
    """
    Creates GitHub repository if it doesn't exist, then returns the remote URL.
    """
    gh = Github(GITHUB_TOKEN)
    try:
        gh.get_user().get_repo(config[REPO_NAME_KEY])
    except:
        gh.get_user().create_repo(config[REPO_NAME_KEY])
        update_repository_access(config)
    prefix = f"https://{GITHUB_TOKEN}@" if with_token else "https://"
    return f"{prefix}github.com/{gh.get_user().login}/{config[REPO_NAME_KEY]}.git"

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
        
    if files.setup_archive_dir(config):
        repo.index.add([files.PLAYLIST_METADATA_FILENAME])
        repo.index.commit('Initial commit')
        
    if DEFAULT_BRANCH not in repo.heads:
        repo.create_head(DEFAULT_BRANCH)
    repo.heads[DEFAULT_BRANCH].checkout()
    
    return repo

def commit_and_push_changes(repo, config):
    """
    Commits (and pushes to remote if configured) any changes in `archive_dir`.
    """
    repo.git.add(A=True) # Add all changes including deletions to git index
    if repo.is_dirty(): # Don't commit if there are no changes
        yield 'Committing changes'
        
        repo.index.commit(formatting.commit_message(playlist_changes(repo, config)))
        remote_url = get_remote_url(config, with_token=True)
        if remote_url:
            yield 'Pushing to remote'
            repo.git.push(remote_url, f"{DEFAULT_BRANCH}:{DEFAULT_BRANCH}")
    else:
        yield 'No changes to commit'
        
def playlist_changes(repo, config):
    """
    Returns an object describing the changes made since the last commit
    by comparing current and previous playlist metadata and tracks.
    """
    content = repo.git.show(f'HEAD:{files.PLAYLIST_METADATA_FILENAME}')
    previous_metadata = {p['id']: p for p in json.loads(content)}
    current_metadata = files.read_playlists_metadata(config) or {}
    
    changes = {
        'added_playlists': [],
        'removed_playlists': [],
        'changed_playlists': []
    }
    
    # Add added playlists to changes object
    for playlist_id in set(current_metadata.keys()) - set(previous_metadata.keys()):
        changes['added_playlists'].append({
            'id': playlist_id,
            'name': current_metadata[playlist_id]['name']
        })
            
    # Add removed playlists to changes object
    for playlist_id in set(previous_metadata.keys()) - set(current_metadata.keys()):
        changes['removed_playlists'].append({
            'id': playlist_id,
            'name': previous_metadata[playlist_id]['name']
        })
    
    # Add changed playlists and their changes to changes object
    for playlist_id in set(current_metadata.keys()) & set(previous_metadata.keys()):
        playlist = current_metadata[playlist_id]
        if playlist.get('snapshot_id') != previous_metadata[playlist_id].get('snapshot_id'):
            
            track_info = {}
            def store_track_info_and_return_id(track):
                track_info[track['id']] = {
                    'name': track['name'],
                    'artist': track['artist']
                }
                return track['id']
            
            # Load current tracks
            current_track_ids = set(store_track_info_and_return_id(t) for t in files.read_playlist_tracks(playlist, config))
            
            # Load previous tracks
            content = repo.git.show(f'HEAD:{files.PLAYLISTS_DIR}/{files.playlist_filename(playlist)}')
            previous_track_ids = set(store_track_info_and_return_id(t) for t in (json.loads(content) or []))
            
            added_tracks = []
            removed_tracks = []
            
            for track_id in current_track_ids - previous_track_ids:
                added_tracks.append(track_info[track_id])
                
            for track_id in previous_track_ids - current_track_ids:
                removed_tracks.append(track_info[track_id])
            
            changes['changed_playlists'].append({
                'id': playlist_id,
                'name': playlist['name'],
                'old_name': previous_metadata[playlist_id]['name'],
                'added_tracks': added_tracks,
                'removed_tracks': removed_tracks
            })
    
    return changes
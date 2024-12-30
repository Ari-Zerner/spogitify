import json
from git import Repo, exc
from helpers.config import *
from helpers import files

REMOTE_NAME = 'origin'
DEFAULT_BRANCH = 'main'

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
        
    if files.setup_archive_dir(config):
        repo.index.add([config[PLAYLIST_METADATA_FILENAME_KEY]])
        repo.index.commit('Initial commit')
        
    if DEFAULT_BRANCH not in repo.heads:
        repo.create_head(DEFAULT_BRANCH)
    repo.heads[DEFAULT_BRANCH].checkout()
    
    return repo

def commit_and_push_changes(repo, config, message):
    """
    Commits (and pushes to remote if configured) any changes in `archive_dir`.
    """
    repo.git.add(A=True) # Add all changes including deletions to git index
    if repo.is_dirty(): # Don't commit if there are no changes
        yield 'Committing changes'
        
        repo.index.commit(message)
        remote_url = get_remote_url(config, with_token=True)
        if remote_url:
            yield 'Pushing to remote'
            repo.git.push(remote_url, f"{DEFAULT_BRANCH}:{DEFAULT_BRANCH}")
    else:
        yield 'No changes to commit'
        
def read_head_playlists_metadata_json(repo, config):
    try:
        content = repo.git.show(f'HEAD:{config[PLAYLIST_METADATA_FILENAME_KEY]}')
        return {p['id']: p for p in json.loads(content)}
    except Exception as e:
        return None
            
def read_head_playlist_tracks_json(playlist, repo, config):
    try:
        content = repo.git.show(f'HEAD:{files.playlist_filename(playlist, config)}')
        return json.loads(content)
    except Exception as e:
        return None

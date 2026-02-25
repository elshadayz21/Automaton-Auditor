import os
import tempfile
import ast
from git import Repo
import git.exc

def clone_repository(repo_url: str) -> tempfile.TemporaryDirectory:
    """
    Clones a git repository safely into a temporary directory.
    
    Returns the TemporaryDirectory object. The caller is responsible for 
    cleaning it up by calling .cleanup() or using it in a context manager.
    """
    temp_dir = tempfile.TemporaryDirectory()
    try:
        Repo.clone_from(repo_url, temp_dir.name)
        return temp_dir
    except git.exc.GitCommandError as e:
        temp_dir.cleanup()
        raise ValueError(f"Failed to clone repository: {str(e)}")

def analyze_graph_structure(path: str) -> dict:
    """
    Analyzes the structure of Python files in the given path using the built-in ast module.
    
    Returns a dictionary mapping file paths to their structural representation
    (classes, functions, and their inheritance/arguments).
    """
    structure = {}
    
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                        
                        tree = ast.parse(file_content)
                        classes = []
                        functions = []
                        
                        for node in ast.walk(tree):
                            if isinstance(node, ast.ClassDef):
                                bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
                                methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                                classes.append({
                                    'name': node.name,
                                    'bases': bases,
                                    'methods': methods
                                })
                            elif isinstance(node, ast.FunctionDef):
                                # Only record module-level functions, not methods (which are nested in classes)
                                if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree) if hasattr(parent, 'body') and node in parent.body):
                                    functions.append(node.name)
                        
                        if classes or functions:
                            relative_path = os.path.relpath(file_path, path)
                            structure[relative_path] = {
                                'classes': classes,
                                'functions': functions
                            }
                except Exception as e:
                    # Log parsing errors but continue with other files
                    print(f"Warning: Could not parse {file_path}: {str(e)}")
                    
    return structure

def extract_git_history(path: str, max_commits: int = 50) -> list[dict]:
    """
    Extracts commit history from a local git repository.
    
    Returns a list of dictionaries containing commit metadata.
    """
    try:
        repo = Repo(path)
        commits = []
        for commit in repo.iter_commits(max_count=max_commits):
            commits.append({
                'hash': commit.hexsha,
                'author': str(commit.author),
                'date': commit.authored_datetime.isoformat(),
                'message': commit.message.strip()
            })
        return commits
    except git.exc.InvalidGitRepositoryError:
        raise ValueError(f"Path '{path}' is not a valid git repository.")
    except Exception as e:
        raise ValueError(f"Error extracting git history: {str(e)}")

"""
GitHub API client — create branches, commit files, open PRs.
Uses the Git Data API so multiple files land in one commit.
"""
import requests
from config import GITHUB_TOKEN, GITHUB_REPO

_API = "https://api.github.com"
_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _get_branch_commit_sha(branch: str) -> str:
    url = f"{_API}/repos/{GITHUB_REPO}/git/ref/heads/{branch}"
    resp = requests.get(url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()["object"]["sha"]


def _get_tree_sha(commit_sha: str) -> str:
    url = f"{_API}/repos/{GITHUB_REPO}/git/commits/{commit_sha}"
    resp = requests.get(url, headers=_HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.json()["tree"]["sha"]


def create_branch(branch_name: str, from_branch: str) -> None:
    """Create branch_name branching off from_branch."""
    sha = _get_branch_commit_sha(from_branch)
    url = f"{_API}/repos/{GITHUB_REPO}/git/refs"
    resp = requests.post(url, headers=_HEADERS, timeout=15, json={
        "ref": f"refs/heads/{branch_name}",
        "sha": sha,
    })
    resp.raise_for_status()


def commit_files(branch_name: str, files: dict[str, str], message: str) -> None:
    """
    Commit multiple files to branch_name in a single commit.
    files: {repo-relative path → file content string}
    """
    base_commit_sha = _get_branch_commit_sha(branch_name)
    base_tree_sha = _get_tree_sha(base_commit_sha)

    # Create blobs
    tree_items = []
    for path, content in files.items():
        blob_resp = requests.post(
            f"{_API}/repos/{GITHUB_REPO}/git/blobs",
            headers=_HEADERS, timeout=15,
            json={"content": content, "encoding": "utf-8"},
        )
        blob_resp.raise_for_status()
        tree_items.append({
            "path": path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_resp.json()["sha"],
        })

    # Create tree on top of base
    tree_resp = requests.post(
        f"{_API}/repos/{GITHUB_REPO}/git/trees",
        headers=_HEADERS, timeout=15,
        json={"base_tree": base_tree_sha, "tree": tree_items},
    )
    tree_resp.raise_for_status()
    new_tree_sha = tree_resp.json()["sha"]

    # Create commit
    commit_resp = requests.post(
        f"{_API}/repos/{GITHUB_REPO}/git/commits",
        headers=_HEADERS, timeout=15,
        json={"message": message, "tree": new_tree_sha, "parents": [base_commit_sha]},
    )
    commit_resp.raise_for_status()
    new_commit_sha = commit_resp.json()["sha"]

    # Advance branch ref
    requests.patch(
        f"{_API}/repos/{GITHUB_REPO}/git/refs/heads/{branch_name}",
        headers=_HEADERS, timeout=15,
        json={"sha": new_commit_sha},
    ).raise_for_status()


def create_pull_request(
    branch_name: str,
    base_branch: str,
    title: str,
    body: str,
) -> dict:
    """Open a PR and return {url, number}."""
    resp = requests.post(
        f"{_API}/repos/{GITHUB_REPO}/pulls",
        headers=_HEADERS, timeout=15,
        json={"title": title, "head": branch_name, "base": base_branch, "body": body},
    )
    resp.raise_for_status()
    data = resp.json()
    return {"url": data["html_url"], "number": data["number"]}

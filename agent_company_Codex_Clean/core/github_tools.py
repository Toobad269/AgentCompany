"""
core/github_tools.py — GitHub lesen/schreiben
"""

from __future__ import annotations

import base64
import os
from typing import Any

import httpx

import settings


class GithubConfigError(RuntimeError):
    pass


def require_repo(repo: str | None) -> str:
    value = (repo or settings.GITHUB_DEFAULT_REPO or "").strip()
    if "/" not in value:
        raise GithubConfigError(
            "Kein GitHub-Repo angegeben. Nutze owner/repo oder setze GITHUB_DEFAULT_REPO."
        )
    return value


def require_token() -> str:
    token = settings.GITHUB_TOKEN.strip()
    if not token:
        raise GithubConfigError("GITHUB_TOKEN fehlt fuer GitHub-Schreibzugriffe.")
    return token


async def repo_info(repo: str | None) -> dict[str, Any]:
    repo_name = require_repo(repo)
    data = await _request_json("GET", f"/repos/{repo_name}")
    return {
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "default_branch": data.get("default_branch"),
        "private": data.get("private"),
        "html_url": data.get("html_url"),
        "clone_url": data.get("clone_url"),
    }


async def list_files(repo: str | None, path: str = "", ref: str = "") -> dict[str, Any]:
    repo_name = require_repo(repo)
    suffix = f"?ref={ref}" if ref else ""
    data = await _request_json("GET", f"/repos/{repo_name}/contents/{path.lstrip('/')}{suffix}")
    entries = data if isinstance(data, list) else [data]
    normalized = []
    for item in entries:
        normalized.append({
            "path": item.get("path"),
            "type": item.get("type"),
            "size": item.get("size"),
            "download_url": item.get("download_url"),
            "sha": item.get("sha"),
        })
    return {"repo": repo_name, "path": path or ".", "entries": normalized}


async def read_file(repo: str | None, path: str, ref: str = "") -> dict[str, Any]:
    repo_name = require_repo(repo)
    suffix = f"?ref={ref}" if ref else ""
    data = await _request_json("GET", f"/repos/{repo_name}/contents/{path.lstrip('/')}{suffix}")
    if data.get("type") != "file":
        raise FileNotFoundError(f"Keine Datei: {path}")
    content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
    return {
        "repo": repo_name,
        "path": data.get("path"),
        "sha": data.get("sha"),
        "content": content,
    }


async def download_repo(repo: str | None, destination_zip: str, ref: str = "") -> dict[str, Any]:
    repo_name = require_repo(repo)
    branch = ref or (await repo_info(repo_name)).get("default_branch") or "main"
    url = f"https://github.com/{repo_name}/archive/refs/heads/{branch}.zip"
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
    os.makedirs(os.path.dirname(destination_zip) or ".", exist_ok=True)
    with open(destination_zip, "wb") as f:
        f.write(response.content)
    return {"repo": repo_name, "ref": branch, "zip_path": destination_zip}


async def create_file(repo: str | None, path: str, content: str, message: str, branch: str = "") -> dict[str, Any]:
    repo_name = require_repo(repo)
    token = require_token()
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
    }
    if branch:
        payload["branch"] = branch
    data = await _request_json(
        "PUT",
        f"/repos/{repo_name}/contents/{path.lstrip('/')}",
        json=payload,
        token=token,
    )
    return {"repo": repo_name, "path": path, "commit_sha": data.get("commit", {}).get("sha")}


async def update_file(repo: str | None, path: str, content: str, message: str, sha: str = "", branch: str = "") -> dict[str, Any]:
    repo_name = require_repo(repo)
    token = require_token()
    file_sha = sha
    if not file_sha:
        current = await read_file(repo_name, path, ref=branch)
        file_sha = current["sha"]
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "sha": file_sha,
    }
    if branch:
        payload["branch"] = branch
    data = await _request_json(
        "PUT",
        f"/repos/{repo_name}/contents/{path.lstrip('/')}",
        json=payload,
        token=token,
    )
    return {"repo": repo_name, "path": path, "commit_sha": data.get("commit", {}).get("sha")}


async def delete_file(repo: str | None, path: str, message: str, sha: str = "", branch: str = "") -> dict[str, Any]:
    repo_name = require_repo(repo)
    token = require_token()
    file_sha = sha
    if not file_sha:
        current = await read_file(repo_name, path, ref=branch)
        file_sha = current["sha"]
    payload = {"message": message, "sha": file_sha}
    if branch:
        payload["branch"] = branch
    data = await _request_json(
        "DELETE",
        f"/repos/{repo_name}/contents/{path.lstrip('/')}",
        json=payload,
        token=token,
    )
    return {"repo": repo_name, "path": path, "commit_sha": data.get("commit", {}).get("sha")}


async def _request_json(method: str, path: str, *, json: dict[str, Any] | None = None, token: str = "") -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(
        base_url=settings.GITHUB_API_BASE_URL,
        headers=headers,
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        response = await client.request(method, path, json=json)
        response.raise_for_status()
        return response.json()

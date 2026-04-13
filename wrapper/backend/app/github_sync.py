from __future__ import annotations

import base64
import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests


LOG = logging.getLogger("wrapper.github_sync")


@dataclass
class GitHubSyncConfig:
    enabled: bool
    token: str
    repo: str
    branch: str = "main"
    timeout_seconds: float = 20.0


class GitHubSyncService:
    def __init__(self, config: GitHubSyncConfig) -> None:
        self._config = config
        self._lock_guard = threading.Lock()
        self._path_locks: Dict[str, threading.Lock] = {}

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def repo(self) -> str:
        return self._config.repo

    @property
    def branch(self) -> str:
        return self._config.branch

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self._config.enabled,
            "repo": self._config.repo,
            "branch": self._config.branch,
        }

    def fetch_text(self, repo_path: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "path": repo_path,
            "repo": self._config.repo,
            "branch": self._config.branch,
            "enabled": self._config.enabled,
        }
        if not self._config.enabled:
            result["status"] = "disabled"
            return result
        if not self._config.token or not self._config.repo:
            result["status"] = "misconfigured"
            result["message"] = "GitHub sync token or repository is missing."
            return result

        try:
            response = requests.get(
                self._content_url(repo_path),
                params={"ref": self._config.branch},
                headers=self._headers(),
                timeout=self._config.timeout_seconds,
            )
        except Exception as exc:
            result["status"] = "failed"
            result["message"] = str(exc)
            return result

        result["http_status"] = response.status_code
        if response.status_code == 404:
            result["status"] = "missing"
            return result
        if response.status_code != 200:
            result["status"] = "failed"
            result["message"] = response.text[:500]
            return result

        payload = response.json()
        encoded = str(payload.get("content", "")).replace("\n", "")
        try:
            decoded = base64.b64decode(encoded).decode("utf-8")
        except Exception as exc:
            result["status"] = "failed"
            result["message"] = f"Could not decode GitHub file content: {exc}"
            return result

        result["status"] = "ok"
        result["text"] = decoded
        result["sha"] = str(payload.get("sha", "")).strip()
        return result

    def update_text(self, repo_path: str, text: str, *, message: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "path": repo_path,
            "repo": self._config.repo,
            "branch": self._config.branch,
            "enabled": self._config.enabled,
        }
        if not self._config.enabled:
            result["status"] = "disabled"
            result["message"] = "GitHub sync is disabled."
            return result
        if not self._config.token or not self._config.repo:
            result["status"] = "misconfigured"
            result["message"] = "GitHub sync token or repository is missing."
            return result

        lock = self._path_lock(repo_path)
        with lock:
            for attempt in range(1, 4):
                fetch = self.fetch_text(repo_path)
                if fetch.get("status") not in {"ok", "missing"}:
                    return fetch

                body: Dict[str, Any] = {
                    "message": message,
                    "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
                    "branch": self._config.branch,
                }
                sha = str(fetch.get("sha", "")).strip()
                if sha:
                    body["sha"] = sha

                try:
                    response = requests.put(
                        self._content_url(repo_path),
                        headers=self._headers(),
                        json=body,
                        timeout=self._config.timeout_seconds,
                    )
                except Exception as exc:
                    result["status"] = "failed"
                    result["message"] = str(exc)
                    return result

                result["http_status"] = response.status_code
                if response.status_code in {200, 201}:
                    payload = response.json()
                    commit = payload.get("commit", {}) if isinstance(payload, dict) else {}
                    result["status"] = "ok"
                    result["commit_sha"] = str(commit.get("sha", "")).strip()
                    result["message"] = "GitHub file updated."
                    LOG.info(
                        "github_sync_update_success repo=%s branch=%s path=%s commit=%s",
                        self._config.repo,
                        self._config.branch,
                        repo_path,
                        result["commit_sha"],
                    )
                    return result

                if response.status_code == 409 and attempt < 3:
                    LOG.warning(
                        "github_sync_conflict repo=%s branch=%s path=%s attempt=%s",
                        self._config.repo,
                        self._config.branch,
                        repo_path,
                        attempt,
                    )
                    continue

                result["status"] = "failed"
                result["message"] = response.text[:500]
                return result

        result["status"] = "failed"
        result["message"] = "GitHub sync lock failure."
        return result

    def _path_lock(self, repo_path: str) -> threading.Lock:
        with self._lock_guard:
            existing = self._path_locks.get(repo_path)
            if existing is None:
                existing = threading.Lock()
                self._path_locks[repo_path] = existing
            return existing

    def _content_url(self, repo_path: str) -> str:
        quoted_path = quote(repo_path, safe="/")
        return f"https://api.github.com/repos/{self._config.repo}/contents/{quoted_path}"

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._config.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

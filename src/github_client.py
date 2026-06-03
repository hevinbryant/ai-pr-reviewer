"""GitHub API client — fetch PR diffs and post review comments."""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

import requests


class GitHubClient:
    """Thin wrapper around the GitHub REST API for PR review workflows."""

    BOT_MARKER = "<!-- ai-pr-reviewer -->"

    def __init__(self) -> None:
        self.token = os.environ["GITHUB_TOKEN"]
        self.repo = os.environ["GITHUB_REPOSITORY"]        # "owner/repo"
        self.event_path = os.environ.get("GITHUB_EVENT_PATH", "")
        self.api = "https://api.github.com"

        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        self._event: Optional[dict] = None

    # ── Event data ─────────────────────────────────────────────────────────────

    @property
    def event(self) -> dict:
        if self._event is None:
            with open(self.event_path, encoding="utf-8") as fh:
                self._event = json.load(fh)
        return self._event

    @property
    def pr_number(self) -> int:
        return int(self.event["number"])

    @property
    def pr_title(self) -> str:
        return self.event.get("pull_request", {}).get("title", "")

    @property
    def pr_body(self) -> str:
        return self.event.get("pull_request", {}).get("body") or ""

    # ── API calls ──────────────────────────────────────────────────────────────

    def get_pr_files(self) -> List[Dict]:
        """Return the list of changed files with their patches."""
        url = f"{self.api}/repos/{self.repo}/pulls/{self.pr_number}/files"
        resp = self._session.get(url, params={"per_page": 100})
        resp.raise_for_status()
        return resp.json()

    def post_comment(self, body: str) -> None:
        """Post (or replace) the bot review comment on the PR."""
        self._delete_previous_reviews()
        url = f"{self.api}/repos/{self.repo}/issues/{self.pr_number}/comments"
        resp = self._session.post(url, json={"body": f"{self.BOT_MARKER}\n{body}"})
        resp.raise_for_status()

    def _delete_previous_reviews(self) -> None:
        """Remove old bot comments so each push gets a fresh review."""
        url = f"{self.api}/repos/{self.repo}/issues/{self.pr_number}/comments"
        resp = self._session.get(url, params={"per_page": 100})
        if not resp.ok:
            return
        for comment in resp.json():
            if self.BOT_MARKER in comment.get("body", ""):
                del_url = f"{self.api}/repos/{self.repo}/issues/comments/{comment['id']}"
                self._session.delete(del_url)

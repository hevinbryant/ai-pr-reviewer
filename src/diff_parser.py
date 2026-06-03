"""Parse and filter PR diffs before sending them to the AI."""
from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass
from typing import List

MAX_PATCH_CHARS = 3_000   # truncate individual file patches
MAX_TOTAL_CHARS = 24_000  # total context budget


@dataclass
class FileDiff:
    filename: str
    status: str          # added | modified | removed | renamed
    additions: int
    deletions: int
    patch: str           # unified diff text


def parse_and_filter(raw_files: list) -> tuple[list[FileDiff], list[str]]:
    """
    Convert GitHub API file objects → FileDiff list.
    Returns (included_diffs, skipped_filenames).
    """
    exclude_raw = os.environ.get("EXCLUDE_PATTERNS", "*.lock,*-lock.json,*.min.js,*.min.css")
    exclude_patterns = [p.strip() for p in exclude_raw.split(",") if p.strip()]
    max_files = int(os.environ.get("MAX_FILES", "10"))

    included: list[FileDiff] = []
    skipped: list[str] = []
    total_chars = 0

    for f in raw_files:
        fname = f.get("filename", "")

        # Skip excluded patterns
        if any(fnmatch.fnmatch(fname, pat) for pat in exclude_patterns):
            skipped.append(f"{fname} (excluded by pattern)")
            continue

        # Skip binary / no-patch files
        patch = f.get("patch", "")
        if not patch:
            skipped.append(f"{fname} (binary or empty)")
            continue

        # Enforce max files limit
        if len(included) >= max_files:
            skipped.append(f"{fname} (max_files limit reached)")
            continue

        # Truncate very large patches
        if len(patch) > MAX_PATCH_CHARS:
            patch = patch[:MAX_PATCH_CHARS] + "\n... (truncated)"

        # Enforce total context budget
        if total_chars + len(patch) > MAX_TOTAL_CHARS:
            skipped.append(f"{fname} (context budget exhausted)")
            continue

        included.append(
            FileDiff(
                filename=fname,
                status=f.get("status", "modified"),
                additions=f.get("additions", 0),
                deletions=f.get("deletions", 0),
                patch=patch,
            )
        )
        total_chars += len(patch)

    return included, skipped


def format_diff_for_prompt(diffs: list[FileDiff]) -> str:
    """Render the filtered diffs as a single text block for the prompt."""
    parts: list[str] = []
    for d in diffs:
        parts.append(
            f"### File: `{d.filename}` ({d.status})"
            f"  +{d.additions} / -{d.deletions}\n"
            f"```diff\n{d.patch}\n```"
        )
    return "\n\n".join(parts)

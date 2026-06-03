"""Entry point for the ai-pr-reviewer GitHub Action."""
from __future__ import annotations

import sys
import traceback

from diff_parser import format_diff_for_prompt, parse_and_filter
from github_client import GitHubClient
from reviewer import Reviewer


def main() -> None:
    gh = GitHubClient()

    print(f"[ai-pr-reviewer] Reviewing PR #{gh.pr_number}: {gh.pr_title!r}")

    # 1. Fetch changed files
    raw_files = gh.get_pr_files()
    print(f"[ai-pr-reviewer] {len(raw_files)} file(s) changed in this PR.")

    # 2. Filter and parse diffs
    diffs, skipped = parse_and_filter(raw_files)
    print(f"[ai-pr-reviewer] Reviewing {len(diffs)} file(s), skipping {len(skipped)}.")

    if not diffs:
        print("[ai-pr-reviewer] No reviewable diffs found. Posting a notice.")
        gh.post_comment(
            "## 🤖 AI Code Review\n\n"
            "No reviewable changes were found (all files were binary, "
            "empty, or matched the exclude patterns)."
        )
        return

    diff_text = format_diff_for_prompt(diffs)

    # 3. Run AI review
    rev = Reviewer()
    print(f"[ai-pr-reviewer] Calling {rev.provider} ({rev.model}) …")
    review_body = rev.review(
        title=gh.pr_title,
        body=gh.pr_body,
        diff_text=diff_text,
        skipped=skipped,
    )

    # 4. Post comment
    gh.post_comment(review_body)
    print("[ai-pr-reviewer] ✅ Review posted successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ai-pr-reviewer] ❌ Error: {exc}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

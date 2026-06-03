# 👁️ ai-pr-reviewer

![GitHub Action](https://img.shields.io/badge/GitHub-Action-2088FF?logo=github-actions&logoColor=white)
![Python](https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-v1-orange)

**A GitHub Action that automatically reviews pull requests using AI.**

Every time a PR is opened or updated, `ai-pr-reviewer` fetches the diff, sends it to an AI model, and posts a structured code review comment — covering bugs, security issues, and improvement suggestions.

---

## How It Looks

When a PR is opened, the bot posts a comment like this:

> ## 🤖 AI Code Review
>
> ### 📋 Summary
> This PR adds user authentication using JWT tokens and introduces a new `/login` endpoint.
>
> ### 🚨 Issues
> - `auth/jwt.py` — The JWT secret is hardcoded as `"secret123"`. Use an environment variable instead.
> - `routes/login.py` — Missing rate limiting on the login endpoint; vulnerable to brute-force attacks.
>
> ### 💡 Suggestions
> - `models/user.py` — Consider indexing the `email` column for faster lookups.
>
> ### ✅ What's Good
> - Good separation of concerns between route handlers and business logic.
> - Error responses follow a consistent JSON format.

---

## Quickstart

### 1. Add the workflow to your repository

Create `.github/workflows/ai-review.yml`:

```yaml
name: AI PR Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  pull-requests: write
  contents: read

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: hevinbryant/ai-pr-reviewer@v1
        with:
          github_token:   ${{ secrets.GITHUB_TOKEN }}
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

### 2. Add your API key as a secret

Go to your repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Name | Value |
|------|-------|
| `OPENAI_API_KEY` | `sk-...` |

That's it. Open a pull request and the bot will comment automatically.

---

## Configuration

All inputs are optional except `github_token`.

| Input | Default | Description |
|-------|---------|-------------|
| `github_token` | — | **Required.** Use `${{ secrets.GITHUB_TOKEN }}` |
| `provider` | `openai` | AI provider: `openai` or `anthropic` |
| `openai_api_key` | — | Required when `provider: openai` |
| `anthropic_api_key` | — | Required when `provider: anthropic` |
| `model` | auto | Override the model (e.g. `gpt-4-turbo`, `claude-3-5-sonnet-20241022`) |
| `language` | `en` | Review language: `en` or `zh` |
| `max_files` | `10` | Max number of files to review per PR (controls cost) |
| `exclude_patterns` | `*.lock,...` | Comma-separated glob patterns to skip |

### Using Anthropic Claude

```yaml
- uses: hevinbryant/ai-pr-reviewer@v1
  with:
    github_token:      ${{ secrets.GITHUB_TOKEN }}
    provider:          anthropic
    anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
    language:          en
```

### Chinese review output

```yaml
- uses: hevinbryant/ai-pr-reviewer@v1
  with:
    github_token:   ${{ secrets.GITHUB_TOKEN }}
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    language:       zh
```

---

## How It Works

```
Pull Request opened / updated
         │
         ▼
  Fetch changed files
  via GitHub API
         │
         ▼
  Filter & chunk diffs
  (exclude patterns,
   max_files, token budget)
         │
         ▼
  Send to AI provider
  (OpenAI / Anthropic)
         │
         ▼
  Post structured review
  as PR comment ✅
```

1. **Fetch** — calls GitHub API to get the list of changed files and their unified diffs.
2. **Filter** — skips binary files, lock files, and anything matching `exclude_patterns`; enforces `max_files` and a token budget to keep costs predictable.
3. **Review** — sends the PR title, description, and filtered diffs to the AI with a structured prompt.
4. **Post** — deletes any previous bot comment on the same PR, then posts the fresh review.

---

## Cost Estimate

| Provider | Model | Typical PR (10 files) |
|----------|-------|-----------------------|
| OpenAI | gpt-4o | ~$0.02–0.05 |
| Anthropic | claude-3-5-sonnet | ~$0.01–0.03 |

Each review uses roughly 3,000–8,000 tokens depending on PR size.

---

## Contributing

Issues and pull requests are welcome! Please open an issue first for major changes.

```bash
git clone https://github.com/hevinbryant/ai-pr-reviewer.git
cd ai-pr-reviewer
pip install requests openai anthropic ruff
ruff check src/
```

---

## License

[MIT](LICENSE) © hevinbryant

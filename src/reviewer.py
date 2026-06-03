"""Call the AI provider and return a formatted Markdown review."""
from __future__ import annotations

import os
from typing import Optional

# ── Prompts ────────────────────────────────────────────────────────────────────

_SYSTEM_EN = """\
You are a senior software engineer performing a GitHub pull request code review.
Your goal is to provide clear, constructive, and actionable feedback.

Review priorities (in order):
1. Bugs and correctness issues
2. Security vulnerabilities
3. Performance problems
4. Code quality and maintainability
5. Style and readability

Rules:
- Be specific: reference the filename and approximate line when possible
- Be constructive: suggest HOW to fix, not just what is wrong
- Be concise: skip trivial or obvious remarks
- If you find no issues in a section, say so briefly — do not pad

Output ONLY the following Markdown structure, nothing else:

## 🤖 AI Code Review

### 📋 Summary
[2-3 sentences: what does this PR change and what is the overall quality?]

### 🚨 Issues
[Critical bugs, security problems, or breaking changes as a bullet list.
 Format: `filename` — description. If none: "✅ No critical issues found."]

### 💡 Suggestions
[Non-blocking improvements: performance, readability, naming, tests.
 Format: `filename` — description. If none: "✅ Code looks clean!"]

### ✅ What's Good
[1-3 things done well: good patterns, tests, documentation, etc.]
"""

_SYSTEM_ZH = """\
你是一位资深软件工程师，正在对一个 GitHub Pull Request 进行代码审查。
目标是提供清晰、建设性、可操作的反馈。

审查优先级（按重要性排序）：
1. Bug 和正确性问题
2. 安全漏洞
3. 性能问题
4. 代码质量和可维护性
5. 风格和可读性

规则：
- 具体：尽量引用文件名和大致行号
- 建设性：不只指出问题，还要说明如何修复
- 简洁：跳过显而易见的琐碎备注
- 如某部分没有问题，简短说明即可，不要凑字数

只输出以下 Markdown 结构，不要其他任何内容：

## 🤖 AI 代码审查

### 📋 概述
[2-3 句话：这个 PR 改了什么，整体质量如何？]

### 🚨 问题
[严重 Bug、安全问题或破坏性更改，以项目符号列出。
 格式：`文件名` — 描述。如无：「✅ 未发现严重问题。」]

### 💡 建议
[非阻塞性改进：性能、可读性、命名、测试等。
 格式：`文件名` — 描述。如无：「✅ 代码看起来很整洁！」]

### ✅ 优点
[1-3 条做得好的地方：良好的设计模式、测试覆盖、文档等]
"""

_USER_TEMPLATE = """\
## PR Information
- **Title**: {title}
- **Description**: {body}

## Changed Files
{diff_text}

{skipped_note}
"""


class Reviewer:
    """Unified reviewer supporting OpenAI and Anthropic."""

    DEFAULTS = {
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-20250514",
    }

    def __init__(self) -> None:
        self.provider = os.environ.get("AI_PROVIDER", "openai").lower()
        self.model = os.environ.get("AI_MODEL", "").strip() or self.DEFAULTS.get(self.provider, "gpt-4o")
        self.language = os.environ.get("REVIEW_LANGUAGE", "en").lower()
        self.api_key: Optional[str] = None

        if self.provider == "openai":
            self.api_key = os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                raise EnvironmentError("OPENAI_API_KEY is not set.")
        elif self.provider == "anthropic":
            self.api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise EnvironmentError("ANTHROPIC_API_KEY is not set.")
        else:
            raise ValueError(f"Unknown provider: {self.provider!r}. Use 'openai' or 'anthropic'.")

    def review(self, title: str, body: str, diff_text: str, skipped: list[str]) -> str:
        """Return a Markdown-formatted review string."""
        system = _SYSTEM_ZH if self.language == "zh" else _SYSTEM_EN
        skipped_note = ""
        if skipped:
            skipped_note = (
                "**Note:** The following files were skipped:\n"
                + "\n".join(f"- {s}" for s in skipped)
            )
        user = _USER_TEMPLATE.format(
            title=title or "(no title)",
            body=body or "(no description)",
            diff_text=diff_text,
            skipped_note=skipped_note,
        )

        if self.provider == "openai":
            content = self._call_openai(system, user)
        else:
            content = self._call_anthropic(system, user)

        # Append metadata footer
        footer = (
            f"\n\n---\n"
            f"*🤖 Reviewed by [ai-pr-reviewer](https://github.com/hevinbryant/ai-pr-reviewer) "
            f"· Provider: `{self.provider}` · Model: `{self.model}`*"
        )
        return content.strip() + footer

    # ── Backends ───────────────────────────────────────────────────────────────

    def _call_openai(self, system: str, user: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("openai package missing. Add it to requirements.txt") from e

        client = OpenAI(api_key=self.api_key)
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        return resp.choices[0].message.content or ""

    def _call_anthropic(self, system: str, user: str) -> str:
        try:
            import anthropic
        except ImportError as e:
            raise ImportError("anthropic package missing. Add it to requirements.txt") from e

        client = anthropic.Anthropic(api_key=self.api_key)
        msg = client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text

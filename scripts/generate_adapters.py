#!/usr/bin/env python3
"""
Phoenix 6 FRC Skill — Cross-Tool Adapter Generator
====================================================
Generates instruction files for AI coding tools other than Claude Code,
sourced from the same phoenix6-frc skill content.

Usage:
    python scripts/generate_adapters.py [--output-dir PATH]

Outputs (default: adapters/):
    copilot-instructions.md   →  copy to <robot-project>/.github/copilot-instructions.md
    cursorrules               →  copy to <robot-project>/.cursorrules
    phoenix6-frc.mdc          →  copy to <robot-project>/.cursor/rules/phoenix6-frc.mdc

The adapters embed the gotchas and cheat sheet inline (always-on context) and
reference the full API/patterns files by relative path for on-demand loading.

Requires: Python 3.8+ stdlib only
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SKILL_DIR = REPO_ROOT / "phoenix6-frc"
SKILL_MD = SKILL_DIR / "SKILL.md"
API_MD = SKILL_DIR / "references" / "phoenix6-api.md"
PATTERNS_MD = SKILL_DIR / "references" / "phoenix6-patterns.md"
TUNER_MD = SKILL_DIR / "references" / "tuner-x.md"

GITHUB_URL = "https://github.com/Filip-Kin/CTRE-Skill"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter (--- ... ---) from a markdown file."""
    if text.startswith("---"):
        end = text.index("---", 3)
        return text[end + 3:].lstrip("\n")
    return text


def read_skill_body() -> str:
    """Return SKILL.md body with frontmatter stripped."""
    return strip_frontmatter(SKILL_MD.read_text(encoding="utf-8"))


def read_references() -> dict[str, str]:
    return {
        "api": strip_frontmatter(API_MD.read_text(encoding="utf-8")),
        "patterns": strip_frontmatter(PATTERNS_MD.read_text(encoding="utf-8")),
        "tuner": strip_frontmatter(TUNER_MD.read_text(encoding="utf-8")),
    }


def extract_section(body: str, heading: str) -> str:
    """
    Extract a markdown section by its heading (## Heading).
    Returns from that heading up to (not including) the next same-level heading.
    """
    pattern = rf"(^{re.escape(heading)}\n.*?)(?=^#{{{len(heading.split()[0])},}}[^#]|\Z)"
    m = re.search(pattern, body, re.MULTILINE | re.DOTALL)
    return m.group(1).rstrip() if m else ""


# ---------------------------------------------------------------------------
# Copilot adapter
# ---------------------------------------------------------------------------

COPILOT_HEADER = """\
<!-- Phoenix 6 FRC instructions for GitHub Copilot -->
<!-- Generated from {url} -->
<!-- Drop this file at .github/copilot-instructions.md in your robot project -->

When writing FRC Java code, apply all Phoenix 6 rules below.
"""

def build_copilot_instructions(body: str, refs: dict) -> str:
    """
    Build .github/copilot-instructions.md

    Strategy: embed gotchas + cheat sheet inline (always in context).
    Append full API and patterns inline too — Copilot instructions have no
    hard per-file limit and teams benefit from having everything available.
    """
    sections = [
        COPILOT_HEADER.format(url=GITHUB_URL),
        body,
        "---\n",
        "## Full API Reference\n",
        refs["api"],
        "\n---\n",
        "## Code Patterns\n",
        refs["patterns"],
        "\n---\n",
        "## Phoenix Tuner X & Swerve Generator\n",
        refs["tuner"],
    ]
    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Cursor adapters
# ---------------------------------------------------------------------------

CURSORRULES_HEADER = """\
# Phoenix 6 FRC — Cursor Rules
# Generated from {url}
# Drop this file at .cursorrules in your robot project
#
# For the modern Cursor rules format (.mdc), see phoenix6-frc.mdc instead.

"""

def build_cursorrules(body: str, refs: dict) -> str:
    """Build legacy .cursorrules file (plain markdown, always-on)."""
    sections = [
        CURSORRULES_HEADER.format(url=GITHUB_URL),
        body,
        "\n---\n",
        refs["api"],
        "\n---\n",
        refs["patterns"],
        "\n---\n",
        refs["tuner"],
    ]
    return "\n".join(sections)


MDC_TEMPLATE = """\
---
description: >
  CTRE Phoenix 6 FRC Java rules. Apply when writing code that uses TalonFX,
  Kraken, Falcon, CANcoder, Pigeon2, MotionMagic, Phoenix 6, CTRE, or swerve
  drive in an FRC Java context.
globs:
  - "**/*.java"
alwaysApply: false
---

<!-- Generated from {url} -->

{body}

---

{api}

---

{patterns}

---

{tuner}
"""

def build_mdc(body: str, refs: dict) -> str:
    """Build .cursor/rules/phoenix6-frc.mdc (modern Cursor rules format)."""
    return MDC_TEMPLATE.format(
        url=GITHUB_URL,
        body=body.strip(),
        api=refs["api"].strip(),
        patterns=refs["patterns"].strip(),
        tuner=refs["tuner"].strip(),
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate AI tool adapter files from phoenix6-frc skill content.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "adapters"),
        help="Directory to write adapter files (default: adapters/)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print file sizes without writing",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)

    for src in [SKILL_MD, API_MD, PATTERNS_MD, TUNER_MD]:
        if not src.exists():
            print(f"ERROR: Missing source file: {src}", file=sys.stderr)
            sys.exit(1)

    print("Reading skill content...", file=sys.stderr)
    body = read_skill_body()
    refs = read_references()

    outputs = {
        "copilot-instructions.md": build_copilot_instructions(body, refs),
        "cursorrules": build_cursorrules(body, refs),
        "phoenix6-frc.mdc": build_mdc(body, refs),
    }

    if args.dry_run:
        print("\nDry run — files that would be written:")
        for name, content in outputs.items():
            kb = len(content.encode()) / 1024
            print(f"  {name:35s} {kb:6.1f} KB")
        print("\nInstall instructions:")
        print("  copilot-instructions.md  ->  <project>/.github/copilot-instructions.md")
        print("  cursorrules              ->  <project>/.cursorrules")
        print("  phoenix6-frc.mdc         ->  <project>/.cursor/rules/phoenix6-frc.mdc")
        return

    if not out_dir.exists():
        out_dir.mkdir(parents=True)
        print(f"Created: {out_dir}", file=sys.stderr)

    print(f"\nWriting adapters to {out_dir}/", file=sys.stderr)
    for name, content in outputs.items():
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        kb = len(content.encode()) / 1024
        print(f"  {name:35s} {kb:6.1f} KB", file=sys.stderr)

    print(file=sys.stderr)
    print("Install instructions:", file=sys.stderr)
    print("  copilot-instructions.md  ->  <project>/.github/copilot-instructions.md", file=sys.stderr)
    print("  cursorrules              ->  <project>/.cursorrules", file=sys.stderr)
    print("  phoenix6-frc.mdc         ->  <project>/.cursor/rules/phoenix6-frc.mdc", file=sys.stderr)


if __name__ == "__main__":
    main()

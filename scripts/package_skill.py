#!/usr/bin/env python3
"""
Phoenix 6 FRC Skill Packager
==============================
Packages the phoenix6-frc/ skill directory into a distributable phoenix6-frc.skill file.

Usage:
    python scripts/package_skill.py [--output PATH]

The .skill file is a ZIP archive with the skill directory at its root:
    phoenix6-frc/SKILL.md
    phoenix6-frc/references/phoenix6-api.md
    phoenix6-frc/references/phoenix6-patterns.md
    phoenix6-frc/references/tuner-x.md
    phoenix6-frc/scripts/scrape_phoenix6.py

The archive name must match the skill's `name` field in SKILL.md frontmatter.

Install:
    - Project-level: unzip into .claude/skills/phoenix6-frc/
    - User-level:    unzip into ~/.claude/skills/phoenix6-frc/
    - Or upload the .skill file via Claude Code Settings > Features
"""

import argparse
import zipfile
from pathlib import Path

SKILL_NAME = "phoenix6-frc"
REPO_ROOT = Path(__file__).parent.parent
SKILL_DIR = REPO_ROOT / SKILL_NAME
DEFAULT_OUTPUT = REPO_ROOT / f"{SKILL_NAME}.skill"


def package(output_path: Path) -> None:
    if not SKILL_DIR.exists():
        raise FileNotFoundError(f"Skill directory not found: {SKILL_DIR}")

    skill_md = SKILL_DIR / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"SKILL.md not found in {SKILL_DIR}")

    # Collect all files, sorted for deterministic output
    files = sorted(f for f in SKILL_DIR.rglob("*") if f.is_file())

    if not files:
        raise RuntimeError(f"No files found in {SKILL_DIR}")

    print(f"Packaging {SKILL_NAME} -> {output_path}")
    print()

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            # Archive path: phoenix6-frc/<relative-path>
            rel = file_path.relative_to(SKILL_DIR)
            arc_name = f"{SKILL_NAME}/{rel}"
            zf.write(file_path, arc_name)
            print(f"  + {arc_name}")

    size_kb = output_path.stat().st_size / 1024
    print()
    print(f"Created: {output_path}")
    print(f"Size:    {size_kb:.1f} KB")
    print(f"Files:   {len(files)}")
    print()
    print("Install options:")
    print(f"  Project : unzip {output_path.name} -d <project>/.claude/skills/")
    print(f"  User    : unzip {output_path.name} -d ~/.claude/skills/")
    print(f"  GUI     : Upload via Claude Code -> Settings -> Features")


def verify(output_path: Path) -> None:
    """Verify the produced .skill file has the expected structure."""
    print()
    print("Verifying archive structure...")
    required = {
        f"{SKILL_NAME}/SKILL.md",
        f"{SKILL_NAME}/references/phoenix6-api.md",
        f"{SKILL_NAME}/references/phoenix6-patterns.md",
        f"{SKILL_NAME}/references/tuner-x.md",
        f"{SKILL_NAME}/scripts/scrape_phoenix6.py",
    }

    with zipfile.ZipFile(output_path) as zf:
        names = set(zf.namelist())

    missing = required - names
    if missing:
        print("WARNING: Expected files missing from archive:")
        for f in sorted(missing):
            print(f"  ! {f}")
    else:
        print("  All required files present.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Package phoenix6-frc skill into a .skill file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output .skill file path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip post-package verification",
    )
    args = parser.parse_args()

    output = Path(args.output)
    package(output)

    if not args.no_verify:
        verify(output)


if __name__ == "__main__":
    main()

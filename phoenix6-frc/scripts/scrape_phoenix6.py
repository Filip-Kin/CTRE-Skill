#!/usr/bin/env python3
"""
Phoenix 6 Reference Scraper
============================
Regenerates references/phoenix6-api.md and references/phoenix6-patterns.md
from live CTRE Javadoc and GitHub example code.

Usage:
    python scrape_phoenix6.py [--version 26.1.x] [--dry-run] [--output-dir PATH]

Requires: Python 3.8+ stdlib only (no pip packages needed)

Rerun this script each FRC season to update the references for the new
Phoenix 6 version. The tuner-x.md file is hand-authored and not regenerated.
"""

import argparse
import html.parser
import sys
import textwrap
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JAVADOC_BASE = "https://api.ctr-electronics.com/phoenix6/stable/java"

PACKAGE_PAGES = {
    "controls": f"{JAVADOC_BASE}/com/ctre/phoenix6/controls/package-summary.html",
    "configs": f"{JAVADOC_BASE}/com/ctre/phoenix6/configs/package-summary.html",
    "hardware": f"{JAVADOC_BASE}/com/ctre/phoenix6/hardware/package-summary.html",
    "signals": f"{JAVADOC_BASE}/com/ctre/phoenix6/signals/package-summary.html",
    "sim": f"{JAVADOC_BASE}/com/ctre/phoenix6/sim/package-summary.html",
}

GITHUB_RAW = "https://raw.githubusercontent.com/CrossTheRoadElec/Phoenix6-Examples/main/java"

EXAMPLE_FILES = {
    "MotionMagic": f"{GITHUB_RAW}/MotionMagic/src/main/java/frc/robot/Robot.java",
    "PositionClosedLoop": f"{GITHUB_RAW}/PositionClosedLoop/src/main/java/frc/robot/Robot.java",
    "VelocityClosedLoop": f"{GITHUB_RAW}/VelocityClosedLoop/src/main/java/frc/robot/Robot.java",
    "CurrentLimits": f"{GITHUB_RAW}/CurrentLimits/src/main/java/frc/robot/Robot.java",
    "Simulation": f"{GITHUB_RAW}/Simulation/src/main/java/frc/robot/Robot.java",
    "SwerveWithPathPlanner_TunerConstants": (
        f"{GITHUB_RAW}/SwerveWithPathPlanner/src/main/java/frc/robot/generated/TunerConstants.java"
    ),
    "SwerveWithChoreo_CommandSwerveDrivetrain": (
        f"{GITHUB_RAW}/SwerveWithChoreo/src/main/java/frc/robot/subsystems/CommandSwerveDrivetrain.java"
    ),
}

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def fetch_url(url: str, label: str = "") -> str:
    """Fetch a URL and return the body as a string. Raises on failure."""
    tag = f" ({label})" if label else ""
    print(f"  Fetching{tag}: {url}", file=sys.stderr)
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "phoenix6-skill-scraper/1.0 (FRC team reference tool)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} fetching {url}{tag}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error fetching {url}{tag}: {e.reason}") from e


# ---------------------------------------------------------------------------
# HTML parsing helpers
# ---------------------------------------------------------------------------


class TableRowParser(html.parser.HTMLParser):
    """Extract text from table rows in a Javadoc package-summary page."""

    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._in_td = False
        self._in_th = False
        self._current_row: list[str] = []
        self._current_cell: list[str] = []
        self._in_tr = False

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._in_tr = True
            self._current_row = []
        elif tag in ("td", "th"):
            self._in_td = True
            self._current_cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_td:
            self._current_row.append(" ".join(self._current_cell).strip())
            self._in_td = False
            self._current_cell = []
        elif tag == "tr" and self._in_tr:
            if self._current_row:
                self.rows.append(self._current_row)
            self._in_tr = False

    def handle_data(self, data):
        if self._in_td:
            stripped = data.strip()
            if stripped:
                self._current_cell.append(stripped)


def parse_class_table(html_content: str) -> list[tuple[str, str]]:
    """
    Parse a Javadoc package-summary page and return (ClassName, description)
    pairs from the class/interface summary tables.
    """
    parser = TableRowParser()
    parser.feed(html_content)
    results = []
    for row in parser.rows:
        if len(row) >= 2:
            name = row[0].strip()
            desc = row[1].strip() if len(row) > 1 else ""
            # Skip header rows
            if name.lower() in ("class", "interface", "enum", "exception", "description"):
                continue
            if name:
                results.append((name, desc))
    return results


# ---------------------------------------------------------------------------
# Scrape functions
# ---------------------------------------------------------------------------


def scrape_controls(version: str) -> str:
    """Scrape the controls package and return a markdown section."""
    lines = [
        f"## Control Request Classes (phoenix6 {version})",
        "",
        f"Source: {PACKAGE_PAGES['controls']}",
        "",
    ]

    try:
        html = fetch_url(PACKAGE_PAGES["controls"], "controls")
        classes = parse_class_table(html)
        if not classes:
            lines.append("_Warning: no classes parsed — HTML structure may have changed._")
        else:
            lines.append("| Class | Description |")
            lines.append("|-------|-------------|")
            for name, desc in sorted(classes):
                desc_clean = desc.replace("|", "\\|").replace("\n", " ")
                lines.append(f"| `{name}` | {desc_clean} |")
    except RuntimeError as e:
        lines.append(f"_Scrape failed: {e}_")
        lines.append("")
        lines.append("Manually populate from:")
        lines.append(f"  {PACKAGE_PAGES['controls']}")

    lines.append("")
    return "\n".join(lines)


def scrape_configs(version: str) -> str:
    """Scrape the configs package and return a markdown section."""
    lines = [
        f"## Configuration Classes (phoenix6 {version})",
        "",
        f"Source: {PACKAGE_PAGES['configs']}",
        "",
    ]

    try:
        html = fetch_url(PACKAGE_PAGES["configs"], "configs")
        classes = parse_class_table(html)
        if not classes:
            lines.append("_Warning: no classes parsed — HTML structure may have changed._")
        else:
            lines.append("| Class | Description |")
            lines.append("|-------|-------------|")
            for name, desc in sorted(classes):
                desc_clean = desc.replace("|", "\\|").replace("\n", " ")
                lines.append(f"| `{name}` | {desc_clean} |")
    except RuntimeError as e:
        lines.append(f"_Scrape failed: {e}_")

    lines.append("")
    return "\n".join(lines)


def scrape_hardware(version: str) -> str:
    """Scrape the hardware package and return a markdown section."""
    lines = [
        f"## Hardware Classes (phoenix6 {version})",
        "",
        f"Source: {PACKAGE_PAGES['hardware']}",
        "",
    ]

    try:
        html = fetch_url(PACKAGE_PAGES["hardware"], "hardware")
        classes = parse_class_table(html)
        if not classes:
            lines.append("_Warning: no classes parsed._")
        else:
            lines.append("| Class | Description |")
            lines.append("|-------|-------------|")
            for name, desc in sorted(classes):
                desc_clean = desc.replace("|", "\\|").replace("\n", " ")
                lines.append(f"| `{name}` | {desc_clean} |")
    except RuntimeError as e:
        lines.append(f"_Scrape failed: {e}_")

    lines.append("")
    return "\n".join(lines)


def scrape_examples() -> str:
    """Fetch GitHub example files and return them as a markdown section."""
    lines = [
        "## Official CTRE Examples (extracted source)",
        "",
        "Source: https://github.com/CrossTheRoadElec/Phoenix6-Examples",
        "",
    ]

    for label, url in EXAMPLE_FILES.items():
        lines.append(f"### {label}")
        lines.append(f"Source: `{url}`")
        lines.append("")
        try:
            code = fetch_url(url, label)
            # Trim to first 150 lines to keep file manageable
            code_lines = code.splitlines()
            truncated = len(code_lines) > 150
            snippet = "\n".join(code_lines[:150])
            lines.append("```java")
            lines.append(snippet)
            if truncated:
                lines.append(f"// ... truncated ({len(code_lines)} lines total, showing first 150)")
            lines.append("```")
        except RuntimeError as e:
            lines.append(f"_Fetch failed: {e}_")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output builders
# ---------------------------------------------------------------------------


def build_api_md(version: str) -> str:
    """Build the full phoenix6-api.md content by scraping live docs."""
    header = textwrap.dedent(f"""\
        # Phoenix 6 API Reference (scraped)

        > Auto-generated by scrape_phoenix6.py on {datetime.now().strftime('%Y-%m-%d')}
        > Phoenix 6 version: {version}
        > Javadoc: {JAVADOC_BASE}/
        >
        > **Review this file after regeneration.** The scraper extracts class names and
        > descriptions but does not extract individual field definitions — those are
        > hand-authored in the curated phoenix6-api.md. Use this file to verify that
        > no classes were added or removed between versions.

        ---

    """)
    body = "\n\n".join([
        scrape_hardware(version),
        scrape_controls(version),
        scrape_configs(version),
    ])
    return header + body


def build_patterns_md(version: str) -> str:
    """Build patterns file from scraped GitHub examples."""
    header = textwrap.dedent(f"""\
        # Phoenix 6 Patterns (scraped from official examples)

        > Auto-generated by scrape_phoenix6.py on {datetime.now().strftime('%Y-%m-%d')}
        > Phoenix 6 version: {version}
        > Source: https://github.com/CrossTheRoadElec/Phoenix6-Examples
        >
        > **Review this file after regeneration.** The curated phoenix6-patterns.md
        > contains hand-written patterns with explanations. Use this file to check for
        > new patterns or API changes in official CTRE examples.

        ---

    """)
    body = scrape_examples()
    return header + body


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Regenerate Phoenix 6 reference files from live docs and GitHub examples.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python scrape_phoenix6.py
              python scrape_phoenix6.py --version 26.2.0
              python scrape_phoenix6.py --dry-run
              python scrape_phoenix6.py --output-dir /tmp/refs
        """),
    )
    parser.add_argument(
        "--version",
        default="26.1.x",
        help="Phoenix 6 version string to embed in output headers (default: 26.1.x)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print output to stdout instead of writing files",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write output files (default: ../references/ relative to this script)",
    )
    args = parser.parse_args()

    # Determine output directory
    script_dir = Path(__file__).parent
    if args.output_dir:
        out_dir = Path(args.output_dir)
    else:
        out_dir = script_dir.parent / "references"

    print(f"Phoenix 6 Reference Scraper", file=sys.stderr)
    print(f"  Version : {args.version}", file=sys.stderr)
    print(f"  Output  : {'(dry run — stdout)' if args.dry_run else str(out_dir)}", file=sys.stderr)
    print("", file=sys.stderr)

    errors = []

    # Build API reference
    print("Scraping API reference...", file=sys.stderr)
    try:
        api_content = build_api_md(args.version)
    except Exception as e:
        print(f"ERROR building api content: {e}", file=sys.stderr)
        errors.append(str(e))
        api_content = None

    # Build patterns reference
    print("Scraping example patterns...", file=sys.stderr)
    try:
        patterns_content = build_patterns_md(args.version)
    except Exception as e:
        print(f"ERROR building patterns content: {e}", file=sys.stderr)
        errors.append(str(e))
        patterns_content = None

    # Write or print
    if args.dry_run:
        if api_content:
            print("=" * 60)
            print("FILE: references/phoenix6-api-scraped.md")
            print("=" * 60)
            print(api_content[:3000])
            print("... (truncated for dry-run preview)")
        if patterns_content:
            print("=" * 60)
            print("FILE: references/phoenix6-patterns-scraped.md")
            print("=" * 60)
            print(patterns_content[:3000])
            print("... (truncated for dry-run preview)")
    else:
        if not out_dir.exists():
            print(f"ERROR: Output directory does not exist: {out_dir}", file=sys.stderr)
            print("Create it first or pass --output-dir.", file=sys.stderr)
            sys.exit(1)

        if api_content:
            out_path = out_dir / "phoenix6-api-scraped.md"
            out_path.write_text(api_content, encoding="utf-8")
            print(f"Wrote: {out_path}", file=sys.stderr)

        if patterns_content:
            out_path = out_dir / "phoenix6-patterns-scraped.md"
            out_path.write_text(patterns_content, encoding="utf-8")
            print(f"Wrote: {out_path}", file=sys.stderr)

    if errors:
        print("", file=sys.stderr)
        print(f"Completed with {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    else:
        print("", file=sys.stderr)
        print("Done. Review scraped files before using them to update curated references.", file=sys.stderr)
        print("Note: tuner-x.md is hand-authored and not regenerated by this script.", file=sys.stderr)


if __name__ == "__main__":
    main()

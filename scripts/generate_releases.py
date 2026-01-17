"""
Generate Release Notes page from GitHub Releases API.

This script fetches release information from the GitHub API and generates
a markdown file for MkDocs documentation.

Note: Requires the 'requests' library, which is included in the 'docs'
optional dependencies.
"""

import os
from datetime import datetime
from pathlib import Path

import requests


def fetch_releases(owner: str, repo: str, limit: int = 20) -> list:
    """Fetch releases from GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"

    headers = {"Accept": "application/vnd.github+json"}

    # Use token if available (for higher rate limits)
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(url, headers=headers, params={"per_page": limit})
    response.raise_for_status()

    return response.json()


def format_date(iso_date: str) -> str:
    """Format ISO date to 'December 24, 2025' format."""
    dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
    return dt.strftime("%B %d, %Y")


def generate_markdown(releases: list) -> str:
    """Generate markdown content from releases."""
    lines = [
        "---",
        "hide:",
        "  - navigation",
        "---",
        "",
        "# Release Notes",
        "",
    ]

    if not releases:
        lines.append("*No releases found.*")
        return "\n".join(lines)

    for release in releases:
        tag = release["tag_name"]
        pypi_url = f"https://pypi.org/project/pbir-utils/{tag}/"
        date = (
            format_date(release["published_at"])
            if release.get("published_at")
            else "N/A"
        )
        body = release.get("body") or "*No release notes provided.*"

        lines.append(f"## [{tag}]({pypi_url}) - {date}")
        lines.append("")
        lines.append(body)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    releases = fetch_releases("akhilannan", "pbir-utils")
    markdown = generate_markdown(releases)

    output_path = Path(__file__).parent.parent / "docs" / "releases.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"Generated {output_path} with {len(releases)} releases")


if __name__ == "__main__":
    main()

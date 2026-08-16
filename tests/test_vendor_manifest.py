"""Guards the vendored-code drop: manifest complete, no env files smuggled in.

The vendor folder holds one-way reference copies of the author's own earlier
work. These checks fail the build if a manifest entry goes missing or if any
environment file ever lands under vendor/.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "vendor" / "secondbrain"
MANIFEST = VENDOR / "MANIFEST.md"


def vendored_names_from_manifest() -> list[str]:
    """Parse the manifest's files table: the second column is the vendored name."""
    names = []
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\|\s*`[^`]+`\s*(?:\([^)]*\))?\s*\|\s*`([^`]+)`\s*\|", line)
        if match:
            names.append(match.group(1))
    return names


def test_manifest_exists_and_lists_files():
    assert MANIFEST.exists(), "vendor/secondbrain/MANIFEST.md must exist"
    names = vendored_names_from_manifest()
    assert len(names) >= 10, f"manifest table lists {len(names)} files, expected >= 10"


def test_every_manifest_entry_exists_on_disk():
    missing = [n for n in vendored_names_from_manifest() if not (VENDOR / n).exists()]
    assert missing == [], f"manifest entries missing from vendor/secondbrain/: {missing}"


def test_no_unmanifested_files_in_vendor():
    listed = set(vendored_names_from_manifest()) | {"MANIFEST.md"}
    on_disk = {p.name for p in VENDOR.iterdir() if p.is_file()}
    assert on_disk <= listed, f"files in vendor/ not recorded in the manifest: {on_disk - listed}"


def test_no_env_files_under_vendor():
    env_files = [p for p in (ROOT / "vendor").rglob("*") if p.name.startswith(".env")]
    assert env_files == [], f"env files must never be vendored: {env_files}"

#!/usr/bin/env python3
"""Build the Pages site: index.json + the raw version .md files.

index.json lists every version with its frontmatter metadata, newest first,
so consumers (portal.gambio.de, developers.gambio.de) never need the GitHub API.
"""
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"


def version_key(stem):
    """Numeric sort; pre-releases (_beta/_rc) rank below their final release."""
    base, _, pre = stem.partition("_")
    parts = [int(p) if p.isdigit() else 0 for p in base.split(".")]
    parts += [0] * (4 - len(parts))
    pre_rank, pre_num = 3, 0
    m = re.match(r"(beta|rc)(\d*)", pre)
    if m:
        pre_rank = {"beta": 1, "rc": 2}[m.group(1)]
        pre_num = int(m.group(2) or 0)
    return (parts, pre_rank, pre_num)


def parse_frontmatter(path):
    meta = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return meta
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, val = line.partition(":")
        meta[key.strip()] = val.strip().strip('"')
    return meta


def main():
    files = sorted(
        (p for p in ROOT.glob("*.md") if p.stem[0].isdigit()),
        key=lambda p: version_key(p.stem),
        reverse=True,
    )
    if not files:
        sys.exit("no version .md files found")

    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()

    versions = []
    for p in files:
        meta = parse_frontmatter(p)
        entry = {"version": p.stem, "file": p.name}
        for key in ("status", "php", "mysql", "mariadb", "php_extensions"):
            if meta.get(key):
                entry[key] = meta[key]
        versions.append(entry)
        shutil.copy2(p, OUT / p.name)

    current = next((v["version"] for v in versions if v.get("status") == "current"),
                   versions[0]["version"])
    index = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "current": current,
        "versions": versions,
    }
    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"built _site with index.json ({len(versions)} versions, current: {current})")


main()

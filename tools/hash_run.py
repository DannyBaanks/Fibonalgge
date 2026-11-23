#!/usr/bin/env python3
"""Genera o verifica un manifiesto SHA-256 sin alterar la evidencia original."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

MANIFEST = "ARTIFACT_MANIFEST.json"
SUMS = "SHA256SUMS.txt"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def inventory(root: Path) -> list[dict]:
    records = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name not in {MANIFEST, SUMS}):
        records.append({
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest(path),
        })
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = args.run_dir.resolve()
    if not (root / "RESULTS.json").is_file():
        parser.error("el directorio no contiene RESULTS.json")
    current = inventory(root)
    if args.verify:
        recorded = json.loads((root / MANIFEST).read_text(encoding="utf-8"))["artifacts"]
        if current != recorded:
            print("HASH_MANIFEST_MISMATCH")
            return 1
        print(f"HASH_MANIFEST_OK artifacts={len(current)}")
        return 0
    if (root / MANIFEST).exists() or (root / SUMS).exists():
        parser.error("no se sobrescribe un manifiesto existente")
    (root / MANIFEST).write_text(json.dumps({
        "schema": "fibonalgge-artifact-manifest/v1",
        "run_id": root.name,
        "artifacts": current,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (root / SUMS).write_text("".join(f"{r['sha256']}  {r['path']}\n" for r in current), encoding="utf-8")
    print(f"HASH_MANIFEST_WRITTEN artifacts={len(current)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

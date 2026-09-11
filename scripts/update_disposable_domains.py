"""Explicitly refresh the vendored disposable-domain snapshot.

The application never downloads this list at runtime.  Run this script during
the documented monthly maintenance review, inspect the diff, then commit it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_URL = (
    "https://raw.githubusercontent.com/disposable-email-domains/"
    "disposable-email-domains/main/disposable_email_blocklist.conf"
)


def normalize_domains(text: str) -> list[str]:
    domains: set[str] = set()
    for line_number, raw in enumerate(text.splitlines(), 1):
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        try:
            normalized = value.rstrip(".").encode("idna").decode("ascii").casefold()
        except UnicodeError as exc:
            raise ValueError(f"Invalid IDN on line {line_number}: {value!r}") from exc
        if "@" in normalized or normalized.count(".") < 1 or any(not part for part in normalized.split(".")):
            raise ValueError(f"Invalid domain on line {line_number}: {value!r}")
        domains.add(normalized)
    return sorted(domains)


def refresh(
    source_text: str,
    destination: Path,
    metadata_path: Path,
    source: str,
    source_commit: str,
    minimum_count: int = 1_000,
) -> dict:
    domains = normalize_domains(source_text)
    if len(domains) < minimum_count:
        raise ValueError(
            f"Refusing suspiciously small snapshot: {len(domains)} < {minimum_count}"
        )
    content = "\n".join(domains) + "\n"
    metadata = {
        "source": "https://github.com/disposable-email-domains/disposable-email-domains",
        "source_file": source,
        "source_commit": source_commit or "not-recorded",
        "retrieved_on": date.today().isoformat(),
        "domain_count": len(domains),
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
        "license": "Public Domain dedication; vendored text in docs/licenses/disposable-email-domains-LICENSE.txt",
        "runtime_network_access": False,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(destination)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--source-commit", default="")
    parser.add_argument("--minimum-count", type=int, default=1_000)
    parser.add_argument("--output", type=Path, default=ROOT / "data/disposable_domains.txt")
    parser.add_argument("--metadata", type=Path, default=ROOT / "data/disposable_domains.meta.json")
    args = parser.parse_args()

    if args.source_file:
        source_text = args.source_file.read_text(encoding="utf-8")
        source = str(args.source_file)
    else:
        request = urllib.request.Request(args.url, headers={"User-Agent": "postnode-task1-maintenance"})
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - explicit maintenance URL
            source_text = response.read().decode("utf-8")
        source = args.url

    metadata = refresh(
        source_text,
        args.output,
        args.metadata,
        source,
        args.source_commit,
        args.minimum_count,
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()

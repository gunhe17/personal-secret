from __future__ import annotations

import argparse
import getpass
import json
import subprocess
from datetime import datetime, timezone

from personal_secret.cli.exception import CliError, UsageError
from personal_secret.cli.infrastructure.api.client import api
from personal_secret.cli.infrastructure.ssh.client import ssh


# #
# command

def add(args: argparse.Namespace) -> None:
    data = _collect_fields(args.field)
    created = api.create(
        kind=args.kind,
        name=args.name,
        tags=args.tag,
        expires_at=args.expires,
        data=data,
    )
    print(f"✓ added {created['kind']}:{created['name']}")


def ls(args: argparse.Namespace) -> None:
    rows = api.list(kind=args.kind, tag=args.tag, query=args.query)
    _print_table(rows)


def get(args: argparse.Namespace) -> None:
    revealed = api.reveal(identifier=args.identifier)
    data = revealed.get("data", {})

    # copy — a single field straight to the clipboard
    if args.copy:
        if args.copy not in data:
            raise UsageError(f"필드 '{args.copy}' 가 없습니다. (가능: {', '.join(data)})")
        _pbcopy(str(data[args.copy]))
        print(f"✓ copied '{args.copy}' to clipboard")
        return

    # json — raw dump
    if args.json:
        print(json.dumps(revealed, ensure_ascii=False, indent=2))
        return

    # default — print every field (this is a local terminal, the point is to read it)
    print(f"{revealed['kind']}:{revealed['name']}")
    for key, value in data.items():
        print(f"  {key}: {value}")


def rm(args: argparse.Namespace) -> None:
    if not args.yes:
        answer = input(f'delete "{args.identifier}"? [y/N] ').strip().lower()
        if answer != "y":
            print("aborted")
            return
    api.delete(identifier=args.identifier)
    print("✓ deleted")


def ssh_connect(args: argparse.Namespace) -> None:
    revealed = api.reveal(identifier=args.name)
    if revealed["kind"] != "ssh":
        raise UsageError(f"'{args.name}' 는 ssh 시크릿이 아닙니다 (kind={revealed['kind']}).")
    ssh.connect(data=revealed.get("data", {}))


def expiring(args: argparse.Namespace) -> None:
    rows = api.expiring(within_days=args.days)
    if not rows:
        print(f"(none expiring within {args.days}d)")
        return
    now = datetime.now(timezone.utc)
    for row in rows:
        left = (datetime.fromisoformat(row["expires_at"]) - now).days
        marker = "EXPIRED" if left < 0 else f"{left}d"
        print(f"  {marker:>8}  {row['kind']}:{row['name']}")


# #
# internal

def _collect_fields(raw: list[str]) -> dict:
    # each entry is "key=value"; a bare "key" prompts (hidden) for a sensitive value
    data: dict[str, str] = {}
    for item in raw:
        if "=" in item:
            key, value = item.split("=", 1)
            data[key.strip()] = value
        else:
            key = item.strip()
            data[key] = getpass.getpass(f"{key}: ")
    if not data:
        raise CliError("필드가 비어 있습니다. --field key=value 로 지정하세요.")
    return data


def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("(none)")
        return
    width = max(len(r["name"]) for r in rows)
    for row in rows:
        tags = " ".join(row.get("tags", []))
        expires = row["expires_at"] or "-"
        print(f"  {row['name']:<{width}}  {row['kind']:<8}  {expires:<26}  {tags}")


def _pbcopy(value: str) -> None:
    subprocess.run(["pbcopy"], input=value.encode("utf-8"), check=True)

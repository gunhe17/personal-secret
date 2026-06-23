from __future__ import annotations

import argparse
import getpass
import json
import subprocess

from personal_secret.cli.infrastructure.api.client import api


# #
# command

def login(args: argparse.Namespace) -> None:
    password = getpass.getpass("password: ")
    result = api.login(email=args.email, password=password)
    print(f"✓ logged in (token expires {result['data']['expires_at']})")


def add(args: argparse.Namespace) -> None:
    # value
    # hidden prompt avoids leaving bare keys in shell history
    value = args.value if args.value is not None else getpass.getpass(f"{args.field}: ")
    created = api.create(
        domain=args.domain,
        service=args.service,
        project=args.project,
        field=args.field,
        value=value,
    )
    print(f"✓ added {created['domain']}/{created['service']}/{created['project']}/{created['field']}")


def ls(args: argparse.Namespace) -> None:
    rows = api.list(domain=args.domain, service=args.service, project=args.project)
    _print_table(rows)


def get(args: argparse.Namespace) -> None:
    revealed = api.reveal(id=args.id)
    value = revealed.get("value", "")

    # copy
    if args.copy:
        _pbcopy(value)
        print("✓ copied value to clipboard")
        return

    # json
    if args.json:
        print(json.dumps(revealed, ensure_ascii=False, indent=2))
        return

    # default
    # this is a local terminal, so printing the plaintext value is the point
    print(f"{revealed['domain']}/{revealed['service']}/{revealed['project']}/{revealed['field']}")
    print(f"  {value}")


def rm(args: argparse.Namespace) -> None:
    if not args.yes:
        answer = input(f'delete "{args.id}"? [y/N] ').strip().lower()
        if answer != "y":
            print("aborted")
            return
    api.delete(id=args.id)
    print("✓ deleted")


# #
# internal

def _print_table(rows: list[dict]) -> None:
    if not rows:
        print("(none)")
        return
    width = max(len(_path(r)) for r in rows)
    for row in rows:
        print(f"  {_path(row):<{width}}  {row['id']}")


def _path(row: dict) -> str:
    return f"{row['domain']}/{row['service']}/{row['project']}/{row['field']}"


def _pbcopy(value: str) -> None:
    subprocess.run(["pbcopy"], input=value.encode("utf-8"), check=True)

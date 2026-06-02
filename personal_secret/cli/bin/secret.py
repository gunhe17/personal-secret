from __future__ import annotations

import argparse
import sys

from personal_secret.cli.command import secret
from personal_secret.cli.exception import CliError

KINDS = ("ssh", "service", "api", "db", "cert", "memo")


# #
# parser

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="secret")
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="add a secret")
    p_add.add_argument("kind", choices=KINDS)
    p_add.add_argument("name")
    p_add.add_argument("--tag", action="append", default=[])
    p_add.add_argument("--expires", default=None, help="ISO 8601, e.g. 2026-12-31T00:00:00Z")
    p_add.add_argument("--field", action="append", default=[], help="key=value (bare key prompts hidden)")
    p_add.set_defaults(func=secret.add)

    # ls
    p_ls = sub.add_parser("ls", help="list secrets (metadata only)")
    p_ls.add_argument("--kind", default=None, choices=KINDS)
    p_ls.add_argument("--tag", default=None)
    p_ls.add_argument("--query", default=None)
    p_ls.set_defaults(func=secret.ls)

    # get
    p_get = sub.add_parser("get", help="reveal a secret by name or id")
    p_get.add_argument("identifier")
    p_get.add_argument("--copy", default=None, metavar="FIELD", help="copy one field to clipboard")
    p_get.add_argument("--json", action="store_true")
    p_get.set_defaults(func=secret.get)

    # rm
    p_rm = sub.add_parser("rm", help="delete a secret")
    p_rm.add_argument("identifier")
    p_rm.add_argument("--yes", "-y", action="store_true")
    p_rm.set_defaults(func=secret.rm)

    # ssh
    p_ssh = sub.add_parser("ssh", help="connect using a stored ssh secret")
    p_ssh.add_argument("name")
    p_ssh.set_defaults(func=secret.ssh_connect)

    # expiring
    p_exp = sub.add_parser("expiring", help="secrets near expiry")
    p_exp.add_argument("--days", type=int, default=30)
    p_exp.set_defaults(func=secret.expiring)

    return parser


# #
# run

def main() -> None:
    args = _build_parser().parse_args()
    try:
        args.func(args)
    except CliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()

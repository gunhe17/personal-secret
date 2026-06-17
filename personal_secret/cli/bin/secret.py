from __future__ import annotations

import argparse
import sys

from personal_secret.cli.command import secret
from personal_secret.cli.exception import CliError


# #
# parser

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="secret")
    sub = parser.add_subparsers(dest="command", required=True)

    # login
    p_login = sub.add_parser("login", help="log in (email + password) and store a token")
    p_login.add_argument("email")
    p_login.set_defaults(func=secret.login)

    # add
    p_add = sub.add_parser("add", help="add a secret (domain/service/project/key = value)")
    p_add.add_argument("domain")
    p_add.add_argument("service")
    p_add.add_argument("project")
    p_add.add_argument("field")
    p_add.add_argument("--value", default=None, help="omit to be prompted (hidden)")
    p_add.set_defaults(func=secret.add)

    # ls
    p_ls = sub.add_parser("ls", help="list secrets (metadata only)")
    p_ls.add_argument("--domain", default=None)
    p_ls.add_argument("--service", default=None)
    p_ls.add_argument("--project", default=None)
    p_ls.set_defaults(func=secret.ls)

    # get
    p_get = sub.add_parser("get", help="reveal a secret value by id")
    p_get.add_argument("id")
    p_get.add_argument("--copy", action="store_true", help="copy the value to clipboard")
    p_get.add_argument("--json", action="store_true")
    p_get.set_defaults(func=secret.get)

    # rm
    p_rm = sub.add_parser("rm", help="delete a secret by id")
    p_rm.add_argument("id")
    p_rm.add_argument("--yes", "-y", action="store_true")
    p_rm.set_defaults(func=secret.rm)

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

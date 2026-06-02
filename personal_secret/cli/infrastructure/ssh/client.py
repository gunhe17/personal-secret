from __future__ import annotations

import os
import subprocess
import tempfile

from personal_secret.cli.exception import UsageError


# #
# ssh

class Ssh:
    def connect(self, *, data: dict) -> int:
        # required
        host = data.get("host")
        if not host:
            raise UsageError("ssh 시크릿에 host가 없습니다.")

        # target
        user = data.get("user")
        target = f"{user}@{host}" if user else host

        # args
        args = ["ssh"]
        if data.get("port"):
            args += ["-p", str(data["port"])]
        if data.get("bastion"):
            args += ["-J", str(data["bastion"])]

        # key — explicit path, or materialize an inline key to a 0600 temp file
        key_file = None
        if data.get("key_path"):
            args += ["-i", os.path.expanduser(str(data["key_path"]))]
        elif data.get("private_key"):
            key_file = self._write_key(private_key=str(data["private_key"]))
            args += ["-i", key_file]

        args.append(target)

        # run — inherits the tty; clean up the temp key regardless of outcome
        try:
            completed = subprocess.run(args)
            return completed.returncode
        finally:
            if key_file is not None:
                os.unlink(key_file)

    # #
    # internal

    def _write_key(self, *, private_key: str) -> str:
        fd, path = tempfile.mkstemp(prefix="personal-secret-", suffix=".key")
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(private_key if private_key.endswith("\n") else private_key + "\n")
        return path


# #
# Ssh

ssh = Ssh()

#!/bin/sh
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# pick a Python >= 3.13 (keychain/Touch ID/ssh run on the host, not the container)
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  if command -v python3.13 >/dev/null 2>&1; then
    PY=python3.13
  else
    PY=python3
  fi
fi

VERSION="$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
case "$VERSION" in
  3.13|3.14|3.15) ;;
  *)
    echo "Python 3.13+ 필요 (현재 $PY → $VERSION)."
    echo "  pyenv install 3.13 && PYTHON=\"\$(pyenv prefix 3.13)/bin/python\" sh scripts/install-cli.sh"
    exit 1
    ;;
esac

"$PY" -m venv "$ROOT/.venv-cli"
"$ROOT/.venv-cli/bin/pip" install -U pip >/dev/null
"$ROOT/.venv-cli/bin/pip" install -e "$ROOT[cli]"

echo
echo "✓ installed: $ROOT/.venv-cli/bin/secret"
echo "  PATH에 추가하려면:"
echo "    ln -sf \"$ROOT/.venv-cli/bin/secret\" /usr/local/bin/secret"

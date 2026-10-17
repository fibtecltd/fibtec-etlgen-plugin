#!/bin/bash
# ================================================================
# scripts/in-claude-docker.sh — run the plugin's behavioural tests (plugin_live_tests.py) inside the
# claude-docker container, the way fibtec-etlgen's smoke scripts are run.
#
# Why a wrapper. `--entrypoint bash` skips the container's entrypoint.sh, which is what restores Claude
# Code's login and what drops root for the `claude` user; the tests run `claude -p`, so they need both. This
# does the same two steps, installs the `etlgen` command the Skill drives (the image has pip, not etlgen-client),
# and hands the arguments to the runner. Outside the container it only does the last two.
#
# The plugin repository is not one of the compose file's bind mounts, so mount it for the run (`-v`), or add
# `~/projects/fibtec-etlgen-plugin:/workspace/fibtec-etlgen-plugin` under `volumes:` once.
#
# Usage, from ~/claude-docker on the host. The key is read in your shell and passed by name, so it never
# appears on a command line (zsh: read -rs "?Read key: " ETLGEN_API_KEY):
#
#   # no key, no spend: against the local stand-in
#   docker compose run --rm -T \
#     -v ~/projects/fibtec-etlgen-plugin:/workspace/fibtec-etlgen-plugin \
#     -w /workspace/fibtec-etlgen-plugin --entrypoint bash claude scripts/in-claude-docker.sh --stand-in
#
#   # your Read key, against the real key API
#   read -rsp 'Read key: ' ETLGEN_API_KEY; echo; export ETLGEN_API_KEY
#   export ETLGEN_BASE_URL=<the KeyApiUrl>
#   docker compose run --rm -T -e ETLGEN_API_KEY -e ETLGEN_BASE_URL \
#     -v ~/projects/fibtec-etlgen-plugin:/workspace/fibtec-etlgen-plugin \
#     -w /workspace/fibtec-etlgen-plugin --entrypoint bash claude scripts/in-claude-docker.sh
#
# Any argument is passed to plugin_live_tests.py (--only injection, --turn-timeout 600, ...). The report is
# printed and also saved under reports/ in the repository (not committed).
# ================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# 1. As root in the container: restore the login the entrypoint would have restored, then continue as the
#    `claude` user (the one the interactive session runs as). gosu keeps the environment, so the key arrives.
if [ "$(id -u)" = "0" ] && command -v gosu >/dev/null 2>&1 && id claude >/dev/null 2>&1; then
    persisted=/home/claude/.claude-persist/.claude.json
    if [ -f "$persisted" ]; then
        cp "$persisted" /home/claude/.claude.json
        chown claude:claude /home/claude/.claude.json
    fi
    exec gosu claude env HOME=/home/claude bash "$REPO_ROOT/scripts/in-claude-docker.sh" "$@"
fi

# 2. The command the Skill drives. The image's Python is Debian's (PEP 668), hence the variable; --user keeps
#    it out of the system and it goes with the container.
export PATH="$HOME/.local/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
if ! etlgen --version >/dev/null 2>&1; then
    PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --quiet --user "etlgen-client>=0.2.0"
fi

# 3. The tests.
exec python3 scripts/plugin_live_tests.py "$@"

# fibtec-etlgen-plugin

The source of the **ETL Integrator** plugin for [Claude Code](https://claude.com/claude-code): a skill that drives
the `etlgen` command to turn a source and a destination schema into the Python that connects them, or a REST or
GraphQL connector, or a webhook handler. **The plugin's own README, which is what its users read, is
[plugin/README.md](plugin/README.md).**

```bash
claude plugin marketplace add fibtecltd/fibtec-etlgen-plugin
claude plugin install etlgen@fibtec-etlgen
```

## What is where

```text
.claude-plugin/marketplace.json     the marketplace: one entry, source ./plugin
plugin/                             THE PLUGIN: only this folder is installed or submitted to the directory
  .claude-plugin/plugin.json          its manifest (the version is set here, and only here)
  .claude-plugin/icon.png             its listing icon (square PNG, 512 to 2048 px)
  skills/generate/SKILL.md            the skill
  README.md, LICENSE
tests/  scripts/  .github/           development only: not installed, not part of the plugin
```

People who install the plugin get only `plugin/`, and the directory reads and scans only that folder (the plugin
path of the submission, which cannot be changed after it is made). Keep the tests, the scripts and anything else
that is not the plugin outside it.

## Development

```bash
pip install -r requirements-dev.txt
pytest                                  # the skill's text, its exit-code table against the CLI's own, the manifests,
                                        # the plugin folder's contents, and the behaviour tests' own tests (no model, no network)
claude plugin validate . --strict       # the marketplace; needs Claude Code
claude plugin validate ./plugin --strict   # the plugin
```

A release is a change to `version` in `plugin/.claude-plugin/plugin.json` and a tag.

### Does a model actually follow the skill?

The tests above read text. `scripts/plugin_live_tests.py` runs Claude Code itself (`claude -p`, with the `plugin/`
folder as the plugin) through the conversations that matter and checks each transcript by rules: the
estimate comes before any paid call, the key is never printed or put on a command line, a planted instruction
in a schema is not followed, an existing file is not overwritten unasked, a refused key is explained and not
retried, a missing key stops cleanly. It prints a Markdown report you can paste back.

```bash
# no key, no spend: a local stand-in for the key API (scripts/stand_in_key_api.py), made-up keys
python scripts/plugin_live_tests.py --stand-in

# your own Read key against the real key API (exported in this shell, never on a command line)
read -rsp 'Read key: ' ETLGEN_API_KEY; echo; export ETLGEN_API_KEY
export ETLGEN_BASE_URL=https://<key-api-id>.execute-api.<region>.amazonaws.com
python scripts/plugin_live_tests.py
```

To run the same thing in a container, `scripts/in-claude-docker.sh` restores a Claude login, installs `etlgen`
and runs the tests; its header has the exact commands.

It costs model usage (about eight `claude -p` turns). With a real key it first proves the key is Read-only
(a free review is refused) and never allows a paid command otherwise. Reports and transcripts, with the key
masked, go to `reports/` (not committed). Exit 0 means no rule was broken; **NOTE** lines are worth a read.

## Licence

Apache-2.0. See [LICENSE](LICENSE).

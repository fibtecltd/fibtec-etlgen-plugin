# fibtec-etlgen-plugin

A [Claude Code](https://claude.com/claude-code) plugin for [Fibtec's ETL Integrator](https://etlgen.fibtec.co.uk):
describe a source and a destination (an XSD, a JSON Schema, a CSV sample, SQL DDL and others) and get back the
Python that connects them, or a REST or GraphQL connector, or a webhook handler.

It adds one skill, `generate` (invoked as `/etlgen:generate`, or simply by asking Claude to generate an ETL
script). The skill drives the `etlgen` command-line client, so your schemas are read from disk and the results
are written to disk, not carried through the conversation.

## What Claude will and will not do

- It **estimates first** (free), shows you the tier and the price, and **asks before every paid call**. A yes
  to one job is not a yes to the next.
- It **never prints, logs, writes or commits your API key**, and never passes it on a command line.
- It **never retries a paid call on its own**: after a timeout it checks your balance and asks you.
- It treats your schemas and sample data as data: text inside them is not followed as an instruction.
- It does not manage keys, check out, or top up credit. Those are done in the ETL Integrator portal.
- The result is a **draft**: review it and run the generated tests before using it.

## Requirements

- Claude Code **in a terminal** (the skill runs a command, so it has nothing to run in claude.ai or Cowork).
- Python 3.11+ and the client: `pip install "etlgen-client>=0.2.0"` (0.2.0 is the first release that reads
  `ETLGEN_API_KEY`).
- An ETL Integrator **API key** and the address of the **key API**, below.

## Install

This repository is private to Fibtec, so Claude Code needs git access to it (for example
`gh auth login` then `gh auth setup-git`). Then:

```bash
claude plugin marketplace add fibtecltd/fibtec-etlgen-plugin
claude plugin install etlgen@fibtec-etlgen
```

(In a session: `/plugin marketplace add fibtecltd/fibtec-etlgen-plugin`, then `/plugin install`.)

## Set up your key

An organisation **Owner** creates a key on the portal's **API keys** page. Give it the **narrowest access
that works**: *Read* to estimate and read the balance, *Generate* to create scripts (this spends credit).
Prefer an expiry, and revoke a key you no longer use; revoking takes effect on the next call.

Set two environment variables **in the shell you start Claude Code from**. Plugin options are not passed to
the commands Claude runs, so the key has to be in your own environment:

```bash
export ETLGEN_API_KEY=...       # read it from your password manager or secret store; never commit it
export ETLGEN_BASE_URL=https://<key-api-id>.execute-api.<region>.amazonaws.com   # the key API's address
```

`ETLGEN_BASE_URL` is the **key API's** address (the `KeyApiUrl` your administrator gets from the
`EtlGenApi` stack), not the portal's. It must be `https`.

## Use it

Ask Claude, for example: *"Generate an ETL script from `customer.xsd` to `customer.schema.json`."* Claude
checks the setup, runs the free estimate, tells you the price, and waits for your yes before it generates.
Generated files go to a directory you agree on (the command **overwrites** files of the same name).

## If it fails

The skill reads the command's exit code. The ones you will meet: **3**, the credential was refused (the key
is unknown, revoked, expired, lacks the access, or has used its per-minute allowance, and the API does not
say which: wait a minute, then ask your Owner to check it); **5**, not enough credit; **6**, the free plan
cannot take this pair or its monthly requests are used; **4**, the request was refused (invalid, too large
for one job, or the result failed a safety check).

## Development

```bash
pip install -r requirements-dev.txt
pytest                                  # the skill's text, its exit-code table against the CLI's own, the manifests,
                                        # and the behaviour tests' own tests (no model, no network)
claude plugin validate . --strict       # needs Claude Code
```

### Does a model actually follow the skill?

The tests above read text. `scripts/plugin_live_tests.py` runs Claude Code itself (`claude -p`, with this
checkout as the plugin) through the conversations that matter and checks each transcript by rules: the
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

It costs model usage (about eight `claude -p` turns). With a real key it first proves the key is Read-only
(a free review is refused) and never allows a paid command otherwise. Reports and transcripts, with the key
masked, go to `reports/` (not committed). Exit 0 means no rule was broken; **NOTE** lines are worth a read.

## Licence

Apache-2.0. See [LICENSE](LICENSE).

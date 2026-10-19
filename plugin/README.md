# ETL Integrator for Claude Code

**Status: alpha (0.1.x).** A [Claude Code](https://claude.com/claude-code) plugin for [Fibtec's ETL Integrator](https://etlgen.fibtec.co.uk):
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
export ETLGEN_BASE_URL=https://<key-api-id>.execute-api.<region>.amazonaws.com   # copy it from the API keys page
```

`ETLGEN_BASE_URL` is the **key API's** address, not the portal's. The portal shows it on the **API keys**
page, above your keys, with a button to copy it. It is not a secret. It must be `https`.

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

## What it runs, sends and fetches

- **The plugin is one skill and nothing else:** no hooks, no MCP servers, no agents and no scripts. It never
  installs or downloads anything itself.
- **What Claude runs:** the `etlgen` command (the published `etlgen-client` from PyPI, which you install): a version
  check, `etlgen billing get`, `etlgen generate estimate`, `etlgen generate etl` (and `connector`, `webhook`, `review`)
  and `etlgen triangle`, plus `mktemp`, `ls` and `rm` for a temporary parameters file. The paid commands keep
  Claude Code's permission prompt, and Claude asks for your yes first.
- **What is sent, and where:** `etlgen` sends the content of the source and destination files you point it at,
  the job's options, and your API key to the address in `ETLGEN_BASE_URL` (the ETL Integrator's key API) and to
  nowhere else. The plugin itself makes no network request. Fibtec's own pages say how the service handles what it
  receives: <https://etlgen.fibtec.co.uk>.
- **What is read:** the files you name, and the two environment variables above. Claude is told never to print,
  log or write the key; the command reads it from your environment, not from Claude.

## Support

Questions and problems: <https://github.com/fibtecltd/fibtec-etlgen-plugin/issues>. The product is at
<https://etlgen.fibtec.co.uk>, with an [API reference](https://etlgen.fibtec.co.uk/api-docs.html).

## Licence

Apache-2.0. See [LICENSE](LICENSE).

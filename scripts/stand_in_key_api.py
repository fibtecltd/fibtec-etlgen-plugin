"""scripts/stand_in_key_api.py — a local stand-in for the ETL Integrator's key API.

For trying the plugin without a real key, a real organisation or any spend: it answers the seven routes
the `etlgen` command uses (the key API's, E15) from memory, on 127.0.0.1. It is not the service. It
reproduces only what the plugin's behaviour depends on:

- a request without a Bearer header is a 401 `{"message": "Unauthorized"}`; an unknown key, or a key
  without the scope the route needs, is a bare 403 `{"message": "Forbidden"}` that does not say which;
- scopes: `read` for the estimate, the balance and the triangle, `generate` for `POST /generate`, and
  independent of each other;
- a generation takes its price from the balance, and a review (`options.review_inferred_schema`) does
  not; `POST /generate` with no formats is a 422 before any charge.

The two keys it knows are made up here, at run time, and are worth nothing anywhere else. Every request is
recorded (path, which key, status, never the key) in `StandIn.requests`, so a test can ask what the
plugin really called.

    python scripts/stand_in_key_api.py --port 8765
"""

from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, NamedTuple

PRICE_PENCE = 200
START_BALANCE_PENCE = 100_000


def fake_key(letter: str) -> str:
    """A key-shaped string that exists nowhere: 12 hex characters of `a`/`b` and 43 of `letter`."""
    return "elk_" + (letter * 12) + "_" + (letter * 43)


READ_KEY = fake_key("a")
GENERATE_KEY = fake_key("b")
KEYS = {READ_KEY: ("read",), GENERATE_KEY: ("read", "generate")}
KEY_NAMES = {READ_KEY: "READ", GENERATE_KEY: "GENERATE"}

# route -> the scope it needs (the real table is api_key.ROUTE_SCOPES in fibtec-etlgen)
ROUTES = {
    ("POST", "/generate"): "generate",
    ("POST", "/generate/estimate"): "read",
    ("GET", "/billing"): "read",
    ("GET", "/triangle"): "read",
}

TRIANGLE = {
    "c": 0.12, "t": 0.2, "q": 0.05, "a_hat": 0.0347, "tes": 9.7, "flags": [], "it_version": "IT-1.0.0",
}


class Request(NamedTuple):
    method: str
    path: str
    key: str  # "none", "unknown", "READ" or "GENERATE"
    status: int


class StandIn:
    """The state behind the server: one organisation, a balance, a job count and the request log."""

    def __init__(self) -> None:
        self.balance = START_BALANCE_PENCE
        self.jobs = 0
        self.requests: list[Request] = []
        self._lock = threading.Lock()

    def answer(self, method: str, path: str, auth: str, body: dict[str, Any]) -> tuple[int, dict]:
        credential = auth.removeprefix("Bearer ") if auth.startswith("Bearer ") else ""
        key = KEY_NAMES.get(credential, "unknown" if credential else "none")
        with self._lock:
            status, payload = self._route(method, path, credential, body)
            self.requests.append(Request(method, path, key, status))
        return status, payload

    def _route(self, method: str, path: str, credential: str, body: dict) -> tuple[int, dict]:
        scope = ROUTES.get((method, path.split("?")[0]))
        if scope is None and not path.startswith("/triangle/"):
            return 404, {"message": "Not Found"}
        if not credential:
            return 401, {"message": "Unauthorized"}
        scopes = KEYS.get(credential)
        if scopes is None or (scope and scope not in scopes):
            return 403, {"message": "Forbidden"}
        if path.startswith("/triangle/"):
            return 404, {"error": "job not found"}
        if path == "/billing":
            return 200, {
                "plan": "paid", "credit_balance_pence": self.balance, "payments": [],
                "price_table": {"low": {"model": "stand-in", "price_gbp_pence": PRICE_PENCE}},
            }
        if path == "/triangle":
            return 200, {"job_count": self.jobs, "triangle": TRIANGLE if self.jobs else None}
        if not (body.get("source") or {}).get("format") or not (
            body.get("destination") or {}
        ).get("format"):
            return 422, {"error": "source.format and destination.format are required"}
        if path == "/generate/estimate":
            return 200, {
                "tier": "medium", "model": "stand-in", "price_expected_gbp_pence": PRICE_PENCE,
                "dev_cost_gbp_pence": 48_000, "dev_hours": 6.0,
            }
        options = body.get("options") or {}
        if options.get("review_inferred_schema"):
            return 200, {"review": {"source": {}, "destination": {}}}
        if self.balance < PRICE_PENCE:
            return 402, {"error": "insufficient credit balance", "price_gbp_pence": PRICE_PENCE}
        self.balance -= PRICE_PENCE
        self.jobs += 1
        return 200, {
            "script": "def run(record):\n    return record\n",
            "tests": "def test_run():\n    assert True\n" if options.get("include_tests") else None,
            "unresolved_fields": [],
            "pricing": {
                "plan": "paid", "tier": "medium", "model": "stand-in",
                "price_expected_gbp_pence": PRICE_PENCE, "price_charged_gbp_pence": PRICE_PENCE,
            },
            "triangle": TRIANGLE,
        }

    def calls(self, path: str, *, key: str | None = None) -> list[Request]:
        return [r for r in self.requests if r.path == path and (key is None or r.key == key)]


def _handler(stand_in: StandIn) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: object) -> None:  # silent: the request log is the record
            pass

        def _serve(self) -> None:
            length = int(self.headers.get("content-length") or 0)
            raw = self.rfile.read(length) if length else b""
            try:
                body = json.loads(raw) if raw else {}
            except ValueError:
                body = {}
            status, payload = stand_in.answer(
                self.command, self.path, self.headers.get("authorization", ""), body
            )
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = _serve

    return Handler


def start(port: int = 0) -> tuple[StandIn, ThreadingHTTPServer, str]:
    """Serve on 127.0.0.1 in a thread. Returns the state, the server (call `.shutdown()`) and its URL."""
    stand_in = StandIn()
    server = ThreadingHTTPServer(("127.0.0.1", port), _handler(stand_in))
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
    return stand_in, server, f"http://127.0.0.1:{server.server_address[1]}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    _, server, url = start(args.port)
    print(f"stand-in key API on {url}")
    print("Read key and Generate key (made up, worth nothing): export ETLGEN_API_KEY=<one of them>")
    print(f"  Read:     {READ_KEY}")
    print(f"  Generate: {GENERATE_KEY}")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

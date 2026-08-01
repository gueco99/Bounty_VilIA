#!/usr/bin/env python3
"""
Secur0 API client — the pieces needed to take a newly-detected program from
"just appeared" to "guidelines signed, report drafted and (on confirmation)
submitted", without ever handling the user's password.

Endpoints (all discovered by reading captured browser traffic this session,
2026-07-31; none are officially documented):
  GET  /api/programs/list                          -- public, no auth
  GET  /api/programs/details?type=X&name=Y          -- public, no auth
  POST /api/guidelines/sign/{program_id}             -- needs session cookies
  POST /api/reports/create                           -- needs session cookies

Session cookies are never fetched by this module. The user logs in
themselves (browser, or `!curl` in a live Claude Code session) and the
resulting sessionid/csrftoken are stored via `save_session()` into
memory/secur0_session.json (gitignored). Every function that needs auth
reads from that file and raises Secur0AuthError if it's missing or the
server rejects it -- the caller is responsible for telling the user to
refresh their session, never for obtaining a new one on its own.

CVSS/Endpoint/Colaboradores/Attachments fields are deliberately NOT part of
create_report() -- per explicit instruction, reports go out with just
title/description/payload/proof_of_concept/impact and those richer fields
are left for manual follow-up if ever needed.
"""

import json
import urllib.error
import urllib.request
from base64 import b64encode
from pathlib import Path
from typing import Optional

API_BASE = "https://api.secur0.com/api"
SESSION_CACHE_PATH = Path(__file__).resolve().parent.parent / "memory" / "secur0_session.json"

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:151.0) Gecko/20100101 Firefox/151.0"


class Secur0AuthError(Exception):
    """Raised when there's no cached session, or the server rejects it (expired/invalid)."""


class Secur0ApiError(Exception):
    """Raised for any other non-2xx response."""


def save_session(sessionid: str, csrftoken: str) -> None:
    """Persist a freshly-obtained session to the local (gitignored) cache."""
    SESSION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSION_CACHE_PATH.write_text(json.dumps({"sessionid": sessionid, "csrftoken": csrftoken}))
    SESSION_CACHE_PATH.chmod(0o600)


def _load_session() -> tuple[str, str]:
    if not SESSION_CACHE_PATH.exists():
        raise Secur0AuthError("No cached Secur0 session. User needs to log in and call save_session().")
    data = json.loads(SESSION_CACHE_PATH.read_text())
    try:
        return data["sessionid"], data["csrftoken"]
    except KeyError as e:
        raise Secur0AuthError(f"Session cache is malformed (missing {e}).") from e


def _request(method: str, path: str, *, params: Optional[dict] = None, body: Optional[dict] = None, auth: bool = False) -> dict:
    url = f"{API_BASE}{path}"
    if params:
        from urllib.parse import urlencode
        url = f"{url}?{urlencode(params)}"

    headers = {
        "User-Agent": USER_AGENT,
        "Origin": "https://app.secur0.com",
    }
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    if auth:
        sessionid, csrftoken = _load_session()
        headers["Cookie"] = f"sessionid={sessionid}; csrftoken={csrftoken}"
        headers["X-CSRFToken"] = csrftoken

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        if e.code in (401, 403) and auth:
            raise Secur0AuthError(f"Secur0 rejected the cached session (HTTP {e.code}): {raw}") from e
        raise Secur0ApiError(f"HTTP {e.code} from {method} {path}: {raw}") from e


def get_program_details(program_type: str, name: str) -> dict:
    """No auth needed. Returns the full program detail payload, including 'scopes'."""
    return _request("GET", "/programs/details", params={"type": program_type, "name": name})


def get_in_scope_targets(program_type: str, name: str) -> list[dict]:
    """Convenience wrapper: just the in-scope scope entries (scope_id + pattern)."""
    details = get_program_details(program_type, name)
    return [s for s in details.get("scopes", []) if s.get("in_scope") and not s.get("is_deleted")]


def sign_guidelines(program_id: int) -> dict:
    """
    Needs a cached session. Empty-body POST; raises Secur0AuthError if the session is stale.
    "Already signed" is treated as success, not an error -- it's a benign, expected outcome
    for any program this account has engaged with before.
    """
    try:
        return _request("POST", f"/guidelines/sign/{program_id}", auth=True)
    except Secur0ApiError as e:
        if "guideline_already_signed" in str(e):
            return {"message": "Guideline was already signed", "already_signed": True}
        raise


def create_report(
    *,
    program_id: int,
    scope_id: int,
    title: str,
    description: str,
    payload: str,
    proof_of_concept: str,
    impact: str,
    language: str = "en",
) -> dict:
    """
    Needs a cached session. Text fields are base64-encoded here (the API expects that).
    Deliberately no cvss/endpoint/attachments/colaboradores support -- see module docstring.
    Returns {"report_id": ..., "upload_token": ...} on success.
    """
    def b64(s: str) -> str:
        return b64encode(s.encode("utf-8")).decode("ascii")

    body = {
        "program": {"program_id": program_id},
        "scope": {"scope_id": scope_id},
        "title": b64(title),
        "payload": b64(payload),
        "language": language,
        "description": b64(description),
        "proof_of_concept": b64(proof_of_concept),
        "impact": b64(impact),
    }
    return _request("POST", "/reports/create", body=body, auth=True)


def parse_report_markdown(path: str) -> dict:
    """
    Parse a findings/**/report_secur0.md file into the section dict used by
    create_report(). Handles both report template generations seen in this
    repo:
      - current: "## Title", "## Technical details", "## Payload",
        "## Proof of Concept (steps)", "## Impact" -- content is the raw
        section body.
      - older ("Secur0 form" style): "## Title (0/100)",
        "## Technical detail (0/5000)", "## Proof of concept (0/5000)", etc
        -- content is wrapped in a single ``` fence, sometimes followed by a
        trailing "(N chars)" line outside the fence.
    Only pulls the 5 fields the API actually accepts -- CVSS/Endpoint/
    Colaboradores/Attachments are ignored even if present in the file.
    """
    import re

    text = Path(path).read_text(encoding="utf-8")
    raw_sections = {}
    for m in re.finditer(r"^## (.+?)\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S):
        # Normalize the header: strip a trailing "(0/500)"-style counter and
        # any leading/trailing whitespace, lowercase for matching.
        header = re.sub(r"\s*\(\d+/\d+\)\s*$", "", m.group(1).strip())
        raw_sections[header.lower()] = m.group(2).strip()

    def extract(*aliases: str) -> str:
        for alias in aliases:
            if alias in raw_sections:
                body = raw_sections[alias]
                fence = re.match(r"^```\n?(.*?)\n?```", body, flags=re.S)
                return fence.group(1).strip() if fence else body
        return ""

    # Spanish-language reports use "## Título"/"## Detalle técnico" etc. instead
    # of the English headers -- detect it from whichever header actually matched,
    # so `language` sent to create_report matches the report's real content
    # instead of always defaulting to "en" (caught 2026-07-31 on cogny: the
    # report was in Spanish but the API call still said language=en).
    is_spanish = "título" in raw_sections or "titulo" in raw_sections

    return {
        "title": extract("title", "título", "titulo"),
        "description": extract("technical details", "technical detail", "detalle técnico", "detalle tecnico"),
        "payload": extract("payload"),
        "proof_of_concept": extract("proof of concept (steps)", "proof of concept", "prueba de concepto (pasos)", "prueba de concepto"),
        "impact": extract("impact", "impacto"),
        "language": "es" if is_spanish else "en",
    }


def submit_report_from_file(report_path: str, program_type: str, program_name: str) -> dict:
    """
    Full submit flow for one drafted report: look up the program's program_id
    + first in-scope scope_id (no auth), parse the report markdown, then
    create_report() (auth). Raises if the program has no in-scope entries.
    """
    details = get_program_details(program_type, program_name)
    in_scope = [s for s in details.get("scopes", []) if s.get("in_scope") and not s.get("is_deleted")]
    if not in_scope:
        raise Secur0ApiError(f"No in-scope targets found for {program_name} ({program_type})")

    fields = parse_report_markdown(report_path)
    return create_report(
        program_id=details["program_id"],
        scope_id=in_scope[0]["scope_id"],
        **fields,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "save-session" and len(sys.argv) == 4:
        save_session(sys.argv[2], sys.argv[3])
        print(f"Session cached to {SESSION_CACHE_PATH}")
    elif cmd == "details" and len(sys.argv) == 4:
        print(json.dumps(get_program_details(sys.argv[2], sys.argv[3]), indent=2))
    elif cmd == "sign" and len(sys.argv) == 3:
        print(json.dumps(sign_guidelines(int(sys.argv[2])), indent=2))
    elif cmd == "parse" and len(sys.argv) == 3:
        print(json.dumps(parse_report_markdown(sys.argv[2]), indent=2))
    elif cmd == "submit" and len(sys.argv) == 5:
        print(json.dumps(submit_report_from_file(sys.argv[2], sys.argv[3], sys.argv[4]), indent=2))
    else:
        print("Usage:")
        print("  secur0_api.py save-session <sessionid> <csrftoken>")
        print("  secur0_api.py details <type> <name>")
        print("  secur0_api.py sign <program_id>")
        print("  secur0_api.py parse <report_secur0.md path>")
        print("  secur0_api.py submit <report_secur0.md path> <program_type> <program_name>")
        sys.exit(1)

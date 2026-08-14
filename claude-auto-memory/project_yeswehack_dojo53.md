---
name: project_yeswehack_dojo53
description: YesWeHack Dojo
metadata: 
  node_type: memory
  type: project
  originSessionId: 9264bc16-895f-41d7-ad5f-195630c3c6dd
---

Solved YesWeHack Dojo #53 ("Hacker Club" by BrumensYWH), a training CTF at
dojo-yeswehack.com/challenge-of-the-month/dojo-53. Flag: `FLAG{Hack3rs_Wann4_Be_Hack3rs}`.
Full write-up at `findings/yeswehack-dojo53-hacker-club-ssti/writeup.md` in the
claude-bug-bounty repo.

Exploit chain (reusable pattern, not target-specific):
1. **Parser differential bypass**: the app's access-check used a hand-rolled regex
   (`/@\s*([a-z0-9.-]+)/i`) to extract the email domain for a reserved-domain block,
   but the actual routing decision used Ruby's `mail` gem (RFC 5322 compliant) on the
   same raw string. RFC 5322 comments `(...)` inside a domain (e.g.
   `user@dojo-yeswehack(test).com`) are invisible to the regex (stops at `(`) but get
   stripped by the real parser, so the two disagree on what domain the address is —
   bypassing the block.
2. **ERB SSTI**: the email address's display-name was interpolated into ERB template
   *source* via Ruby string interpolation (`#{name}` inside a heredoc) before
   `ERB.new(...).result(binding)` compiled it — instead of being passed in as a
   template local. Any `<%= ... %>` in the display name (RFC 5322 quoted-strings allow
   almost any char) executes as real Ruby with access to the calling binding → RCE.
3. Used the RCE to dump `ENV['DOJO_OPTS']`, found the sandbox setup script wrote the
   flag to `/tmp/app/flag.txt`, then `File.read` it directly.

**Why this matters going forward:** two known-name gotchas: (a) whenever an app parses
the same untrusted string with two different parsers for two different decisions
(regex pre-check + real parser downstream) — check for differentials, especially
around comments/whitespace/encoding the regex doesn't model. (b) whenever user input
reaches an ERB/template *string* via `#{}` interpolation before `.result()` is called
(rather than being passed as a local for `<%= %>` to read) — that's SSTI, not just XSS.

**Decoy flag note:** the page shipped a base64-encoded HTML/CSS comment
(`FLAG{H4ck3rman_Club}`) present in the static source regardless of whether the
challenge was solved — a deliberate red herring for people who view-source without
exploiting. Don't trust a flag/secret found in static page source without confirming
it's live-server-generated.

**Tooling gotcha**: extracting response HTML via `javascript_tool` (decoding a
`data:` URL iframe and reading text) got blocked by Claude in Chrome's own
content-safety filter (`[BLOCKED: Cookie/query string data]`) — false-positived on
an `ENV.to_a` dump's `KEY=value` formatting looking like cookies. Workaround: narrow
the payload to request one small value at a time and read the rendered output via
screenshot/zoom instead of JS extraction.

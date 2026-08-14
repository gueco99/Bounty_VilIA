---
name: project-boomingmusic
description: "BoomingMusic Android VDP hunt state — fresh target, 1 finding submitted (ReDoS)"
metadata: 
  node_type: memory
  type: project
  originSessionId: ff7451f9-ed99-4be8-8d13-3103f0c4f6ba
---

Active since 2026-08-04. Secur0 VDP (program_id 132, scope_id 502 = github.com/mardous/BoomingMusic), fresh target (0 prior reports before this session). Kotlin/Android music player, Media3-based.

Findings:
- **report_id 3507 (SUBMITTED)**: ReDoS in `LyricsDownloadService.kt`'s `cleanTitle()` — last entry of `TITLE_CLEANUP_PATTERNS` (`\s*\([^)]*\d{4}[^)]*\)`) is O(n²) under Java's backtracking regex engine. Triggered via `song.title` (sourced from the file's own ID3 tag via MediaStore) when the "Automatic Lyrics Download" feature fetches lyrics. Verified end-to-end with a REAL playable MP3 (`ffmpeg` + `mutagen`, real ID3v2 TIT2 frame = 130,001 chars, unbalanced `(`), independently re-parsed, fed through the real regex pipeline: 45.7s hang for one song. Evidence MP3 at `findings/dia3/boomingmusic-lyrics-title-redos/evidence/malicious_song.mp3`.
- **report_id 3532 (SUBMITTED)**: `ErrorActivity` exported with no permission, trusts `CustomActivityOnCrash` Intent extras (`EXTRA_CONFIG`/`EXTRA_STACK_TRACE`/etc — verified against the library's real 2.4.0 source) with zero caller verification. Explicit-intent targeting bypasses the intent-filter action check entirely (standard Android behavior). Any unprivileged app can make BoomingMusic display/save/offer-to-share attacker-chosen text as if it were a legitimate crash report (UI/content spoofing, CWE-926). No live device to test — static analysis of real app + real dependency source only, disclosed as such in the report.

Discarded per user judgment (real but too weak to be worth a report): `CoverProvider.getType()` throws uncaught `IllegalStateException` for any non-song URI (hardcoded `check(... == 1)`), a genuine cross-app crash-DoS via exported ContentProvider (any app, zero permissions) — user called it "more a bug than a vulnerability" given impact is just a transient crash-and-restart; agreed the trust-boundary framing was right but severity too low to submit.

Ruled out (investigated, not reportable):
- `CoverProvider` (exported ContentProvider, `com.mardous.booming.cover` authority) — looked like path traversal via `album_artist/*` URI (only path allowing non-numeric `id`), but empirically verified NOT exploitable: the code builds the cache filename as `"${matchCode}_${id}.jpg"`, and since there's no separator between the matchCode prefix and the id, the first path component of any `../` traversal always gets fused into a literal non-existent directory name (e.g. `"4_.."`), which breaks real OS path resolution (confirmed via 4 separate Java `File`-resolution tests replicating the exact Kotlin code) even though `getCanonicalPath()` naively suggests it should work. A pure code-review-only pass would have wrongly flagged this as a real vuln — worth remembering as a caution.
- `PlaybackService.onConnect()` (exported MediaLibraryService) accepts any connecting controller with no package/signature verification, granting full playback + library-browse commands. Judged NOT reportable: this is standard, expected Media3/Android MediaBrowserService behavior (virtually all music apps work this way; the framework is designed for external controllers like Android Auto/Assistant to bind freely), not a BoomingMusic-specific flaw.

Environment note: no Android SDK/emulator/adb/kotlinc available in this sandbox — Kotlin-logic verification done by replicating exact code snippets in plain Java (same JVM regex/File APIs Kotlin uses on Android), not full app compilation. Good enough for regex/path-logic bugs; would need a real device/emulator for anything requiring actual app UI or Binder/IPC behavior.

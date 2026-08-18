---
name: patchstack-wordpress-audit
description: WordPress plugin/theme vulnerability hunting for the Patchstack Alliance bug bounty program — scope rules (contributor role excluded since June 2026), the two separate payout tracks (monthly leaderboard top-5 $500-$2000 for standard reports vs. independent zero-day bounties up to $33,000 by install-count/auth-level), no researcher certificates, CNA-guaranteed CVE process, the 8 recurring vuln patterns behind most paid WP plugin CVEs (missing nonce/capability checks, unauthenticated AJAX handlers, $wpdb SQLi, missing esc_*() output escaping, REST API permission_callback gaps, PHP object injection via unserialize(), arbitrary options/user-meta update, IDOR via post/user IDs), where to source targets (wordpress.org SVN + changelog diffing, 1000+ install / updated-within-3-years eligibility bar), and submission mechanics. Use when hunting WordPress plugins/themes specifically, or when told to focus on Patchstack.
---

# PATCHSTACK ALLIANCE — WordPress Plugin/Theme Bug Bounty

> Companion to `web2-vuln-classes` (generic web bug classes) and `triage-validation` (the
> 7-Question Gate still applies here — nothing below replaces it). This skill is the
> WordPress-plugin-specific layer: what to look for, where PHP plugin authors reliably get it
> wrong, and how Patchstack's own program mechanics differ from H1/Bugcrowd/YWH.

---

## 1. Program Shape (different from every other platform this project hunts on)

- **Scope is the entire WordPress plugin/theme ecosystem**, not one company's assets — both
  free (wordpress.org repo) and premium plugins/themes are eligible. For premium components,
  the report must include the original, unmodified archive file for the triager to validate
  against — don't submit against a cracked/modified copy.
- **Payout model is two separate tracks — don't conflate them:**
  1. **Standard reports** pay ONLY via the monthly leaderboard top 5 (see §1.1) — a valid
     report earns XP/points, but XP alone pays nothing if you don't place top 5 that month.
  2. **Zeroday reports** (full site compromise, working exploit, no unusual prerequisites) pay
     **directly, independent of the leaderboard**, scaled by the plugin's active install count
     and whether exploitation needs authentication (see §1.2 table) — verified against the
     current guidelines 2026-08-18, cross-checked twice since the numbers materially change the
     value proposition (a 15M+-install or WP-Core unauthenticated 0day pays **$33,000**, not a
     minor side-bounty).
  3. A level system (1→10) also exists layered on top, unlocking cumulative rewards — total
     unlock value and exact mechanics weren't independently re-verified this pass; treat the
     ~$5,737 figure from an earlier pass as unconfirmed until re-checked.
  4. **No certificates are issued to researchers.** ("SOC 2"/"ISO 27001 certified" badges on
     Patchstack's own site refer to Patchstack's own compliance certifications, not anything
     given to researchers — don't expect a researcher certificate from this program.)

### 1.1 Monthly Leaderboard (standard reports)
| Rank | Payout |
|---|---|
| 1st | $2,000 |
| 2nd | $1,400 |
| 3rd | $800 |
| 4th | $600 |
| 5th | $500 |

Resets on the calendar month, UTC (00:00 on the 1st → 23:59 on the last day). Results are
published only once the full month's backlog of reports is validated (can take up to another
month if there's a backlog). Guaranteed minimum monthly pool: **$5,300**. Ranking below top 5
= no direct cash for that report, regardless of how many valid reports you filed.

### 1.2 Zeroday Bounty Scale (separate track, pays regardless of leaderboard rank)
| Active installs | Unauthenticated | Subscriber/Customer |
|---|---|---|
| 1,000+ | $250 | $125 |
| 5,000+ | $400 | $200 |
| 10,000+ | $600 | $300 |
| 50,000+ | $1,400 | $700 |
| 100,000+ | $2,600 | $1,300 |
| 500,000+ | $4,900 | $2,450 |
| 1,000,000+ | $7,200 | $3,600 |
| 5,000,000+ | $14,400 | $7,200 |
| 15,000,000+ or WordPress Core | $33,000 | $16,500 |

### 1.3 CVE Process
Patchstack is itself a **CVE Numbering Authority (CNA)**. Every valid, in-scope, non-duplicate
report gets a CVE ID published in the researcher's name — Patchstack initiates it, researchers
don't request it. **No fixed SLA/timeframe is published** for how long assignment takes
(delays happen to avoid ID conflicts with other CNAs). On duplicates, the CVE goes to whoever's
report was valid first; later reports of the same bug are rejected — reinforces why the dedup
check in §5 step 4 matters here more than on most platforms.
- **Scope narrowed 2026-06-01: the `contributor` role is no longer in scope.** A finding that
  requires the attacker to already hold `contributor` capability doesn't qualify anymore — the
  attacker must start from `guest` (unauthenticated), `subscriber`, `customer`, or a custom role,
  and custom roles only count if a site admin would grant them by default (not a role the
  attacker self-assigns). **Check this first, before diving into any finding** — this
  invalidates a large class of "logged-in-as-a-low-priv-role" bugs that would have counted
  before June 2026.
- **CVE gets published in your name** once verified — this is a real, durable credential, not
  just a payout.

## 2. Where to Source Targets

**No curated target list exists — there is no dashboard/portal listing in-scope plugins.**
Scope is the entire WordPress.org ecosystem (plus premium plugins/themes, GitHub-hosted, and
vendor-site-hosted components); researchers pick targets themselves. Real eligibility
thresholds (confirmed against the current guidelines, verify they haven't moved before relying
on them):
- **1,000+ active installs** (exceptions exist for premium products and the mVDP program)
- **Updated within the last 3 years** — abandoned/stale plugins don't qualify
- Publicly available (wordpress.org, vendor site, GitHub, etc.)

Two productive sourcing strategies, in order of hit rate:

1. **wordpress.org SVN + changelog diffing** (same "recently-patched-code review" pattern used
   elsewhere this project — highest signal-to-noise). Browse
   `wordpress.org/plugins/browse/updated/` for recently-touched plugins meeting the 1,000+
   install bar, then pull the SVN history (`plugins.svn.wordpress.org/<slug>/`), diff the last
   2-3 tagged versions, and read the changelog for words like "security fix", "sanitization",
   "escaping", "permission" — then check whether the SAME pattern exists elsewhere in the
   codebase, unfixed (the sibling-function trap — a fix in one function rarely gets applied
   everywhere the same bug exists).
2. **`wordpress.org/plugins/browse/popular/`** for well-installed plugins, filtered toward ones
   with less audit visibility than the top 20-30 everyone already hunts.

Avoid: plugins under the 1,000-install bar or not updated in 3+ years (both make the report
ineligible regardless of the bug's quality), and plugins already flagged with an open, unfixed
CVE from another researcher (dedup risk — check the plugin's own changelog and
wpscan.com/wordpress/plugins/<slug> first).

## 3. The 8 Recurring Vuln Patterns (read for these first, in order of hit rate)

### 3.1 Unauthenticated AJAX handler (no nonce, no capability check) 🔥 highest hit rate
```php
// VULNERABLE — registered for both logged-in AND anonymous users, no checks at all
add_action('wp_ajax_change_password', 'plugin_change_password');
add_action('wp_ajax_nopriv_change_password', 'plugin_change_password');  // <- nopriv = unauthenticated

function plugin_change_password() {
    $user_id = intval($_POST['user_id']);
    $new_pass = sanitize_text_field($_POST['password']);
    wp_set_password($new_pass, $user_id);   // no check_ajax_referer(), no current_user_can()
    wp_send_json_success();
}
```
Real 2026 example: TrueBooker's arbitrary-password-change bug (unauthenticated attacker resets
ANY user's password, including admin) — the exact shape above. Also ShopLentor (email-relay
abuse via the same missing-check pattern) and SignUp&SignIn's `pravel_change_password()`.
**Grep for**: `wp_ajax_nopriv_` action registrations, then check the handler for BOTH
`check_ajax_referer()`/`wp_verify_nonce()` AND `current_user_can()` — missing either is a bug,
missing both (as above) is usually a Critical.

### 3.2 REST API route with a missing or trivial `permission_callback`
```php
// VULNERABLE — permission_callback returns true unconditionally, or is omitted (older WP
// versions silently allowed this; current WP throws a deprecation notice but still runs it)
register_rest_route('myplugin/v1', '/users/(?P<id>\d+)', [
    'methods' => 'GET',
    'callback' => 'get_user_data',
    'permission_callback' => '__return_true',   // <- anyone, including logged-out
]);
```
**Grep for**: `register_rest_route(` then check `permission_callback` — `__return_true`, a
missing key entirely, or a callback that only checks `is_user_logged_in()` (not the specific
capability needed) are all red flags.

### 3.3 `$wpdb` SQL injection (unprepared query with request input)
```php
// VULNERABLE
$wpdb->get_results("SELECT * FROM {$wpdb->prefix}orders WHERE id = " . $_GET['id']);

// SECURE
$wpdb->get_results($wpdb->prepare("SELECT * FROM {$wpdb->prefix}orders WHERE id = %d", $_GET['id']));
```
**Grep for**: `$wpdb->get_results(`, `$wpdb->query(`, `$wpdb->get_var(` — anywhere a `$_GET`/
`$_POST`/`$_REQUEST` value is concatenated (`.` or `{$var}`) directly into the SQL string
instead of passed through `$wpdb->prepare()` with a placeholder.

### 3.4 Missing output escaping (stored/reflected XSS)
```php
// VULNERABLE
echo '<div>' . $_GET['name'] . '</div>';
echo $post_meta_value;   // if $post_meta_value came from user input without esc_html() on output

// SECURE
echo '<div>' . esc_html($_GET['name']) . '</div>';
```
**Grep for**: `echo $_GET`, `echo $_POST`, `echo $_REQUEST`, and any `echo`/`print` of a
variable traced back to `get_post_meta()`/`get_user_meta()` without `esc_html()`/`esc_attr()`/
`esc_url()`/`wp_kses()` at the output point. WordPress's convention is escape-on-output, not
escape-on-input — a value can be "sanitized" on the way in and still XSS on the way out if the
specific output context (HTML body vs. attribute vs. URL) doesn't match the escaping function.

### 3.5 Arbitrary options/user-meta update (→ privilege escalation)
```php
// VULNERABLE — attacker-controlled option name/value, no allowlist, no capability check
function plugin_save_settings() {
    $key = sanitize_text_field($_POST['option_name']);
    $value = sanitize_text_field($_POST['option_value']);
    update_option($key, $value);   // could set 'default_role' or any WP core option
}
```
Chains directly to admin takeover if `option_name` can be `default_role` (set to
`administrator`) or `users_can_register`. Same pattern with `update_user_meta()` targeting
`wp_capabilities` is a direct role-escalation primitive.

### 3.6 PHP Object Injection via `unserialize()`
```php
// VULNERABLE
$data = unserialize($_COOKIE['plugin_data']);   // or base64_decode() first, same issue

// SECURE
$data = json_decode($_COOKIE['plugin_data'], true);
```
Needs a POP (property-oriented programming) gadget chain somewhere in WP core or another
installed plugin/theme to be exploitable to RCE — but even without a known gadget chain,
report the unsafe `unserialize()` call itself; Patchstack triages these seriously because gadget
chains get discovered later across the ecosystem.

### 3.7 IDOR via post/attachment/order ID with no ownership check
```php
// VULNERABLE
function get_order_details() {
    $order_id = intval($_GET['order_id']);
    $order = wc_get_order($order_id);
    wp_send_json_success($order->get_data());   // never checks $order->get_customer_id() === get_current_user_id()
}
```
Very common in WooCommerce-adjacent plugins (orders, invoices, downloads) — the ID is
guessable/enumerable and the handler trusts it without an ownership check.

### 3.8 Arbitrary file upload / path traversal in a media or import handler
```php
// VULNERABLE — no extension allowlist, or check happens on MIME type which is attacker-controlled
move_uploaded_file($_FILES['import']['tmp_name'], $upload_dir . '/' . $_FILES['import']['name']);
```
**Grep for**: `move_uploaded_file(`, `copy(`, `file_put_contents(` fed by `$_FILES[...]['name']`
or `['tmp_name']` without an extension allowlist AND a randomized destination filename.

## 4. Quick Recon Commands

```bash
# Pull a plugin's SVN history to diff versions
svn co https://plugins.svn.wordpress.org/<slug>/tags/<version>/ /tmp/plugin-audit
svn log https://plugins.svn.wordpress.org/<slug>/trunk/ | head -50

# Grep sweep for the 8 patterns above, run from the plugin's extracted source root
grep -rn "wp_ajax_nopriv_" --include="*.php" .
grep -rn "permission_callback.*__return_true\|register_rest_route" --include="*.php" .
grep -rn '\$wpdb->\(get_results\|query\|get_var\)' --include="*.php" . | grep -v "prepare("
grep -rn "unserialize(" --include="*.php" .
grep -rn "move_uploaded_file\|file_put_contents" --include="*.php" .
```

## 5. Submission Mechanics (differs from H1/Bugcrowd/YWH conventions used elsewhere)

1. Submit via the researcher portal (`vdp.patchstack.com/researchers/login`, email magic-link
   login) or the public form at `patchstack.com/bug-bounty/`.
2. **You must select an OWASP Top 10 category from a dropdown** — same requirement we already
   apply as standing practice (see `feedback_verification_bar_five_times` / CLAUDE.md Critical
   Rule 3) — pick the closest accurate match if there's no exact fit, same discipline as the
   Bugcrowd VRT-selection process in `bugcrowd-reporting`.
3. Include plugin slug + exact affected version, full PoC (request/response or PHP snippet
   showing the unsafe sink), and the fix location (file:line).
4. **Before submitting, verify the contributor-role scope exclusion doesn't apply** (§1) and run
   the standard dedup check (`triage-validation` Gate 2 + this project's mandatory GitHub-
   issues/commits search pattern from `agents/validator.md`) — WordPress plugin CVEs are
   heavily hunted, dedup risk is real.

## 5.1 Vulnerability Disclosure Timeline (Patchstack VDP-specific)

Patchstack requires coordinated disclosure through the plugin author before any public
write-up — don't publish a blog post/tweet about a finding here until Patchstack confirms the
fix shipped, same discipline as every other program in this project (`feedback_report_language_
by_program`-adjacent: check the platform's specific disclosure timeline before publishing).

## 6. Pairing with Other Skills

| For this question | Use this skill |
|---|---|
| "Is this WP-specific bug reportable at all?" | `triage-validation` (7-Question Gate, always) |
| "What's the generic web vuln class behind this?" | `web2-vuln-classes` |
| "How do I write the report body?" | `report-writing`, adapted to Patchstack's OWASP-category-dropdown format above |
| "Where do I find WP-adjacent recon tooling?" | `web2-recon` |

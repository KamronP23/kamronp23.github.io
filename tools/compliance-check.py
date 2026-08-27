#!/usr/bin/env python3
"""
A1 Compliance Gate — Kindred Mental Health
==========================================

Blocks a change from reaching the live site if it breaks one of the rules in
CLAUDE.md. Every rule here comes from statute or professional-ethics code, not
preference. Nothing in this file requires an API key, a token, or a paid
service: it is plain pattern matching over the repo's own files.

Run locally:   python3 tools/compliance-check.py
Exit codes:    0 = clean, 1 = one or more FAILures

FAIL blocks the merge. WARN prints and does not block.

When a rule genuinely needs an exception, add it to the allowlist beside that
rule with a comment saying why. Do not delete a rule to make the build pass.
"""

import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = sorted(ROOT.glob("*.html"))

# In GitHub Actions, emit workflow commands so each failure appears as an
# inline annotation on the offending line in the pull request diff.
CI = bool(os.environ.get("GITHUB_ACTIONS"))

failures: list[tuple[str, str, str | None, int | None]] = []
warnings: list[tuple[str, str, str | None, int | None]] = []


def _loc(msg: str) -> tuple[str | None, int | None]:
    """Pull 'file.html:123' or 'file.html' out of a message for annotations."""
    m = re.match(r"([\w.-]+\.(?:html|txt|xml))(?::(\d+))?", msg)
    if not m:
        return None, None
    return m.group(1), int(m.group(2)) if m.group(2) else None


def fail(rule: str, msg: str) -> None:
    f, n = _loc(msg)
    failures.append((rule, msg, f, n))


def warn(rule: str, msg: str) -> None:
    f, n = _loc(msg)
    warnings.append((rule, msg, f, n))


def text(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def lines(p: pathlib.Path):
    return enumerate(text(p).split("\n"), start=1)


# Strip HTML comments before prose checks so a commented-out note can't trip a
# rule, and strip <script>/<style> so vendor JS can't either.
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_SCRIPT = re.compile(r"<script\b.*?</script>", re.S | re.I)
_STYLE = re.compile(r"<style\b.*?</style>", re.S | re.I)


def prose(p: pathlib.Path) -> str:
    s = text(p)
    s = _COMMENT.sub(" ", s)
    s = _SCRIPT.sub(" ", s)
    s = _STYLE.sub(" ", s)
    return s


def scan(p: pathlib.Path, rx: re.Pattern, before: int = 90, after: int = 60):
    """Yield (line_no, match_text, context) for rx over a page's prose.

    The context window is taken from the raw prose and then whitespace-collapsed,
    so a phrase broken across an HTML line wrap still reads as one phrase. Do NOT
    replace this with a per-line scan: source HTML wraps prose at ~80 columns, so
    "a receipt, not a\n guarantee" would lose its negation and false-positive on
    R3. This bug shipped once and cost a real debugging cycle.
    """
    body = prose(p)
    for m in rx.finditer(body):
        line_no = body.count("\n", 0, m.start()) + 1
        window = body[max(0, m.start() - before): m.end() + after]
        yield line_no, m.group(0), " ".join(window.split())


# ---------------------------------------------------------------------------
# Rule 1 — License block on every page
# CA 16 CCR §1811 (amended eff. 1 Apr 2026). Legal name as filed with the
# Board, the LMFT designation, and the license number.
# ---------------------------------------------------------------------------
LICENSE_MARKERS = ["Kamron Poosti", "LMFT", "124629"]

for p in PAGES:
    body = text(p)
    missing = [m for m in LICENSE_MARKERS if m not in body]
    if missing:
        fail("R1 license block", f"{p.name} is missing {', '.join(missing)}")


# ---------------------------------------------------------------------------
# Rule 2 — Protected terms
# BPC §2903 reserves "psychology" / "psychological" / "psychologist" to
# licensed psychologists. "Psychotherapy" and "psychotherapist" are fine and
# do not contain the stem, so they never match here.
#
# ALLOWED, and deliberately so:
#   - "Psychology Today", the directory. Naming it is not a title claim.
#   - The actual conferred degree. Kamron holds an MA in Clinical Psychology,
#     Marriage and Family Therapy. Stating a real degree is permitted and must
#     never be stripped by this gate.
# ---------------------------------------------------------------------------
PROTECTED = re.compile(r"psycholog(?:y|ical|ically|ist|ists)", re.I)

PROTECTED_ALLOWED = [
    re.compile(r"psychology\s*today", re.I),          # the directory
    re.compile(r"psychologytoday", re.I),             # URLs, badge script
    re.compile(r"(?:MA|M\.A\.)\s+in\s+Clinical\s+Psychology", re.I),  # the degree
    re.compile(r"Clinical\s+Psychology,\s*Marriage\s+and\s+Family", re.I),
]

for p in PAGES:
    for n, hit, window in scan(p, PROTECTED, before=45, after=45):
        if any(a.search(window) for a in PROTECTED_ALLOWED):
            continue
        fail(
            "R2 protected term",
            f'{p.name}:{n} uses "{hit}" — reserved under BPC §2903. '
            f'Use "psychotherapy"/"psychotherapist". Context: ...{window}...',
        )


# ---------------------------------------------------------------------------
# Rule 3 — No superiority or outcome claims
# BPC §651. "Specializing in X" is explicitly permitted and is not flagged.
# A term is only flagged when it is NOT negated nearby, so honest lines like
# "a superbill is a receipt, not a guarantee" pass.
# ---------------------------------------------------------------------------
CLAIMS = re.compile(
    r"\b(?:best|#1|number\s+one|top[-\s]rated|world[-\s]class|leading|premier|"
    r"proven|guarantee[sd]?|guaranteed|cure[sd]?|curing|"
    r"success\s+rate|results?\s+guaranteed|most\s+effective|highly\s+effective)\b",
    re.I,
)

NEGATED = re.compile(
    r"\b(?:not|isn't|is not|no|never|cannot|can't|rather than|instead of|"
    r"doesn't|does not|won't|will not)\b",
    re.I,
)

for p in PAGES:
    for n, hit, window in scan(p, CLAIMS, before=70, after=40):
        if NEGATED.search(window):
            # e.g. "a superbill is a receipt, not a guarantee" — honest, keep
            continue
        fail(
            "R3 superiority/outcome claim",
            f'{p.name}:{n} contains "{hit}" — BPC §651 bars superiority '
            f"and assured-result claims. Context: ...{window}...",
        )


# ---------------------------------------------------------------------------
# Rule 4 — No testimonials, reviews, or client quotes
# AAMFT 9.2 bars soliciting testimonials from current clients; replying to
# reviews is a separate confidentiality problem. Structural markers only —
# this cannot read intent, so it looks for the shapes a reviews section takes.
# ---------------------------------------------------------------------------
TESTIMONIAL_MARKERS = [
    (re.compile(r"<blockquote", re.I), "a <blockquote> element"),
    (re.compile(r"\btestimonial", re.I), 'the word "testimonial"'),
    (re.compile(r'class="[^"]*\b(?:review|rating|stars?)\b', re.I), "review/rating markup"),
    (re.compile(r'itemprop="(?:reviewBody|ratingValue|aggregateRating)"', re.I), "review schema markup"),
    (re.compile(r'"@type"\s*:\s*"(?:Review|AggregateRating)"', re.I), "Review/AggregateRating JSON-LD"),
]

for p in PAGES:
    body = text(p)
    for rx, label in TESTIMONIAL_MARKERS:
        if rx.search(body):
            fail(
                "R4 testimonial",
                f"{p.name} contains {label}. AAMFT 9.2 — no testimonials, reviews, "
                f"client quotes, or star ratings anywhere on the site.",
            )


# ---------------------------------------------------------------------------
# Rule 5 — No ad-network tags on health or booking pages
# WA My Health My Data Act, RCW 19.373. A pageview on a condition page is
# consumer health data, HIPAA does not exempt it, and the Act carries a
# private right of action.
# ---------------------------------------------------------------------------
HEALTH_PAGES = {
    "mens-mental-health.html",
    "financial-anxiety.html",
    "job-loss-and-career-therapy.html",
    "online-therapy-washington.html",
    "contact.html",
}

AD_TAGS = [
    (re.compile(r"connect\.facebook\.net|fbevents\.js|\bfbq\s*\(", re.I), "Meta Pixel"),
    (re.compile(r"snap\.licdn\.com|_linkedin_partner_id", re.I), "LinkedIn Insight Tag"),
    (re.compile(r"googleadservices|googlesyndication|gtag\([^)]*['\"]AW-", re.I), "Google Ads remarketing"),
    (re.compile(r"static\.ads-twitter\.com|twq\s*\(", re.I), "X/Twitter pixel"),
    (re.compile(r"analytics\.tiktok\.com|ttq\.", re.I), "TikTok pixel"),
    (re.compile(r"sc-static\.net/scevent", re.I), "Snap pixel"),
    (re.compile(r"bat\.bing\.com", re.I), "Microsoft UET"),
]

for p in PAGES:
    body = text(p)
    for rx, label in AD_TAGS:
        if rx.search(body):
            if p.name in HEALTH_PAGES:
                fail(
                    "R5 ad tag on health page",
                    f"{p.name} loads {label}. RCW 19.373 treats a pageview here as "
                    f"consumer health data. This one has a private right of action.",
                )
            else:
                warn(
                    "R5 ad tag",
                    f"{p.name} loads {label}. Allowed here, but confirm it is not "
                    f"also firing on a condition or booking page.",
                )


# ---------------------------------------------------------------------------
# Rule 6 — good-faith-estimate.html must stay indexable
# No Surprises Act, 45 CFR §149.610(b)(1)(i): the notice must be "easily
# searchable from a public search engine." Hiding it is the single change that
# would make the site non-compliant.
# ---------------------------------------------------------------------------
gfe = ROOT / "good-faith-estimate.html"

if not gfe.exists():
    fail("R6 GFE", "good-faith-estimate.html is missing. Required by 45 CFR §149.610.")
else:
    body = text(gfe)
    if re.search(r"noindex", body, re.I):
        fail("R6 GFE", "good-faith-estimate.html carries a noindex directive.")
    if re.search(r"display\s*:\s*none", body, re.I):
        fail("R6 GFE", "good-faith-estimate.html hides content with display:none.")
    if not re.search(r'rel=["\']canonical', body, re.I):
        warn("R6 GFE", "good-faith-estimate.html has no canonical tag.")

    robots = ROOT / "robots.txt"
    if robots.exists():
        for n, line in enumerate(text(robots).split("\n"), start=1):
            if re.match(r"\s*Disallow:", line, re.I) and "good-faith" in line.lower():
                fail("R6 GFE", f"robots.txt:{n} disallows the Good Faith Estimate page.")

    sitemap = ROOT / "sitemap.xml"
    if sitemap.exists() and "good-faith-estimate.html" not in text(sitemap):
        fail("R6 GFE", "good-faith-estimate.html is not listed in sitemap.xml.")


# ---------------------------------------------------------------------------
# Rule 7 — Florida footnote on any page advertising the free consultation
# FS §456.062 requires that exact all-caps wording wherever a free service is
# advertised. A new page that offers the consult needs the footnote too.
# ---------------------------------------------------------------------------
FREE_CONSULT = re.compile(r"free\s+(?:\d+[-\s]?minute\s+)?consultation", re.I)
FL_NOTE = re.compile(r"THE\s+PATIENT\s+AND\s+ANY\s+OTHER\s+PERSON")

for p in PAGES:
    body = prose(p)
    if FREE_CONSULT.search(body) and not FL_NOTE.search(text(p)):
        fail(
            "R7 Florida footnote",
            f"{p.name} advertises a free consultation but has no FS §456.062 "
            f"footnote. Copy the <sup>1</sup> block from financial-anxiety.html.",
        )


# ---------------------------------------------------------------------------
# Rule 8 — The four required pages exist and are linked from every footer
# Under MHMDA every page that collects personal information counts as a
# "homepage," so the links must be site-wide, not on one page.
# ---------------------------------------------------------------------------
REQUIRED_PAGES = {
    "good-faith-estimate.html": "No Surprises Act, 45 CFR §149.610(b)(1)(i)",
    "consumer-health-privacy.html": "WA My Health My Data Act, RCW 19.373.020",
    "notice-of-privacy-practices.html": "HIPAA, 45 CFR §164.520(c)(3)(i)",
    "privacy.html": "CalOPPA, Cal. B&P §22575",
}

for name, basis in REQUIRED_PAGES.items():
    if not (ROOT / name).exists():
        fail("R8 required page", f"{name} is missing. Required by {basis}.")

for p in PAGES:
    body = text(p)
    for name in REQUIRED_PAGES:
        if name == p.name:
            continue  # a page need not link to itself
        if f'href="{name}"' not in body and f"href='{name}'" not in body:
            fail("R8 footer link", f"{p.name} does not link to {name}.")


# ---------------------------------------------------------------------------
# Rule 9 — Florida is a telehealth REGISTRATION, not a license
# FS §456.47. Florida DOH issues an approval letter and a registration
# number; no license is issued. Saying "licensed in Florida" is a false
# credential claim.
# ---------------------------------------------------------------------------
FL_LICENSE_CLAIM = re.compile(
    r"licen[sc]ed\s+(?:therapist\s+)?in\s+[^.<]{0,60}\bFlorida\b"
    r"|\bFlorida\b[^.<]{0,30}\blicen[sc]e(?:d|\s+number)?\b",
    re.I,
)

for p in PAGES:
    for n, hit, window in scan(p, FL_LICENSE_CLAIM, before=20, after=40):
        fail(
            "R9 Florida credential",
            f"{p.name}:{n} appears to claim Florida licensure. FS §456.47 is an "
            f"out-of-state telehealth REGISTRATION (TPMF1707); no license is "
            f"issued. Context: ...{window[:150]}...",
        )


# ---------------------------------------------------------------------------
# Rule 10 — FS §456.47(2)(c) hyperlink to the Florida DOH telehealth registry
# "The website of a telehealth provider registered under paragraph (b) must
# prominently display a hyperlink to the department's website." The statute
# attaches to the website, so one page carrying it satisfies it.
# ---------------------------------------------------------------------------
if not any("flhealthsource.gov/telehealth" in text(p) for p in PAGES):
    fail(
        "R10 FL registry link",
        "No page links to flhealthsource.gov/telehealth. FS §456.47(2)(c) requires "
        "the website to display a hyperlink to the department's site.",
    )


# ---------------------------------------------------------------------------
# Rule 11 — Unresolved placeholders must never publish
# They render as visible text on a live medical practice site.
# ---------------------------------------------------------------------------
for p in list(PAGES) + [q for q in (ROOT / "robots.txt", ROOT / "sitemap.xml") if q.exists()]:
    for n, line in lines(p):
        if "[[CONFIRM" in line or "TODO:" in line and "<!--" not in line:
            fail("R11 placeholder", f"{p.name}:{n} contains an unresolved placeholder.")


# ---------------------------------------------------------------------------
# Rule 12 — Advertised price must agree with the JSON-LD priceRange
# Not a statute. It is here because the rate lives in three places a human
# reading the rendered page cannot see: two JavaScript string literals inside
# the state selector, and the JSON-LD priceRange. A mismatch between the
# structured data and the visible page is what search engines and assistants
# quote back at people.
# ---------------------------------------------------------------------------
visible_prices = set()
for p in PAGES:
    for m in re.finditer(r"\$(\d{2,4})\s*(?:per|for|each|a\b)", prose(p), re.I):
        visible_prices.add(m.group(1))

declared = set()
for p in PAGES:
    for m in re.finditer(r'"priceRange"\s*:\s*"\$?(\d{2,4})', text(p)):
        declared.add(m.group(1))

if declared and visible_prices and not (declared & visible_prices):
    fail(
        "R12 price mismatch",
        f"JSON-LD priceRange declares {sorted(declared)} but the visible copy says "
        f"{sorted(visible_prices)}. Structured data is what assistants quote.",
    )


# ---------------------------------------------------------------------------
# Rule 13 — Every page needs a canonical that points at ITSELF
# Not a statute, but this one is a silent site-killer. New pages here are built
# by copying a sibling page, and a copied canonical still points at the page it
# was copied from — which tells search engines "this page is a duplicate, index
# the other one instead." The page then never indexes, looks completely fine in
# a browser, and gives no error anywhere. A missing canonical is a warning; a
# WRONG one is a failure.
# ---------------------------------------------------------------------------
CANON = re.compile(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']', re.I | re.S)
SITE = "https://kindredmentalhealth.com"

for p in PAGES:
    m = CANON.search(text(p))
    if not m:
        warn("R13 canonical", f"{p.name} has no canonical tag.")
        continue

    href = m.group(1).strip()
    expected = f"{SITE}/" if p.name == "index.html" else f"{SITE}/{p.name}"

    if href.rstrip("/") != expected.rstrip("/"):
        fail(
            "R13 canonical",
            f"{p.name} declares canonical {href} but should be {expected}. "
            f"A canonical pointing at another page makes this one unindexable — "
            f"almost always a leftover from copying a sibling page.",
        )


# ---------------------------------------------------------------------------
# Rule 14 — JSON-LD must parse
# A malformed block is silently ignored by every consumer of it.
# ---------------------------------------------------------------------------
LD = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I
)

for p in PAGES:
    for i, block in enumerate(LD.findall(text(p)), start=1):
        try:
            json.loads(block)
        except json.JSONDecodeError as e:
            fail("R14 JSON-LD", f"{p.name} JSON-LD block {i} does not parse: {e}")


# ---------------------------------------------------------------------------
# Rule 15 — Meta description length
# Not a statute. Search engines truncate past roughly 160 characters, which
# cuts the pitch off mid-sentence with an ellipsis in the results page. Bing
# Webmaster Tools flags it as an Error. Six pages drifted over before anyone
# noticed, because nothing renders a meta description on the page itself.
# ---------------------------------------------------------------------------
DESC = re.compile(r'<meta\s+name="description"\s+content="(.*?)"', re.S | re.I)

for p in PAGES:
    m = DESC.search(text(p))
    if not m:
        fail("R15 meta description", f"{p.name} has no meta description.")
        continue
    d = " ".join(m.group(1).split())
    if len(d) > 160:
        fail("R15 meta description",
             f"{p.name} meta description is {len(d)} chars; over 160 gets truncated "
             f"in search results. Trim it.")
    elif len(d) < 50:
        warn("R15 meta description",
             f"{p.name} meta description is only {len(d)} chars — likely leaving "
             f"useful snippet space unused.")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def annotate(level: str, rule: str, msg: str, f: str | None, n: int | None) -> None:
    if not CI:
        return
    loc = ""
    if f:
        loc = f" file={f}"
        if n:
            loc += f",line={n}"
    # Newlines break the workflow-command format.
    flat = " ".join(msg.split())
    print(f"::{level}{loc},title=A1 {rule}::{flat}")


print(f"A1 Compliance Gate — checked {len(PAGES)} pages\n")

if warnings:
    print(f"WARNINGS ({len(warnings)}) — not blocking\n")
    for rule, msg, f, n in warnings:
        print(f"  ! {rule}: {msg}")
        annotate("warning", rule, msg, f, n)
    print()

if failures:
    print(f"FAILURES ({len(failures)}) — blocking\n")
    for rule, msg, f, n in failures:
        print(f"  X {rule}: {msg}")
        annotate("error", rule, msg, f, n)
    print(
        "\nThese rules come from statute and professional-ethics code, not preference.\n"
        "Fix the content. Do not delete the rule to make the build pass.\n"
        "If a rule is genuinely wrong, add a documented exception beside it and say why."
    )
    sys.exit(1)

print("PASS — no compliance failures.")
sys.exit(0)

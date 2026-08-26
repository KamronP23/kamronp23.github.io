# Kindred Mental Health — kindredmentalhealth.com

Static site for a solo telehealth psychotherapy practice. **Kamron Poosti, LMFT** —
licensed in California (#124629) and Washington (MFT.LF.70083737), and registered
to provide telehealth in Florida (registration TPMF1707 — not a license; see rule 9).
Adults only. Anxiety, depression, burnout, relationships, dating, ADHD, autism,
life transitions, financial anxiety, career transitions and job loss (incl.
tech-worker layoffs), men's mental health.

## Stack

Plain HTML + CSS. No build step, no framework, no package.json. Bootstrap 5.3.3
and Source Serif 4 load from CDN. Deployed by GitHub Pages from `main` — pushing
to `main` publishes immediately. Custom domain via `CNAME`.

Edit the `.html` files directly. Every page repeats its own nav and footer; when
you change one, change all of them.

## Business goal

**Washington private-pay is the priority.** California and Florida insurance work
is secondary and deliberately low-effort. Content and SEO should favor Washington.

The SEO strategy is to ignore `[specialty] therapist [city]` — Psychology Today
and TherapyDen own those and a solo site will not win them. Target instead:
modality queries (`online therapy Washington`), payment-qualified queries
(`private pay therapist Seattle`, `out of network therapist Washington`), and
narrow identity queries (`therapy for men Washington`, `financial anxiety
therapist`, `therapist for tech workers Seattle`). Live SERP checks in Aug 2026
showed those are solo-site territory.

## Hard rules — do not break these without asking Kamron first

This is a licensed practice. These come from statute, not preference.

1. **License block on every page.** Legal name as filed with the CA Board +
   "LMFT" + license number, in the footer. CA 16 CCR §1811, amended eff. 1 Apr 2026.
2. **Never use "psychology" or "psychologist."** Reserved for licensed
   psychologists in California. "Psychotherapy" and "psychotherapist" are fine.
   This is the single easiest rule to break by accident.
3. **No superiority or outcome claims.** No "best", "#1", "proven", "guaranteed",
   "cure", success rates, or anything implying assured results. BPC §651.
   "Specializing in X" is explicitly allowed.
4. **No testimonials, reviews, or client quotes** anywhere on the site. AAMFT 9.2
   bars soliciting them; replying to reviews is a confidentiality problem
   separately. Don't add a reviews section, don't add star ratings.
5. **No ad-network tags on health or booking pages.** No Meta Pixel, LinkedIn
   Insight Tag, or Google Ads remarketing on `mens-mental-health.html`,
   `financial-anxiety.html`, or `contact.html`. Washington's My Health My Data Act
   (RCW 19.373) treats a pageview on a condition page as consumer health data,
   HIPAA does not exempt it, and it carries a private right of action.
6. **`good-faith-estimate.html` must stay indexable.** No `noindex`, no
   `display:none`, no robots.txt block. 45 CFR §149.610(b)(1)(i) requires the
   notice be "easily searchable from a public search engine." Hiding it is the
   one change that would make the site non-compliant.
7. **The Florida footnote stays** on any page advertising the free consultation.
   FS §456.062 requires that exact all-caps wording. If a new page advertises the
   free consult, it needs the footnote too.
8. **No AI chatbot that speaks in a clinical voice.** CA AB 489, eff. 1 Jan 2026.
   A clearly-labeled scheduling widget is fine.
9. **Florida is a telehealth registration, NOT a license.** Kamron holds an
   out-of-state telehealth provider registration under FS §456.47 (number
   TPMF1707). Florida issues an approval letter and a registration number and
   does not issue a license. Never write "licensed in Florida" or list Florida
   inside a licensure claim — this is easy to reintroduce. Correct phrasings:
   "registered to provide telehealth in Florida" and, in license blocks,
   "Florida telehealth provider registration TPMF1707". Naming Florida as a
   *service area* ("therapy for adults in California, Florida, and Washington")
   is fine — that states where he can see clients, not a license. FS §456.47(2)(c)
   also requires the site to prominently link the department's website: that is
   the "Florida telehealth registry" link (https://flhealthsource.gov/telehealth/).
   The requirement attaches to the *website*, not every page, so it now lives in
   the homepage (`index.html`) footer's `.footer-legal` block only. Don't remove
   it from there — the homepage placement is what satisfies the statute.

## Verification notes

Things a past session already checked, so a future one doesn't re-flag them:

- **Headway (headway.co) is link-only, not a tracker.** It appears on
  `contact.html`, `fees.html`, and `index.html` only as `<a href>` links — never
  a script or iframe. A link fires no request until clicked, so Headway observes
  nothing on pageview and is not a Hard Rule #5 problem. It is not on the two
  condition pages. It is still correctly listed as a vendor in `privacy.html` and
  `consumer-health-privacy.html` because it receives a referrer once clicked. The
  actual MHMDA tracking surface on the condition pages is Psychology Today's
  `verified-seal.js` and Google Tag Manager/GA4; Kamron has chosen to leave those.

## The compliance gate — run it, don't work around it

`tools/compliance-check.py` encodes the Hard Rules above as 14 mechanical checks,
each carrying its statutory citation in a comment. It needs no API key, no token
and no network: it is pattern matching over the repo's own files.

**Run it before every commit:**

```
python3 tools/compliance-check.py
```

Exit 0 = clean. Exit 1 = blocking failure. It also runs in GitHub Actions on
every pull request and every push to `main`
(`.github/workflows/compliance.yml`), where failures appear as inline
annotations on the offending line.

Rules R1–R10 are statutory and map to the Hard Rules. R11 catches unresolved
`[[CONFIRM]]` placeholders. R12 catches a JSON-LD `priceRange` that disagrees
with the visible price. R13 warns on a missing canonical. R14 catches JSON-LD
that does not parse.

**If the gate fails, fix the content.** Do not delete a rule, loosen a regex, or
add a blanket exception to make the build pass. If a rule is genuinely wrong,
add a narrow documented exception beside it explaining why, and tell Kamron.

Two exceptions already live in the script and must not be removed: "Psychology
Today" (the directory — naming it is not a title claim) and the actual conferred
degree, "MA in Clinical Psychology, Marriage and Family Therapy."

R12 exists because the session rate lives in three places that a human reading
the rendered page cannot see: two JavaScript string literals inside the state
selector (`contact.html`, `index.html`) and the JSON-LD `priceRange`. Grep the
raw files when changing anything numeric. Do not trust a visual review.

## Standing preference

**Legal minimum only.** Kamron does not want anything on the site that isn't a
legal requirement. Prudent-but-optional additions were deliberately stripped in
Aug 2026 (an accessibility page, extra privacy-policy sections). Don't re-add
that category of thing; if you think something optional is worth it, ask first.

## Required pages — do not delete

| File | Requirement |
|---|---|
| `good-faith-estimate.html` | No Surprises Act, 45 CFR §149.610(b)(1)(i) |
| `consumer-health-privacy.html` | WA My Health My Data Act, RCW 19.373.020 |
| `notice-of-privacy-practices.html` | HIPAA, 45 CFR §164.520(c)(3)(i) |
| `privacy.html` | CalOPPA, Cal. B&P §22575 |

All four are linked from `.footer-legal` in every page footer. That footer link is
also how the MHMDA homepage-link requirement is met — under the Act every page
that collects personal information counts as a "homepage," so the links must stay
site-wide.

## Current state (Aug 2026)

**12 pages, all live and committed to `main`.** The site is clean against the
compliance gate as of 26 Aug 2026.

Recent, in order:

- `online-therapy-washington.html` shipped (`23d4f66`). The uncontested primary
  query. 446 body words, six question-phrased `<h2>`s, canonical, FL footnote.
- **Session rate is $250 sitewide**, all three states, same commit. All
  sliding-scale language preserved verbatim. Psychology Today updated to match.
- `.DS_Store` untracked and gitignored (`26d2f15`).
- A1 compliance gate added, plus the FS §456.062 footnote on `contact.html` and
  `services.html`, which had advertised the free consult without it (`e79769e`).
  The gate found that gap on its first run.
- `about.html` is **deleted**. The bio lives on `index.html` in the About Me /
  My Approach sections. **Do not recreate an About page.**
- Florida is a §456.47 telehealth registration (TPMF1707), **not a license**.
  Corrected everywhere; R9 now enforces it.

Inbound links to `online-therapy-washington.html` are `services.html`,
`financial-anxiety.html` and `job-loss-and-career-therapy.html`, plus the
sitemap. **Not linked from `index.html` or the nav — Kamron was offered
homepage, footer and nav placement on 26 Aug and chose to leave it. Do not
re-propose it.**

`notice-of-privacy-practices.html` is still a draft. Kamron should ask his
malpractice carrier for their vetted template and replace it.

## Known issues, not yet fixed

- `contact.html` posts to Formspree with a free-text message field. No BAA. The
  fix is to drop the textarea for a bounded dropdown and link out to a hosted
  HIPAA-compliant page (Hushmail or MailHippo) for anything private.
- No crisis line on the contact page. Should say: call or text 988, or 911.
- GTM, GA4 (with a `generate_lead` event capturing page path) and a Psychology
  Today badge script run on every page including the condition pages. Kamron
  chose to leave these for now. Don't add more — R5 will block new ones.
- Verify GitHub Pages "Enforce HTTPS" is on. Chrome 154 (Oct 2026) shows a
  full-page interstitial for plain-HTTP visits.
- `mens-mental-health.html` has 0 inbound internal links, by Kamron's choice.

## Conventions

- Match the existing page structure exactly — same `<head>` block, same nav, same
  footer. Copy from a sibling page rather than inventing markup.
- Legal pages use the `.legal-body` wrapper and the styles at the bottom of
  `styles.css`.
- Content structure that gets cited by AI search: a question-phrased `<h2>`, a
  direct 40–60 word answer immediately under it, then supporting detail.
- `job-loss-and-career-therapy.html` is the content template for new specialty
  pages — copy its structure (question-phrased `<h2>` headings, a direct 40–60
  word answer under each, then supporting detail). Niche pages like it are
  reachable from `services.html` and search, NOT the main nav — four nav items
  plus the CTA is the intended size.
- Always state which states a service is available in. It's both a compliance
  point and what lets an assistant filter you correctly.
- Never commit directly to `main` — it publishes instantly. Work on a branch.
- Run `python3 tools/compliance-check.py` before every commit. Green or don't ship.

## Background

Fuller research and reasoning, including the SEO strategy and the full compliance
audit, live in the Kindred Mental Health project on claude.ai. Not legal advice —
the statutory readings above should be confirmed with counsel.

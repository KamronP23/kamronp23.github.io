#!/usr/bin/env python3
"""
Ping IndexNow so Bing (and Copilot, and anything else retrieving from Bing's
index) picks up changed pages within hours instead of waiting to be crawled.

This matters for AI search specifically: assistants retrieve from existing
search indexes rather than crawling the open web, and ChatGPT's search leans
on Bing. A page Bing hasn't indexed is invisible to that whole surface.

Usage:
    python3 tools/indexnow.py                 # submit every URL in sitemap.xml
    python3 tools/indexnow.py page.html ...   # submit specific pages

The key file must stay reachable at https://<host>/<key>.txt — that is how
IndexNow verifies you own the site. Do not delete or rename it.
"""

import pathlib
import re
import sys
import json
import urllib.request

HOST = "kindredmentalhealth.com"
KEY = "fc60f20323e8c374a2b211be15acdc25"
ENDPOINT = "https://api.indexnow.org/IndexNow"
ROOT = pathlib.Path(__file__).resolve().parent.parent


def urls_from_sitemap() -> list[str]:
    sm = ROOT / "sitemap.xml"
    if not sm.exists():
        sys.exit("sitemap.xml not found")
    return re.findall(r"<loc>\s*(.*?)\s*</loc>", sm.read_text(encoding="utf-8"))


def main() -> int:
    args = sys.argv[1:]
    if args:
        urls = [
            a if a.startswith("http") else f"https://{HOST}/{a.lstrip('/')}"
            for a in args
        ]
    else:
        urls = urls_from_sitemap()

    if not urls:
        print("nothing to submit")
        return 0

    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": f"https://{HOST}/{KEY}.txt",
        "urlList": urls,
    }

    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:
        print(f"IndexNow submission failed: {e}")
        return 0  # never fail a deploy over this

    # 200 accepted, 202 accepted pending key validation. Both are fine.
    if code in (200, 202):
        print(f"IndexNow: submitted {len(urls)} URLs (HTTP {code})")
    else:
        print(f"IndexNow: HTTP {code} — submission may not have been accepted")
    return 0


if __name__ == "__main__":
    sys.exit(main())

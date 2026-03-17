#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import json
import re
import time
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

START_URL = "https://findingaids.library.columbia.edu/archives/cul-5321412_aspace_a06820e02550cf1839ca72f49e0c8ab9"
BASE_URL = "https://findingaids.library.columbia.edu"

OUT_JSONL = "columbia_armenian_oral_history_archive.jsonl"
OUT_CSV = "columbia_armenian_oral_history_archive.csv"
OUT_DEBUG = "debug_links.json"

USER_DATA_DIR = ".playwright_columbia_profile"


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()


def uniq_by_key(items, key_fn):
    seen = set()
    out = []
    for item in items:
        key = key_fn(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def open_page(page, url):
    print(f"\n[OPEN] {url}", flush=True)
    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(2500)


def get_title(page):
    for sel in ["h1", "main h1", ".page-title", ".record-title"]:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                txt = clean_text(loc.inner_text())
                if txt:
                    return txt
        except Exception:
            pass
    try:
        return clean_text(page.title())
    except Exception:
        return ""


def get_meta_description(page):
    for sel in [
        "meta[name='description']",
        "meta[property='og:description']",
        "meta[name='twitter:description']",
        "meta[name='citation_abstract']",
    ]:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0:
                val = loc.get_attribute("content")
                if val:
                    return clean_text(val)
        except Exception:
            pass
    return ""


def extract_dl_pairs(page):
    try:
        pairs = page.evaluate("""
        () => {
          const rows = [];

          document.querySelectorAll("dl").forEach(dl => {
            const kids = Array.from(dl.children);
            let current = null;
            for (const el of kids) {
              const tag = el.tagName.toLowerCase();
              const txt = (el.innerText || "").replace(/\\s+/g, " ").trim();
              if (!txt) continue;
              if (tag === "dt") current = txt;
              if (tag === "dd" && current) rows.push([current, txt]);
            }
          });

          document.querySelectorAll("tr").forEach(tr => {
            const th = tr.querySelector("th");
            const td = tr.querySelector("td");
            if (th && td) {
              const k = (th.innerText || "").replace(/\\s+/g, " ").trim();
              const v = (td.innerText || "").replace(/\\s+/g, " ").trim();
              if (k && v) rows.push([k, v]);
            }
          });

          return rows;
        }
        """)
    except Exception:
        pairs = []

    meta = {}
    for k, v in pairs:
        kk = clean_text(k).lower()
        vv = clean_text(v)
        if kk and vv:
            meta.setdefault(kk, []).append(vv)
    return meta


def first_matching(meta, keys):
    for mk, vals in meta.items():
        for key in keys:
            if key in mk:
                vals = [clean_text(v) for v in vals if clean_text(v)]
                if vals:
                    return " | ".join(dict.fromkeys(vals))
    return ""


def infer_date(text):
    years = re.findall(r"\b(18\d{2}|19\d{2}|20\d{2})\b", text or "")
    if not years:
        return ""
    if len(years) == 1:
        return years[0]
    return f"{years[0]}-{years[-1]}"


def extract_candidates_from_list_page(page):
    """
    Robust list-page extraction:
    1) visible anchors/buttons/data-* attrs
    2) onclick patterns
    3) raw HTML _aspace_ fallback
    4) visible body-text fallback for names
    """
    try:
        data = page.evaluate("""
        () => {
          const els = Array.from(
            document.querySelectorAll("a, button, [role='link'], [data-href], [data-url], [data-uri], [onclick]")
          ).map(el => {
            const text = (el.innerText || el.textContent || "").replace(/\\s+/g, " ").trim();
            const href =
              el.getAttribute("href") ||
              el.getAttribute("data-href") ||
              el.getAttribute("data-url") ||
              el.getAttribute("data-uri") ||
              "";
            const onclick = el.getAttribute("onclick") || "";
            const rowText =
              (el.closest("tr")?.innerText ||
               el.closest("li")?.innerText ||
               el.parentElement?.parentElement?.innerText ||
               el.parentElement?.innerText ||
               "").replace(/\\s+/g, " ").trim();

            return { text, href, onclick, row_text: rowText };
          });

          const bodyText = (document.body?.innerText || "").replace(/\\s+/g, " ").trim();
          const html = document.documentElement.outerHTML;

          return { els, bodyText, html };
        }
        """)
    except Exception:
        data = {"els": [], "bodyText": "", "html": ""}

    candidates = []

    # pass 1: real elements
    for r in data.get("els", []):
        title = clean_text(r.get("text", ""))
        href = clean_text(r.get("href", ""))
        onclick = clean_text(r.get("onclick", ""))
        row_text = clean_text(r.get("row_text", ""))

        full = ""
        if href:
            full = urljoin(BASE_URL, href)
        elif onclick:
            m = re.search(r"(/archives/cul-5321412_aspace_[A-Za-z0-9]+)", onclick)
            if m:
                full = urljoin(BASE_URL, m.group(1))

        if not full:
            continue
        if "/archives/cul-5321412_aspace_" not in full:
            continue

        m_box = re.search(r"(Box\s+[^,;\n]+,\s*Folder\s+[^\n]+)", row_text, re.I)
        box_folder = clean_text(m_box.group(1)) if m_box else ""

        candidates.append({
            "title": title,
            "href": full,
            "box_folder": box_folder,
            "row_text": row_text,
        })

    # pass 2: raw HTML links
    html = data.get("html", "") or ""
    html_links = re.findall(r"/archives/cul-5321412_aspace_[A-Za-z0-9]+", html)

    for link in html_links:
        candidates.append({
            "title": "",
            "href": urljoin(BASE_URL, link),
            "box_folder": "",
            "row_text": "",
        })

    # pass 3: body-text names fallback
    body = data.get("bodyText", "") or ""
    name_matches = re.findall(r"\b([A-Z][A-Za-z'`.-]+,\s+[A-Z][A-Za-z'` .-]+)\b", body)
    name_matches = [clean_text(x) for x in name_matches if clean_text(x)]

    # dedupe URLs first
    candidates = uniq_by_key(candidates, lambda x: x["href"])

    # if there are blank titles, try to assign from body-text names in order
    names_iter = iter(dict.fromkeys(name_matches))
    fixed = []
    for c in candidates:
        title = c["title"]
        if not title:
            try:
                title = next(names_iter)
            except StopIteration:
                title = ""
        fixed.append({
            "title": title,
            "href": c["href"],
            "box_folder": c["box_folder"],
            "row_text": c["row_text"],
        })

    # remove obvious non-item self-link only if there are many links
    if len(fixed) > 1:
        fixed = [x for x in fixed if x["href"] != START_URL]

    print(f"[INFO] extracted {len(fixed)} candidate links", flush=True)
    for x in fixed[:10]:
        print("   ", x["title"], "|", x["href"], "|", x["box_folder"], flush=True)

    return fixed


def click_next(page):
    for sel in [
        "a:has-text('Next »')",
        "a:has-text('Next')",
        "text=Next »",
        "text=Next",
    ]:
        try:
            loc = page.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                print("[INFO] clicking Next", flush=True)
                loc.click(timeout=5000)
                page.wait_for_load_state("domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)
                return True
        except Exception:
            pass
    return False


def collect_all_rows(page, max_pages=10):
    all_rows = []

    for page_num in range(1, max_pages + 1):
        print(f"[INFO] analyzing page {page_num}", flush=True)
        print(f"[INFO] page title: {get_title(page)}", flush=True)

        rows = extract_candidates_from_list_page(page)
        all_rows.extend(rows)

        if not click_next(page):
            break

    # dedupe by href
    rows = uniq_by_key(all_rows, lambda x: x["href"])
    print(f"[INFO] total unique rows collected: {len(rows)}", flush=True)
    return rows


def extract_record(page, fallback_title="", fallback_box_folder=""):
    title = get_title(page)
    meta = extract_dl_pairs(page)

    description = (
        first_matching(meta, ["scope and content", "scope", "abstract", "description", "summary", "note", "biographical"])
        or get_meta_description(page)
    )

    creator = first_matching(meta, ["creator", "author", "interviewee", "interviewer", "name", "personal name"])
    date_period = first_matching(meta, ["date", "dates", "created", "creation", "period", "date issued"])

    if not date_period:
        date_period = infer_date((title or "") + " " + (description or ""))

    if not title:
        title = fallback_title

    return {
        "title": clean_text(title),
        "date_period": clean_text(date_period),
        "author_creator": clean_text(creator),
        "description_abstract": clean_text(description),
        "box_folder": clean_text(fallback_box_folder),
        "original_url": clean_text(page.url),
    }


def save_jsonl(records, path):
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def save_csv_semicolon(records, path):
    headers = ["title", "date_period", "author_creator", "description_abstract", "box_folder", "original_url"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write(";".join(headers) + "\n")
        for r in records:
            row = []
            for h in headers:
                val = clean_text(r.get(h, ""))
                val = val.replace('"', '""')
                row.append(f'"{val}"')
            f.write(";".join(row) + "\n")


def main():
    with sync_playwright() as p:
        browser_obj = None
        context = None

        try:
            context = p.chromium.launch_persistent_context(
                USER_DATA_DIR,
                headless=False,
                viewport={"width": 1440, "height": 1000},
            )
            page = context.new_page()
            print("[INFO] using persistent browser profile", flush=True)
        except Exception:
            print("[WARN] persistent profile failed, using fresh browser context", flush=True)
            browser_obj = p.chromium.launch(headless=False)
            context = browser_obj.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()

        open_page(page, START_URL)

        rows = collect_all_rows(page, max_pages=10)

        with open(OUT_DEBUG, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

        if not rows:
            print("[ERROR] no rows collected", flush=True)
            context.close()
            if browser_obj:
                browser_obj.close()
            return

        records = []
        for i, row in enumerate(rows, 1):
            print(f"[SCRAPE] {i}/{len(rows)} {row['title'] or row['href']}", flush=True)
            try:
                open_page(page, row["href"])
                rec = extract_record(
                    page,
                    fallback_title=row.get("title", ""),
                    fallback_box_folder=row.get("box_folder", ""),
                )
                if rec["title"] or rec["original_url"]:
                    records.append(rec)
                    print(f"[OK] {rec['title']}", flush=True)
            except Exception as e:
                print(f"[WARN] failed {row['href']} -> {e}", flush=True)

        records = uniq_by_key(records, lambda x: (x["original_url"], x["title"].lower()))
        print(f"[DONE] records collected: {len(records)}", flush=True)

        save_jsonl(records, OUT_JSONL)
        save_csv_semicolon(records, OUT_CSV)

        print(f"[DONE] wrote {OUT_JSONL}", flush=True)
        print(f"[DONE] wrote {OUT_CSV}", flush=True)
        print(f"[DONE] wrote {OUT_DEBUG}", flush=True)

        context.close()
        if browser_obj:
            browser_obj.close()


if __name__ == "__main__":
    main()
"""
Power Platform ニュース ダイジェスト - RSS フィード取得スクリプト

対象フィード:
  1. Power Platform Blog (powerapps.microsoft.com/en-us/blog/feed/)
  2. Power Platform Developer Blog (devblogs.microsoft.com/powerplatform/feed/)

機械翻訳: Google翻訳の無料WebAPI (translate.googleapis.com) を使用
タグ/製品フィルター: 製品名のみ (7カテゴリ)
出力: docs/news.json
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape


FEEDS = [
    {
        "url": "https://powerapps.microsoft.com/en-us/blog/feed/",
        "source": "Blog",
    },
    {
        "url": "https://devblogs.microsoft.com/powerplatform/feed/",
        "source": "DevBlog",
    },
]

# 製品判定キーワード (タグ・フィルターで共通利用)
PRODUCT_KEYWORDS = {
    "Power Apps": ["power apps", "powerapps", "canvas app", "model-driven", "model driven", "code apps"],
    "Power Automate": ["power automate", "process mining", "rpa", "desktop flow", "cloud flow"],
    "Copilot Studio": ["copilot studio", "copilot", "virtual agent", "pva"],
    "Power Pages": ["power pages", "portal"],
    "Dataverse": ["dataverse", "common data service", "cds"],
    "AI Builder": ["ai builder"],
    "管理・ガバナンス": ["admin", "governance", "dlp", "managed environment", "tenant", "ppac",
                         "admin center", "security", "compliance", "licensing"],
}

# 表示用の製品リスト順序 (タグを付ける際の優先順位)
PRODUCT_PRIORITY = [
    "Power Apps", "Power Automate", "Copilot Studio", "Power Pages",
    "Dataverse", "AI Builder", "管理・ガバナンス",
]


def fetch_feed(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 PPNewsDigest/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def strip_html(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def translate_to_ja(text: str) -> str:
    """Google翻訳の無料WebAPIで英語→日本語に翻訳。失敗時は元のテキストを返す"""
    if not text or not text.strip():
        return text
    if len(text) > 1500:
        text = text[:1500]
    try:
        params = {
            "client": "gtx",
            "sl": "en",
            "tl": "ja",
            "dt": "t",
            "q": text,
        }
        url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data and data[0]:
            translated = "".join(seg[0] for seg in data[0] if seg[0])
            return translated.strip() or text
    except Exception as e:
        print(f"  Translation failed: {e}", file=sys.stderr)
    return text


def detect_products(title: str, summary: str) -> list:
    """製品を判定して、該当する製品名のリストを返す (優先順)"""
    combined = (title + " " + summary).lower()
    matched = []
    for product in PRODUCT_PRIORITY:
        keywords = PRODUCT_KEYWORDS[product]
        for kw in keywords:
            if kw in combined:
                if product not in matched:
                    matched.append(product)
                break
    return matched


def parse_date(date_str: str) -> str:
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def parse_rss(xml_bytes: bytes, source: str) -> list:
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"  XML parse error for {source}: {e}", file=sys.stderr)
        return items

    for item_el in root.findall(".//item"):
        title_el = item_el.find("title")
        link_el = item_el.find("link")
        desc_el = item_el.find("description")
        pub_el = item_el.find("pubDate")

        title_en = title_el.text.strip() if title_el is not None and title_el.text else ""
        link = link_el.text.strip() if link_el is not None and link_el.text else ""
        desc_en = strip_html(desc_el.text) if desc_el is not None and desc_el.text else ""
        date = parse_date(pub_el.text) if pub_el is not None and pub_el.text else ""

        if not title_en:
            continue

        # 製品タグを判定 (英語原文ベース)
        products = detect_products(title_en, desc_en)
        primary_product = products[0] if products else "Power Platform"

        # 要約を300文字で切る
        summary_en = desc_en[:300] + "..." if len(desc_en) > 300 else desc_en

        # 日本語に翻訳
        print(f"  Translating: {title_en[:60]}...")
        title_ja = translate_to_ja(title_en)
        summary_ja = translate_to_ja(summary_en)
        time.sleep(0.5)

        items.append({
            "date": date,
            "title": title_ja,
            "titleOriginal": title_en,
            "summary": summary_ja,
            "product": primary_product,
            "tags": products,
            "url": link,
            "source": source,
        })

    return items


def main():
    all_items = []

    for feed in FEEDS:
        print(f"Fetching: {feed['url']}")
        try:
            xml_bytes = fetch_feed(feed["url"])
            items = parse_rss(xml_bytes, feed["source"])
            print(f"  Found {len(items)} items")
            all_items.extend(items)
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)

    all_items.sort(key=lambda x: x["date"], reverse=True)

    seen_urls = set()
    unique_items = []
    for item in all_items:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            unique_items.append(item)

    output = {
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totalCount": len(unique_items),
        "translationNote": "タイトル・要約はGoogle翻訳による機械翻訳です",
        "items": unique_items,
    }

    output_path = "docs/news.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nOutput: {output_path} ({len(unique_items)} items)")


if __name__ == "__main__":
    main()

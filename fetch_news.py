"""
Power Platform ニュース ダイジェスト - RSS フィード取得スクリプト

対象フィード:
  1. Power Platform Blog (powerapps.microsoft.com/en-us/blog/feed/)
  2. Power Platform Developer Blog (devblogs.microsoft.com/powerplatform/feed/)

出力: docs/news.json
"""

import json
import re
import sys
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

# 製品判定用キーワード
PRODUCT_KEYWORDS = {
    "Power Apps": ["power apps", "powerapps", "canvas app", "model-driven", "model driven", "code apps"],
    "Power Automate": ["power automate", "flow", "process mining", "rpa", "desktop flow", "cloud flow"],
    "Copilot Studio": ["copilot studio", "copilot", "virtual agent", "pva"],
    "Power Pages": ["power pages", "portal"],
    "Dataverse": ["dataverse", "common data service", "cds"],
    "AI Builder": ["ai builder"],
    "管理・ガバナンス": ["admin", "governance", "dlp", "managed environment", "tenant", "ppac",
                         "admin center", "security", "compliance", "licensing"],
}

# ステータス判定用キーワード
STATUS_KEYWORDS = {
    "GA": ["generally available", "general availability", "now available", "is now ga", "一般提供"],
    "Preview": ["public preview", "preview", "in preview"],
    "廃止": ["deprecat", "retire", "end of support", "sunset", "廃止"],
    "開発中": ["coming soon", "in development", "planned", "roadmap"],
}

# タグ抽出用キーワード
TAG_KEYWORDS = [
    "Power Apps", "Power Automate", "Copilot Studio", "Power Pages",
    "Dataverse", "AI Builder", "Canvas App", "Model-driven",
    "MCP", "Git", "ALM", "DevOps", "FetchXML", "Power Fx",
    "Offline", "Search", "Security", "Governance", "Admin Center",
    "Azure AI", "LLM", "Agent", "Copilot", "React", "Component",
    "Licensing", "DLP", "Managed Environment",
]


def fetch_feed(url: str) -> bytes:
    """URLからRSSフィードをダウンロード"""
    req = urllib.request.Request(url, headers={"User-Agent": "PPNewsDigest/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def strip_html(text: str) -> str:
    """HTMLタグを除去してプレーンテキストにする"""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_product(title: str, summary: str) -> str:
    """タイトルと要約から製品カテゴリを推定"""
    combined = (title + " " + summary).lower()
    for product, keywords in PRODUCT_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                return product
    return "Power Platform"


def detect_status(title: str, summary: str) -> str:
    """タイトルと要約からステータスを推定"""
    combined = (title + " " + summary).lower()
    # 廃止を先にチェック (他と重複する可能性があるため)
    for kw in STATUS_KEYWORDS["廃止"]:
        if kw in combined:
            return "廃止"
    for kw in STATUS_KEYWORDS["GA"]:
        if kw in combined:
            return "GA"
    for kw in STATUS_KEYWORDS["Preview"]:
        if kw in combined:
            return "Preview"
    for kw in STATUS_KEYWORDS["開発中"]:
        if kw in combined:
            return "開発中"
    return "GA"


def extract_tags(title: str, summary: str) -> list[str]:
    """タイトルと要約から関連タグを抽出"""
    combined = title + " " + summary
    tags = []
    for tag in TAG_KEYWORDS:
        if tag.lower() in combined.lower():
            if tag not in tags:
                tags.append(tag)
    return tags[:5]  # 最大5個


def parse_date(date_str: str) -> str:
    """RFC 2822形式の日付をISO形式に変換"""
    # 例: "Mon, 17 Feb 2026 12:00:00 +0000"
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
    # フォールバック: 今日の日付
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def parse_rss(xml_bytes: bytes, source: str) -> list[dict]:
    """RSSのXMLをパースして記事リストを生成"""
    items = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        print(f"  XML parse error for {source}: {e}", file=sys.stderr)
        return items

    # RSS 2.0: channel/item
    for item_el in root.findall(".//item"):
        title_el = item_el.find("title")
        link_el = item_el.find("link")
        desc_el = item_el.find("description")
        pub_el = item_el.find("pubDate")

        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        link = link_el.text.strip() if link_el is not None and link_el.text else ""
        desc = strip_html(desc_el.text) if desc_el is not None and desc_el.text else ""
        date = parse_date(pub_el.text) if pub_el is not None and pub_el.text else ""

        if not title:
            continue

        # 要約は200文字で切る
        summary = desc[:200] + "..." if len(desc) > 200 else desc

        # カテゴリタグ (RSSのcategoryタグ)
        categories = []
        for cat_el in item_el.findall("category"):
            if cat_el.text:
                categories.append(cat_el.text.strip())

        product = detect_product(title, desc)
        status = detect_status(title, desc)
        tags = extract_tags(title, desc)
        # RSSカテゴリも追加
        for cat in categories[:3]:
            if cat not in tags and len(tags) < 5:
                tags.append(cat)

        items.append({
            "date": date,
            "title": title,
            "summary": summary,
            "status": status,
            "product": product,
            "tags": tags,
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

    # 日付の新しい順にソート
    all_items.sort(key=lambda x: x["date"], reverse=True)

    # 重複除去 (同じURL)
    seen_urls = set()
    unique_items = []
    for item in all_items:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            unique_items.append(item)

    # メタデータ付きで出力
    output = {
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totalCount": len(unique_items),
        "items": unique_items,
    }

    # docs/news.json に書き出し
    output_path = "docs/news.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nOutput: {output_path} ({len(unique_items)} items)")


if __name__ == "__main__":
    main()

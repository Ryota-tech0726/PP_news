"""
Power Platform ニュース ダイジェスト - RSS フィード取得スクリプト

対象フィード:
  1. Power Platform Blog (powerapps.microsoft.com/en-us/blog/feed/)
  2. Power Platform Developer Blog (devblogs.microsoft.com/powerplatform/feed/)

機械翻訳: Google翻訳の無料WebAPI
  - 製品名・固有名詞・技術用語は英語のまま保持 (約110ワード)
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

# 製品判定キーワード
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

PRODUCT_PRIORITY = [
    "Power Apps", "Power Automate", "Copilot Studio", "Power Pages",
    "Dataverse", "AI Builder", "管理・ガバナンス",
]

# 英語のまま残すキーワード (約110ワード)
# 翻訳時にプレースホルダーに置換し、翻訳後に戻す
# 長いキーワードから先に処理されるため、順序は自動ソートされる
KEEP_ENGLISH_KEYWORDS = [
    # ========== Microsoft製品・プラットフォーム ==========
    "Microsoft Power Platform",
    "Microsoft 365 Copilot",
    "Microsoft Power Apps",
    "Microsoft Dataverse",
    "Microsoft Copilot Studio",
    "Microsoft Teams",
    "Microsoft Entra",
    "Microsoft Fabric",
    "Microsoft Learn",
    "Power Platform",
    "Power Apps",
    "Power Automate",
    "Power Automate for desktop",
    "Power Apps Studio",
    "Power Platform admin center",
    "Power Platform CLI",
    "Power Platform inventory",
    "Copilot Studio",
    "Power Pages",
    "Dataverse",
    "Dataverse SDK",
    "Dataverse Search",
    "Dataverse accelerator",
    "AI Builder",
    "Power BI",
    "Power Fx",
    "Dynamics 365",

    # ========== Azure関連 ==========
    "Azure OpenAI",
    "Azure AI Foundry",
    "Azure AI Services",
    "Azure Synapse Link",
    "Azure Synapse",
    "Azure Data Lake",
    "Azure App Insights",
    "Entra ID",

    # ========== 外部ツール・サービス ==========
    "GitHub Copilot CLI",
    "GitHub Copilot",
    "Claude Code",
    "Visual Studio Code",
    "VS Code extension",
    "VS Code",
    "vibe.powerapps.com",

    # ========== 機能・コンポーネント ==========
    "Agent Academy",
    "Agent Feed",
    "Agent Flows",
    "Agent API",
    "Plan Designer",
    "Plan designer",
    "Canvas Apps",
    "Canvas App",
    "Model-driven Apps",
    "Model-driven App",
    "Model-driven",
    "Managed Environments",
    "Managed Environment",
    "Admin Center",
    "Enhanced Component Properties",
    "Component Library",
    "Security Compliance",
    "Power Platform Advisor",
    "Code Apps",
    "Cloud Flow",
    "Desktop Flow",
    "Agent Flow",
    "Server Logic",
    "Process Mining",
    "Object-Centric Process Mining",
    "OCPM",
    "Process Intelligence",
    "Work IQ",
    "Generative Page",
    "generative pages",
    "modern controls",
    "Web API",
    "Web Template",
    "Web Application Firewall",
    "Content Security Policy",
    "Virtual Network",

    # ========== モダンコントロール名 ==========
    "Combo Box",
    "Date Picker",
    "Text Input",
    "Number Input",
    "Tab List",
    "Info Button",

    # ========== セキュリティ・ガバナンス ==========
    "Role-based access control",
    "Run-only user role",
    "Managed identities",

    # ========== 技術プロトコル・用語 ==========
    "Model Context Protocol",
    "MCP Server",
    "MCP",
    "FetchXML",
    "Dataflows",
    "Dataflow",
    "Connectors",
    "Connector",
    "Liquid",
    "REST API",
    "OAuth 2.0",
    "IntelliSense",
    "npm CLI",

    # ========== ステータス・リリース用語 ==========
    "General Availability",
    "Generally Available",
    "Public Preview",

    # ========== 略語・短い用語 ==========
    "Copilot",
    "Agents",
    "Agent",
    "Workflows",
    "Workflow",
    "DLP",
    "ALM",
    "SDK",
    "API",
    "RSS",
    "GA",
    "OAuth",
    "SSO",
    "MFA",
    "KPI",
    "DNA",
    "ERP",
    "React",
    "TypeScript",
    "JavaScript",
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


def protect_keywords(text: str) -> tuple:
    """
    残すキーワードをプレースホルダーに置換する。
    長いキーワードから順に処理 (部分一致による誤置換を防ぐ)
    """
    mapping = {}
    protected = text
    sorted_keywords = sorted(set(KEEP_ENGLISH_KEYWORDS), key=len, reverse=True)

    for keyword in sorted_keywords:
        pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)

        def replace_fn(match):
            placeholder_idx = len(mapping)
            placeholder = f"XKEEPX{placeholder_idx}XKEEPX"
            mapping[placeholder] = keyword
            return placeholder

        protected = pattern.sub(replace_fn, protected)

    return protected, mapping


def restore_keywords(text: str, mapping: dict) -> str:
    """プレースホルダーを元の英語キーワードに戻す"""
    result = text
    for placeholder, keyword in mapping.items():
        result = result.replace(placeholder, keyword)
        # Google翻訳がスペースや大文字小文字を変えた場合の救済
        idx = list(mapping.keys()).index(placeholder)
        loose_pattern = re.compile(
            r'x\s*keep\s*x\s*' + str(idx) + r'\s*x\s*keep\s*x',
            re.IGNORECASE
        )
        result = loose_pattern.sub(keyword, result)
    return result


def translate_to_ja(text: str) -> str:
    """英語→日本語翻訳。固有名詞は英語のまま保持"""
    if not text or not text.strip():
        return text
    if len(text) > 1500:
        text = text[:1500]

    protected_text, mapping = protect_keywords(text)

    try:
        params = {
            "client": "gtx",
            "sl": "en",
            "tl": "ja",
            "dt": "t",
            "q": protected_text,
        }
        url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data and data[0]:
            translated = "".join(seg[0] for seg in data[0] if seg[0])
            translated = translated.strip() or text
            return restore_keywords(translated, mapping)
    except Exception as e:
        print(f"  Translation failed: {e}", file=sys.stderr)
    return text


def detect_products(title: str, summary: str) -> list:
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

        products = detect_products(title_en, desc_en)
        primary_product = products[0] if products else "Power Platform"

        summary_en = desc_en[:300] + "..." if len(desc_en) > 300 else desc_en

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
        "translationNote": "タイトル・要約はGoogle翻訳による機械翻訳です (固有名詞は英語のまま保持)",
        "items": unique_items,
    }

    output_path = "docs/news.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nOutput: {output_path} ({len(unique_items)} items)")


if __name__ == "__main__":
    main()

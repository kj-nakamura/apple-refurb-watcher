import json
import os
import re
import sys
import requests

BASE_URL = "https://www.apple.com/jp/shop/refurbished"
NOTIFIED_FILE = "notified.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# キーワード → フェッチするカテゴリURLのマッピング
KEYWORD_TO_CATEGORY = {
    "Mac mini": "mac",
    "MacBook": "mac",
    "iMac": "mac",
    "Mac Pro": "mac",
    "Mac Studio": "mac",
    "iPhone": "iphone",
    "iPad": "ipad",
    "Apple Watch": "watch",
    "AirPods": "airpods",
    "Apple TV": "appletv",
}

DEFAULT_KEYWORDS = "Mac mini"


def get_watch_keywords():
    raw = os.environ.get("WATCH_KEYWORDS", DEFAULT_KEYWORDS)
    return [k.strip() for k in raw.split(",") if k.strip()]


def get_categories(keywords):
    categories = set()
    for kw in keywords:
        for key, cat in KEYWORD_TO_CATEGORY.items():
            if kw.lower() in key.lower() or key.lower() in kw.lower():
                categories.add(cat)
                break
        else:
            categories.add("mac")  # デフォルトは mac カテゴリ
    return categories


def fetch_products_from(category):
    url = f"{BASE_URL}/{category}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    scripts = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>',
        resp.text,
        re.DOTALL,
    )
    products = []
    for s in scripts:
        try:
            d = json.loads(s)
            if d.get("@type") != "Product":
                continue
            name = d.get("name", "")
            url = d.get("url", "")
            offers = d.get("offers", [{}])
            offer = offers[0] if offers else {}
            sku = offer.get("sku", "")
            price = offer.get("price")
            if sku:
                products.append({"sku": sku, "name": name, "price": price, "url": url})
        except json.JSONDecodeError:
            pass
    return products


def load_notified():
    if os.path.exists(NOTIFIED_FILE):
        with open(NOTIFIED_FILE) as f:
            return json.load(f)
    return {}


def save_notified(data):
    with open(NOTIFIED_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def notify_slack(products):
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL not set", file=sys.stderr)
        return

    lines = ["🎉 整備済み品に入荷しました！\n"]
    for p in products:
        price_str = f"¥{p['price']:,}" if p["price"] else "価格不明"
        lines.append(f"• {p['name']} - {price_str}\n  {p['url']}")

    payload = {"text": "\n".join(lines)}
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    print(f"Slack notified: {len(products)} product(s)")


def main():
    keywords = get_watch_keywords()
    print(f"Watching: {', '.join(keywords)}")

    categories = get_categories(keywords)
    print(f"Fetching categories: {', '.join(categories)}")

    all_products = []
    for cat in categories:
        all_products.extend(fetch_products_from(cat))

    matched = [
        p for p in all_products
        if any(kw.lower() in p["name"].lower() for kw in keywords)
    ]
    print(f"Found {len(matched)} matched product(s)")

    notified = load_notified()
    current_skus = {p["sku"] for p in matched}

    new_products = [p for p in matched if p["sku"] not in notified]

    if new_products:
        notify_slack(new_products)
        for p in new_products:
            notified[p["sku"]] = {"name": p["name"], "price": p["price"]}
    else:
        print("No new products")

    # 在庫から消えたSKUを削除（再入荷を検知するため）
    for sku in list(notified.keys()):
        if sku not in current_skus:
            print(f"Removed from notified (out of stock): {sku}")
            del notified[sku]

    save_notified(notified)


if __name__ == "__main__":
    main()

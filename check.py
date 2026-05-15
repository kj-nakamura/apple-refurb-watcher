import json
import os
import re
import sys
import requests

URL = "https://www.apple.com/jp/shop/refurbished/mac"
NOTIFIED_FILE = "notified.json"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_products():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
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

    lines = ["🎉 Mac mini が整備済み品に入荷しました！\n"]
    for p in products:
        price_str = f"¥{p['price']:,}" if p["price"] else "価格不明"
        lines.append(f"• {p['name']} - {price_str}\n  {p['url']}")

    payload = {"text": "\n".join(lines)}
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    print(f"Slack notified: {len(products)} product(s)")


def main():
    all_products = fetch_products()
    mac_mini = [p for p in all_products if "Mac mini" in p["name"]]
    print(f"Found {len(mac_mini)} Mac mini product(s) in refurbished store")

    notified = load_notified()
    current_skus = {p["sku"] for p in mac_mini}

    new_products = [p for p in mac_mini if p["sku"] not in notified]

    if new_products:
        notify_slack(new_products)
        for p in new_products:
            notified[p["sku"]] = {"name": p["name"], "price": p["price"]}
    else:
        print("No new Mac mini products")

    # 在庫から消えたSKUを削除（再入荷を検知するため）
    for sku in list(notified.keys()):
        if sku not in current_skus:
            print(f"Removed from notified (out of stock): {sku}")
            del notified[sku]

    save_notified(notified)


if __name__ == "__main__":
    main()

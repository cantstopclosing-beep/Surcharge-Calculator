#!/usr/bin/env python3
"""
Scrapes the TNT Australia domestic fuel surcharge page and writes fuel-rate.json.
Called by the GitHub Action workflow on a monthly schedule.
"""

import re
import json
import urllib.request
from datetime import datetime

URL = "https://www.tnt.com/express/en_au/site/how-to/understand-fuel-surcharges.html"

def fetch_page():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")

def parse_rates(html):
    pattern = r'From\s+(\d{1,2}\s+\w+\s+\d{4})\s+to\s+(\d{1,2}\s+\w+\s+\d{4}):\s*([\d.]+)%'
    matches = re.findall(pattern, html)
    if not matches:
        return None

    now = datetime.now()
    entries = []
    for from_str, to_str, rate_str in matches:
        try:
            from_date = datetime.strptime(from_str, "%d %B %Y")
            to_date = datetime.strptime(to_str, "%d %B %Y")
            entries.append({
                "from": from_str, "to": to_str,
                "fromDate": from_date, "toDate": to_date,
                "rate": float(rate_str),
            })
        except ValueError:
            continue

    if not entries:
        return None

    entries.sort(key=lambda x: x["fromDate"], reverse=True)

    # Current = period containing today, or the most recent
    current = next((e for e in entries if e["fromDate"] <= now <= e["toDate"]), entries[0])

    # Next = any future period that isn't current
    future = [e for e in entries if e["fromDate"] > now and e is not current]
    nxt = future[-1] if future else None

    return current, nxt

def main():
    try:
        html = fetch_page()
    except Exception as e:
        print(f"Failed to fetch page: {e}")
        return

    result = parse_rates(html)
    if not result:
        print("Could not parse fuel rates from page")
        return

    current, nxt = result

    output = {
        "rate": round(current["rate"] / 100, 4),
        "label": f"{current['rate']}%",
        "period": f"{current['from']} \u2013 {current['to']}",
        "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }

    if nxt:
        output["nextRate"] = round(nxt["rate"] / 100, 4)
        output["nextLabel"] = f"{nxt['rate']}%"
        output["nextPeriod"] = f"{nxt['from']} \u2013 {nxt['to']}"

    with open("fuel-rate.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"Updated: {output['label']} for {output['period']}")

if __name__ == "__main__":
    main()

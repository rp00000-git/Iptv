#!/usr/bin/env python3
import concurrent.futures as cf
import json
import re
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
UA = "Mozilla/5.0 (compatible; Personal-IPTV-Builder/1.0)"
ATTR_RE = re.compile(r'([\\w-]+)="([^"]*)"')

def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()

def parse(text, source):
    result, current, options = [], None, []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXTINF:"):
            current = {
                "name": line.rsplit(",", 1)[-1].strip(),
                "attrs": dict(ATTR_RE.findall(line)),
                "source": source,
                "options": []
            }
            options = []
        elif current and line.startswith("#EXTVLCOPT:"):
            options.append(line)
        elif current and line and not line.startswith("#"):
            current["url"] = line
            current["options"] = options
            result.append(current)
            current, options = None, []
    return result

def wanted(entry):
    if entry["source"] == "Israel":
        return True
    a = entry["attrs"]
    haystack = " ".join((entry["name"], a.get("group-title", ""), a.get("tvg-name", ""))).lower()
    return any(word.lower() in haystack for word in CFG["english_keywords"])

def probe(entry):
    headers = {"User-Agent": UA, "Range": "bytes=0-32767"}
    for opt in entry.get("options", []):
        low = opt.lower()
        if "http-user-agent=" in low:
            headers["User-Agent"] = opt.split("=", 1)[1]
        elif "http-referrer=" in low:
            headers["Referer"] = opt.split("=", 1)[1]
    try:
        request = urllib.request.Request(entry["url"], headers=headers)
        with urllib.request.urlopen(request, timeout=CFG["probe_timeout_seconds"]) as response:
            response.read(1024)
            return entry, 200 <= getattr(response, "status", 200) < 400
    except Exception:
        return entry, False

def dedupe(entries):
    seen, result = set(), []
    for entry in entries:
        key = (entry["attrs"].get("tvg-id") or entry["name"].lower(), entry["url"])
        if key not in seen:
            seen.add(key)
            result.append(entry)
    return result

def cap_groups(entries):
    counts, result = defaultdict(int), []
    for entry in entries:
        if entry["source"] == "Israel":
            result.append(entry)
            continue
        group = entry["attrs"].get("group-title", "English")
        if counts[group] < CFG["max_channels_per_english_group"]:
            counts[group] += 1
            result.append(entry)
    return result

def main():
    entries = []
    for source, url in CFG["sources"].items():
        entries.extend(parse(get(url).decode("utf-8", "replace"), source))
    candidates = cap_groups(dedupe([entry for entry in entries if wanted(entry)]))
    israel = [entry for entry in candidates if entry["source"] == "Israel"]
    english = [entry for entry in candidates if entry["source"] != "Israel"]
    with cf.ThreadPoolExecutor(max_workers=CFG["probe_workers"]) as pool:
        checked = list(pool.map(probe, english))
    final = dedupe(israel + [entry for entry, active in checked if active])
    epg_url = "https://raw.githubusercontent.com/rp00000-git/Iptv/main/epg.xml"
    lines = [f'#EXTM3U url-tvg="{epg_url}" x-tvg-url="{epg_url}"']
    for entry in final:
        attrs = entry["attrs"].copy()
        attrs["group-title"] = "ישראל" if entry["source"] == "Israel" else "English | " + attrs.get("group-title", "Other")
        attr_text = " ".join(f'{key}="{str(value).replace(chr(34), chr(39))}"' for key, value in attrs.items() if value)
        lines.append(f'#EXTINF:-1 {attr_text},{entry["name"]}')
        lines.extend(entry.get("options", []))
        lines.append(entry["url"])
    (ROOT / "playlist.m3u").write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    status = {"israel_channels": len(israel), "english_checked": len(english), "english_active": len(final) - len(israel), "total": len(final)}
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import concurrent.futures as cf
import json
import re
import urllib.request
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
UA = "Mozilla/5.0 (compatible; Personal-IPTV-Builder/1.0)"
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
EPG_URL = "https://raw.githubusercontent.com/rp00000-git/Iptv/main/epg.xml.gz"
ISRAEL_EPG_IDS = {
    "5Gold": "5GOLD.il",
    "5Live": "5LIVE.HD.il",
    "5Plus": "5PLUS.HD.il",
    "5Sport": "5SPORT.HD.il",
    "5Stars": "5STARS.il",
    "Channel 9 (Israel)": "ערוץ.9.il",
    "Channel 13 (Israel)": "רשת.il",
    "Channel 24 (Israel)": "מוסיקה.24.il",
    "Disney Channel (Israel)": "דיסני.il",
    "Food Channel": "FOOD.NETWORK.HD.il",
    "Good Life": "GOOD.LIFE+.il",
    "Hidabroot": "ערוץ.הידברות.il",
    "Home +": "בית.+.HD.il",
    "HOT8": "ערוץ.8.שידור.חי.il",
    "i24NEWS Arabic": "i24NEWS.ARABIC.il",
    "i24NEWS French": "i24NEWS.FRENCH.il",
    "i24NEWS Hebrew": "עברית.i24.il",
    "Junior": "ג’וניור.il",
    "Kan 11": "כאן.11.il",
    "Kan Educational": "כאן.חינוכית.il",
    "Keshet 12": "קשת.il",
    "Knesset Channel": "ערוץ.הכנסת.il",
    "Makan 33": "מכאן.il",
    "Now 14": "ערוץ.14.HD.il",
    "One 2": "ONE2.HD.il",
    "Reality Channel": "ערוץ.הריאליטי.il",
    "TeenNick (Israel)": "ערוץ.TeenNick.il",
    "Vacation Channel": "ערוץ.הנופש.il",
    "Viva Istanbul": "ויוה.איסטנבול.il",
    "Viva Premium": "ויוה.פרימיום.il",
    "Viva Telenovelas": "ויוה.טלנובלות.il",
    "Yam Tichoni": "ים.תיכוני.il",
    "Zoom (Israel)": "ZOOM.Toon.il",
}

# A small, useful lineup. Names are the names used by iptv-org; the script
# keeps the first reachable variant when more than one stream exists.
ISRAEL_CHANNELS = {
    "Kan 11": "ישראל | ערוצים מרכזיים",
    "Keshet 12": "ישראל | ערוצים מרכזיים",
    "Channel 13 (Israel)": "ישראל | ערוצים מרכזיים",
    "Now 14": "ישראל | ערוצים מרכזיים",
    "Food Channel": "ישראל | לייף סטייל",
    "Vacation Channel": "ישראל | לייף סטייל",
    "Kabbalah for the People Israel": "ישראל | יהדות",
    "Good Life": "ישראל | לייף סטייל",
    "Channel 24 (Israel)": "ישראל | מוזיקה",
}

ENGLISH_CHANNELS = {
    "BBC News": "English | News",
    "ABC News": "English | News",
    "Al Jazeera English": "English | News",
    "Fox News Channel": "English | News",
    "Sky News": "English | News",
    "Sky News HD": "English | News",
    "CBS News 24/7": "English | News",
    "NBC News NOW": "English | News",
    "NBC News Now": "English | News",
    "Reuters TV": "English | News",
    "Reuters": "English | News",
    "France 24 English": "English | News",
    "DW English": "English | News",
    "Euronews English": "English | News",
    "Bloomberg Originals": "English | News",
    "Comedy Central": "English | Comedy",
    "NBC Comedy Vault": "English | Comedy",
    "Comedy Dynamics": "English | Comedy",
    "Just for Laughs Gags": "English | Comedy",
    "Just for Laughs GAGS": "English | Comedy",
    "FailArmy": "English | Comedy",
    "Cheers + Frasier": "English | Comedy",
    "Happy Days": "English | Comedy",
    "Anger Management": "English | Comedy",
    "Anger Management Channel": "English | Comedy",
    "The Carol Burnett Show": "English | Comedy",
    "Rakuten TV Family Movies UK": "English | Family",
    "Rakuten TV Family Movies Finland": "English | Family",
    "Kids Movie Club": "English | Family",
    "7th Heaven": "English | Family",
    "PBS Kids": "English | Family",
    "Family Movies": "English | Family",
    "National Geographic": "English | Nature & Science",
    "National Geographic Wild": "English | Nature & Science",
    "National Geographic Wild HD East": "English | Nature & Science",
    "BBC Earth US": "English | Nature & Science",
    "Curiosity NOW EN": "English | Nature & Science",
    "Smithsonian Channel Selects (United States)": "English | Nature & Science",
    "Pluto TV Science (United States)": "English | Nature & Science",
    "InWonder": "English | Nature & Science",
    "Wonder": "English | Nature & Science",
    "Love Nature": "English | Nature & Science",
    "WildEarth": "English | Nature & Science",
    "Mythbusters": "English | Nature & Science",
    "MythBusters": "English | Nature & Science",
    "DUST": "English | Movies & Series",
    "Pluto TV Sci-Fi (United States) CA": "English | Movies & Series",
    "Pluto TV Sci-Fi (Germany) GB": "English | Movies & Series",
    "Classic Movies Channel": "English | Movies & Series",
    "Star Trek: Deep Space Nine": "English | Movies & Series",
    "Star Trek: The Next Generation (United States)": "English | Movies & Series",
    "Pluto TV The Twilight Zone": "English | Movies & Series",
    "More TV Sci-fi": "English | Movies & Series",
    "AMC (United States)": "English | Movies & Series",
    "Pluto TV Action (Sweden)": "English | Movies & Series",
    "Pluto TV Adventure": "English | Movies & Series",
    "Pluto TV Comedy Movies": "English | Movies & Series",
    "Pluto TV Horror (United States)": "English | Movies & Series",
    "Blue Bloods": "English | Series",
    "MacGyver (Sweden)": "English | Series",
    "JAG (Sweden)": "English | Series",
    "Mission Impossible (Sweden)": "English | Series",
    "Matlock (Sweden)": "English | Series",
    "History (United States)": "English | History",
    "History Hit": "English | History",
    "Autentic History": "English | History",
    "True History": "English | History",
}

GROUP_HE = {
    "English | News": "אנגלית | חדשות",
    "English | Comedy": "אנגלית | קומדיה",
    "English | Family": "אנגלית | משפחה",
    "English | Nature & Science": "אנגלית | מדע וטבע",
    "English | Movies & Series": "אנגלית | סרטים ומדע בדיוני",
    "English | Series": "אנגלית | סדרות",
    "English | History": "אנגלית | היסטוריה",
}

def base_name(name):
    name = re.sub(r"\s+\[[^]]+\]$", "", name).strip()
    return re.sub(r"\s+\(\d+[pi]?\)$", "", name).strip()

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
    if "[Geo-blocked]" in entry["name"]:
        return False
    name = base_name(entry["name"])
    if entry["source"] == "Israel":
        return name in ISRAEL_CHANNELS
    return name in ENGLISH_CHANNELS

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
            data = response.read(4096)
            ok = 200 <= getattr(response, "status", 200) < 400
            if ".m3u8" in entry["url"].lower() and b"#EXTM3U" not in data:
                ok = False
            return entry, ok
    except Exception:
        return entry, False

def quality(entry):
    name = entry["name"].lower()
    if "2160p" in name: return 2
    if "1080p" in name: return 5
    if "720p" in name: return 4
    if "576" in name or "540p" in name: return 3
    if "480p" in name: return 2
    if "360p" in name or "240p" in name or "144p" in name: return 1
    return 3

def render(entries, epg=True):
    header = f'#EXTM3U url-tvg="{EPG_URL}" x-tvg-url="{EPG_URL}"' if epg else "#EXTM3U"
    lines = [header]
    for entry in entries:
        attrs = entry["attrs"].copy()
        name = base_name(entry["name"])
        if entry["source"] == "Israel" and name in ISRAEL_EPG_IDS:
            attrs["tvg-id"] = ISRAEL_EPG_IDS[name]
        group = (ISRAEL_CHANNELS if entry["source"] == "Israel" else ENGLISH_CHANNELS)[name]
        attrs["group-title"] = GROUP_HE.get(group, group)
        attr_text = " ".join(f'{key}="{str(value).replace(chr(34), chr(39))}"' for key, value in attrs.items() if value)
        lines.append(f'#EXTINF:-1 {attr_text},{entry["name"]}')
        lines.extend(entry.get("options", []))
        lines.append(entry["url"])
    return "\n".join(lines) + "\n"

def dedupe(entries):
    seen, result = set(), []
    for entry in entries:
        key = (entry["attrs"].get("tvg-id") or entry["name"].lower(), entry["url"])
        if key not in seen:
            seen.add(key)
            result.append(entry)
    return result

def cap_groups(entries):
    # Keep all variants until after probing, so a dead first URL does not
    # hide a working alternate stream.
    return entries

def curated_key(entry):
    name = base_name(entry["name"])
    aliases = {
        "Sky News HD": "Sky News",
        "NBC News Now": "NBC News NOW",
        "Reuters": "Reuters TV",
        "Just for Laughs GAGS": "Just for Laughs Gags",
        "Anger Management Channel": "Anger Management",
        "Rakuten TV Family Movies Finland": "Rakuten TV Family Movies UK",
        "National Geographic Wild HD East": "National Geographic Wild",
        "MythBusters": "Mythbusters",
        "Pluto TV Sci-Fi (Germany) GB": "Pluto TV Sci-Fi (United States) CA",
    }
    return aliases.get(name, name)

def choose_one_per_channel(entries):
    seen, result = set(), []
    for entry in entries:
        key = curated_key(entry)
        if key not in seen:
            seen.add(key)
            result.append(entry)
    return result

def main():
    entries = []
    for source, url in CFG["sources"].items():
        entries.extend(parse(get(url).decode("utf-8", "replace"), source))
    candidates = cap_groups(dedupe([entry for entry in entries if wanted(entry)]))
    israel = [entry for entry in candidates if entry["source"] == "Israel"]
    english = sorted([entry for entry in candidates if entry["source"] != "Israel"], key=quality, reverse=True)
    with cf.ThreadPoolExecutor(max_workers=CFG["probe_workers"]) as pool:
        checked = list(pool.map(probe, english))
    active = [entry for entry, ok in checked if ok]
    final = choose_one_per_channel(dedupe(israel + active))
    chosen_urls = {entry["url"] for entry in final}
    backup = choose_one_per_channel([entry for entry in active if entry["url"] not in chosen_urls])
    (ROOT / "playlist.m3u").write_text(render(final), encoding="utf-8")
    (ROOT / "playlist-backup.m3u").write_text(render(backup), encoding="utf-8")
    active_keys = {curated_key(e) for e in final}
    requested = {curated_key({"name": n}) for n in ISRAEL_CHANNELS | ENGLISH_CHANNELS}
    status = {
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "israel_channels": sum(e["source"] == "Israel" for e in final),
        "english_checked": len(english),
        "english_active": sum(e["source"] != "Israel" for e in final),
        "total": len(final),
        "backup_streams": len(backup),
        "missing_channels": sorted(requested - active_keys),
    }
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()

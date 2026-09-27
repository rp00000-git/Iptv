#!/usr/bin/env python3
import concurrent.futures as cf
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
UA = "Mozilla/5.0 (compatible; Personal-IPTV-Builder/1.0)"
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
EPG_URL = "https://raw.githubusercontent.com/rp00000-git/Iptv/main/epg.xml.gz"
CURRENT_PLAYLIST_URL = "https://raw.githubusercontent.com/rp00000-git/Iptv/main/playlist.m3u"
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
    "Kan 11": "ישראל",
    "Keshet 12": "ישראל",
    "Channel 13 (Israel)": "ישראל",
    "Now 14": "ישראל",
    "Channel 24 (Israel)": "ישראל",
    "Food Channel": "ישראל",
    "Good Life": "ישראל",
    "Vacation Channel": "ישראל",
    "Kabbalah for the People Israel": "ישראל",
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
    "MovieSphere UK": "English | Movies",
    "Rakuten TV Action Movies UK": "English | Movies",
    "Rakuten TV Top Movies UK": "English | Movies",
    "Rakuten TV Drama Movies Finland": "English | Movies",
    "Hallmark Movies & More": "English | Movies",
    "OuterSphere": "English | Movies",
    "Ebony TV by Lionsgate": "English | Movies",
    "Gravitas Movies": "English | Movies",
    "Genesis Science Network": "English | Science & Sci-Fi",
    "Space Live powered by sen": "English | Science & Sci-Fi",
    "Terra Mater WILD English": "English | Nature",
    "Love Nature": "English | Nature",
    "Adventure Earth": "English | Nature",
    "WaterBear": "English | Nature",
    "Wonder": "English | Nature",
    "The Pet Collective UK": "English | Nature",
    "Documentary+ International": "English | Documentary",
    "CGTN Documentary": "English | Documentary",
    "CNA Originals": "English | Documentary",
    "History Hit": "English | History",
    "Autentic History": "English | History",
    "Tastemade UK": "English | Travel & Food",
    "INTRAVEL": "English | Travel & Food",
    "Autentic Travel": "English | Travel & Food",
    "bon appetit": "English | Travel & Food",
    "Gusto TV": "English | Travel & Food",
    "Dry Bar Comedy+": "English | Comedy",
    "Universal Comedy": "English | Comedy",
    "HappyKids": "English | Family",
    "Dove Channel": "English | Family",
    "Motorvision": "English | Cars & Lifestyle",
    "PowerNation TV": "English | Cars & Lifestyle",
    "Canal Motor": "English | Cars & Lifestyle",
    "Fun Roads": "English | Cars & Lifestyle",
    "NBC LX Home": "English | Cars & Lifestyle",
}

GROUP_HE = {
    "English | News": "חדשות",
    "English | Movies": "סרטים, בידור ומשפחה",
    "English | Comedy": "סרטים, בידור ומשפחה",
    "English | Family": "סרטים, בידור ומשפחה",
    "English | Science & Sci-Fi": "מדע, טבע ולייף סטייל",
    "English | Nature": "מדע, טבע ולייף סטייל",
    "English | History": "מדע, טבע ולייף סטייל",
    "English | Documentary": "מדע, טבע ולייף סטייל",
    "English | Travel & Food": "מדע, טבע ולייף סטייל",
    "English | Cars & Lifestyle": "מדע, טבע ולייף סטייל",
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

def request_bytes(url, headers, limit=65536):
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=CFG["probe_timeout_seconds"]) as response:
        if not 200 <= getattr(response, "status", 200) < 400:
            raise OSError(f"HTTP {response.status}")
        return response.read(limit), response.geturl()

def probe_hls(url, headers):
    """Verify the manifest, its first variant and one actual media segment."""
    for _ in range(3):
        data, resolved_url = request_bytes(url, headers)
        if b"#EXTM3U" not in data:
            return False
        text = data.decode("utf-8", "replace")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        uris = [line for line in lines if not line.startswith("#")]
        if not uris:
            return False
        next_url = urllib.parse.urljoin(resolved_url, uris[0])
        # A master playlist points to another m3u8; a media playlist points
        # directly to a video segment. Follow either form safely.
        if ".m3u8" in next_url.lower() or "#EXT-X-STREAM-INF" in text:
            url = next_url
            continue
        segment, _ = request_bytes(next_url, headers, limit=2048)
        return bool(segment)
    return False

def probe(entry):
    headers = {"User-Agent": UA, "Range": "bytes=0-32767"}
    for opt in entry.get("options", []):
        low = opt.lower()
        if "http-user-agent=" in low:
            headers["User-Agent"] = opt.split("=", 1)[1]
        elif "http-referrer=" in low:
            headers["Referer"] = opt.split("=", 1)[1]
    try:
        if ".m3u8" in entry["url"].lower():
            return entry, probe_hls(entry["url"], headers)
        data, _ = request_bytes(entry["url"], headers, limit=4096)
        return entry, bool(data)
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
        "InWild": "INWILD",
        "InTravel": "INTRAVEL",
        "Journy": "JOURNY TV",
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
    # Keep the last known URLs as fallbacks. This is especially important for
    # Israeli streams, which can appear offline to a GitHub runner abroad.
    if (ROOT / "playlist.m3u").exists():
        previous = parse((ROOT / "playlist.m3u").read_text(encoding="utf-8"), "English")
        for entry in previous:
            if base_name(entry["name"]) in ISRAEL_CHANNELS:
                entry["source"] = "Israel"
        entries.extend(previous)
    try:
        previous_remote = parse(get(CURRENT_PLAYLIST_URL).decode("utf-8", "replace"), "English")
        for entry in previous_remote:
            if base_name(entry["name"]) in ISRAEL_CHANNELS:
                entry["source"] = "Israel"
        entries.extend(previous_remote)
    except Exception:
        pass
    for source, url in CFG["sources"].items():
        entries.extend(parse(get(url).decode("utf-8", "replace"), source))
    candidates = cap_groups(dedupe([entry for entry in entries if wanted(entry)]))
    playlist_order = [
        "Kan 11", "Keshet 12", "Channel 13 (Israel)", "Now 14",
        "Channel 24 (Israel)", "Food Channel", "Good Life",
        "Vacation Channel", "Kabbalah for the People Israel",
        "Al Jazeera English", "BBC News", "Bloomberg Originals", "DW English",
        "France 24 English", "NBC News NOW", "Reuters TV", "Sky News",
        "ABC News", "CBS News 24/7", "Euronews English", "Fox News Channel",
        "MovieSphere UK", "Rakuten TV Action Movies UK", "Rakuten TV Top Movies UK",
        "Rakuten TV Drama Movies Finland", "Hallmark Movies & More", "OuterSphere",
        "Ebony TV by Lionsgate", "Gravitas Movies", "Genesis Science Network",
        "Space Live powered by sen", "Terra Mater WILD English", "Love Nature",
        "Adventure Earth", "WaterBear", "Wonder", "The Pet Collective UK",
        "Documentary+ International", "CGTN Documentary", "CNA Originals",
        "History Hit", "Autentic History", "Tastemade UK", "INTRAVEL",
        "Autentic Travel", "bon appetit", "Gusto TV", "Dry Bar Comedy+",
        "Universal Comedy", "HappyKids", "Dove Channel", "Motorvision",
        "PowerNation TV", "Canal Motor", "Fun Roads", "NBC LX Home",
    ]
    order_rank = {name: index for index, name in enumerate(playlist_order)}
    ordered = sorted(
        candidates,
        key=lambda entry: (order_rank.get(curated_key(entry), 9999), -quality(entry)),
    )
    with cf.ThreadPoolExecutor(max_workers=CFG["probe_workers"]) as pool:
        checked = list(pool.map(probe, ordered))
    active = [entry for entry, ok in checked if ok]
    active_by_key = defaultdict(list)
    fallback_by_key = defaultdict(list)
    for entry in active:
        active_by_key[curated_key(entry)].append(entry)
    for entry in ordered:
        fallback_by_key[curated_key(entry)].append(entry)
    final = []
    for name in playlist_order:
        options = active_by_key.get(name) or fallback_by_key.get(name) or []
        if options:
            final.append(options[0])
    final = dedupe(final)
    chosen_urls = {entry["url"] for entry in final}
    backup = choose_one_per_channel([entry for entry in active if entry["url"] not in chosen_urls])
    (ROOT / "playlist.m3u").write_text(render(final), encoding="utf-8")
    (ROOT / "playlist-backup.m3u").write_text(render(backup), encoding="utf-8")
    active_keys = {curated_key(e) for e in final}
    requested = {curated_key({"name": n}) for n in ISRAEL_CHANNELS | ENGLISH_CHANNELS}
    status = {
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "israel_channels": sum(e["source"] == "Israel" for e in final),
        "streams_checked": len(ordered),
        "english_active": sum(e["source"] != "Israel" for e in final),
        "total": len(final),
        "backup_streams": len(backup),
        "missing_channels": sorted(requested - active_keys),
    }
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    main()

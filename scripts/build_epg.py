#!/usr/bin/env python3
import copy
import gzip
import io
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_IL1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_US2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_IE1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_UK1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_DE1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_FR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_AU1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_RAKUTEN1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_PLEX1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_WHALETVPLUS1.xml.gz",
]
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')

ALIASES = {
    "al jazeera english": ["al jazeera english", "al jazeera", "al jazeera hd"],
    "dw english": ["dw"],
    "france 24 english": ["france 24 engl", "france 24", "france 24 hd"],
    "abc news": ["abc news sydney"],
    "euronews english": ["euronews"],
    "fox news channel": ["fox news"],
    "cbs news 24 7": ["cbs news"],
    "nbc news now": ["nbc news now"],
    "bbc earth us": ["bbc earth"],
    "smithsonian channel selects united states": ["smithsonian channel"],
    "pluto tv science united states": ["pluto tv science"],
    "history united states": ["history channel", "history"],
    "amc united states": ["amc"],
    "pbs kids": ["pbs kids"],
    "national geographic wild hd east": ["national geographic wild", "nat geo wild"],
    "moviesphere uk": ["moviesphere"],
    "rakuten tv action movies uk": ["uk action movies rakuten tv"],
    "rakuten tv top movies uk": ["uk top movies rakuten tv"],
    "rakuten tv drama movies finland": ["uk drama movies rakuten tv"],
    "terra mater wild english": ["uk terra mater wild", "terra mater wild"],
    "adventure earth": ["uk adventure earth"],
    "waterbear": ["uk waterbear"],
    "the pet collective uk": ["uk the pet collective", "the pet collective"],
    "documentary international": ["documentary+"],
    "cgtn documentary": ["uk cgtn documentary"],
    "cna originals": ["uk cna originals"],
    "tastemade uk": ["tastemade"],
    "intravel": ["uk intravel", "se intravel", "intravel"],
    "gusto tv": ["uk gusto tv"],
    "dove channel": ["dove"],
    "motorvision": ["motorvision tv"],
    "powernation tv": ["powernation"],
    "nbc lx home": ["lx home streaming"],
}

def norm(value):
    value = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", value.lower())
    return re.sub(r"[^a-z0-9א-ת]+", " ", value).strip()

def playlist_channels():
    result = []
    for line in (ROOT / "playlist.m3u").read_text(encoding="utf-8").splitlines():
        if not line.startswith("#EXTINF"):
            continue
        attrs = dict(ATTR_RE.findall(line))
        channel_id = attrs.get("tvg-id")
        if channel_id:
            result.append((channel_id, line.rsplit(",", 1)[-1].strip()))
    return result

def open_source(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return gzip.GzipFile(fileobj=urllib.request.urlopen(req, timeout=120))

def main():
    targets = playlist_channels()
    by_id = {channel_id: channel_id for channel_id, _ in targets}
    by_name = {}
    for channel_id, name in targets:
        key = norm(name)
        by_name[key] = channel_id
        for alias in ALIASES.get(key, []):
            by_name[norm(alias)] = channel_id

    out = ET.Element("tv", {"generator-info-name": "Personal IPTV EPG Builder"})
    added_channels, added_programmes = set(), set()

    for url in SOURCES:
        source_map = {}
        with open_source(url) as stream:
            for _, elem in ET.iterparse(stream, events=("end",)):
                if elem.tag == "channel":
                    old_id = elem.get("id", "")
                    names = [norm(x.text or "") for x in elem.findall("display-name")]
                    target_id = by_id.get(old_id)
                    if not target_id:
                        target_id = next((by_name[n] for n in names if n in by_name), None)
                    if target_id:
                        source_map[old_id] = target_id
                        if target_id not in added_channels:
                            cloned = copy.deepcopy(elem)
                            cloned.set("id", target_id)
                            out.append(cloned)
                            added_channels.add(target_id)
                    elem.clear()
                elif elem.tag == "programme":
                    target_id = source_map.get(elem.get("channel", ""))
                    if target_id:
                        key = (target_id, elem.get("start"), elem.get("stop"), (elem.findtext("title") or ""))
                        if key not in added_programmes:
                            cloned = copy.deepcopy(elem)
                            cloned.set("channel", target_id)
                            out.append(cloned)
                            added_programmes.add(key)
                    elem.clear()

    xml = ET.tostring(out, encoding="utf-8", xml_declaration=True)
    (ROOT / "epg.xml").write_bytes(xml)
    with gzip.open(ROOT / "epg.xml.gz", "wb", compresslevel=9) as f:
        f.write(xml)
    print({"epg_channels": len(added_channels), "epg_programmes": len(added_programmes)})

if __name__ == "__main__":
    main()

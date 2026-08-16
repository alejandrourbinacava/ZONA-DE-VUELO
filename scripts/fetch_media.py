#!/usr/bin/env python3
"""Resuelve el shot-list en medios reales:
- kind 'broll' -> clip de Pexels (query en ingles)
- kind 'image' -> imagen de Wikipedia de esa entidad (query)
- kind stat/fact/outro -> sin medio (beat grafico)
Descarga a public/stock/ y escribe public/stock/media.json (planos ordenados por seccion,
conservando 'text' para sincronizar en el render). Requiere PEXELS_KEY."""
import os, sys, json, subprocess, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get("PEXELS_KEY")
OUT = os.path.join(ROOT, "public", "stock")
SHOT = os.path.join(ROOT, "out", "shotlist.json")
UA = "ZonaDeVueloBot/1.0 (canal educativo aviacion)"


def curl_json(url, headers=None):
    cmd = ["curl", "-s", url]
    for h in (headers or []):
        cmd += ["-H", h]
    out = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=60).stdout
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {}


def download(url, dst, ua=False):
    cmd = ["curl", "-s", "-L", url, "-o", dst]
    if ua:
        cmd += ["-A", UA]
    subprocess.run(cmd, timeout=180)
    return os.path.exists(dst) and os.path.getsize(dst) > 1500


def pexels_clip(query, key_prefix, i):
    url = (f"https://api.pexels.com/videos/search?query={query.replace(' ', '%20')}"
           f"&per_page=3&orientation=landscape&size=medium")
    data = curl_json(url, [f"Authorization: {KEY}"])
    for vid in data.get("videos", [])[:1]:
        files = [f for f in vid.get("video_files", []) if f.get("file_type") == "video/mp4"]
        if not files:
            continue
        files.sort(key=lambda f: abs((f.get("height") or 0) - 720))
        fn = f"{key_prefix}_{i}_{vid['id']}.mp4"
        dst = os.path.join(OUT, fn)
        if download(files[0]["link"], dst):
            return {"file": f"stock/{fn}", "duration": vid.get("duration", 0),
                    "credit": vid.get("user", {}).get("name", "")}
    return None


def wiki_image(query, key_prefix, i):
    for lang in ("es", "en"):
        url = (f"https://{lang}.wikipedia.org/w/api.php?action=query&format=json"
               f"&generator=search&gsrsearch={query.replace(' ', '%20')}&gsrlimit=1"
               f"&prop=pageimages&piprop=thumbnail&pithumbsize=1280")
        data = curl_json(url, [f"User-Agent: {UA}"])
        pages = (data.get("query", {}) or {}).get("pages", {}) or {}
        for p in pages.values():
            thumb = (p.get("thumbnail") or {}).get("source")
            if thumb:
                ext = ".png" if ".png" in thumb.lower() else ".jpg"
                fn = f"img_{key_prefix}_{i}{ext}"
                dst = os.path.join(OUT, fn)
                if download(thumb, dst, ua=True):
                    return {"file": f"stock/{fn}"}
    return None


def main():
    if not KEY:
        print("FALTA PEXELS_KEY"); sys.exit(1)
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith((".mp4", ".jpg", ".png")):
            try: os.remove(os.path.join(OUT, f))
            except OSError: pass
    shot = json.load(open(SHOT, encoding="utf-8"))
    out_sections = []
    for sec in shot["sections"]:
        key = sec["key"]
        resolved = []
        for i, sh in enumerate(sec.get("shots", [])):
            kind = sh.get("kind")
            item = {"kind": kind, "text": sh.get("text", "")}
            if kind == "image":
                media = wiki_image(sh.get("query", ""), key, i) \
                        or pexels_clip(sh.get("query", ""), key, i)
                if media and media["file"].endswith((".jpg", ".png")):
                    item.update({"kind": "image", "file": media["file"], "label": sh.get("label", "")})
                elif media:
                    item.update({"kind": "broll", "file": media["file"], "duration": media.get("duration", 0)})
                else:
                    m = pexels_clip("aircraft aviation", key, i)
                    item.update({"kind": "broll", "file": m["file"] if m else "", "duration": m.get("duration", 0) if m else 0})
                print(f"[{key}] {item['kind']:5} {sh.get('query','')[:30]}")
            elif kind == "broll":
                m = pexels_clip(sh.get("query", ""), key, i) or pexels_clip("aircraft aviation clouds", key, i)
                item.update({"file": m["file"] if m else "", "duration": m.get("duration", 0) if m else 0})
                print(f"[{key}] broll {sh.get('query','')[:30]}")
            else:  # stat / fact / outro -> beat grafico
                for k in ("value", "suffix", "label", "color", "kicker", "body", "accent"):
                    if k in sh:
                        item[k] = sh[k]
            resolved.append(item)
        out_sections.append({"key": key, "shots": resolved})
    media = {"sections": out_sections}
    json.dump(media, open(os.path.join(OUT, "media.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    nimg = sum(1 for s in out_sections for sh in s["shots"] if sh["kind"] == "image")
    nvid = sum(1 for s in out_sections for sh in s["shots"] if sh["kind"] == "broll")
    print(f"\nLISTO -> public/stock/media.json  ({nimg} imagenes, {nvid} clips)")


if __name__ == "__main__":
    main()

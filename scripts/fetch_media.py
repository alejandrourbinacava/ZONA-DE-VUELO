#!/usr/bin/env python3
"""Resuelve el shot-list en medios reales, con varias fuentes:
- kind 'broll' -> mejor clip de Pexels (elige el de mas resolucion de varios; opcional Pixabay)
- kind 'image' -> imagen de la entidad: Wikipedia -> Openverse (ambos libres)
- kind 'ai'    -> imagen generada con Google Imagen (si hay GOOGLE_API_KEY), si no cae a stock
- kind stat/fact/outro -> sin medio (beat grafico)
Descarga a public/stock/ y escribe public/stock/media.json. Requiere PEXELS_KEY.
Opcionales: PIXABAY_KEY, GOOGLE_API_KEY."""
import os, sys, json, base64, subprocess, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PEXELS = os.environ.get("PEXELS_KEY")
PIXABAY = os.environ.get("PIXABAY_KEY")
GOOGLE = os.environ.get("GOOGLE_API_KEY")
OUT = os.path.join(ROOT, "public", "stock")
SHOT = os.path.join(ROOT, "out", "shotlist.json")
UA = "ZonaDeVueloBot/1.0 (canal educativo aviacion)"


def curl_json(url, headers=None, data=None):
    cmd = ["curl", "-s", url]
    for h in (headers or []):
        cmd += ["-H", h]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    out = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=90).stdout
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


# ---------- CLIPS ----------
USED = set()   # ids de clips ya usados en este video (para NO repetir)


def best_pexels(query):
    url = (f"https://api.pexels.com/videos/search?query={query.replace(' ', '%20')}"
           f"&per_page=12&orientation=landscape&size=medium")
    data = curl_json(url, [f"Authorization: {PEXELS}"])
    best = None
    for vid in data.get("videos", []):
        vid_id = f"px{vid.get('id')}"
        if vid_id in USED:          # ya usado -> saltar (sin repeticiones)
            continue
        for f in vid.get("video_files", []):
            if f.get("file_type") != "video/mp4":
                continue
            h = f.get("height") or 0
            if h > 1080:            # descarta 4K (pesado y lento de renderizar)
                continue
            if not best or h > best[0]:
                best = (h, f["link"], vid.get("duration", 0), vid.get("user", {}).get("name", ""), vid_id)
    if best:
        USED.add(best[4])
    return best  # (score, link, duration, credit, id) | None


def best_pixabay(query):
    if not PIXABAY:
        return None
    url = f"https://pixabay.com/api/videos/?key={PIXABAY}&q={query.replace(' ', '+')}&per_page=8"
    data = curl_json(url)
    for hit in data.get("hits", []):
        vid_id = f"pb{hit.get('id')}"
        if vid_id in USED:
            continue
        v = (hit.get("videos", {}) or {})
        f = v.get("large") or v.get("medium")
        if f and f.get("url"):
            USED.add(vid_id)
            return (f.get("height", 0), f["url"], hit.get("duration", 0), hit.get("user", ""), vid_id)
    return None


def get_clip(query, prefix, i):
    cand = best_pexels(query) or best_pixabay(query)
    if not cand:
        return None
    fn = f"{prefix}_{i}.mp4"
    dst = os.path.join(OUT, fn)
    if download(cand[1], dst):
        return {"file": f"stock/{fn}", "duration": cand[2], "credit": cand[3]}
    return None


# ---------- IMAGENES DE ENTIDAD ----------
def wiki_image(query, prefix, i):
    for lang in ("es", "en"):
        url = (f"https://{lang}.wikipedia.org/w/api.php?action=query&format=json"
               f"&generator=search&gsrsearch={query.replace(' ', '%20')}&gsrlimit=1"
               f"&prop=pageimages&piprop=thumbnail&pithumbsize=1280")
        data = curl_json(url, [f"User-Agent: {UA}"])
        for p in ((data.get("query", {}) or {}).get("pages", {}) or {}).values():
            thumb = (p.get("thumbnail") or {}).get("source")
            if thumb:
                ext = ".png" if ".png" in thumb.lower() else ".jpg"
                dst = os.path.join(OUT, f"img_{prefix}_{i}{ext}")
                if download(thumb, dst, ua=True) and os.path.getsize(dst) >= 8000:
                    return {"file": f"stock/img_{prefix}_{i}{ext}"}
                if os.path.exists(dst):
                    os.remove(dst)
    return None


def openverse_image(query, prefix, i):
    url = (f"https://api.openverse.org/v1/images/?q={query.replace(' ', '%20')}"
           f"&license_type=commercial&page_size=4")
    data = curl_json(url, [f"User-Agent: {UA}"])
    for r in data.get("results", []):
        src = r.get("url") or r.get("thumbnail")
        if not src:
            continue
        dst = os.path.join(OUT, f"ov_{prefix}_{i}.jpg")
        if download(src, dst, ua=True) and os.path.getsize(dst) >= 8000:
            return {"file": f"stock/ov_{prefix}_{i}.jpg"}
        if os.path.exists(dst):
            os.remove(dst)
    return None


def get_entity_image(query, prefix, i):
    return wiki_image(query, prefix, i) or openverse_image(query, prefix, i)


# ---------- IMAGEN IA (Google Imagen) ----------
def ai_image(prompt, prefix, i):
    # Pollinations (Flux): generacion de imagen IA GRATIS, sin key ni facturacion.
    full = prompt + ", cinematic, photorealistic, aviation documentary style, dramatic, high detail"
    q = urllib.parse.quote(full, safe="")
    url = (f"https://image.pollinations.ai/prompt/{q}"
           f"?width=1280&height=720&nologo=true&model=flux&seed={abs(hash(prompt)) % 100000}")
    dst = os.path.join(OUT, f"ai_{prefix}_{i}.jpg")
    if download(url, dst) and os.path.getsize(dst) >= 8000:
        return {"file": f"stock/ai_{prefix}_{i}.jpg"}
    return None


def decodable(rel):
    p = os.path.join(ROOT, "public", rel)
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width", "-of", "csv=p=0", p],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip().isdigit()


def main():
    if not PEXELS:
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
                m = get_entity_image(sh.get("query", ""), key, i)
                if m:
                    item.update({"kind": "image", "file": m["file"], "label": sh.get("label", "")})
                else:
                    c = get_clip(sh.get("query", ""), key, i) or get_clip("aviation aircraft", key, i)
                    item.update({"kind": "broll", "file": c["file"] if c else "", "duration": c.get("duration", 0) if c else 0})
                print(f"[{key}] {item['kind']:5} {sh.get('query','')[:28]}")
            elif kind == "ai":
                m = ai_image(sh.get("query", "") or sh.get("text", ""), key, i)
                if m:
                    item.update({"kind": "image", "file": m["file"], "label": sh.get("label", "")})
                else:  # sin key de Google -> cae a stock
                    c = get_clip(sh.get("query", ""), key, i) or get_clip("aviation", key, i)
                    item.update({"kind": "broll", "file": c["file"] if c else "", "duration": c.get("duration", 0) if c else 0})
                print(f"[{key}] {item['kind']:5} (ai) {sh.get('query','')[:24]}")
            elif kind == "broll":
                c = get_clip(sh.get("query", ""), key, i) or get_clip("aircraft aviation clouds", key, i)
                item.update({"file": c["file"] if c else "", "duration": c.get("duration", 0) if c else 0})
                print(f"[{key}] broll {sh.get('query','')[:28]}")
            else:
                for k in ("value", "suffix", "label", "color", "kicker", "body", "accent"):
                    if k in sh:
                        item[k] = sh[k]
            resolved.append(item)
        out_sections.append({"key": key, "shots": resolved})
    # validacion final con ffprobe
    for sec in out_sections:
        for sh in sec["shots"]:
            if sh.get("file") and not decodable(sh["file"]):
                print("  ! medio corrupto neutralizado:", sh["file"]); sh["file"] = ""
    json.dump({"sections": out_sections}, open(os.path.join(OUT, "media.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    nimg = sum(1 for s in out_sections for sh in s["shots"] if sh["kind"] == "image")
    nvid = sum(1 for s in out_sections for sh in s["shots"] if sh["kind"] == "broll")
    print(f"\nLISTO -> media.json  ({nimg} imagenes, {nvid} clips) | Pixabay:{'si' if PIXABAY else 'no'} | IA:Pollinations(gratis)")


if __name__ == "__main__":
    main()

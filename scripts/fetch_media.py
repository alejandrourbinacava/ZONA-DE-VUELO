#!/usr/bin/env python3
"""Resuelve el shot-list en medios reales, con varias fuentes:
- kind 'broll' -> mejor clip de Pexels (elige el de mas resolucion de varios; opcional Pixabay)
- kind 'image' -> imagen de la entidad: Wikipedia -> Openverse (ambos libres)
- kind 'ai'    -> imagen generada con Google Imagen (si hay GOOGLE_API_KEY), si no cae a stock
- kind stat/fact/outro -> sin medio (beat grafico)
Descarga a public/stock/ y escribe public/stock/media.json. Requiere PEXELS_KEY.
Opcionales: PIXABAY_KEY, GOOGLE_API_KEY."""
import os, sys, json, base64, time, tempfile, subprocess, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PEXELS = os.environ.get("PEXELS_KEY")
PIXABAY = os.environ.get("PIXABAY_KEY")
GOOGLE = os.environ.get("GOOGLE_API_KEY")
AI33_KEY = os.environ.get("AI33_API_KEY")
AI33_BASE = os.environ.get("AI33_BASE", "https://api.ai33.pro")
AI33_MODEL = "bytedance-seedream-4"     # 16:9 1080p, buena calidad/coste (~800 cr/imagen)
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
USED = set()   # ids de clips ya usados (este video + los de videos anteriores) para NO repetir
USED_FILE = os.path.join(ROOT, "queue", "used_clips.json")   # dedup GLOBAL entre videos


def load_used():
    try:
        for x in json.load(open(USED_FILE, encoding="utf-8")):
            USED.add(x)
    except (OSError, json.JSONDecodeError):
        pass


def save_used():
    try:
        os.makedirs(os.path.dirname(USED_FILE), exist_ok=True)
        json.dump(sorted(USED), open(USED_FILE, "w", encoding="utf-8"))
    except OSError:
        pass


def best_pexels(query):
    url = (f"https://api.pexels.com/videos/search?query={query.replace(' ', '%20')}"
           f"&per_page=30&orientation=landscape&size=medium")   # mas candidatos = mas variedad (anti-repeticion)
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
    # prueba hasta 2 candidatos: si el 1o descarga corrupto, va al siguiente (evita huecos)
    for cand in (best_pexels(query), best_pixabay(query)):
        if not cand:
            continue
        fn = f"{prefix}_{i}.mp4"
        dst = os.path.join(OUT, fn)
        if download(cand[1], dst) and decodable(f"stock/{fn}"):
            return {"file": f"stock/{fn}", "duration": cand[2], "credit": cand[3]}
        if os.path.exists(dst):
            os.remove(dst)
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


def stock_photo(query, prefix, i):
    """Foto REAL de stock (Pexels) — respaldo cuando no hay clip. NUNCA IA."""
    url = (f"https://api.pexels.com/v1/search?query={query.replace(' ', '%20')}"
           f"&per_page=20&orientation=landscape&size=large")
    data = curl_json(url, [f"Authorization: {PEXELS}"])
    for p in data.get("photos", []):
        pid = f"pxph{p.get('id')}"
        if pid in USED:
            continue
        src = p.get("src") or {}
        u = src.get("large2x") or src.get("large") or src.get("original")
        if not u:
            continue
        dst = os.path.join(OUT, f"ph_{prefix}_{i}.jpg")
        if download(u, dst) and os.path.getsize(dst) >= 20000:
            w, h = img_dims(dst)
            if w >= 1000 and h >= 560:
                USED.add(pid)
                return {"file": f"stock/ph_{prefix}_{i}.jpg"}
        if os.path.exists(dst):
            os.remove(dst)
    return None


# ---------- IMAGEN IA (Pollinations / Flux, gratis) ----------
def img_dims(path):
    """(ancho, alto) de una imagen via ffprobe, o (0,0) si no se puede leer."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", path],
                       capture_output=True, text=True)
    try:
        w, h = r.stdout.strip().split("x")
        return int(w), int(h)
    except (ValueError, AttributeError):
        return 0, 0


def _ai33_prompt(prompt):
    return (prompt + ", aviation and sky context, cinematic film still, photorealistic, "
            "dramatic natural lighting, sharp focus, ultra detailed, professional color grading, 16:9")


def ai33_image(prompt, prefix, i):
    """Genera imagen IA con ai33.pro (seedream, 16:9 1080p). Calidad muy superior a Pollinations."""
    if not AI33_KEY:
        return None
    tf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    tf.write(_ai33_prompt(prompt)); tf.close()
    try:
        out = subprocess.run(
            ["curl", "-s", "-X", "POST", f"{AI33_BASE}/v1i/task/generate-image",
             "-H", f"xi-api-key: {AI33_KEY}",
             "-F", f"prompt=<{tf.name}",
             "-F", f"model_id={AI33_MODEL}",
             "-F", "generations_count=1",
             "-F", 'model_parameters={"aspect_ratio":"16:9","resolution":"1080p"}'],
            capture_output=True, encoding="utf-8", errors="replace", timeout=90).stdout
    finally:
        try: os.remove(tf.name)
        except OSError: pass
    try:
        tid = json.loads(out).get("task_id")
    except json.JSONDecodeError:
        tid = None
    if not tid:
        print("   (ai33 sin task_id:", (out or "")[:100], ")"); return None
    for _ in range(60):   # hasta ~3 min
        time.sleep(3)
        t = curl_json(f"{AI33_BASE}/v1/task/{tid}", [f"xi-api-key: {AI33_KEY}"])
        st = t.get("status")
        if st == "done":
            imgs = (t.get("metadata") or {}).get("result_images") or []
            url = imgs[0].get("imageUrl") if imgs else None
            if not url:
                return None
            dst = os.path.join(OUT, f"ai_{prefix}_{i}.jpg")
            if download(url, dst) and os.path.getsize(dst) >= 30000:
                w, h = img_dims(dst)
                if w >= 1200 and h >= 600:
                    return {"file": f"stock/ai_{prefix}_{i}.jpg"}
            return None
        if st == "error":
            print("   (ai33 error:", json.dumps(t)[:120], ")"); return None
    return None


# ---------- CLIP DE VIDEO IA (ai33) — para lo que el stock no tiene, con aspecto REAL ----------
AI33_VIDEO_PATH = os.environ.get("AI33_VIDEO_PATH", "/v1v/task/generate-video")
AI33_VIDEO_MODEL = os.environ.get("AI33_VIDEO_MODEL", "kling-2.5")
_VIDEO_OK = None   # cache: ¿la cuenta tiene plan de video activo?


def video_available():
    """Comprueba UNA vez si la cuenta ai33 puede generar video (evita 50 llamadas inutiles)."""
    global _VIDEO_OK
    if _VIDEO_OK is None:
        if not AI33_KEY:
            _VIDEO_OK = False
        else:
            r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                f"{AI33_BASE}/v1v/models", "-H", f"xi-api-key: {AI33_KEY}"],
                               capture_output=True, text=True).stdout.strip()
            _VIDEO_OK = (r == "200")
            print(f"   [ai33 video: {'DISPONIBLE' if _VIDEO_OK else 'no activado (usare stock)'}]")
    return _VIDEO_OK


def ai33_video(prompt, prefix, i):
    """Genera un CLIP DE VIDEO IA fotorealista con ai33 (cuando la cuenta tenga plan de video)."""
    if not video_available():
        return None
    full = (prompt + ", photorealistic real footage, cinematic, natural lighting, 16:9")
    tf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    tf.write(full); tf.close()
    try:
        out = subprocess.run(
            ["curl", "-s", "-X", "POST", f"{AI33_BASE}{AI33_VIDEO_PATH}", "-H", f"xi-api-key: {AI33_KEY}",
             "-F", f"prompt=<{tf.name}", "-F", f"model_id={AI33_VIDEO_MODEL}",
             "-F", "duration=5", "-F", 'model_parameters={"aspect_ratio":"16:9","resolution":"1080p"}'],
            capture_output=True, encoding="utf-8", errors="replace", timeout=90).stdout
    finally:
        try: os.remove(tf.name)
        except OSError: pass
    try:
        tid = json.loads(out).get("task_id")
    except json.JSONDecodeError:
        tid = None
    if not tid:
        return None
    for _ in range(120):   # el video tarda mas (hasta ~6 min)
        time.sleep(3)
        t = curl_json(f"{AI33_BASE}/v1/task/{tid}", [f"xi-api-key: {AI33_KEY}"])
        st = t.get("status")
        if st == "done":
            md = t.get("metadata") or {}
            url = md.get("video_url")
            if not url:
                vids = md.get("result_videos") or []
                url = (vids[0].get("videoUrl") or vids[0].get("url")) if vids else None
            if not url:
                return None
            dst = os.path.join(OUT, f"aiv_{prefix}_{i}.mp4")
            if download(url, dst) and decodable(f"stock/aiv_{prefix}_{i}.mp4"):
                return {"file": f"stock/aiv_{prefix}_{i}.mp4", "duration": 5}
            return None
        if st == "error":
            return None
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
    load_used()   # cargar ids de clips usados en videos anteriores (dedup global)
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
            q = sh.get("query", "") or sh.get("text", "")
            item = {"kind": kind, "text": sh.get("text", "")}

            def as_image(m, src):
                item.update({"kind": "image", "file": m["file"], "label": sh.get("label", ""), "source": src})

            def as_clip(c, src):
                item.update({"kind": "broll", "file": c["file"] if c else "", "source": src,
                             "duration": c.get("duration", 0) if c else 0})

            def as_photo(m):   # foto REAL de stock, a pantalla completa con movimiento (no tarjeta de entidad)
                item.update({"kind": "image", "file": m["file"], "label": "", "source": "FOTO-STOCK"})

            if kind == "image":
                # entidad con nombre -> foto de la entidad (tarjeta premium); si no, clip real; si no, foto real
                m = get_entity_image(sh.get("query", ""), key, i)
                if m:
                    as_image(m, "FOTO")
                else:
                    c = get_clip(q, key, i)
                    p = None if c else stock_photo(q, key, i)
                    as_clip(c, "CLIP") if c else (as_photo(p) if p else as_clip(None, ""))
            elif kind == "ai":
                # metafora/concepto: clip video IA si el plan esta activo; si no, CLIP real; si no, FOTO real
                v = ai33_video(q, key, i)
                if v:
                    as_clip(v, "CLIP-IA")
                else:
                    c = get_clip(q, key, i)
                    p = None if c else stock_photo(q, key, i)
                    as_clip(c, "CLIP") if c else (as_photo(p) if p else as_clip(None, ""))
            elif kind == "broll":
                c = get_clip(sh.get("query", ""), key, i)                  # 1) clip real que describe
                if c:
                    as_clip(c, "CLIP")
                else:
                    v = ai33_video(q, key, i)                               # 2) clip video IA (si activo)
                    if v:
                        as_clip(v, "CLIP-IA")
                    else:
                        p = stock_photo(q, key, i)                          # 3) foto REAL (nunca IA)
                        as_photo(p) if p else as_clip(None, "")             # 4) nada -> tarjeta de texto
            else:
                item["source"] = "GRAFICO"
                for k in ("value", "suffix", "label", "color", "kicker", "body", "accent"):
                    if k in sh:
                        item[k] = sh[k]
            print(f"[{key}] {item.get('source','?'):7} {sh.get('query', sh.get('text',''))[:34]}")
            resolved.append(item)
        out_sections.append({"key": key, "shots": resolved})
    # validacion final con ffprobe: medio corrupto -> re-buscar otro clip (o video IA); nunca imagen IA
    for si, sec in enumerate(out_sections):
        for sj, sh in enumerate(sec["shots"]):
            if sh.get("file") and not decodable(sh["file"]):
                print("  ! medio corrupto, re-buscando clip:", sh["file"])
                repl = get_clip(sh.get("text", "") or "aviation aircraft", sec["key"], f"fix_{si}_{sj}") \
                    or ai33_video(sh.get("text", "") or "aviation", sec["key"], f"fix_{si}_{sj}")
                if repl:
                    sh.update({"kind": "broll", "file": repl["file"], "source": "CLIP",
                               "duration": repl.get("duration", 0)})
                else:
                    sh["file"] = ""
    save_used()   # persistir clips usados para NO repetirlos en futuros videos
    json.dump({"sections": out_sections}, open(os.path.join(OUT, "media.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    nfoto = sum(1 for s in out_sections for sh in s["shots"] if sh.get("source") == "FOTO")
    nclip = sum(1 for s in out_sections for sh in s["shots"] if sh["kind"] == "broll")
    print(f"\nLISTO -> media.json  ({nclip} clips, {nfoto} fotos de entidad) | dedup global: {len(USED)} ids usados")


if __name__ == "__main__":
    main()

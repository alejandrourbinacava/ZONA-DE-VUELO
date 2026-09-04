#!/usr/bin/env python3
"""Resuelve el shot-list en medios reales, con varias fuentes:
- kind 'broll' -> mejor clip de Pexels (elige el de mas resolucion de varios; opcional Pixabay)
- kind 'image' -> imagen de la entidad: Wikipedia -> Openverse (ambos libres)
- kind 'ai'    -> imagen generada con Google Imagen (si hay GOOGLE_API_KEY), si no cae a stock
- kind stat/fact/outro -> sin medio (beat grafico)
Descarga a public/stock/ y escribe public/stock/media.json. Requiere PEXELS_KEY.
Opcionales: PIXABAY_KEY, GOOGLE_API_KEY."""
import os, sys, json, base64, time, tempfile, subprocess, urllib.parse, io, re

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
    # --max-time hace que CURL aborte solo; el try/except evita que un clip lento tumbe todo el fetch
    cmd = ["curl", "-s", "-L", "--max-time", "120", "--connect-timeout", "20", url, "-o", dst]
    if ua:
        cmd += ["-A", UA]
    try:
        subprocess.run(cmd, timeout=150)
    except subprocess.TimeoutExpired:
        try: os.remove(dst)
        except OSError: pass
        return False
    return os.path.exists(dst) and os.path.getsize(dst) > 1500


# ---------- CLIPS ----------
# Terminos que NUNCA salen en contenido de aviacion: si el slug del clip/foto los contiene, se descarta.
BLOCK = ("covid", "coronavirus", "pandemic", "face-mask", "protest", "riot", "election",
         "wedding", "funeral", "birthday", "-party", "dancing", "food", "cooking", "recipe",
         "makeup", "fashion-model", "baby", "puppy", "kitten", "gym", "yoga", "influencer",
         # transporte terrestre: casi nunca encaja en aviacion (los "-car-" evitan pillar cargo/aircraft)
         "-car-", "-cars-", "sports-car", "highway", "traffic", "driving", "motorway",
         "road-trip", "-vehicle", "steering-wheel", "-truck", "motorcycle", "bicycle", "train-",
         # personas en escenas domesticas que se cuelan por analogias (bañera, etc.)
         "bath", "bathing", "shower", "-child", "children", "toddler", "-kid", "swimming-pool")


def off_topic(url):
    u = (url or "").lower()
    return any(b in u for b in BLOCK)


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


# ---------- REVISOR IA por VISION: Gemini (Google). Reemplaza a Anthropic (retirado por coste). ----------
GEMINI_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")   # 'latest' no se deprecia


def _gemini_vision(prompt, b64_images, max_tokens=250):
    """Llama a Gemini (vision) con texto + imagenes base64. Cuerpo por fichero (-d @) para no reventar el
    limite de linea de comandos. thinkingBudget=0 (si no, el modelo gasta los tokens 'pensando' y no responde).
    Devuelve el TEXTO de respuesta, o None si falla."""
    if not GEMINI_KEY:
        return None
    parts = [{"text": prompt}]
    for b in b64_images:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b}})
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens,
                                 "thinkingConfig": {"thinkingBudget": 0}}}
    tf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(body, tf); tf.close()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
    try:
        for intento in range(4):   # 503 por alta demanda -> reintento breve
            out = subprocess.run(["curl", "-s", url, "-H", "content-type: application/json", "-d", "@" + tf.name],
                                 capture_output=True, encoding="utf-8", errors="replace", timeout=90).stdout
            try:
                d = json.loads(out)
            except json.JSONDecodeError:
                d = None
            if d and "candidates" in d:
                return "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
            code = (d or {}).get("error", {}).get("code")
            if code not in (429, 500, 503) and d is not None:
                return None                    # error no transitorio (p.ej. key mala) -> no insistir
            time.sleep(4 * (intento + 1))
        return None
    finally:
        try: os.remove(tf.name)
        except OSError: pass


def _img_to_b64(src, is_url, max_px=440):
    """Abre (path relativo a public/) o descarga (url) una imagen, la reduce y la devuelve en base64 JPEG."""
    try:
        from PIL import Image
        if is_url:
            raw = subprocess.run(["curl", "-s", "-L", src], capture_output=True, timeout=60).stdout
            im = Image.open(io.BytesIO(raw)).convert("RGB")
        else:
            im = Image.open(os.path.join(ROOT, "public", src)).convert("RGB")
        im.thumbnail((max_px, max_px))
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=82)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def vision_match(narration, image_urls):
    """REVISION IA (Gemini): mira las miniaturas candidatas y devuelve el NUMERO (1-based) de la que
    de verdad ilustra la narracion en un canal de AVIACION, o 0 si NINGUNA encaja.
    Devuelve None si no hay clave/imagenes o si la llamada falla (=> el caller usa la 1a)."""
    if not GEMINI_KEY or not image_urls:
        return None
    b64s = []
    for u in image_urls:
        if "pexels.com" in u:            # miniatura pequeña -> revision mas barata/rapida
            u = u.split("?")[0] + "?auto=compress&w=420&h=236&fit=crop"
        b = _img_to_b64(u, True)
        if not b:
            return None                  # si falla una descarga, no arriesgamos una eleccion sesgada
        b64s.append(b)
    prompt = ("Eres el revisor de un canal de AVIACION. La narracion en este momento dice:\n"
              f"\"{narration}\"\n\n"
              f"Te paso {len(b64s)} miniaturas candidatas EN ORDEN (la 1a imagen es el Clip 1, la 2a el Clip 2...). "
              "Elige el NUMERO de la que MEJOR ilustra lo que dice la frase en un canal de AVIACION. Criterio:\n"
              "- Prefiere la que muestre el sujeto de la frase; si no la hay, vale una escena de aviacion CLARAMENTE "
              "relacionada con la frase (avion, cabina, motor, aeropuerto, cielo...).\n"
              "- RECHAZA (nunca elijas) lo que NO sea de aviacion o no pegue: coches/carreteras, casas, puertas de "
              "casa, personas aleatorias o de espaldas, ninos, campos, objetos domesticos, cosas sin relacion.\n"
              "- Si TODAS son de fuera de tema o no pegan nada, responde 0.\n"
              f"Responde SOLO con un numero del 0 al {len(b64s)}.")
    txt = _gemini_vision(prompt, b64s, max_tokens=60)
    if not txt:
        return None
    digits = "".join(ch for ch in txt if ch.isdigit())
    return int(digits) if digits else None


def vision_locate(local_rel, labels, narration):
    """Mira la imagen YA descargada y devuelve, por cada etiqueta, DONDE esta esa parte (x,y en 0..1)
    o None si NO es visible. Sirve para colocar las flechas con logica. Devuelve lista alineada con
    `labels` (cada elem {x,y} o None), o None si la imagen no vale / falla."""
    if not GEMINI_KEY or not labels:
        return None
    b64 = _img_to_b64(local_rel, False, max_px=720)
    if not b64:
        return None
    labs = "\n".join(f"{j + 1}) {l}" for j, l in enumerate(labels))
    prompt = ("Canal de aviacion. Esta imagen se usara para SEÑALAR partes con flechas mientras se narra:\n"
              f"\"{narration}\"\n\n"
              "Para CADA elemento de la lista, dime en QUE PUNTO de la imagen esta, como porcentajes "
              "x,y (0-100; x izquierda->derecha, y arriba->abajo). Si un elemento NO se ve CLARAMENTE en "
              "esta imagen concreta, pon null (no te lo inventes).\n"
              f"Elementos:\n{labs}\n\n"
              f"Responde SOLO un JSON: lista de {len(labels)} valores en orden, cada uno {{\"x\":num,\"y\":num}} "
              "o null.")
    txt = _gemini_vision(prompt, [b64], max_tokens=400)
    if not txt:
        return None
    try:
        arr = json.loads(re.search(r"\[.*\]", txt, re.S).group(0))
        res = []
        for v in arr[:len(labels)]:
            if isinstance(v, dict) and v.get("x") is not None and v.get("y") is not None:
                res.append({"x": max(0.04, min(0.96, v["x"] / 100.0)), "y": max(0.06, min(0.94, v["y"] / 100.0))})
            else:
                res.append(None)
        return res
    except Exception:
        return None


def pexels_candidates(query, n=5):
    """Candidatos de Pexels con miniatura. Dedup BLANDO: prefiere clips no usados, pero si no quedan,
    permite reutilizar (mejor repetir un clip que dejar un hueco). Blocklist sigue siendo dura."""
    url = (f"https://api.pexels.com/videos/search?query={query.replace(' ', '%20')}"
           f"&per_page=30&orientation=landscape&size=medium")
    data = curl_json(url, [f"Authorization: {PEXELS}"])
    fresh, used = [], []
    for vid in data.get("videos", []):
        vid_id = f"px{vid.get('id')}"
        if off_topic(vid.get("url")):
            continue
        best = None
        for f in vid.get("video_files", []):
            if f.get("file_type") != "video/mp4":
                continue
            h = f.get("height") or 0
            if h > 1080:
                continue
            if not best or h > best[0]:
                best = (h, f["link"])
        if best:
            cand = {"id": vid_id, "link": best[1], "duration": vid.get("duration", 0),
                    "credit": vid.get("user", {}).get("name", ""), "image": vid.get("image", "")}
            (used if vid_id in USED else fresh).append(cand)
    return (fresh + used)[:n]   # nuevos primero; usados como ultimo recurso (nunca vacio)


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


# plano de aviacion GENERICO y bonito (relleno cuando no hay clip literal; nunca fuera de tema)
SAFE_QUERIES = ["airliner flying above clouds", "airplane cockpit pilots hands", "jet engine turbine closeup",
                "airplane wing view window clouds", "airport runway airplane taxi", "clouds sky aerial sunset",
                "airplane cabin interior seats", "commercial airplane landing", "aerial view clouds sky",
                "airplane tail vertical stabilizer sky", "control tower airport", "airplane taking off"]
_safe_idx = [0]


def safe_aviation_clip(prefix, i):
    """Devuelve un clip real de aviacion generico (rotando el pool, sin repetir). Relleno on-brand."""
    for _ in range(len(SAFE_QUERIES)):
        q = SAFE_QUERIES[_safe_idx[0] % len(SAFE_QUERIES)]
        _safe_idx[0] += 1
        for c in pexels_candidates(q, 6):
            fn = f"{prefix}_{i}.mp4"
            dst = os.path.join(OUT, fn)
            if download(c["link"], dst) and decodable(f"stock/{fn}"):
                USED.add(c["id"])
                return {"file": f"stock/{fn}", "duration": c["duration"], "credit": c["credit"]}
            if os.path.exists(dst):
                os.remove(dst)
    return None


def resolve_visual(q, text, key, i, allow_video=True):
    """Cadena unica para un plano visual: clip literal revisado -> (video IA) -> foto revisada ->
    plano de aviacion generico (relleno). Devuelve (source_tag, media, tipo) o (None,None,None)."""
    c = get_clip(q, text, key, i)
    if c:
        return ("CLIP", c, "clip")
    if allow_video:
        v = ai33_video(q, key, i)
        if v:
            return ("CLIP-IA", v, "clip")
    p = stock_photo(q, text, key, i)
    if p:
        return ("FOTO-STOCK", p, "photo")
    s = safe_aviation_clip(key, i)   # mezcla inteligente: relleno de aviacion en vez de tarjeta de texto
    if s:
        return ("CLIP-AVIA", s, "clip")
    return (None, None, None)


def get_clip(query, text, prefix, i):
    """Busca candidatos, la IA de vision revisa que ENCAJEN con la narracion y elige el bueno.
    Si ninguno encaja, devuelve None (el caller usa foto real / otro recurso). `text` = la frase narrada."""
    cands = pexels_candidates(query)
    if not cands:
        return None
    imgs = [c.get("image") for c in cands if c.get("image")]
    pick = vision_match(text or query, imgs) if imgs else None
    # pick: None=fallo/sin clave -> usar el 1o; 0=ninguno encaja -> rechazar; 1..n=indice elegido
    if pick == 0:
        print(f"   [vision: ningun clip encaja con '{(text or query)[:40]}' -> descarto]")
        return None
    order = [cands[pick - 1]] if (pick and 1 <= pick <= len(cands)) else []
    order += [c for c in cands if c not in order]   # el elegido primero; el resto por si el descargar falla
    for c in order:
        fn = f"{prefix}_{i}.mp4"
        dst = os.path.join(OUT, fn)
        if download(c["link"], dst) and decodable(f"stock/{fn}"):
            USED.add(c["id"])
            return {"file": f"stock/{fn}", "duration": c["duration"], "credit": c["credit"]}
        if os.path.exists(dst):
            os.remove(dst)
    return None


# ---------- IMAGENES DE ENTIDAD (revisadas por vision) ----------
def wiki_image(query, text, prefix, i):
    for lang in ("es", "en"):
        url = (f"https://{lang}.wikipedia.org/w/api.php?action=query&format=json"
               f"&generator=search&gsrsearch={query.replace(' ', '%20')}&gsrlimit=1"
               f"&prop=pageimages&piprop=thumbnail&pithumbsize=1280")
        data = curl_json(url, [f"User-Agent: {UA}"])
        for p in ((data.get("query", {}) or {}).get("pages", {}) or {}).values():
            thumb = (p.get("thumbnail") or {}).get("source")
            if thumb:
                if text and vision_match(text, [thumb]) == 0:   # revision: descarta si no encaja
                    continue
                ext = ".png" if ".png" in thumb.lower() else ".jpg"
                dst = os.path.join(OUT, f"img_{prefix}_{i}{ext}")
                if download(thumb, dst, ua=True) and os.path.getsize(dst) >= 8000:
                    return {"file": f"stock/img_{prefix}_{i}{ext}"}
                if os.path.exists(dst):
                    os.remove(dst)
    return None


def openverse_image(query, text, prefix, i):
    url = (f"https://api.openverse.org/v1/images/?q={query.replace(' ', '%20')}"
           f"&license_type=commercial&page_size=4")
    data = curl_json(url, [f"User-Agent: {UA}"])
    for r in data.get("results", []):
        src = r.get("url") or r.get("thumbnail")
        if not src:
            continue
        if text and vision_match(text, [src]) == 0:   # revision: descarta si no encaja
            continue
        dst = os.path.join(OUT, f"ov_{prefix}_{i}.jpg")
        if download(src, dst, ua=True) and os.path.getsize(dst) >= 8000:
            return {"file": f"stock/ov_{prefix}_{i}.jpg"}
        if os.path.exists(dst):
            os.remove(dst)
    return None


def get_entity_image(query, text, prefix, i):
    return wiki_image(query, text, prefix, i) or openverse_image(query, text, prefix, i)


def stock_photo(query, text, prefix, i):
    """Foto REAL de stock (Pexels) REVISADA por vision — respaldo cuando no hay clip. NUNCA IA."""
    url = (f"https://api.pexels.com/v1/search?query={query.replace(' ', '%20')}"
           f"&per_page=20&orientation=landscape&size=large")
    data = curl_json(url, [f"Authorization: {PEXELS}"])
    cands = []
    for p in data.get("photos", []):
        pid = f"pxph{p.get('id')}"
        if pid in USED or off_topic(p.get("url")):
            continue
        src = p.get("src") or {}
        u = src.get("large2x") or src.get("large") or src.get("original")
        prev = src.get("medium") or src.get("small") or u
        if u:
            cands.append({"id": pid, "url": u, "image": prev})
        if len(cands) >= 5:
            break
    if not cands:
        return None
    pick = vision_match(text or query, [c["image"] for c in cands])
    if pick == 0:
        return None
    order = [cands[pick - 1]] if (pick and 1 <= pick <= len(cands)) else []
    order += [c for c in cands if c not in order]
    for c in order:
        dst = os.path.join(OUT, f"ph_{prefix}_{i}.jpg")
        if download(c["url"], dst) and os.path.getsize(dst) >= 20000:
            w, h = img_dims(dst)
            if w >= 1000 and h >= 560:
                USED.add(c["id"])
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


def _ai33_diagram_prompt(prompt):
    # ILUSTRACION 3D realista EN CONTEXTO (dentro del avion), pero limpia para poner flechas encima.
    return (prompt + ", seen from inside a real modern airliner cabin, mounted in the curved fuselage wall "
            "with surrounding cabin interior panels and floor, realistic aircraft proportions and materials, "
            "detailed 3D render, architectural visualization quality, soft cinematic interior lighting, "
            "the subject large and centered and clearly readable, no text, no labels, no logos, no people, "
            "sharp focus, 16:9")


def ai33_image(prompt, prefix, i, style="real"):
    """Genera imagen IA con ai33.pro (seedream, 16:9 1080p).
    style='real' -> foto cinematografica (solo para 'ai' cuando no hay stock).
    style='diagram' -> ilustracion 3D tecnica limpia (base de los explicadores 'annotate')."""
    if not AI33_KEY:
        return None
    styled = _ai33_diagram_prompt(prompt) if style == "diagram" else _ai33_prompt(prompt)
    tf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    tf.write(styled); tf.close()
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
    for _ in range(90):   # hasta ~6 min (seedream a veces va lento)
        time.sleep(4)
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
            t = sh.get("text", "")   # frase narrada -> se usa para la REVISION por vision
            item = {"kind": kind, "text": t}

            def as_image(m, src):
                item.update({"kind": "image", "file": m["file"], "label": sh.get("label", ""), "source": src})

            def as_clip(c, src):
                item.update({"kind": "broll", "file": c["file"] if c else "", "source": src,
                             "duration": c.get("duration", 0) if c else 0})

            def as_photo(m):   # foto REAL de stock, a pantalla completa con movimiento (no tarjeta de entidad)
                item.update({"kind": "image", "file": m["file"], "label": "", "source": "FOTO-STOCK"})

            def apply_visual(tag, media, typ):
                if typ == "clip":
                    as_clip(media, tag)
                elif typ == "photo":
                    as_photo(media)
                else:
                    as_clip(None, "")   # nada de nada -> tarjeta de texto (raro)

            if kind == "image":
                # entidad con nombre -> foto de la entidad (tarjeta premium); si no, cadena visual normal
                m = get_entity_image(sh.get("query", ""), t, key, i)
                if m:
                    as_image(m, "FOTO")
                else:
                    apply_visual(*resolve_visual(q, t, key, i))
            elif kind == "ai":
                apply_visual(*resolve_visual(q, t, key, i))
            elif kind == "broll":
                apply_visual(*resolve_visual(sh.get("query", "") or t, t, key, i))
            elif kind == "map":
                # mapa con ruta animada (motion graphics, sin media): pasa coords
                item["source"] = "MAPA"
                for k in ("from", "to", "label"):
                    if k in sh:
                        item[k] = sh[k]
            elif kind == "annotate":
                # explicador: base = ILUSTRACION 3D tecnica limpia (clay, fondo neutro) generada con ai33.
                # Es MUCHO mejor que una foto de stock para señalar piezas con flechas. Si falla, foto real.
                labels = [c.get("label", "") for c in (sh.get("callouts") or []) if c.get("label")][:4]
                dq = sh.get("query", "") or q
                p = ai33_image(dq, key, f"ann{i}", style="diagram") or get_entity_image(sh.get("query", ""), t, key, i) or stock_photo(q, t, key, i)
                coords = vision_locate(p["file"], labels, t) if (p and labels) else None
                placed = ([{"label": labels[j], "x": coords[j]["x"], "y": coords[j]["y"]}
                           for j in range(len(labels)) if j < len(coords) and coords[j]] if coords else [])
                if p and placed:
                    # arrows a coordenadas REALES; solo las partes que de verdad se ven
                    item.update({"file": p["file"], "source": "ANOTADO", "callouts": placed,
                                 "label": sh.get("label", "")})
                else:
                    apply_visual(*resolve_visual(q, t, key, i))   # no se ven las partes -> clip normal
            else:
                item["source"] = "GRAFICO"
                for k in ("value", "suffix", "label", "color", "kicker", "body", "accent",
                          "a", "b", "alabel", "blabel", "unit", "events"):
                    if k in sh:
                        item[k] = sh[k]
            # rotulo/palabra clave opcional sobre clips (para que no parezca stock crudo)
            if sh.get("key") and item.get("kind") in ("broll", "image"):
                item["key"] = sh["key"]
            print(f"[{key}] {item.get('source','?'):7} {sh.get('query', sh.get('text',''))[:34]}")
            resolved.append(item)
        out_sections.append({"key": key, "shots": resolved})
    # validacion final con ffprobe: medio corrupto -> re-buscar otro clip (o video IA); nunca imagen IA
    for si, sec in enumerate(out_sections):
        for sj, sh in enumerate(sec["shots"]):
            if sh.get("file") and not decodable(sh["file"]):
                print("  ! medio corrupto, re-buscando clip:", sh["file"])
                txt = sh.get("text", "")
                repl = get_clip(txt or "aviation aircraft", txt, sec["key"], f"fix_{si}_{sj}") \
                    or ai33_video(txt or "aviation", sec["key"], f"fix_{si}_{sj}")
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

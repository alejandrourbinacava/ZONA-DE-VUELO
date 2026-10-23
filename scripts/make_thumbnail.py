#!/usr/bin/env python3
"""Miniatura 1280x720 automatica para YouTube.
Uso: python scripts/make_thumbnail.py <metadata.json> <salida.jpg> [media.json]
- Fondo: el MEJOR fotograma (nitido, ni muy oscuro ni quemado) de los primeros planos del video
  (public/stock/media.json); asi sale siempre un avion/escena real de ese video.
- Texto: 2 lineas cortas y potentes (Gemini si hay GOOGLE_API_KEY; si no, heuristica del titulo).
- Tipografia: assets/fonts/Anton-Regular.ttf (en el repo, para que funcione en el runner de Linux).
- Salida <2 MB (limite de YouTube)."""
import os, sys, re, json, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter, ImageStat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
W, H = 1280, 720
FONT = os.path.join(ROOT, "assets", "fonts", "Anton-Regular.ttf")
CY, RED, WHITE, DK = (55, 226, 255), (255, 45, 60), (255, 255, 255), (4, 9, 20)


def font(sz):
    return ImageFont.truetype(FONT, sz) if os.path.exists(FONT) else ImageFont.load_default()


# ---------- fondo: mejor fotograma de los primeros planos ----------
def candidate_frames(media_path, limit=10):
    media = json.load(open(media_path, encoding="utf-8"))
    out, tmp = [], tempfile.mkdtemp()
    for sec in media.get("sections", []):
        for sh in sec.get("shots", []):
            f = sh.get("file")
            if not f or sh.get("kind") not in ("broll", "image", "annotate"):
                continue
            p = os.path.join(ROOT, "public", f)
            if not os.path.exists(p):
                continue
            if p.lower().endswith((".jpg", ".jpeg", ".png")):
                try: out.append(Image.open(p).convert("RGB"))
                except Exception: pass
            else:
                for t in ("1.2", "3.0"):
                    dst = os.path.join(tmp, f"f{len(out)}.jpg")
                    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", t, "-i", p, "-frames:v", "1", dst],
                                   capture_output=True)
                    if os.path.exists(dst):
                        try: out.append(Image.open(dst).convert("RGB"))
                        except Exception: pass
            if len(out) >= limit * 2:
                return out
    return out


def score(im):
    s = im.resize((320, 180)).convert("L")
    edge = ImageStat.Stat(s.filter(ImageFilter.FIND_EDGES)).mean[0]       # nitidez / detalle
    br = ImageStat.Stat(s).mean[0]
    sd = ImageStat.Stat(s).stddev[0]                                       # contraste
    pen = 0.35 if (br < 50 or br > 205) else 1.0                           # ni oscuro ni quemado
    return (edge * 1.5 + sd) * pen


def background(media_path):
    frames = candidate_frames(media_path) if os.path.exists(media_path) else []
    if not frames:
        return Image.new("RGB", (W, H), (10, 22, 46))
    best = max(frames, key=score)
    sc = max(W / best.width, H / best.height)
    best = best.resize((int(best.width * sc) + 1, int(best.height * sc) + 1), Image.LANCZOS)
    x, y = (best.width - W) // 2, (best.height - H) // 2
    best = best.crop((x, y, x + W, y + H))
    best = ImageEnhance.Contrast(best).enhance(1.15)
    return ImageEnhance.Color(best).enhance(1.25)


# ---------- texto ----------
def heuristic_text(title):
    t = re.sub(r"[¿?¡!]", "", title).upper()
    t = re.sub(r"^(POR QU[ÉE]|C[ÓO]MO|QU[ÉE])\s+(LOS\s+)?(AVIONES|PILOTOS)?\s*", "", t).strip()
    words = t.split()
    words = words[-3:] if len(words) > 3 else words
    if len(words) <= 1:
        return {"top": "", "line1": "", "line2": " ".join(words)}
    return {"top": "", "line1": " ".join(words[:-1]), "line2": words[-1]}


def thumb_text(title):
    try:
        import generate_script as gs
        if not gs.KEY:
            raise RuntimeError("sin clave")
        system = ("Eres experto en miniaturas virales de YouTube para un canal de curiosidades de aviacion en español. "
                  "Dado el titulo, devuelve SOLO JSON {\"top\":..., \"line1\":..., \"line2\":...} con: "
                  "top = kicker en MAYUSCULAS de 2-4 palabras (<=24 caracteres) que da contexto; "
                  "line1 = 1-2 palabras en MAYUSCULAS (<=14 caracteres) que plantean la duda; "
                  "line2 = 1 palabra IMPACTANTE en MAYUSCULAS (<=12 caracteres), la que mas curiosidad genera. "
                  "Sin signos raros; puedes usar ¿ ? ! . Nada de comillas.")
        text, _ = gs.call_claude(system, f"TITULO: {title}", max_tokens=600, thinking={"type": "disabled"})
        d = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
        for k in ("top", "line1", "line2"):
            d[k] = str(d.get(k, "")).upper().strip()
        if d["line2"]:
            return d
    except Exception as e:
        print("  (miniatura: texto por heuristica:", str(e)[:60], ")", file=sys.stderr)
    return heuristic_text(title)


def fit(draw_font_size, text, max_w):
    sz = draw_font_size
    while sz > 40 and font(sz).getlength(text) > max_w:
        sz -= 4
    return sz


def main():
    meta = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    media = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "public", "stock", "media.json")
    tx = thumb_text(meta.get("title") or "Zona de Vuelo")

    img = background(media).convert("RGBA")
    # degradado oscuro a la izquierda y arriba para que el texto resalte
    grad = Image.new("L", (W, H), 0); gd = ImageDraw.Draw(grad)
    for i in range(W):
        gd.line([(i, 0), (i, H)], fill=int(max(0, 215 * (1 - i / (W * 0.66)))))
    dark = Image.new("RGBA", (W, H), DK + (255,))
    img = Image.alpha_composite(img, Image.merge("RGBA", (*dark.split()[:3], grad)))
    d = ImageDraw.Draw(img)

    def txt(pos, s, f, fill, sw=8, stroke=DK, anchor="la"):
        d.text(pos, s, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke, anchor=anchor)

    maxw = 780
    if tx.get("top"):
        txt((58, 46), tx["top"], font(fit(46, tx["top"], maxw)), CY, sw=5)
    y = 120
    if tx.get("line1"):
        s1 = fit(170, tx["line1"], maxw)
        txt((54, y), tx["line1"], font(s1), WHITE, sw=10); y += int(s1 * 1.12)
    s2 = fit(230, tx["line2"], maxw + 60)
    txt((54, y), tx["line2"], font(s2), RED, sw=12, stroke=WHITE)
    txt((W - 56, H - 48), "ZONA DE VUELO", font(34), CY, sw=5, anchor="ra")
    img = img.convert("RGB")
    for q in (90, 86, 82, 76):
        img.save(out, quality=q, optimize=True)
        if os.path.getsize(out) < 1_900_000:
            break
    print(f"MINIATURA -> {out} ({os.path.getsize(out)//1024} KB) | texto: {tx}")


if __name__ == "__main__":
    main()

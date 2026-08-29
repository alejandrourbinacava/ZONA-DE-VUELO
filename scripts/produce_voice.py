#!/usr/bin/env python3
"""Genera la narracion completa (Gabriel) por secciones + timeline + subtitulos locales.
Resumible: reutiliza los mp3 ya generados. Ejecutar desde la raiz del proyecto."""
import os, re, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\aleja\Downloads\guion_12_antartida.md"
OUTDIR = os.path.join(ROOT, "out", "voz")
os.makedirs(OUTDIR, exist_ok=True)

VOICE = "4R9s73RrCF4wi6GqmzrT"   # Gabriel Blanco
MODEL = "eleven_multilingual_v2"
KEYS = ["hook", "parte1", "parte2", "parte3", "parte4", "parte5", "cierre"]


def parse_sections(path):
    lines = open(path, encoding="utf-8").read().splitlines()
    sections, cur = [], None
    for ln in lines:
        s = ln.strip()
        if s.startswith("## "):
            if cur:
                sections.append(cur)
            cur = {"title": re.sub(r"^#+\s*", "", s), "text": []}
            continue
        if cur is None:
            continue
        if not s or s.startswith("#") or s == "---":
            continue
        if re.match(r"^Minuto\b", s):
            continue
        if s.startswith("*") and s.endswith("*"):
            continue
        cur["text"].append(s)
    if cur:
        sections.append(cur)
    for sec in sections:
        sec["text"] = " ".join(sec["text"]).strip()
    return [s for s in sections if s["text"]]


def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", path],
                         capture_output=True, text=True).stdout.strip()
    return float(out)


def make_cues(text, offset, duration, max_chars=38):
    """Reparte el texto en frases cortas con tiempos proporcionales a su longitud."""
    # trocear por puntuacion manteniendo trozos <= max_chars
    parts = re.split(r"(?<=[\.,;:!\?])\s+", text)
    chunks, buf = [], ""
    for p in parts:
        while len(p) > max_chars:  # frase larga: cortar por palabras
            cut = p.rfind(" ", 0, max_chars)
            cut = cut if cut > 0 else max_chars
            chunks.append(p[:cut].strip()); p = p[cut:].strip()
        if len(buf) + len(p) + 1 <= max_chars:
            buf = (buf + " " + p).strip()
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    total = sum(len(c) for c in chunks) or 1
    cues, t = [], offset
    for c in chunks:
        d = duration * len(c) / total
        cues.append({"start": round(t, 3), "end": round(t + d, 3), "text": c})
        t += d
    return cues


def find_task_id(text):
    hist = tts._req("GET", "/v1/labs/task?page=1&limit=50").get("tasks", [])
    return next((t["id"] for t in hist if (t.get("input", "") or "")[:40] == text[:40]), None)


def main():
    secs = parse_sections(SRC)
    print(f"Secciones: {len(secs)}")
    manifest, offset, listing = [], 0.0, []
    for i, sec in enumerate(secs):
        key = KEYS[i] if i < len(KEYS) else f"sec{i}"
        mp3 = os.path.join(OUTDIR, f"{i:02d}_{key}.mp3")
        if os.path.exists(mp3) and os.path.getsize(mp3) > 2000:
            print(f"[{i+1}/{len(secs)}] {key}: reuso audio")
        else:
            print(f"[{i+1}/{len(secs)}] {key}: generando ({len(sec['text'])}c)")
            # Voz "B": mas agil (speed 1.1) y menos monotona (stability baja + style alto), v2 preciso
            r = tts.synth(sec["text"], VOICE, mp3, model=MODEL,
                          stability=0.3, similarity=0.8, style=0.5, speed=1.1)
            if not r:
                # cortar YA con error (no seguir con medios y morir 90 min despues)
                print(f"  ! fallo TTS en seccion '{key}' -> abortando", file=sys.stderr)
                sys.exit(1)
        d = dur(mp3)
        cues = make_cues(sec["text"], offset, d)
        manifest.append({"key": key, "title": sec["title"], "mp3": os.path.relpath(mp3, ROOT).replace("\\", "/"),
                         "offset": round(offset, 3), "duration": round(d, 3),
                         "text": sec["text"], "cues": cues})
        listing.append(f"file '{mp3.replace(chr(92), '/')}'")
        offset += d
    concat_list = os.path.join(OUTDIR, "concat.txt")
    open(concat_list, "w", encoding="utf-8").write("\n".join(listing))
    full = os.path.join(OUTDIR, "narration_full.mp3")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
                    "-c:a", "libmp3lame", "-q:a", "2", full], capture_output=True, text=True)
    total = dur(full)
    data = {"voice": "Gabriel Blanco", "voice_id": VOICE, "model": MODEL,
            "full_audio": "out/voz/narration_full.mp3", "total_duration": round(total, 3),
            "fps": 30, "sections": manifest}
    json.dump(data, open(os.path.join(OUTDIR, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\nLISTO: {total:.1f}s ({total/60:.2f} min) -> out/voz/manifest.json")


if __name__ == "__main__":
    main()

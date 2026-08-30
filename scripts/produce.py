#!/usr/bin/env python3
"""Orquestador: una idea -> video final en VIDEOS FINALIZADOS.
Uso: python scripts/produce.py "idea del video" [--norender]
Encadena: guion (Claude) -> shot-list (Claude) -> voz (GenAIPro) -> stock (Pexels)
          -> props -> render (Remotion) -> mover + metadatos."""
import os, re, sys, json, shutil, subprocess, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
# En local: carpeta del escritorio. En la nube: se pasa VIDEOS_DIR (ej. ./salidas).
FINAL = os.environ.get("VIDEOS_DIR", r"C:\Users\aleja\Desktop\VIDEOS FINALIZADOS")


def slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return (re.sub(r"[^a-zA-Z0-9]+", "_", t).strip("_").lower())[:60] or "video"


def clean_title(t):
    # nombre de archivo legible = el titulo del guion (sin caracteres invalidos en Windows)
    t = t.replace("¿", "").replace("¡", "")
    t = re.sub(r'[\\/:*?"<>|]', "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:110] or "video"


def run(cmd, **kw):
    print("»", " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, cwd=ROOT, **kw)
    if r.returncode != 0:
        print("! fallo en:", cmd[:3]); sys.exit(1)


def main():
    args = [a for a in sys.argv[1:] if a != "--norender"]
    norender = "--norender" in sys.argv
    idea = " ".join(args)
    if not idea:
        print('Uso: python scripts/produce.py "idea" [--norender]'); sys.exit(1)
    s = slug(idea)
    guion = os.path.join(ROOT, "guiones", s + ".md")   # carpeta trackeada -> reuso entre renders

    print("\n=== 1/6 GUION ===")
    if os.path.exists(guion) and os.path.getsize(guion) > 500:
        print("guion ya existe -> lo REUSO (no gasta Opus):", guion)
    else:
        run([PY, "scripts/generate_script.py", idea])

    print("\n=== 2/6 SHOT-LIST ===")
    run([PY, "scripts/generate_shotlist.py", guion])

    print("\n=== 3/6 VOZ (Gabriel) ===")
    voz_dir = os.path.join(ROOT, "out", "voz")
    if os.path.isdir(voz_dir):
        shutil.rmtree(voz_dir)  # limpiar audios de un tema anterior
    run([PY, "scripts/produce_voice.py", guion])

    print("\n=== 4/6 MEDIOS (imagenes + clips) ===")
    run([PY, "scripts/fetch_media.py"])

    print("\n=== 5/6 PROPS + AUDIO + ASSETS ===")
    manifest = json.load(open(os.path.join(ROOT, "out", "voz", "manifest.json"), encoding="utf-8"))
    media = json.load(open(os.path.join(ROOT, "public", "stock", "media.json"), encoding="utf-8"))
    props = {"manifest": manifest, "media": media}
    props_path = os.path.join(ROOT, "out", "render_props.json")
    json.dump(props, open(props_path, "w", encoding="utf-8"), ensure_ascii=False)
    os.makedirs(os.path.join(ROOT, "public"), exist_ok=True)
    shutil.copy(os.path.join(ROOT, "out", "voz", "narration_full.mp3"),
                os.path.join(ROOT, "public", "narration_full.mp3"))
    for a in ("grid.mp4", "music.mp3", "worldmap.jpg"):
        src = os.path.join(ROOT, "assets", a)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(ROOT, "public", a))
    print(f"props -> {props_path}  ({manifest['total_duration']:.0f}s)")

    if norender:
        print("\n[--norender] Paro antes de renderizar."); return

    print("\n=== 6/6 RENDER ===")
    raw = os.path.join(ROOT, "out", s + ".mp4")
    cmd = ["npx", "remotion", "render", "Auto", raw, "--props=out/render_props.json"]
    conc = os.environ.get("RENDER_CONCURRENCY")  # opcional; si no, Remotion elige segun nucleos
    if conc:
        cmd.append(f"--concurrency={conc}")
    run(cmd, shell=(os.name == "nt"))  # shell solo en Windows para hallar npx
    # comprimir para subir
    web = os.path.join(ROOT, "out", s + "_web.mp4")
    subprocess.run(["ffmpeg", "-y", "-i", raw, "-c:v", "libx264", "-crf", "22",
                    "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", web],
                   cwd=ROOT, capture_output=True)
    os.makedirs(FINAL, exist_ok=True)
    n = len([f for f in os.listdir(FINAL) if f.endswith(".mp4")]) + 1
    base = f"{n:02d} - {clean_title(idea)}"   # nombre = titulo legible del guion
    dst = os.path.join(FINAL, base + ".mp4")
    shutil.copy(web if os.path.exists(web) else raw, dst)
    # metadatos para YouTube (titulo/descripcion/keywords)
    meta_path = os.path.join(FINAL, base + ".json")
    try:
        r = subprocess.run([PY, "scripts/generate_metadata.py", guion], cwd=ROOT,
                           capture_output=True, encoding="utf-8", errors="replace")
        if r.returncode == 0 and r.stdout.strip():
            open(meta_path, "w", encoding="utf-8").write(r.stdout.strip())
    except Exception as e:
        print("aviso: metadatos fallaron:", e)
    # informe de planos: minuto:segundo + fuente de cada plano (IA / FOTO / CLIP / GRAFICO)
    try:
        secoff = {s["key"]: (s["offset"], s["duration"]) for s in manifest["sections"]}
        lines = [f"INFORME DE PLANOS — {clean_title(idea)}", "=" * 60,
                 "TIEMPO   FUENTE  | texto", "-" * 60]
        cnt = {}
        for sec in media["sections"]:
            off, dur = secoff.get(sec["key"], (0, 0))
            shots = sec["shots"]
            weights = [max(8, len(sh.get("text", ""))) for sh in shots]
            tot = sum(weights) or 1
            t = off
            for sh, w in zip(shots, weights):
                mm, ss = int(t // 60), int(t % 60)
                src = sh.get("source", "?")
                cnt[src] = cnt.get(src, 0) + 1
                lines.append(f"{mm:2d}:{ss:02d}   {src:7} | {sh.get('text','')[:66]}")
                t += dur * w / tot
        lines.append("-" * 60)
        lines.append("RESUMEN: " + " · ".join(f"{v} {k}" for k, v in sorted(cnt.items())))
        open(os.path.join(FINAL, base + " - PLANOS.txt"), "w", encoding="utf-8").write("\n".join(lines))
    except Exception as e:
        print("aviso: informe de planos fallo:", e)
    print(f"\n✔ LISTO -> {dst}")
    print(f"VIDEO::{dst}")
    print(f"META::{meta_path if os.path.exists(meta_path) else ''}")


if __name__ == "__main__":
    main()

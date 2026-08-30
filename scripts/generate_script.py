#!/usr/bin/env python3
"""Genera un guion de Zona de Vuelo con Claude (API de Anthropic) a partir de una idea.
Uso: python scripts/generate_script.py "Por que los aviones evitan el Triangulo de las Bermudas"
Requiere ANTHROPIC_API_KEY en el entorno."""
import os, re, sys, json, subprocess, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
SYS_PATH = os.path.join(ROOT, "brain", "system_prompt.md")
OUTDIR = os.path.join(ROOT, "guiones")   # trackeado en git -> reuso entre renders (no regenera Opus)


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text[:60] or "guion"


def call_claude(system, user, max_tokens=12000, thinking=None, model=None, output_config=None):
    body = {
        "model": model or MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    if thinking is not None:
        body["thinking"] = thinking  # ej. {"type":"disabled"} para tareas JSON
    if output_config is not None:
        body["output_config"] = output_config  # ej. {"effort":"high"}
    cmd = ["curl", "-s", "https://api.anthropic.com/v1/messages",
           "-H", f"x-api-key: {KEY}",
           "-H", "anthropic-version: 2023-06-01",
           "-H", "content-type: application/json",
           "-d", json.dumps(body)]
    out = subprocess.run(cmd, capture_output=True, encoding="utf-8",
                         errors="replace", timeout=600).stdout
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        print("Respuesta no-JSON:", out[:500], file=sys.stderr); sys.exit(1)
    if data.get("type") == "error" or "content" not in data:
        print("Error API:", json.dumps(data)[:500], file=sys.stderr); sys.exit(1)
    # concatenar todos los bloques de texto
    text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
    usage = data.get("usage", {})
    return text.strip(), usage


def generate(idea, out_path=None):
    if not KEY:
        print("FALTA ANTHROPIC_API_KEY en el entorno."); sys.exit(1)
    system = open(SYS_PATH, encoding="utf-8").read()
    user = (f"TEMA DEL VIDEO: {idea}\n\n"
            f"Escribe el guion completo siguiendo tu estructura y reglas. "
            f"Recuerda: empieza directamente por el encabezado del HOOK, sin preambulo.")
    # Guiones = maxima calidad: Opus 4.8 con effort alto + pensamiento adaptativo
    print(f"Generando guion (Opus 4.8, effort alto) sobre: {idea}")
    text, usage = call_claude(system, user, max_tokens=16000, model="claude-opus-4-8",
                              thinking={"type": "adaptive"}, output_config={"effort": "high"})
    # titular del video = primera linea del HOOK si el modelo la pone, si no la idea
    title = idea.strip()
    header = f"# {title}\n\n"
    if not text.startswith("#"):
        text = header + text
    os.makedirs(OUTDIR, exist_ok=True)
    out_path = out_path or os.path.join(OUTDIR, slugify(idea) + ".md")
    open(out_path, "w", encoding="utf-8").write(text)
    n = len(text)
    print(f"LISTO: {n} caracteres -> {out_path}")
    print(f"Tokens: entrada={usage.get('input_tokens')} salida={usage.get('output_tokens')}")
    return out_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/generate_script.py \"idea del video\""); sys.exit(1)
    generate(" ".join(sys.argv[1:]))

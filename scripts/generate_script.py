#!/usr/bin/env python3
"""Genera texto (guion / shotlist / metadata) con Gemini (Google) a partir de una idea.
Antes usaba Anthropic; se migro a Gemini (GOOGLE_API_KEY) porque la key de Anthropic se retiro por coste.
NOTA: el guion de maxima calidad lo escribe Claude Code en sesion y se commitea en guiones/ (se REUSA
y no se regenera). Esta generacion por Gemini es el respaldo automatico si no hay guion commiteado.
Uso: python scripts/generate_script.py "Por que los aviones evitan el Triangulo de las Bermudas"
Requiere GOOGLE_API_KEY en el entorno."""
import os, re, sys, json, time, subprocess, tempfile, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
# 'latest' no se deprecia; pro para guion (calidad), flash para tareas mecanicas (shotlist/metadata)
MODEL_FLASH = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
MODEL_PRO = os.environ.get("GEMINI_PRO_MODEL", "gemini-pro-latest")
SYS_PATH = os.path.join(ROOT, "brain", "system_prompt.md")
OUTDIR = os.path.join(ROOT, "guiones")   # trackeado en git -> reuso entre renders


def slugify(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return text[:60] or "guion"


def call_claude(system, user, max_tokens=12000, thinking=None, model=None, output_config=None):
    """Mantiene la firma antigua (para no tocar generate_shotlist/metadata) pero llama a GEMINI.
    - model: si el nombre pedido sugiere maxima calidad ('opus'/'pro') o effort alto -> Gemini Pro; si no, Flash.
    - thinking={'type':'disabled'} (tareas JSON) -> thinkingBudget 0 (o el modelo gasta tokens 'pensando').
    Devuelve (texto, usage) con usage traducido a input_tokens/output_tokens."""
    want_pro = bool((model and ("opus" in model or "pro" in model)) or
                    (output_config and output_config.get("effort") == "high"))
    # Cadena de modelos: Pro (si se pide) -> Flash. La capa gratuita de Google deja el Pro sin cuota (429 RESOURCE_EXHAUSTED):
    # entonces se cae al Flash al instante, y el Flash se reintenta con paciencia (503 = alta demanda, transitorio).
    chain = ([MODEL_PRO, MODEL_FLASH] if want_pro else [MODEL_FLASH])
    gen = {"temperature": 0.85 if want_pro else 0.4, "maxOutputTokens": max_tokens}
    if thinking is not None and thinking.get("type") == "disabled":
        gen["thinkingConfig"] = {"thinkingBudget": 0}
    body = {"systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": gen}
    tf = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(body, tf); tf.close()
    data = None
    try:
        mi, intento = 0, 0
        while data is None and intento < 10 and mi < len(chain):
            gmodel = chain[mi]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{gmodel}:generateContent"
            try:
                out = subprocess.run(["curl", "-s", "--max-time", "420", url, "-H", "content-type: application/json",
                                      "-H", f"x-goog-api-key: {KEY}", "-d", "@" + tf.name],
                                     capture_output=True, encoding="utf-8", errors="replace", timeout=450).stdout
            except subprocess.TimeoutExpired:
                out = ""
            try:
                d = json.loads(out)
            except json.JSONDecodeError:
                d = None
            if d and "candidates" in d:
                data = d; break
            err = (d or {}).get("error", {})
            code, status = err.get("code"), err.get("status", "sin JSON")
            print(f"  (Gemini {gmodel} intento {intento+1}/10: {status})", file=sys.stderr)
            intento += 1
            if status == "RESOURCE_EXHAUSTED" and mi + 1 < len(chain):
                mi += 1; print(f"  -> sin cuota en {gmodel}; pruebo {chain[mi]}", file=sys.stderr); continue
            if not (code in (429, 500, 503) or d is None):
                print("Error API Gemini:", (out or "")[:400], file=sys.stderr); sys.exit(1)
            time.sleep(min(15 * intento, 75))   # 15s, 30s, 45s, 60s, 75s...
    finally:
        try: os.remove(tf.name)
        except OSError: pass
    if not data:
        print("Gemini no respondio (cuota agotada o sobrecarga sostenida).", file=sys.stderr); sys.exit(1)
    cand = data["candidates"][0]
    text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    um = data.get("usageMetadata", {})
    usage = {"input_tokens": um.get("promptTokenCount"), "output_tokens": um.get("candidatesTokenCount")}
    return text.strip(), usage


def generate(idea, out_path=None):
    if not KEY:
        print("FALTA GOOGLE_API_KEY en el entorno."); sys.exit(1)
    system = open(SYS_PATH, encoding="utf-8").read()
    user = (f"TEMA DEL VIDEO: {idea}\n\n"
            f"Escribe el guion completo siguiendo tu estructura y reglas. "
            f"Recuerda: empieza directamente por el encabezado del HOOK, sin preambulo.")
    # Respaldo automatico: guion con Gemini Pro (el de maxima calidad lo escribe Claude Code en sesion)
    print(f"Generando guion (Gemini Pro, respaldo) sobre: {idea}")
    text, usage = call_claude(system, user, max_tokens=16000, model="pro",
                              output_config={"effort": "high"})
    # LONGITUD MINIMA: el video debe durar >= 8 min (anuncios mid-roll) -> >= ~9.000 caracteres de narracion.
    # Si el guion sale corto, se pide UNA reescritura mas extensa y se queda con la mas larga.
    if len(text) < 9000:
        print(f"  guion corto ({len(text)} caracteres) -> pido version mas extensa")
        user2 = (user + f"\n\nIMPORTANTE: tu primer intento tenia solo {len(text)} caracteres y es DEMASIADO corto. "
                 "Reescribelo MAS EXTENSO: minimo 11.000 caracteres de narracion (7 secciones, cada una de 1.400-2.000 "
                 "caracteres), con mas ejemplos, datos y explicaciones, sin relleno ni repeticiones.")
        text2, usage2 = call_claude(system, user2, max_tokens=16000, model="pro", output_config={"effort": "high"})
        if len(text2) > len(text):
            text, usage = text2, usage2
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

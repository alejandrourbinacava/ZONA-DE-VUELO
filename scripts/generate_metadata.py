#!/usr/bin/env python3
"""Genera titulo, descripcion y keywords de YouTube a partir del guion (Claude).
Uso: python scripts/generate_metadata.py out/guiones/xxx.md > out/metadata.json"""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_script as gs

SYSTEM = """Eres el gestor SEO del canal de YouTube "Zona de Vuelo" (curiosidades de aviacion, español).
A partir del guion, devuelve metadatos para publicar. Reglas:
- "title": pregunta gancho con una palabra clave en MAYUSCULAS, <=90 caracteres (estilo del canal).
- "description": 3-5 frases con gancho + que se aprende, luego una linea "Suscríbete a Zona de Vuelo 🛩️", y al final 5-7 hashtags. <=1200 caracteres.
- "keywords": lista de 12-18 etiquetas (strings) para el campo de tags, mezcla long-tail + amplias, SIN #.
Devuelve UNICAMENTE JSON valido: {"title":"...","description":"...","keywords":["...",...]}"""


def main():
    guion = open(sys.argv[1], encoding="utf-8").read()
    text, _ = gs.call_claude(SYSTEM, f"GUION:\n\n{guion}", max_tokens=1500)
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    data = json.loads(text)
    print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()

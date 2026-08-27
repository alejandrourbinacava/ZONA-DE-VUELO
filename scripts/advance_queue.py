#!/usr/bin/env python3
"""Avanza el puntero de la cola (queue/state.json) en 1.
Se ejecuta SOLO tras producir un video con exito, para que los runs fallidos
NO consuman ideas. No hace nada si ya no quedan ideas."""
import os, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDEAS = os.path.join(ROOT, "queue", "ideas.txt")
STATE = os.path.join(ROOT, "queue", "state.json")


def n_ideas():
    return sum(1 for l in open(IDEAS, encoding="utf-8")
              if l.strip() and not l.strip().startswith("#"))


def main():
    idx = 0
    if os.path.exists(STATE):
        idx = json.load(open(STATE, encoding="utf-8")).get("index", 0)
    idx = min(idx + 1, n_ideas())   # no pasar del final
    json.dump({"index": idx}, open(STATE, "w", encoding="utf-8"))
    print(f"cola avanzada -> index {idx}")


if __name__ == "__main__":
    main()

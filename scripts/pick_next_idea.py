#!/usr/bin/env python3
"""Devuelve la siguiente idea sin usar de queue/ideas.txt (SIN avanzar el puntero).
Imprime SOLO la idea (para usar en el workflow). Si no quedan ideas, sale con codigo 2.
El puntero SOLO se avanza despues de producir el video con exito (scripts/advance_queue.py)."""
import os, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDEAS = os.path.join(ROOT, "queue", "ideas.txt")
STATE = os.path.join(ROOT, "queue", "state.json")


def load_ideas():
    out = []
    for line in open(IDEAS, encoding="utf-8"):
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def main():
    ideas = load_ideas()
    idx = 0
    if os.path.exists(STATE):
        idx = json.load(open(STATE, encoding="utf-8")).get("index", 0)
    if idx >= len(ideas):
        print("SIN_IDEAS", file=sys.stderr); sys.exit(2)
    idea = ideas[idx]
    print(idea)   # NO se avanza aqui; lo hace advance_queue.py tras un render con exito


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Devuelve la siguiente idea sin usar de queue/ideas.txt y avanza el puntero.
Imprime SOLO la idea (para usar en el workflow). Si no quedan ideas, sale con codigo 2."""
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
    # avanzar puntero
    json.dump({"index": idx + 1}, open(STATE, "w", encoding="utf-8"))
    print(idea)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Configura secretos de GitHub Actions en el repo (cifrados con la clave publica del repo).
Lee GITHUB_TOKEN y GITHUB_REPO del entorno. Los nombres/valores se pasan por argumentos:
  python scripts/gh_secrets.py NOMBRE1=valor1 NOMBRE2=valor2 ..."""
import os, sys, json, base64, subprocess
from nacl import encoding, public

TOKEN = os.environ["GITHUB_TOKEN"]
REPO = os.environ["GITHUB_REPO"]
API = f"https://api.github.com/repos/{REPO}/actions/secrets"
H = ["-H", f"Authorization: token {TOKEN}", "-H", "Accept: application/vnd.github+json"]


def curl(method, url, data=None):
    cmd = ["curl", "-s", "-X", method, url] + H
    if data is not None:
        cmd += ["-d", json.dumps(data)]
    out = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace").stdout
    try:
        return json.loads(out) if out.strip() else {}
    except json.JSONDecodeError:
        return {"raw": out}


def encrypt(pubkey_b64, value):
    pk = public.PublicKey(pubkey_b64.encode(), encoding.Base64Encoder())
    sealed = public.SealedBox(pk)
    return base64.b64encode(sealed.encrypt(value.encode())).decode()


def main():
    key = curl("GET", f"{API}/public-key")
    if "key" not in key:
        print("No pude obtener la clave publica:", key); sys.exit(1)
    for arg in sys.argv[1:]:
        name, _, value = arg.partition("=")
        if not value:
            print("saltando (vacio):", name); continue
        enc = encrypt(key["key"], value)
        r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                            "-X", "PUT", f"{API}/{name}"] + H +
                           ["-d", json.dumps({"encrypted_value": enc, "key_id": key["key_id"]})],
                           capture_output=True, text=True).stdout
        print(f"  {name}: HTTP {r}")


if __name__ == "__main__":
    main()

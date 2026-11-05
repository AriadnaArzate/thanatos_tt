"""
Cliente de prueba: inicia sesión, manda un audio a /conversar y guarda la
respuesta hablada.

Uso (con el servidor corriendo; la contraseña se pide por teclado):
    python scripts/probar_voz.py mi_audio.m4a nombre_de_usuario
    python scripts/probar_voz.py otro_audio.m4a nombre_de_usuario <session_id>
"""
import getpass
import sys
from pathlib import Path

import httpx

URL = "http://localhost:8000"


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit("Uso: python scripts/probar_voz.py <audio> <usuario> [session_id]")

    ruta = Path(sys.argv[1])
    usuario = sys.argv[2]
    datos_form = {"session_id": sys.argv[3]} if len(sys.argv) > 3 else {}

    # 1) Login -> token
    r = httpx.post(f"{URL}/auth/login",
                   data={"username": usuario, "password": getpass.getpass("Contraseña: ")})
    if r.status_code == 401:
        sys.exit("Usuario o contraseña incorrectos.")
    r.raise_for_status()
    cabeceras = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # 2) Turno de conversación (timeout largo: en CPU el primer turno tarda).
    with ruta.open("rb") as f:
        r = httpx.post(f"{URL}/conversar", headers=cabeceras,
                       files={"audio": (ruta.name, f)}, data=datos_form, timeout=300)
    if r.status_code == 403:
        sys.exit("Esta cuenta no es de adulto mayor: /conversar solo la usan pacientes.")
    r.raise_for_status()
    d = r.json()

    print(f"\nUsted dijo   : {d['texto_usuario']}")
    print(f"Thanatos dice: {d['texto_respuesta']}")
    print(f"Tiempos (s)  : {d['tiempos']}")
    print(f"session_id   : {d['session_id']}  (úsalo para continuar la charla)")

    audio = httpx.get(URL + d["audio_url"], timeout=60)
    audio.raise_for_status()
    destino = Path("respuesta" + Path(d["audio_url"]).suffix)
    destino.write_bytes(audio.content)
    print(f"Audio guardado en {destino}\n")


if __name__ == "__main__":
    main()
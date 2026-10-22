"""
Cliente de prueba: manda un audio a /conversar y guarda la respuesta hablada.

Uso (con el servidor ya corriendo):
    python scripts/probar_voz.py mi_audio.m4a
    python scripts/probar_voz.py otro_audio.wav <session_id>   # continuar la charla
"""
import sys
from pathlib import Path

import httpx

URL = "http://localhost:8000"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Uso: python scripts/probar_voz.py <audio> [session_id]")

    ruta = Path(sys.argv[1])
    datos_form = {"session_id": sys.argv[2]} if len(sys.argv) > 2 else {}

    # timeout largo: en CPU el primer turno puede tardar bastante.
    with ruta.open("rb") as f:
        r = httpx.post(f"{URL}/conversar", files={"audio": (ruta.name, f)},
                       data=datos_form, timeout=300)
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
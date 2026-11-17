"""
Comprueba el módulo de riesgo contra los casos de data/casos_riesgo.csv y contra
los mensajes del dataset semilla (que son todos de riesgo bajo).

Uso, desde thanatos-backend con .venv activo:  python scripts/probar_riesgo.py

Para ampliar las pruebas, agrega filas a data/casos_riesgo.csv:
    frase,nivel_esperado,origen        (nivel_esperado: verde, amarillo o rojo)
El script termina con error (código 1) si alguna frase de nivel ROJO no se detecta
como rojo, que es el fallo más grave.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.services import riesgo  # noqa: E402

CASOS = RAIZ / "data" / "casos_riesgo.csv"
DATASET = RAIZ / "data" / "dataset_respuestas_empaticas_es_mx_v1.xlsx"
NIVELES = ["verde", "amarillo", "rojo"]


def _tipo_de_error(esperado: str, obtenido: str) -> str | None:
    if esperado == obtenido:
        return None
    if riesgo.ORDEN[obtenido] < riesgo.ORDEN[esperado]:
        return "FALSO NEGATIVO CRÍTICO" if esperado == "rojo" else "FALSO NEGATIVO"
    return "SOBRE-ESCALADO"


def _casos_csv() -> list[tuple[str, str, str]]:
    with CASOS.open(encoding="utf-8-sig", newline="") as f:
        return [(fila["frase"], fila["nivel_esperado"].strip().lower(), fila.get("origen", ""))
                for fila in csv.DictReader(f) if fila.get("frase", "").strip()]


def _casos_dataset() -> list[tuple[str, str, str]]:
    if not DATASET.is_file():
        return []
    import openpyxl
    libro = openpyxl.load_workbook(DATASET, read_only=True, data_only=True)
    filas = libro["Dataset_empatico"].iter_rows(values_only=True)
    encabezado = [str(c) for c in next(filas)]
    i_id, i_msg = encabezado.index("id"), encabezado.index("mensaje_usuario")
    casos = [(str(f[i_msg]), "verde", f"dataset {f[i_id]}") for f in filas if f and f[i_msg]]
    libro.close()
    return casos


def main() -> None:
    casos = _casos_csv() + _casos_dataset()
    matriz: Counter = Counter()
    errores = []
    for frase, esperado, origen in casos:
        if esperado not in NIVELES:
            sys.exit(f"Nivel esperado inválido '{esperado}' en: {frase}")
        resultado = riesgo.clasificar(frase)
        matriz[(esperado, resultado.nivel)] += 1
        tipo = _tipo_de_error(esperado, resultado.nivel)
        if tipo:
            errores.append((tipo, esperado, resultado.nivel, resultado.categorias, frase, origen))

    print(f"Reglas v{riesgo.REGLAS_VERSION} | casos evaluados: {len(casos)}\n")
    print("Filas = nivel esperado, columnas = nivel obtenido")
    print(f"{'':10}" + "".join(f"{n:>10}" for n in NIVELES))
    for esperado in NIVELES:
        print(f"{esperado:10}" + "".join(f"{matriz[(esperado, o)]:>10}" for o in NIVELES))

    total_rojo = sum(matriz[("rojo", o)] for o in NIVELES)
    if total_rojo:
        print(f"\nDetección de rojo: {matriz[('rojo', 'rojo')]}/{total_rojo}")

    criticos = [e for e in errores if e[0] == "FALSO NEGATIVO CRÍTICO"]
    if errores:
        print(f"\nDiscrepancias ({len(errores)}):")
        for tipo, esperado, obtenido, categorias, frase, origen in sorted(errores):
            print(f"  [{tipo}] esperado {esperado}, obtuvo {obtenido} {categorias} <- {frase!r} ({origen})")
    else:
        print("\nSin discrepancias.")
    sys.exit(1 if criticos else 0)


if __name__ == "__main__":
    main()
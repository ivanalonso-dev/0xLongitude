"""
0xLongitude - Descarga los resultados de una query de Dune a CSV mediante la API.

Para planes sin exportación desde la web: lee el ÚLTIMO resultado ya calculado de la
query (no la vuelve a ejecutar), así que gasta pocos créditos.

Preparación (una sola vez):
  1. En Dune: Settings -> API -> crea una API key.
  2. En la carpeta 0XLongitude crea un archivo llamado .env con una línea:
         DUNE_API_KEY=tu_clave
     (.env está en .gitignore: no se sube a GitHub)
  3. Guarda la query en Dune y ejecútala allí una vez. El ID es el número de la URL:
         https://dune.com/queries/1234567  ->  1234567

Uso:
  python src/descargar_dune.py <query_id> <ruta_salida.csv>
Ejemplo:
  python src/descargar_dune.py 1234567 data/raw/dune/00a_nombres_cex.csv
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parent.parent
BASE = "https://api.dune.com/api/v1"
POR_PAGINA = 5000


def leer_clave() -> str:
    clave = os.environ.get("DUNE_API_KEY")
    env = RAIZ / ".env"
    if not clave and env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if linea.strip().startswith("DUNE_API_KEY="):
                clave = linea.split("=", 1)[1].strip().strip('"').strip("'")
    if not clave:
        sys.exit("Falta la API key: crea el archivo .env con DUNE_API_KEY=tu_clave (ver instrucciones arriba).")
    return clave


def descargar(query_id: str, clave: str) -> pd.DataFrame:
    cab = {"X-Dune-API-Key": clave}
    url = f"{BASE}/query/{query_id}/results/csv"
    params = {"limit": POR_PAGINA, "offset": 0}
    trozos = []
    while True:
        r = requests.get(url, headers=cab, params=params, timeout=120)
        if r.status_code == 401:
            sys.exit("Dune rechaza la API key (401). Revisa el archivo .env.")
        if r.status_code == 402:
            sys.exit("Dune indica que no quedan créditos o que el plan no lo permite (402).")
        if r.status_code == 404:
            sys.exit("Query no encontrada o sin resultados (404). ¿Está guardada y ejecutada al menos una vez en Dune?")
        r.raise_for_status()
        trozo = pd.read_csv(io.StringIO(r.text))
        trozos.append(trozo)
        print(f"  filas descargadas: {sum(len(t) for t in trozos):,}")
        siguiente = r.headers.get("x-dune-next-offset")
        if not siguiente or len(trozo) == 0:
            break
        params["offset"] = int(siguiente)
    return pd.concat(trozos, ignore_index=True)


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    query_id, salida = sys.argv[1], RAIZ / sys.argv[2]
    df = descargar(query_id, leer_clave())
    salida.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(salida, index=False)
    print(f"Guardado: {salida} ({len(df):,} filas, {len(df.columns)} columnas)")


if __name__ == "__main__":
    main()

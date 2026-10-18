"""
0xLongitude - Pruebas con datos sintéticos (sin internet, sin Dune, sin pytest).

Comprueba que la maquinaria de H1 hace lo que dice:
  1. Logística en numpy: llega al óptimo (gradiente ~ 0), binaria y multinomial.
  2. Etiquetado: un salto conocido se clasifica como continuación en la hora correcta.
  3. Potencia: con una señal regional plantada, el pipeline completo la detecta ("APORTA").
  4. Falsos positivos: con flujos regionales de puro ruido, NO la detecta.

Uso (desde la carpeta 0XLongitude):
    python tests/test_sinteticos.py
Tarda 1-3 minutos. Trabaja en una carpeta temporal: no toca los datos reales.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

RESULTADOS: list[tuple[str, bool, str]] = []


def comprobar(nombre: str, ok: bool, detalle: str = "") -> None:
    RESULTADOS.append((nombre, ok, detalle))
    print(f"[{'OK' if ok else 'FALLO'}] {nombre}" + (f" - {detalle}" if detalle else ""))


# --------------------------------------------------------------------------
def test_logistica() -> None:
    from logistica_np import LogisticRegression, roc_auc_score

    rng = np.random.default_rng(0)
    X = rng.normal(size=(400, 8))
    y = (X[:, 0] + rng.normal(size=400) > 0.3).astype(int)
    for C in (0.01, 1.0):
        m = LogisticRegression(C=C).fit(X, y)
        p = m.predict_proba(X)[:, 1]
        g_w = m.coef_[0] + C * X.T @ (p - y)
        g_b = C * np.sum(p - y)
        comprobar(f"logística binaria C={C}: gradiente ~ 0", max(abs(g_w).max(), abs(g_b)) < 1e-6,
                  f"max |grad| = {max(abs(g_w).max(), abs(g_b)):.1e}")
    y3 = rng.integers(0, 3, 400)
    y3[X[:, 1] > 1] = 2
    m = LogisticRegression(C=0.3).fit(X, y3)
    P = m.predict_proba(X)
    Y = (y3[:, None] == np.arange(3)[None, :]).astype(float)
    g = m.coef_ + 0.3 * (P - Y).T @ X
    comprobar("logística multinomial: gradiente ~ 0 y probabilidades suman 1",
              abs(g).max() < 1e-5 and np.allclose(P.sum(axis=1), 1),
              f"max |grad| = {abs(g).max():.1e}")
    comprobar("AUC: perfecta = 1, invertida = 0",
              roc_auc_score([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == 1.0
              and roc_auc_score([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]) == 0.0)


# --------------------------------------------------------------------------
def preparar_proyecto(tmp: Path) -> None:
    shutil.copytree(RAIZ / "src", tmp / "src")
    for d in ("data/raw/precios", "data/raw/dune", "data/processed", "results", "docs"):
        (tmp / d).mkdir(parents=True, exist_ok=True)


def escribir_precios(tmp: Path, ts: pd.DatetimeIndex, p: np.ndarray) -> None:
    bn = pd.DataFrame({"ts": ts, "open": p, "high": p * 1.0005, "low": p * 0.9995, "close": p,
                       "volume": 10.0, "trades": 100, "taker_buy_volume": 5.0})
    bn.to_csv(tmp / "data/raw/precios/binance_btcusdt_1h.csv", index=False)
    pd.DataFrame({"ts": ts, "open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}).to_csv(
        tmp / "data/raw/precios/coinbase_usdtusd_1h.csv", index=False)


def ejecutar(tmp: Path, *args: str) -> str:
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}   # Windows: evita errores con tildes y "·"
    r = subprocess.run([sys.executable, *args], cwd=tmp, capture_output=True, text=True,
                       encoding="utf-8", env=entorno)
    if r.returncode != 0:
        raise RuntimeError(f"Falló {' '.join(args)}:\n{r.stderr[-2000:]}")
    return r.stdout


def test_etiquetado() -> None:
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        preparar_proyecto(tmp)
        rng = np.random.default_rng(0)
        ts = pd.date_range("2022-01-01", periods=24 * 60, freq="h", tz="UTC")
        lp = np.cumsum(rng.normal(0, 0.002, len(ts))) + np.log(40000)
        lp[24 * 40:] += 0.10            # salto el día 40 (2022-02-10)
        lp[24 * 41 + 5:] += 0.10        # continúa en la hora 6 del día siguiente
        escribir_precios(tmp, ts, np.exp(lp))
        ejecutar(tmp, "src/etiquetas_eventos.py")
        e = pd.read_csv(tmp / "data/processed/eventos_etiquetados.csv").set_index("fecha")
        ok = ("2022-02-10" in e.index and e.loc["2022-02-10", "resultado"] == "continuacion"
              and e.loc["2022-02-10", "horas_hasta_barrera"] == 6)
        comprobar("etiquetado: salto conocido = continuación en la hora 6", ok)


# --------------------------------------------------------------------------
def pipeline_potencia(amplitud: float) -> str:
    """Pipeline completo con precios, primas, contexto y Dune sintéticos; devuelve el informe."""
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        preparar_proyecto(tmp)
        rng = np.random.default_rng(1)
        ts = pd.date_range("2021-12-01", "2024-12-31 23:00", freq="h", tz="UTC")
        vol = 0.006 * np.exp(np.cumsum(rng.normal(0, 0.01, len(ts))).clip(-1, 1))
        lp = np.cumsum(rng.normal(0, vol)) + np.log(40000)
        escribir_precios(tmp, ts, np.exp(lp))
        ejecutar(tmp, "src/etiquetas_eventos.py")

        fechas = pd.date_range("2021-12-01", "2024-12-31").strftime("%Y-%m-%d")
        pd.DataFrame({"fecha": fechas, "binance_spot_imbalance": rng.normal(0, 0.03, len(fechas)),
                      "coinbase_premium_pct": rng.normal(0, 0.01, len(fechas)),
                      "kimchi_premium_pct": 1.5 + rng.normal(0, 1, len(fechas)).cumsum() * 0.05}).to_csv(
            tmp / "data/processed/primas_diarias.csv", index=False)
        pd.DataFrame({"fecha": fechas, "funding_anualizado_pct": rng.normal(8, 5, len(fechas)),
                      "oi_cambio_pct": rng.normal(0, 4, len(fechas)),
                      "taker_buy_sell": np.exp(rng.normal(0.1, 0.05, len(fechas)))}).to_csv(
            tmp / "data/processed/contexto_diario.csv", index=False)

        ev = pd.read_csv(tmp / "data/processed/eventos_etiquetados.csv").set_index("fecha")
        filas = []
        for f in fechas:
            for reg in ("US", "EU", "ASIA", "BINANCE", "OFFSHORE"):
                for a in ("ETH", "WBTC", "USDT", "USDC"):
                    ent, sal = rng.uniform(5e7, 1e8), rng.uniform(5e7, 1e8)
                    if amplitud and reg == "US" and a == "USDT" and f in ev.index:
                        e = ev.loc[f]
                        ent += e["direccion"] * (e["A_continuacion"] - 0.3) * amplitud
                    filas.append(dict(fecha=f, region=reg, subregion="X", activo=a,
                                      entrada_externo=ent, salida_externo=sal, neto_externo=ent - sal,
                                      neto_otro_exchange=0, neto_interno=0, neto_staking=0,
                                      neto_total=ent - sal, transferencias=1, transferencias_externo=1))
        pd.DataFrame(filas).to_csv(tmp / "data/raw/dune/01_flujos_diarios_region.csv", index=False)
        ejecutar(tmp, "src/flujos_dune.py")
        return ejecutar(tmp, "src/modelo_h1.py")


def veredicto_A(informe: str) -> str:
    bloque = informe.split("=== A · continuación", 1)[1].split("\n===", 1)[0]
    linea = [l for l in bloque.splitlines() if "regional vs global" in l][0]
    return linea.strip()


def test_potencia_y_falsos_positivos() -> None:
    v = veredicto_A(pipeline_potencia(2e7))
    comprobar("potencia: señal plantada (~1 desviación típica) detectada", v.endswith("APORTA"), v)
    v = veredicto_A(pipeline_potencia(0.0))
    comprobar("falsos positivos: ruido puro NO detectado", v.endswith("no demostrado"), v)


# --------------------------------------------------------------------------
if __name__ == "__main__":
    test_logistica()
    test_etiquetado()
    test_potencia_y_falsos_positivos()
    fallos = [r for r in RESULTADOS if not r[1]]
    print(f"\n{len(RESULTADOS) - len(fallos)}/{len(RESULTADOS)} pruebas superadas")
    sys.exit(1 if fallos else 0)

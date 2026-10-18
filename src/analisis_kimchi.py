"""
0xLongitude - Paso 6 (parcial): ¿la kimchi premium anticipa el retorno de BTC?

SOLO periodo de entrenamiento (2022-01-01 a 2024-12-31). No toca 2025+.

Variables candidatas (calculadas con información disponible al cierre del día t):
  kimchi_nivel   kimchi premium media del día t
  kimchi_d1      cambio respecto al día anterior
  kimchi_d3      cambio respecto a hace 3 días
  kimchi_z30     nivel frente a su media y desviación de los 30 días anteriores
Referencia (lo que hay que batir):
  mom_1, mom_3   retorno de BTC de los últimos 1 y 3 días (momentum)

Objetivo: retorno logarítmico de BTC de t a t+h, h = 1, 2, 3 días.

Medidas:
  IC         correlación de Spearman entre la variable y el retorno futuro
  p_boot     p-valor por bootstrap de bloques (respeta la autocorrelación)
  t_hac      t de la regresión retorno ~ variable + momentum, con errores Newey-West
  quintiles  retorno medio futuro según el quintil de la variable
  estabilidad IC por año (2022, 2023, 2024)

Uso: python src/analisis_kimchi.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "data" / "processed" / "primas_diarias.csv"
SALIDA_TXT = RAIZ / "results" / "analisis_kimchi.txt"
SALIDA_CSV = RAIZ / "results" / "analisis_kimchi_ic.csv"

INICIO, FIN = "2022-01-01", "2025-01-01"   # fin exclusivo
HORIZONTES = [1, 2, 3]
VARIABLES = ["kimchi_nivel", "kimchi_d1", "kimchi_d3", "kimchi_z30"]
REFERENCIAS = ["mom_1", "mom_3"]
N_BOOT, BLOQUE, SEMILLA = 2000, 10, 42


def preparar() -> pd.DataFrame:
    d = pd.read_csv(ENTRADA, parse_dates=["fecha"]).sort_values("fecha")
    # se calcula todo con el histórico completo para que los primeros días de
    # 2022 tengan ventana, pero luego SOLO se evalúa el entrenamiento
    d = d[d["fecha"] < FIN].reset_index(drop=True)
    k = d["kimchi_premium_pct"]
    d["kimchi_nivel"] = k
    d["kimchi_d1"] = k.diff(1)
    d["kimchi_d3"] = k.diff(3)
    pasado = k.shift(1).rolling(30, min_periods=20)
    d["kimchi_z30"] = (k - pasado.mean()) / pasado.std()
    lp = np.log(d["btc_close"])
    d["mom_1"] = lp.diff(1)
    d["mom_3"] = lp.diff(3)
    for h in HORIZONTES:
        d[f"ret_{h}"] = lp.shift(-h) - lp
    return d[d["fecha"] >= INICIO].reset_index(drop=True)


def spearman(x: pd.Series, y: pd.Series) -> float:
    m = x.notna() & y.notna()
    return x[m].rank().corr(y[m].rank())


def p_bootstrap(x: pd.Series, y: pd.Series, rng: np.random.Generator) -> float:
    """p-valor bilateral de IC=0 con bootstrap de bloques móviles bajo la nula
    (se rompe la relación desplazando x en bloques respecto a y)."""
    m = x.notna() & y.notna()
    xr, yr = x[m].rank().to_numpy(), y[m].rank().to_numpy()
    n = len(xr)
    obs = np.corrcoef(xr, yr)[0, 1]
    nb = int(np.ceil(n / BLOQUE))
    nulos = np.empty(N_BOOT)
    for i in range(N_BOOT):
        inicios = rng.integers(0, n - BLOQUE, nb)
        idx = (inicios[:, None] + np.arange(BLOQUE)).ravel()[:n]
        nulos[i] = np.corrcoef(xr[idx], yr)[0, 1]
    return float((np.abs(nulos) >= abs(obs)).mean())


def ols_hac(y: np.ndarray, X: np.ndarray, lags: int) -> tuple[np.ndarray, np.ndarray]:
    """MCO con errores Newey-West. Devuelve coeficientes y estadísticos t."""
    X = np.column_stack([np.ones(len(X)), X])
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    u = y - X @ b
    Xu = X * u[:, None]
    S = Xu.T @ Xu
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        G = Xu[L:].T @ Xu[:-L]
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    return b, b / np.sqrt(np.diag(V))


def zscore(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std()


def main() -> None:
    d = preparar()
    rng = np.random.default_rng(SEMILLA)
    filas, lin = [], []
    lin.append("0xLongitude - ¿La kimchi premium anticipa el retorno de BTC?")
    lin.append(f"Periodo: {d['fecha'].min():%Y-%m-%d} -> {d['fecha'].max():%Y-%m-%d} "
               f"({len(d)} días) - SOLO entrenamiento")
    lin.append("")

    for h in HORIZONTES:
        y = d[f"ret_{h}"]
        for v in VARIABLES + REFERENCIAS:
            x = d[v]
            ic = spearman(x, y)
            p = p_bootstrap(x, y, rng)
            anual = {a: spearman(x[d["fecha"].dt.year == a], y[d["fecha"].dt.year == a])
                     for a in (2022, 2023, 2024)}
            fila = {"horizonte": h, "variable": v, "ic": ic, "p_boot": p,
                    **{f"ic_{a}": val for a, val in anual.items()}}
            if v in VARIABLES:
                m = x.notna() & y.notna() & d["mom_1"].notna()
                X = np.column_stack([zscore(x[m]), zscore(d.loc[m, "mom_1"])])
                _, t = ols_hac(y[m].to_numpy() * 100, X, lags=max(h, 5))
                fila["t_hac_con_momentum"] = t[1]
            filas.append(fila)

    res = pd.DataFrame(filas)
    SALIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    res.round(4).to_csv(SALIDA_CSV, index=False)

    lin.append("IC = correlación de Spearman con el retorno futuro. |IC| > 0,05 sostenido ya es útil en mercados.")
    lin.append("p_boot < 0,05 = poco probable por azar. t_hac = efecto controlando por momentum (|t| > 2 = relevante).")
    lin.append("Signo coherente en los 3 años = estable.")
    lin.append("")
    for h in HORIZONTES:
        lin.append(f"--- Retorno a {h} día(s) ---")
        sub = res[res["horizonte"] == h].copy()
        sub["estable"] = sub[["ic_2022", "ic_2023", "ic_2024"]].apply(
            lambda r: "sí" if (np.sign(r) == np.sign(r.iloc[0])).all() else "no", axis=1)
        cols = ["variable", "ic", "p_boot", "t_hac_con_momentum", "ic_2022", "ic_2023", "ic_2024", "estable"]
        lin.append(sub[cols].to_string(index=False, float_format=lambda f: f"{f:+.3f}", na_rep="-"))
        lin.append("")

    lin.append("--- Retorno medio futuro (%) por quintil de la variable (Q1 = valores más bajos) ---")
    for v in VARIABLES:
        q = pd.qcut(d[v], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
        t = d.groupby(q, observed=True)[[f"ret_{h}" for h in HORIZONTES]].mean() * 100
        t.columns = [f"{h}d" for h in HORIZONTES]
        lin.append(f"{v}:")
        lin.append(t.round(3).to_string())
        lin.append("")

    # --- Calidad del movimiento (posicionamiento del producto) ---
    # Pregunta: un movimiento de BTC acompañado de subida de la kimchi (empujado por Corea),
    # ¿continúa o se revierte? Se prueba con la interacción momentum x cambio de kimchi.
    lin.append("--- Calidad del movimiento: ¿el movimiento de hoy continúa si lo acompaña Corea? ---")
    lin.append("Modelo: ret_futuro ~ mom_1 + kimchi_d1 + mom_1*kimchi_d1 (variables estandarizadas, errores Newey-West)")
    lin.append("Interacción negativa = los movimientos empujados por Corea tienden a revertirse.")
    for h in HORIZONTES:
        m = d["mom_1"].notna() & d["kimchi_d1"].notna() & d[f"ret_{h}"].notna()
        a, b = zscore(d.loc[m, "mom_1"]), zscore(d.loc[m, "kimchi_d1"])
        coef, t = ols_hac(d.loc[m, f"ret_{h}"].to_numpy() * 100,
                          np.column_stack([a, b, a * b]), lags=max(h, 5))
        lin.append(f"  {h}d: mom_1 {coef[1]:+.3f} (t {t[1]:+.2f}) | kimchi_d1 {coef[2]:+.3f} (t {t[2]:+.2f}) "
                   f"| interacción {coef[3]:+.3f} (t {t[3]:+.2f})")
    lin.append("")
    lin.append("Retorno medio a 1-3 días (%) tras días de subida/bajada de BTC, según la kimchi suba o baje ese día:")
    dd = d.dropna(subset=["mom_1", "kimchi_d1"]).copy()
    dd["btc_hoy"] = np.where(dd["mom_1"] > 0, "BTC sube", "BTC baja")
    dd["corea_hoy"] = np.where(dd["kimchi_d1"] > 0, "kimchi sube", "kimchi baja")
    tab = dd.groupby(["btc_hoy", "corea_hoy"])[[f"ret_{h}" for h in HORIZONTES]].agg(["mean", "count"])
    tab2 = pd.DataFrame({f"{h}d": tab[(f"ret_{h}", "mean")] * 100 for h in HORIZONTES})
    tab2["n"] = tab[("ret_1", "count")]
    lin.append(tab2.round(3).to_string())
    lin.append("")

    lin.append(f"Pruebas realizadas: {len(VARIABLES) * len(HORIZONTES)} combinaciones de kimchi + 3 de interacción. "
               f"Con tantas pruebas, alguna sale 'significativa' por azar: exigir p_boot < 0,01 o estabilidad anual.")
    txt = "\n".join(lin)
    SALIDA_TXT.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"\nGuardado en:\n  {SALIDA_TXT}\n  {SALIDA_CSV}")


if __name__ == "__main__":
    main()

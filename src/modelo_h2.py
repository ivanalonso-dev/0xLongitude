"""
0xLongitude - H2: divergencia contado / derivados (prerregistro docs/07_PREREGISTRO_H2.md)

Evento divergente (día t, d = dirección del movimiento):
  1. binance_spot_imbalance * d <= 0      (el contado no empuja)
  2. oi_cambio_pct > 0                    (se abre apalancamiento)
  3. log(taker_buy_sell futuros) * d > 0  (los derivados empujan a favor)

Pruebas: diferencia de tasas B (reversión) y C (fragilidad) divergente vs. resto en 2022-2024,
y mejora incremental en walk-forward 2023-2024 sobre el modelo global de H1.
Test 2025-01-04 -> 2026-06-30 bloqueado salvo docs/SENAL_CONGELADA_H2.md + --abrir-test.

Uso: python src/modelo_h2.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modelo_h1 as h1  # noqa: E402  (reutiliza variables, ajuste y bootstrap de H1)

RAIZ = Path(__file__).resolve().parent.parent
CANDADO = RAIZ / "docs" / "SENAL_CONGELADA_H2.md"
TARGETS = {"B_reversion": "B · reversión", "C_fragilidad": "C · fragilidad"}


def marcar(d: pd.DataFrame, umbral_imb: float = 0.0, umbral_oi: float = 0.0) -> pd.Series:
    s = d["direccion"]
    c1 = d["binance_spot_imbalance"] * s <= umbral_imb
    c2 = d["oi_cambio_pct"] > umbral_oi
    c3 = d["log_taker_fut"] * s > 0
    return (c1 & c2 & c3).astype(float)


def diferencia_tasas(d: pd.DataFrame, tgt: str, rng, bloque_dias: int = 10) -> tuple[float, float, float, float, float]:
    f = pd.to_datetime(d["fecha"]).reset_index(drop=True)
    y = d[tgt].to_numpy()
    div = d["h2_div"].to_numpy() == 1
    if div.sum() == 0 or (~div).sum() == 0:
        return np.nan, np.nan, np.nan, np.nan, np.nan
    bloque = ((f - f.min()).dt.days // bloque_dias).to_numpy()
    ids = np.unique(bloque)
    idx = [np.where(bloque == b)[0] for b in ids]
    difs = []
    for _ in range(h1.N_BOOT):
        sel = np.concatenate([idx[j] for j in rng.choice(len(ids), len(ids), replace=True)])
        dv, yy = div[sel], y[sel]
        if dv.any() and (~dv).any():
            difs.append(yy[dv].mean() - yy[~dv].mean())
    t_div, t_resto = y[div].mean(), y[~div].mean()
    return t_div, t_resto, t_div - t_resto, float(np.quantile(difs, 0.025)), float(np.quantile(difs, 0.975))


def walk_forward(d: pd.DataFrame, globales: list[str], tgt: str, rng) -> str:
    fechas = pd.to_datetime(d["fecha"])
    trozos = []
    for q in h1.TRIMESTRES:
        fit = d[fechas < q.start_time - pd.Timedelta(days=h1.EMBARGO_DIAS)]
        ev = d[(fechas >= q.start_time) & (fechas <= q.end_time)]
        if len(ev) == 0:
            continue
        p_g, _ = h1.ajustar_y_predecir(fit, ev, globales, tgt)
        p_d, _ = h1.ajustar_y_predecir(fit, ev, globales + ["h2_div"], tgt)
        trozos.append((ev, p_g, p_d))
    ev = pd.concat([t[0] for t in trozos])
    pg, pd_ = np.concatenate([t[1] for t in trozos]), np.concatenate([t[2] for t in trozos])
    dm, lo, hi = h1.delta_bootstrap(ev["fecha"], ev[tgt].to_numpy(), pg, pd_, rng)
    return (f"  walk-forward 2023-2024 ({len(ev)} eventos): mejora log loss global+divergencia vs global "
            f"{dm:+.4f}  IC95 [{lo:+.4f}, {hi:+.4f}]")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--abrir-test", action="store_true")
    args = ap.parse_args()
    if args.abrir_test:
        if not CANDADO.exists():
            sys.exit(f"Test bloqueado: falta {CANDADO}.")
        sys.exit("El test de H2 se implementará solo si la exploración 2022-2024 cumple el criterio (prerregistro §5).")

    d, globales, _ = h1.construir_variables(False)
    d = d.dropna(subset=["binance_spot_imbalance", "oi_cambio_pct", "log_taker_fut"]).copy()
    d["h2_div"] = marcar(d)
    dev = d[d["fecha"] < h1.FIN_DESARROLLO].reset_index(drop=True)
    rng = np.random.default_rng(h1.SEMILLA)

    lin = ["0xLongitude - H2 divergencia contado / derivados (prerregistro 07)", ""]
    lin.append(f"Eventos 2022-2024 con las tres variables: {len(dev)} "
               f"(excluidos por datos ausentes: {(h1.construir_variables(False)[0]['fecha'] < h1.FIN_DESARROLLO).sum() - len(dev)})")
    por_anio = dev.assign(anio=dev["fecha"].str[:4]).groupby("anio")["h2_div"].agg(["sum", "size"])
    lin.append("Eventos divergentes por año: " + ", ".join(f"{a}: {int(r['sum'])}/{int(r['size'])}" for a, r in por_anio.iterrows()))
    n_div = int(dev["h2_div"].sum())
    if n_div < 30:
        lin.append(f"AVISO: solo {n_div} eventos divergentes (< 30): resultado NO CONCLUYENTE según el prerregistro.")
    lin.append("")

    lin.append("##### PRINCIPAL: tasa en eventos divergentes vs. resto (2022-2024) #####")
    for tgt, nombre in TARGETS.items():
        t_d, t_r, dif, lo, hi = diferencia_tasas(dev, tgt, rng)
        lin.append(f"{nombre}: divergentes {t_d:.3f} vs resto {t_r:.3f} | diferencia {dif:+.3f}  IC95 [{lo:+.3f}, {hi:+.3f}]"
                   + ("  -> diferencia positiva" if lo > 0 else ""))
        lin.append(walk_forward(dev, globales, tgt, rng))
    lin.append("")

    lin.append("##### SENSIBILIDAD (no cambia el veredicto) #####")
    for etiqueta, kw in [("imbalance*d <= -0,01", dict(umbral_imb=-0.01)), ("OI > +1 %", dict(umbral_oi=1.0))]:
        dv = dev.copy()
        dv["h2_div"] = marcar(dv, **kw)
        partes = []
        for tgt, nombre in TARGETS.items():
            t_d, t_r, dif, lo, hi = diferencia_tasas(dv, tgt, rng)
            partes.append(f"{nombre} {dif:+.3f} [{lo:+.3f}, {hi:+.3f}]")
        lin.append(f"{etiqueta} (n div = {int(dv['h2_div'].sum())}): " + " | ".join(partes))
    for nombre_dir, valor in [("solo subidas", 1), ("solo bajadas", -1)]:
        dv = dev[dev["direccion"] == valor].reset_index(drop=True)
        partes = []
        for tgt, nombre in TARGETS.items():
            t_d, t_r, dif, lo, hi = diferencia_tasas(dv, tgt, rng)
            partes.append(f"{nombre} {dif:+.3f} [{lo:+.3f}, {hi:+.3f}]")
        lin.append(f"{nombre_dir} (n div = {int(dv['h2_div'].sum())}): " + " | ".join(partes))

    txt = "\n".join(lin)
    salida = h1.RES / "evaluacion_h2_exploracion.txt"
    salida.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"\nGuardado en {salida}")


if __name__ == "__main__":
    main()

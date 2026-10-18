"""
0xLongitude - Etiquetado de movimientos (prerregistro H1 v2 + anexo v2.1)

Para cada día t:
  - r_t = retorno log diario de BTC en dólares reales (cierre de la vela de las 23:00 UTC)
  - sigma_t = desviación típica de los 30 retornos diarios ANTERIORES a t
  - evento si |r_t| > 0.5 * sigma_t (v3) ; dirección d_t = signo(r_t)
Para cada evento, en las 72 h siguientes al cierre de t, con máximos/mínimos horarios:
  - b = 1.0 * sigma_t * sqrt(3)
  - A (continuación): toca primero +b a favor de d_t
  - B (reversión):    toca primero -b en contra (si ambas en la misma hora -> reversión)
  - neutro:           no toca ninguna
  - C (fragilidad):   MAE > 1.5 * sigma_t * sqrt(3)
  - MFE, MAE y retornos a 1/2/3 días alineados con d_t

Entrada:  data/raw/precios/binance_btcusdt_1h.csv, data/raw/precios/coinbase_usdtusd_1h.csv
Salida:   data/processed/eventos_etiquetados.csv
          results/eventos_resumen.txt  (solo diseño + validación, 2022-2024)

Uso: python src/etiquetas_eventos.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PRECIOS = RAIZ / "data" / "raw" / "precios"
SALIDA = RAIZ / "data" / "processed" / "eventos_etiquetados.csv"
RESUMEN = RAIZ / "results" / "eventos_resumen.txt"

K_EVENTO = 0.5        # umbral de evento en sigmas (prerregistro v3; v2 era 1.0)
K_BARRERA = 1.0       # barrera en sigmas * sqrt(H)
K_FRAGIL = 1.5        # fragilidad en sigmas * sqrt(H)
H_DIAS = 3
H_HORAS = 24 * H_DIAS
MAX_HORAS_FALTANTES = 3
VENTANA_SIGMA = 30
FIN_VALIDACION = "2025-01-01"


def cargar_horario() -> pd.DataFrame:
    bn = pd.read_csv(PRECIOS / "binance_btcusdt_1h.csv", parse_dates=["ts"])
    us = pd.read_csv(PRECIOS / "coinbase_usdtusd_1h.csv", parse_dates=["ts"])
    for d in (bn, us):
        d["ts"] = pd.to_datetime(d["ts"], utc=True)
    h = bn[["ts", "high", "low", "close"]].merge(
        us[["ts", "close"]].rename(columns={"close": "usdt_usd"}), on="ts", how="left")
    h["usdt_usd"] = h["usdt_usd"].ffill(limit=2)
    for c in ["high", "low", "close"]:
        h[c] = h[c] * h["usdt_usd"]
    # rejilla horaria completa: las horas que faltan quedan como NaN (no se interpolan)
    rejilla = pd.date_range(h["ts"].min(), h["ts"].max(), freq="h", tz="UTC")
    return h.set_index("ts").reindex(rejilla).rename_axis("ts")[["high", "low", "close"]]


def diario(h: pd.DataFrame) -> pd.DataFrame:
    # cierre del día t = cierre de la vela que abre a las 23:00 UTC de t
    c23 = h[h.index.hour == 23]["close"]
    d = pd.DataFrame({"cierre": c23.values}, index=c23.index.normalize())
    d.index.name = "fecha"
    d["r"] = np.log(d["cierre"]).diff()
    d["sigma"] = d["r"].shift(1).rolling(VENTANA_SIGMA, min_periods=VENTANA_SIGMA).std()
    rango = h.groupby(h.index.normalize()).agg(alto=("high", "max"), bajo=("low", "min"))
    d = d.join(rango)
    d["rango_rel"] = np.log(d["alto"] / d["bajo"])
    return d


def etiquetar(h: pd.DataFrame, d: pd.DataFrame) -> pd.DataFrame:
    filas = []
    ev = d[(d["r"].abs() > K_EVENTO * d["sigma"]) & d["sigma"].notna() & d["cierre"].notna()]
    raiz_h = np.sqrt(H_DIAS)
    for fecha, x in ev.iterrows():
        inicio = fecha + pd.Timedelta(days=1)                  # 00:00 UTC de t+1
        tramo = h.loc[inicio: inicio + pd.Timedelta(hours=H_HORAS - 1)]
        if len(tramo) < H_HORAS or tramo["close"].isna().sum() > MAX_HORAS_FALTANTES:
            continue
        dirc = 1.0 if x["r"] > 0 else -1.0
        p0, sig = x["cierre"], x["sigma"]
        b = K_BARRERA * sig * raiz_h
        # excursiones logarítmicas alineadas con la dirección del movimiento
        a_favor = np.log((tramo["high"] if dirc > 0 else tramo["low"]) / p0) * dirc
        en_contra = np.log((tramo["low"] if dirc > 0 else tramo["high"]) / p0) * dirc
        toca_favor = (a_favor >= b).to_numpy()
        toca_contra = (en_contra <= -b).to_numpy()
        i_f = int(np.argmax(toca_favor)) if toca_favor.any() else None
        i_c = int(np.argmax(toca_contra)) if toca_contra.any() else None
        if i_f is None and i_c is None:
            resultado = "neutro"
        elif i_c is not None and (i_f is None or i_c <= i_f):   # misma hora -> reversión
            resultado = "reversion"
        else:
            resultado = "continuacion"
        mfe = float(np.nanmax(a_favor))
        mae = float(-np.nanmin(en_contra))
        fila = {
            "fecha": fecha.date().isoformat(), "direccion": int(dirc), "r": x["r"], "sigma": sig,
            "r_en_sigmas": abs(x["r"]) / sig, "rango_rel": x["rango_rel"], "barrera": b,
            "resultado": resultado,
            "A_continuacion": int(resultado == "continuacion"),
            "B_reversion": int(resultado == "reversion"),
            "C_fragilidad": int(mae > K_FRAGIL * sig * raiz_h),
            "mfe": mfe, "mae": mae,
            "horas_hasta_barrera": (min(v for v in (i_f, i_c) if v is not None) + 1)
                                   if resultado != "neutro" else np.nan,
            "horas_faltantes": int(tramo["close"].isna().sum()),
        }
        for k in (1, 2, 3):
            pk = tramo["close"].iloc[24 * k - 1]
            fila[f"ret_{k}d_alineado"] = np.log(pk / p0) * dirc if pd.notna(pk) else np.nan
        filas.append(fila)
    return pd.DataFrame(filas)


def resumen(e: pd.DataFrame, d: pd.DataFrame) -> str:
    e = e[e["fecha"] < FIN_VALIDACION]
    dias = d[(d.index < FIN_VALIDACION) & d["sigma"].notna()]
    lin = ["0xLongitude - eventos etiquetados (SOLO diseño + validación, 2022-2024)", ""]
    lin.append(f"Días con sigma: {len(dias)} | eventos: {len(e)} ({len(e) / len(dias):.1%} de los días)")
    lin.append(f"Subidas: {(e['direccion'] > 0).sum()} | bajadas: {(e['direccion'] < 0).sum()}")
    lin.append("")
    lin.append("Resultado (tasa base):")
    lin.append(e["resultado"].value_counts(normalize=True).round(3).to_string())
    lin.append(f"C_fragilidad: {e['C_fragilidad'].mean():.3f}")
    lin.append("")
    lin.append("Por dirección del movimiento:")
    t = e.groupby("direccion")[["A_continuacion", "B_reversion", "C_fragilidad"]].mean().round(3)
    t.index = t.index.map({1: "subida", -1: "bajada"})
    lin.append(t.to_string())
    lin.append("")
    lin.append("Por año:")
    t = e.assign(anio=e["fecha"].str[:4]).groupby("anio")[["A_continuacion", "B_reversion", "C_fragilidad"]].agg(["mean"]).round(3)
    t.columns = [c[0] for c in t.columns]
    t["n"] = e.assign(anio=e["fecha"].str[:4]).groupby("anio").size()
    lin.append(t.to_string())
    lin.append("")
    lin.append("MFE / MAE (en sigmas*sqrt(3)) - mediana: "
               f"{(e['mfe'] / e['barrera']).median():.2f} / {(e['mae'] / e['barrera']).median():.2f}")
    lin.append(f"Retorno alineado medio a 1/2/3 d (%): "
               + " / ".join(f"{e[f'ret_{k}d_alineado'].mean() * 100:+.3f}" for k in (1, 2, 3)))
    return "\n".join(lin)


def main() -> None:
    h = cargar_horario()
    d = diario(h)
    e = etiquetar(h, d)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    e.to_csv(SALIDA, index=False)
    # también se guarda la tabla diaria (sigma, r, rango) para el modelo
    d.reset_index().assign(fecha=lambda x: x["fecha"].dt.date.astype(str)).to_csv(
        RAIZ / "data" / "processed" / "btc_diario_usd.csv", index=False)
    txt = resumen(e, d)
    RESUMEN.parent.mkdir(parents=True, exist_ok=True)
    RESUMEN.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"\nGuardado en {SALIDA}")


if __name__ == "__main__":
    main()

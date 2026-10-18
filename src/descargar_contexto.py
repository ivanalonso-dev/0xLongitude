"""
0xLongitude - Datos de contexto (sin Dune), para adelantar trabajo.

Descarga desde 2022-01-01 hasta hoy:
  1) Funding rate de BTCUSDT perpetuo en Binance (cada 8 h)        -> apalancamiento
  2) Métricas diarias de futuros de Binance (data.binance.vision):
     open interest, ratio largos/cortos, ratio compras/ventas agresoras
  3) Oferta total de USDT y USDC (DefiLlama)                         -> pólvora seca

Salidas:
  data/raw/contexto/binance_funding_btcusdt.csv
  data/raw/contexto/binance_metricas_btcusdt_diario.csv
  data/raw/contexto/stablecoins_oferta_diaria.csv
  data/processed/contexto_diario.csv         (todo unido por día)
  results/contexto_resumen.txt               (solo periodo de entrenamiento)

Uso:  python src/descargar_contexto.py      (reanudable)
"""

from __future__ import annotations

import io
import sys
import time
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

INICIO = date(2022, 1, 1)
FIN_ENTRENAMIENTO = "2025-01-01"
RAIZ = Path(__file__).resolve().parent.parent
DIR_CTX = RAIZ / "data" / "raw" / "contexto"
DIR_PROC = RAIZ / "data" / "processed"
DIR_RES = RAIZ / "results"

SESION = requests.Session()
SESION.headers.update({"User-Agent": "0xLongitude/0.1 (research)"})


def get(url: str, params: dict | None = None, intentos: int = 6, aceptar_404: bool = False):
    espera = 1.0
    for i in range(intentos):
        try:
            r = SESION.get(url, params=params, timeout=30)
            if aceptar_404 and r.status_code == 404:
                return None
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if i == intentos - 1:
                raise
            print(f"    aviso: {e} -> reintento en {espera:.0f}s")
            time.sleep(espera)
            espera = min(espera * 2, 60)


# --------------------------------------------------------------------------
# 1) Funding rate Binance (máx. 1000 registros por petición)
# --------------------------------------------------------------------------
def descargar_funding() -> pd.DataFrame:
    ruta = DIR_CTX / "binance_funding_btcusdt.csv"
    if ruta.exists():
        cache = pd.read_csv(ruta)
        desde_ms = int(cache["funding_time"].max()) + 1
    else:
        cache = pd.DataFrame()
        desde_ms = int(datetime(INICIO.year, INICIO.month, INICIO.day, tzinfo=timezone.utc).timestamp() * 1000)
    print(f"[Funding Binance BTCUSDT] desde {pd.Timestamp(desde_ms, unit='ms'):%Y-%m-%d}")
    filas = []
    while True:
        datos = get("https://fapi.binance.com/fapi/v1/fundingRate",
                    {"symbol": "BTCUSDT", "startTime": desde_ms, "limit": 1000}).json()
        if not datos:
            break
        for x in datos:
            filas.append({"funding_time": int(x["fundingTime"]),
                          "funding_rate": float(x["fundingRate"])})
        nuevo = int(datos[-1]["fundingTime"]) + 1
        if nuevo <= desde_ms or len(datos) < 1000:
            break
        desde_ms = nuevo
        time.sleep(0.3)
    df = pd.concat([cache, pd.DataFrame(filas)], ignore_index=True)
    df = df.drop_duplicates("funding_time").sort_values("funding_time")
    DIR_CTX.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False)
    print(f"    {len(df):,} registros")
    return df


# --------------------------------------------------------------------------
# 2) Métricas diarias de futuros (un zip por día, filas cada 5 min)
# --------------------------------------------------------------------------
URL_METRICAS = "https://data.binance.vision/data/futures/um/daily/metrics/BTCUSDT/BTCUSDT-metrics-{d}.zip"


def resumir_metricas(csv_bytes: bytes, dia: date) -> dict:
    m = pd.read_csv(io.BytesIO(csv_bytes))
    m = m.sort_values("create_time")
    # Binance publica a veces filas con open interest a 0: se ignoran
    oi = m[(m["sum_open_interest"] > 0) & (m["sum_open_interest_value"] > 0)]
    return {
        "fecha": dia.isoformat(),
        "oi_btc": float(oi["sum_open_interest"].iloc[-1]) if len(oi) else None,
        "oi_usd": float(oi["sum_open_interest_value"].iloc[-1]) if len(oi) else None,
        "ls_ratio_top": float(m["sum_toptrader_long_short_ratio"].mean()),
        "ls_ratio_cuentas": float(m["count_long_short_ratio"].mean()),
        "taker_buy_sell": float(m["sum_taker_long_short_vol_ratio"].mean()),
        "muestras": len(m),
    }


def descargar_metricas() -> pd.DataFrame:
    ruta = DIR_CTX / "binance_metricas_btcusdt_diario.csv"
    cache = pd.read_csv(ruta) if ruta.exists() else pd.DataFrame(columns=["fecha"])
    if "oi_usd" in cache:
        # días guardados con open interest a 0 (versión anterior del script): se vuelven a bajar
        malos = cache["oi_usd"].isna() | (cache["oi_usd"] <= 0)
        cache = cache[~malos]
    hechos = set(cache["fecha"].astype(str))
    ayer = datetime.now(timezone.utc).date() - timedelta(days=1)
    pendientes = [INICIO + timedelta(days=i) for i in range((ayer - INICIO).days + 1)]
    pendientes = [d for d in pendientes if d.isoformat() not in hechos]
    print(f"[Métricas futuros Binance] {len(pendientes)} días pendientes")
    filas, faltan = [], []
    for n, dia in enumerate(pendientes, 1):
        r = get(URL_METRICAS.format(d=dia.isoformat()), aceptar_404=True)
        if r is None:
            faltan.append(dia.isoformat())
        else:
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                filas.append(resumir_metricas(z.read(z.namelist()[0]), dia))
        if n % 100 == 0 or n == len(pendientes):
            cache = pd.concat([cache, pd.DataFrame(filas)], ignore_index=True)
            cache = cache.drop_duplicates("fecha").sort_values("fecha")
            DIR_CTX.mkdir(parents=True, exist_ok=True)
            cache.to_csv(ruta, index=False)
            filas = []
            print(f"    ... {n}/{len(pendientes)}")
        time.sleep(0.05)
    if faltan:
        print(f"    días sin archivo en Binance: {len(faltan)} (p. ej. {', '.join(faltan[:5])})")
    print(f"    {len(cache):,} días")
    return cache


# --------------------------------------------------------------------------
# 3) Oferta de stablecoins (DefiLlama: id 1 = USDT, id 2 = USDC)
# --------------------------------------------------------------------------
def descargar_stablecoins() -> pd.DataFrame:
    print("[Oferta USDT / USDC - DefiLlama]")
    series = {}
    for nombre, sid in [("usdt", 1), ("usdc", 2)]:
        datos = get("https://stablecoins.llama.fi/stablecoincharts/all",
                    {"stablecoin": sid}).json()
        s = {}
        for x in datos:
            f = datetime.fromtimestamp(int(x["date"]), timezone.utc).date().isoformat()
            v = (x.get("totalCirculatingUSD") or x.get("totalCirculating") or {}).get("peggedUSD")
            if v is not None:
                s[f] = float(v)
        series[f"{nombre}_oferta_usd"] = pd.Series(s)
    df = pd.DataFrame(series).rename_axis("fecha").reset_index()
    df = df[df["fecha"] >= INICIO.isoformat()].sort_values("fecha")
    DIR_CTX.mkdir(parents=True, exist_ok=True)
    df.to_csv(DIR_CTX / "stablecoins_oferta_diaria.csv", index=False)
    print(f"    {len(df):,} días")
    return df


# --------------------------------------------------------------------------
# Unión diaria
# --------------------------------------------------------------------------
def unir(fund: pd.DataFrame, met: pd.DataFrame, st: pd.DataFrame) -> pd.DataFrame:
    f = fund.copy()
    f["fecha"] = pd.to_datetime(f["funding_time"], unit="ms", utc=True).dt.date.astype(str)
    f = f.groupby("fecha").agg(funding_medio=("funding_rate", "mean"),
                               funding_n=("funding_rate", "count")).reset_index()
    f["funding_anualizado_pct"] = f["funding_medio"] * 3 * 365 * 100
    d = f.merge(met, on="fecha", how="outer").merge(st, on="fecha", how="outer")
    d = d.sort_values("fecha").reset_index(drop=True)
    d.loc[d["oi_usd"] <= 0, ["oi_usd", "oi_btc"]] = None
    d["oi_cambio_pct"] = d["oi_usd"].pct_change(fill_method=None) * 100
    for c in ["usdt_oferta_usd", "usdc_oferta_usd"]:
        d[c.replace("_oferta_usd", "_emision_usd")] = d[c].diff()
    d = d[d["fecha"] >= INICIO.isoformat()]
    return d


def resumen(d: pd.DataFrame) -> str:
    t = d[d["fecha"] < FIN_ENTRENAMIENTO]
    lin = ["0xLongitude - datos de contexto (SOLO entrenamiento 2022-2024)", ""]
    lin.append(f"Días: {len(t)}")
    cols = ["funding_anualizado_pct", "oi_usd", "oi_cambio_pct", "ls_ratio_top",
            "ls_ratio_cuentas", "taker_buy_sell", "usdt_emision_usd", "usdc_emision_usd"]
    for c in cols:
        s = t[c].dropna()
        lin.append(f"{c:24s} n={len(s):4d}  faltan={t[c].isna().sum():4d}  "
                   f"media={s.mean():.4g}  p5={s.quantile(.05):.4g}  p95={s.quantile(.95):.4g}")
    return "\n".join(lin)


def main() -> None:
    print(f"Proyecto: {RAIZ}\n")
    fund = descargar_funding()
    met = descargar_metricas()
    st = descargar_stablecoins()
    d = unir(fund, met, st)
    DIR_PROC.mkdir(parents=True, exist_ok=True)
    DIR_RES.mkdir(parents=True, exist_ok=True)
    d.to_csv(DIR_PROC / "contexto_diario.csv", index=False)
    txt = resumen(d)
    (DIR_RES / "contexto_resumen.txt").write_text(txt, encoding="utf-8")
    print("\n" + txt)
    print(f"\nGuardado en {DIR_PROC / 'contexto_diario.csv'}")


if __name__ == "__main__":
    sys.exit(main())

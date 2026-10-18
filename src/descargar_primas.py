"""
0xLongitude - Paso 3: descarga de precios y cálculo de primas regionales.

Descarga velas horarias de BTC desde 2022-01-01 hasta hoy:
  - Coinbase  BTC-USD   (demanda de EE. UU.)
  - Coinbase  USDT-USD  (para pasar Binance a dólares reales)
  - Binance   BTCUSDT   (referencia global)
  - Upbit     KRW-BTC   (demanda de Corea)
  - Tipo de cambio USD/KRW diario (BCE vía Frankfurter)

Calcula:
  - Coinbase premium (%) = (Coinbase / Binance_USD - 1) * 100
  - Kimchi premium  (%)  = (Upbit / USDKRW / Binance_USD - 1) * 100
  donde Binance_USD = BTCUSDT * precio USDT-USD (Coinbase), para que los
  desanclajes de USDT no se confundan con demanda regional.

Uso (desde la carpeta 0XLongitude):
    python src/descargar_primas.py

Es reanudable: si se corta, al volver a ejecutarlo continúa donde lo dejó.
Requisitos: pip install requests pandas
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------
INICIO = datetime(2022, 1, 1, tzinfo=timezone.utc)
RAIZ = Path(__file__).resolve().parent.parent
DIR_PRECIOS = RAIZ / "data" / "raw" / "precios"
DIR_PROCESADO = RAIZ / "data" / "processed"
DIR_RESULTADOS = RAIZ / "results"

SESION = requests.Session()
SESION.headers.update({"User-Agent": "0xLongitude/0.1 (research)"})


def ahora_hora() -> datetime:
    """Última hora completa en UTC (la vela en curso no se usa)."""
    n = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return n - timedelta(hours=1)


def get_json(url: str, params: dict | None = None, intentos: int = 6):
    """GET con reintentos y espera ante límites de peticiones."""
    espera = 1.0
    for i in range(intentos):
        try:
            r = SESION.get(url, params=params, timeout=30)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if i == intentos - 1:
                raise
            print(f"    aviso: {e} -> reintento en {espera:.0f}s")
            time.sleep(espera)
            espera = min(espera * 2, 60)


def cargar_cache(ruta: Path) -> pd.DataFrame:
    if ruta.exists():
        df = pd.read_csv(ruta, parse_dates=["ts"])
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        return df
    return pd.DataFrame(columns=["ts", "open", "high", "low", "close", "volume"])


def guardar(df: pd.DataFrame, ruta: Path) -> pd.DataFrame:
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c])
    df = (
        df.drop_duplicates("ts", keep="last")
        .sort_values("ts")
        .reset_index(drop=True)
    )
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False)
    return df


def punto_de_partida(cache: pd.DataFrame) -> datetime:
    if cache.empty:
        return INICIO
    return cache["ts"].max().to_pydatetime() + timedelta(hours=1)


# --------------------------------------------------------------------------
# Coinbase BTC-USD (máx. 300 velas por petición)
# --------------------------------------------------------------------------
def descargar_coinbase(producto: str = "BTC-USD") -> pd.DataFrame:
    ruta = DIR_PRECIOS / f"coinbase_{producto.replace('-', '').lower()}_1h.csv"
    cache = cargar_cache(ruta)
    desde, fin = punto_de_partida(cache), ahora_hora()
    print(f"[Coinbase {producto}] desde {desde:%Y-%m-%d %H:%M} hasta {fin:%Y-%m-%d %H:%M}")
    filas = []
    while desde <= fin:
        hasta = min(desde + timedelta(hours=299), fin)
        datos = get_json(
            f"https://api.exchange.coinbase.com/products/{producto}/candles",
            {"granularity": 3600, "start": desde.isoformat(), "end": hasta.isoformat()},
        )
        # formato: [time, low, high, open, close, volume]
        for t, lo, hi, op, cl, vol in datos:
            filas.append({"ts": pd.Timestamp(t, unit="s", tz="UTC"),
                          "open": op, "high": hi, "low": lo, "close": cl, "volume": vol})
        desde = hasta + timedelta(hours=1)
        time.sleep(0.25)
        if len(filas) >= 6000:
            cache = guardar(pd.concat([cache, pd.DataFrame(filas)]), ruta)
            filas = []
            print(f"    ... {cache['ts'].max():%Y-%m-%d}")
    if filas:
        cache = guardar(pd.concat([cache, pd.DataFrame(filas)]), ruta)
    print(f"    {len(cache):,} velas")
    return cache


# --------------------------------------------------------------------------
# Binance BTCUSDT (máx. 1000 velas por petición)
# --------------------------------------------------------------------------
BINANCE_BASES = ["https://api.binance.com", "https://data-api.binance.vision"]


def descargar_binance() -> pd.DataFrame:
    ruta = DIR_PRECIOS / "binance_btcusdt_1h.csv"
    cache = cargar_cache(ruta)
    if not cache.empty and "taker_buy_volume" not in cache.columns:
        print("    la caché no tiene volumen agresor: se descarga de nuevo")
        cache = cache.iloc[0:0]
    desde, fin = punto_de_partida(cache), ahora_hora()
    print(f"[Binance BTCUSDT] desde {desde:%Y-%m-%d %H:%M} hasta {fin:%Y-%m-%d %H:%M}")
    base = None
    for b in BINANCE_BASES:
        try:
            get_json(f"{b}/api/v3/ping", intentos=2)
            base = b
            break
        except requests.RequestException:
            continue
    if base is None:
        sys.exit("No se puede acceder a la API de Binance.")
    filas = []
    while desde <= fin:
        datos = get_json(
            f"{base}/api/v3/klines",
            {"symbol": "BTCUSDT", "interval": "1h",
             "startTime": int(desde.timestamp() * 1000),
             "endTime": int(fin.timestamp() * 1000), "limit": 1000},
        )
        if not datos:
            break
        for k in datos:
            # k[8] = nº de operaciones, k[9] = volumen base comprado por agresores (taker buy)
            filas.append({"ts": pd.Timestamp(k[0], unit="ms", tz="UTC"),
                          "open": float(k[1]), "high": float(k[2]), "low": float(k[3]),
                          "close": float(k[4]), "volume": float(k[5]),
                          "trades": int(k[8]), "taker_buy_volume": float(k[9])})
        desde = pd.Timestamp(datos[-1][0], unit="ms", tz="UTC").to_pydatetime() + timedelta(hours=1)
        time.sleep(0.2)
    if filas:
        cache = guardar(pd.concat([cache, pd.DataFrame(filas)]), ruta)
    print(f"    {len(cache):,} velas")
    return cache


# --------------------------------------------------------------------------
# Upbit KRW-BTC (máx. 200 velas por petición, se pagina hacia atrás)
# --------------------------------------------------------------------------
def descargar_upbit() -> pd.DataFrame:
    ruta = DIR_PRECIOS / "upbit_krwbtc_1h.csv"
    cache = cargar_cache(ruta)
    desde, fin = punto_de_partida(cache), ahora_hora()
    print(f"[Upbit KRW-BTC] desde {desde:%Y-%m-%d %H:%M} hasta {fin:%Y-%m-%d %H:%M}")
    # Upbit devuelve las 'count' velas anteriores a 'to' (exclusivo). Se avanza
    # en ventanas de 200 h hacia delante para que la reanudación sea segura.
    filas = []
    while desde <= fin:
        hasta = min(desde + timedelta(hours=200), fin + timedelta(hours=1))
        datos = get_json(
            "https://api.upbit.com/v1/candles/minutes/60",
            {"market": "KRW-BTC", "count": 200,
             "to": hasta.strftime("%Y-%m-%dT%H:%M:%SZ")},
        )
        for c in datos or []:
            ts = pd.Timestamp(c["candle_date_time_utc"], tz="UTC")
            if pd.Timestamp(desde) <= ts < pd.Timestamp(hasta):
                filas.append({"ts": ts, "open": c["opening_price"], "high": c["high_price"],
                              "low": c["low_price"], "close": c["trade_price"],
                              "volume": c["candle_acc_trade_volume"]})
        desde = hasta
        time.sleep(0.15)
        if len(filas) >= 5000:
            cache = guardar(pd.concat([cache, pd.DataFrame(filas)]), ruta)
            filas = []
            print(f"    ... {cache['ts'].max():%Y-%m-%d}")
    if filas:
        cache = guardar(pd.concat([cache, pd.DataFrame(filas)]), ruta)
    print(f"    {len(cache):,} velas")
    return cache


# --------------------------------------------------------------------------
# Tipo de cambio USD/KRW (BCE vía Frankfurter, solo días hábiles)
# --------------------------------------------------------------------------
FX_BASES = ["https://api.frankfurter.dev/v1", "https://api.frankfurter.app"]


def descargar_fx() -> pd.DataFrame:
    ruta = DIR_PRECIOS / "fx_usd_krw_jpy_diario.csv"
    hoy = datetime.now(timezone.utc).date()
    print(f"[FX USD/KRW, USD/JPY] {INICIO.date()} -> {hoy}")
    filas = []
    for base in FX_BASES:
        try:
            # se pide por años para no hacer peticiones enormes
            filas = []
            inicio_fx = (INICIO - timedelta(days=10)).date()  # para tener el tipo vigente el 01-01-2022
            for anio in range(inicio_fx.year, hoy.year + 1):
                ini = max(datetime(anio, 1, 1).date(), inicio_fx)
                fin = min(datetime(anio, 12, 31).date(), hoy)
                datos = get_json(f"{base}/{ini}..{fin}", {"from": "USD", "to": "KRW,JPY"}, intentos=3)
                for dia, tasas in datos["rates"].items():
                    filas.append({"fecha": dia, "usdkrw": tasas.get("KRW"), "usdjpy": tasas.get("JPY")})
            break
        except requests.RequestException as e:
            print(f"    {base} no responde ({e}); probando alternativa")
    if not filas:
        sys.exit("No se ha podido descargar el tipo de cambio.")
    fx = pd.DataFrame(filas)
    fx["fecha"] = pd.to_datetime(fx["fecha"]).dt.date
    fx = fx.drop_duplicates("fecha").sort_values("fecha")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fx.to_csv(ruta, index=False)
    print(f"    {len(fx):,} días hábiles")
    return fx


# --------------------------------------------------------------------------
# Cálculo de primas
# --------------------------------------------------------------------------
def calcular_primas(cb: pd.DataFrame, bn: pd.DataFrame, up: pd.DataFrame,
                    fx: pd.DataFrame, usdt: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    h = (
        bn[["ts", "close", "volume", "taker_buy_volume"]].rename(
            columns={"close": "binance_usdt", "volume": "binance_volume", "taker_buy_volume": "binance_taker_buy"})
        .merge(cb[["ts", "close"]].rename(columns={"close": "coinbase_usd"}), on="ts", how="left")
        .merge(up[["ts", "close"]].rename(columns={"close": "upbit_krw"}), on="ts", how="left")
        .merge(usdt[["ts", "close"]].rename(columns={"close": "usdt_usd"}), on="ts", how="left")
    )
    # USDT no siempre vale 1 USD (LUNA 2022, FTX 2022, USDC/SVB 2023).
    # Se pasa Binance a dólares reales para que la prima mida demanda y no el desanclaje.
    # Huecos de USDT-USD: se arrastra el último precio como máximo 2 horas; más allá
    # se deja vacío (no se interpolan precios en posibles episodios de estrés).
    h["usdt_usd"] = h["usdt_usd"].ffill(limit=2)
    h["binance_usd"] = h["binance_usdt"] * h["usdt_usd"]
    h["fecha"] = h["ts"].dt.date

    # FX point-in-time: el tipo del BCE del día D se publica hacia las 16:00 CET.
    # Se considera disponible a las 15:00 UTC de D y cada hora usa el último tipo YA publicado
    # (antes se aplicaba el tipo de D a todas las horas de D, incluidas las previas a su publicación).
    fx_t = fx[["fecha", "usdkrw"]].dropna().copy()
    fx_t["disponible_en"] = pd.to_datetime(fx_t["fecha"]).dt.tz_localize("UTC") + pd.Timedelta(hours=15)
    fx_t = fx_t.sort_values("disponible_en")[["disponible_en", "usdkrw"]]
    fx_t["disponible_en"] = fx_t["disponible_en"].astype("datetime64[ns, UTC]")
    h["ts"] = h["ts"].astype("datetime64[ns, UTC]")
    h = pd.merge_asof(h.sort_values("ts"), fx_t, left_on="ts", right_on="disponible_en",
                      direction="backward").drop(columns="disponible_en")

    h["coinbase_premium_pct"] = (h["coinbase_usd"] / h["binance_usd"] - 1) * 100
    # desequilibrio de agresión spot en Binance: +1 = todo compras agresoras, -1 = todo ventas
    h["binance_spot_imbalance"] = (2 * h["binance_taker_buy"] - h["binance_volume"]) / h["binance_volume"]
    h["coinbase_premium_sin_ajuste_pct"] = (h["coinbase_usd"] / h["binance_usdt"] - 1) * 100
    h["upbit_usd"] = h["upbit_krw"] / h["usdkrw"]
    h["kimchi_premium_pct"] = (h["upbit_usd"] / h["binance_usd"] - 1) * 100

    diario = h.groupby("fecha").agg(
        btc_close=("binance_usd", "last"),
        usdt_usd=("usdt_usd", "mean"),
        coinbase_premium_sin_ajuste_pct=("coinbase_premium_sin_ajuste_pct", "mean"),
        coinbase_premium_pct=("coinbase_premium_pct", "mean"),
        coinbase_premium_cierre=("coinbase_premium_pct", "last"),
        kimchi_premium_pct=("kimchi_premium_pct", "mean"),
        kimchi_premium_cierre=("kimchi_premium_pct", "last"),
        usdkrw=("usdkrw", "last"),
        binance_volume=("binance_volume", "sum"),
        binance_taker_buy=("binance_taker_buy", "sum"),
        horas_binance=("binance_usdt", "count"),
        horas_coinbase=("coinbase_usd", "count"),
        horas_upbit=("upbit_krw", "count"),
    ).reset_index()
    diario["binance_spot_imbalance"] = (2 * diario["binance_taker_buy"] - diario["binance_volume"]) / diario["binance_volume"]
    return h, diario


FIN_ENTRENAMIENTO = "2025-01-01"  # lo posterior es fuera de muestra: no se resume ni se mira


def resumen(h: pd.DataFrame, d: pd.DataFrame) -> str:
    h = h[h["ts"] < pd.Timestamp(FIN_ENTRENAMIENTO, tz="UTC")]
    d = d[pd.to_datetime(d["fecha"]) < pd.Timestamp(FIN_ENTRENAMIENTO)]
    lin = ["0xLongitude - resumen de primas (SOLO periodo de entrenamiento 2022-2024)",
           f"generado: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC", ""]
    lin.append(f"Horas totales: {len(h):,}  ({h['ts'].min():%Y-%m-%d} -> {h['ts'].max():%Y-%m-%d})")
    for col, nom in [("coinbase_usd", "Coinbase"), ("upbit_krw", "Upbit")]:
        falt = h[col].isna().sum()
        lin.append(f"Horas sin dato {nom}: {falt:,} ({falt / len(h):.2%})")
    lin.append("")
    for col in ["coinbase_premium_pct", "coinbase_premium_sin_ajuste_pct", "kimchi_premium_pct", "usdt_usd",
                "binance_spot_imbalance"]:
        s = d[col].dropna()
        lin.append(f"{col}: media {s.mean():+.3f}  mediana {s.median():+.3f}  "
                   f"p5 {s.quantile(.05):+.3f}  p95 {s.quantile(.95):+.3f}  "
                   f"min {s.min():+.3f}  max {s.max():+.3f}")
    lin.append("")
    lin.append("Media mensual (%):")
    m = d.assign(mes=pd.to_datetime(d["fecha"]).dt.to_period("M")).groupby("mes")[
        ["coinbase_premium_pct", "kimchi_premium_pct"]].mean()
    lin.append(m.round(3).to_string())
    lin.append("")
    lin.append("Días extremos de cada prima (para revisar eventos):")
    for col in ["coinbase_premium_pct", "kimchi_premium_pct"]:
        top = d.reindex(d[col].abs().sort_values(ascending=False).index).head(5)
        lin.append(f"  {col}: " + ", ".join(f"{f} ({v:+.2f})" for f, v in zip(top["fecha"], top[col])))
    lin.append("")
    lin.append("Días con horas incompletas (<24) en alguna fuente:")
    inc = d[(d[["horas_binance", "horas_coinbase", "horas_upbit"]] < 24).any(axis=1)]
    lin.append(f"  {len(inc)} días" + ("" if inc.empty else f"; ejemplos: {', '.join(map(str, inc['fecha'].head(10)))}"))
    return "\n".join(lin)


def main() -> None:
    print(f"Proyecto: {RAIZ}\n")
    cb = descargar_coinbase("BTC-USD")
    usdt = descargar_coinbase("USDT-USD")
    bn = descargar_binance()
    up = descargar_upbit()
    fx = descargar_fx()

    print("\nCalculando primas...")
    h, d = calcular_primas(cb, bn, up, fx, usdt)
    DIR_PROCESADO.mkdir(parents=True, exist_ok=True)
    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)
    h.to_csv(DIR_PROCESADO / "primas_horarias.csv", index=False)
    d.to_csv(DIR_PROCESADO / "primas_diarias.csv", index=False)
    txt = resumen(h, d)
    (DIR_RESULTADOS / "primas_resumen.txt").write_text(txt, encoding="utf-8")
    print("\n" + txt)
    print("\nArchivos:")
    print(f"  {DIR_PROCESADO / 'primas_diarias.csv'}")
    print(f"  {DIR_PROCESADO / 'primas_horarias.csv'}")
    print(f"  {DIR_RESULTADOS / 'primas_resumen.txt'}")


if __name__ == "__main__":
    main()

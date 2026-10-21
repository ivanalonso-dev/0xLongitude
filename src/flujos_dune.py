"""
0xLongitude - Convierte el CSV de la query 01 de Dune en variables regionales diarias
(prerregistro H1 v2, sección 4).

Entrada:  data/raw/dune/01_flujos_diarios_region.csv   (exportado a mano desde Dune)
Salida:   data/processed/flujos_regionales_diarios.csv (lo lee src/modelo_h1.py)
          results/flujos_dune_resumen.txt              (cobertura y control de calidad)

Variables (5 regiones x 2 grupos x 2 variantes = 20):
  <region>_<grupo>_norm  = neto_externo del día / media de los 30 días ANTERIORES del bruto externo
  <region>_<grupo>_z     = z-score de _norm frente a los 30 días anteriores
  grupo: stables (USDT+USDC) | riesgo (ETH+WBTC)

Uso: python src/flujos_dune.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "data" / "raw" / "dune" / "01_flujos_diarios_region.csv"
SALIDA = RAIZ / "data" / "processed" / "flujos_regionales_diarios.csv"
SALIDA_LIMPIO = RAIZ / "data" / "processed" / "flujos_regionales_diarios_limpio.csv"   # sensibilidad
RESUMEN = RAIZ / "results" / "flujos_dune_resumen.txt"

REGIONES = ["US", "EU", "ASIA", "BINANCE", "OFFSHORE"]
GRUPOS = {"USDT": "stables", "USDC": "stables", "ETH": "riesgo", "WBTC": "riesgo"}
VENTANA = 30
FIN_ENTRENAMIENTO = "2025-01-01"


def cargar() -> pd.DataFrame:
    if not ENTRADA.exists():
        sys.exit(f"No existe {ENTRADA}. Exporta la query 01 de Dune a esa ruta.")
    f = pd.read_csv(ENTRADA)
    f["fecha"] = f["fecha"].astype(str).str[:10]          # Dune exporta '2022-01-01 00:00:00.000 UTC'
    if "grupo" not in f.columns:                           # la query 01L ya trae el grupo agregado
        f["grupo"] = f["activo"].map(GRUPOS)
    if "activo" not in f.columns:
        f["activo"] = f["grupo"]
    desconocidos = f.loc[f["grupo"].isna(), "activo"].unique()  # noqa
    if len(desconocidos):
        print(f"aviso: activos no reconocidos e ignorados: {list(desconocidos)}")
    return f.dropna(subset=["grupo"])


def construir(f: pd.DataFrame, col_neto: str = "neto_externo") -> pd.DataFrame:
    agg = f.groupby(["fecha", "region", "grupo"]).agg(
        neto=(col_neto, "sum"),
        bruto=("entrada_externo", "sum"),
        salida=("salida_externo", "sum"),
    ).reset_index()
    agg["bruto"] = agg["bruto"] + agg["salida"]
    calendario = pd.date_range(f["fecha"].min(), f["fecha"].max(), freq="D").strftime("%Y-%m-%d")
    salida = pd.DataFrame({"fecha": calendario})
    for reg in REGIONES:
        for grupo in sorted(set(GRUPOS.values())):
            s = agg[(agg["region"] == reg) & (agg["grupo"] == grupo)].set_index("fecha").reindex(calendario)
            # un día sin filas = sin transferencias externas (0), no un dato perdido
            neto, bruto = s["neto"].fillna(0.0), s["bruto"].fillna(0.0)
            escala = bruto.shift(1).rolling(VENTANA, min_periods=VENTANA).mean()
            norm = neto / escala.replace(0, np.nan)
            pasado = norm.shift(1).rolling(VENTANA, min_periods=VENTANA)
            z = (norm - pasado.mean()) / pasado.std()
            pref = f"{reg.lower()}_{grupo}"
            salida[f"{pref}_norm"] = norm.to_numpy()
            salida[f"{pref}_z"] = z.to_numpy()
    return salida


def resumen(f: pd.DataFrame, s: pd.DataFrame) -> str:
    f = f[f["fecha"] < FIN_ENTRENAMIENTO]
    s = s[s["fecha"] < FIN_ENTRENAMIENTO]
    lin = ["0xLongitude - flujos de Dune (SOLO entrenamiento 2022-2024)", ""]
    lin.append(f"Días: {f['fecha'].nunique()} ({f['fecha'].min()} -> {f['fecha'].max()})")
    lin.append("")
    lin.append("Peso de cada tipo de contraparte sobre el flujo bruto (|neto| sumado, miles de millones USD):")
    cols = [c for c in ["neto_externo", "neto_externo_limpio", "neto_salida_a_otro_cex", "neto_otro_exchange",
                        "neto_interno", "neto_staking", "neto_total"] if c in f.columns]
    t = f.groupby("region")[cols].agg(lambda x: x.abs().sum() / 1e9).round(1)
    lin.append(t.to_string())
    lin.append("")
    if "neto_interno" in f.columns:
        lin.append("Control: neto_interno debería ser ~0 (si no, faltan etiquetas o hay doble conteo):")
        t = f.groupby("region")[["neto_interno"]].sum().div(1e9).round(2)
        lin.append(t.to_string())
        lin.append("")
    lin.append("Días con transferencias externas por región y grupo:")
    f2 = f
    t = f2[f2["transferencias_externo"] > 0].groupby(["region", "grupo"])["fecha"].nunique().unstack()
    lin.append(t.to_string())
    lin.append("")
    lin.append("Variables generadas (no nulas en entrenamiento):")
    lin.append(s.drop(columns="fecha").notna().sum().to_string())
    return "\n".join(lin)


def main() -> None:
    f = cargar()
    s = construir(f)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    s.to_csv(SALIDA, index=False)
    if "neto_externo_limpio" in f.columns:
        # sensibilidad prerregistrada: sin salidas a direcciones de depósito de otros exchanges
        construir(f, "neto_externo_limpio").to_csv(SALIDA_LIMPIO, index=False)
        print(f"Sensibilidad guardada en {SALIDA_LIMPIO}")
    txt = resumen(f, s)
    RESUMEN.parent.mkdir(parents=True, exist_ok=True)
    RESUMEN.write_text(txt, encoding="utf-8")
    print(txt)
    print(f"\nGuardado en {SALIDA}")


if __name__ == "__main__":
    main()

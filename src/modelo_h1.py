"""
0xLongitude - Evaluación de H1 (prerregistro v3)

Compara, para los targets A (continuación), B (reversión) y C (fragilidad):
  - modelo constante (tasa base del tramo de ajuste)
  - modelo GLOBAL (precio, volatilidad, agresión spot, derivados, primas)
  - modelo GLOBAL + REGIONAL (4 variables fijadas en la v3, si existen los datos de Dune)

Validación (v3): walk-forward trimestral 2023-T1 a 2024-T4, ajuste con todo lo anterior
(embargo de 3 días), C elegido dentro de cada pliegue con el último 25 % del ajuste.
Test: 2025-01-04 -> 2026-06-30, BLOQUEADO salvo docs/SENAL_CONGELADA.md + --abrir-test.

Uso:
  python src/modelo_h1.py                    walk-forward 2023-2024
  python src/modelo_h1.py --exploratorio     usa las 20 variables regionales (solo exploración)
  python src/modelo_h1.py --retardo-flujos 1 sensibilidad: flujos del día anterior (disponibilidad)
  python src/modelo_h1.py --abrir-test       único intento sobre el test (con la señal congelada)
Requisitos: pandas, numpy
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
# Regresión logística y métricas con numpy (sin scikit-learn: Windows bloquea sus DLL en este equipo).
# logistica_np replica sklearn LogisticRegression L2 (validado: diferencias < 1e-6).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from logistica_np import LogisticRegression, brier_score_loss, log_loss, roc_auc_score  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
PROC = RAIZ / "data" / "processed"
RES = RAIZ / "results"
CANDADO = RAIZ / "docs" / "SENAL_CONGELADA.md"

FIN_DESARROLLO = "2025-01-01"
INI_TEST, FIN_TEST = "2025-01-04", "2026-07-01"
TRIMESTRES = pd.period_range("2023Q1", "2024Q4", freq="Q")
EMBARGO_DIAS = 3
TARGETS = {"A_continuacion": "A · continuación", "B_reversion": "B · reversión", "C_fragilidad": "C · fragilidad"}
REGIONALES_V3 = ["us_stables_z", "asia_stables_z", "us_riesgo_z", "asia_riesgo_z"]
GRID_C = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0]
FRACCION_INTERNA = 0.25
BLOQUE_DIAS, N_BOOT, SEMILLA = 10, 2000, 42
EPS = 1e-6


# --------------------------------------------------------------------------
# Variables
# --------------------------------------------------------------------------
def construir_variables(exploratorio: bool, retardo: int = 0) -> tuple[pd.DataFrame, list[str], list[str]]:
    ev = pd.read_csv(PROC / "eventos_etiquetados.csv")
    btc = pd.read_csv(PROC / "btc_diario_usd.csv")
    pr = pd.read_csv(PROC / "primas_diarias.csv")
    ctx = pd.read_csv(PROC / "contexto_diario.csv")

    btc["mom3"] = btc["r"].rolling(3).sum()
    pr["kimchi_d1"] = pr["kimchi_premium_pct"].diff()
    ctx["log_taker_fut"] = np.log(ctx["taker_buy_sell"])

    d = (ev.merge(btc[["fecha", "mom3"]], on="fecha", how="left")
           .merge(pr[["fecha", "binance_spot_imbalance", "coinbase_premium_pct", "kimchi_d1"]], on="fecha", how="left")
           .merge(ctx[["fecha", "funding_anualizado_pct", "oi_cambio_pct", "log_taker_fut"]], on="fecha", how="left"))
    s = d["direccion"]
    d["g_r_en_sigmas"] = d["r_en_sigmas"]
    d["g_sigma"] = d["sigma"]
    d["g_rango_en_sigmas"] = d["rango_rel"] / d["sigma"]
    d["g_mom3_al"] = d["mom3"] * s
    d["g_spot_imbalance_al"] = d["binance_spot_imbalance"] * s
    d["g_coinbase_premium_al"] = d["coinbase_premium_pct"] * s
    d["g_kimchi_d1_al"] = d["kimchi_d1"] * s
    d["g_funding_al"] = d["funding_anualizado_pct"] * s
    d["g_oi_cambio_al"] = d["oi_cambio_pct"] * s
    d["g_taker_fut_al"] = d["log_taker_fut"] * s
    globales = [c for c in d.columns if c.startswith("g_")]

    regionales: list[str] = []
    ruta_reg = PROC / "flujos_regionales_diarios.csv"
    if ruta_reg.exists():
        reg = pd.read_csv(ruta_reg)
        if retardo:
            # sensibilidad: el evento del día t usa los flujos del día t - retardo
            reg["fecha"] = (pd.to_datetime(reg["fecha"]) + pd.Timedelta(days=retardo)).dt.strftime("%Y-%m-%d")
        cols = [c for c in reg.columns if c != "fecha"] if exploratorio else REGIONALES_V3
        faltan = [c for c in cols if c not in reg.columns]
        if faltan:
            sys.exit(f"Faltan variables regionales en {ruta_reg}: {faltan}")
        d = d.merge(reg[["fecha"] + cols], on="fecha", how="left")
        for c in cols:
            d[f"r_{c}_al"] = d[c] * s
        regionales = [f"r_{c}_al" for c in cols]
    return d.sort_values("fecha").reset_index(drop=True), globales, regionales


# --------------------------------------------------------------------------
# Preparación (imputación + estandarización con el tramo de ajuste)
# --------------------------------------------------------------------------
class Preparador:
    def __init__(self, cols: list[str]):
        self.cols = cols

    def ajustar(self, X: pd.DataFrame) -> "Preparador":
        self.med = X[self.cols].median()
        self.con_faltantes = [c for c in self.cols if X[c].isna().any()]
        Z = self._imputar(X)
        self.mu, self.sd = Z.mean(), Z.std().replace(0, 1.0).fillna(1.0)
        return self

    def _imputar(self, X: pd.DataFrame) -> pd.DataFrame:
        Z = X[self.cols].copy()
        for c in self.con_faltantes:
            Z[f"falta_{c}"] = Z[c].isna().astype(float)
        return Z.fillna(self.med)

    def transformar(self, X: pd.DataFrame) -> np.ndarray:
        Z = self._imputar(X)
        for c in self.mu.index:
            if c not in Z:
                Z[c] = 0.0
        return ((Z[self.mu.index] - self.mu) / self.sd).fillna(0.0).to_numpy()


def logistica(C: float) -> LogisticRegression:
    return LogisticRegression(C=C, solver="lbfgs", max_iter=5000)  # L2 por defecto


def ll_media(y, p) -> float:
    return log_loss(y, np.clip(p, EPS, 1 - EPS), labels=[0, 1])


def ajustar_y_predecir(fit: pd.DataFrame, ev: pd.DataFrame, cols: list[str], tgt: str) -> tuple[np.ndarray, float]:
    """Elige C con el último 25 % del ajuste (orden temporal), reajusta con todo y predice."""
    n_int = max(int(len(fit) * FRACCION_INTERNA), 10)
    dentro, interna = fit.iloc[:-n_int], fit.iloc[-n_int:]
    prep = Preparador(cols).ajustar(dentro)
    Xa, Xi = prep.transformar(dentro), prep.transformar(interna)
    ya, yi = dentro[tgt].to_numpy(), interna[tgt].to_numpy()
    if len(np.unique(ya)) < 2:
        C = GRID_C[0]
    else:
        C = min(GRID_C, key=lambda c: ll_media(yi, logistica(c).fit(Xa, ya).predict_proba(Xi)[:, 1]))
    prep = Preparador(cols).ajustar(fit)
    m = logistica(C).fit(prep.transformar(fit), fit[tgt].to_numpy())
    return m.predict_proba(prep.transformar(ev))[:, 1], C


def delta_bootstrap(fechas: pd.Series, y, p_ref, p_nuevo, rng, bloque_dias: int = BLOQUE_DIAS) -> tuple[float, float, float]:
    p_ref, p_nuevo = np.clip(p_ref, EPS, 1 - EPS), np.clip(p_nuevo, EPS, 1 - EPS)
    ll = lambda p: -(y * np.log(p) + (1 - y) * np.log(1 - p))
    mejora = ll(p_ref) - ll(p_nuevo)
    f = pd.to_datetime(fechas.reset_index(drop=True))
    bloque = ((f - f.min()).dt.days // bloque_dias).to_numpy()
    ids = np.unique(bloque)
    por_bloque = [mejora[bloque == b] for b in ids]
    medias = np.empty(N_BOOT)
    for i in range(N_BOOT):
        elegidos = rng.choice(len(ids), len(ids), replace=True)
        medias[i] = np.concatenate([por_bloque[j] for j in elegidos]).mean()
    return float(mejora.mean()), float(np.quantile(medias, 0.025)), float(np.quantile(medias, 0.975))


def sensibilidad_bloques(ev, y, p_ref, p_nuevo, rng) -> str:
    partes = []
    for b in (5, 10, 20, 30):
        _, lo, hi = delta_bootstrap(ev["fecha"], y, p_ref, p_nuevo, rng, b)
        partes.append(f"{b}d [{lo:+.4f}, {hi:+.4f}]")
    return "  sensibilidad IC95 por tamaño de bloque (regional vs global): " + " | ".join(partes)


def resumen_predicciones(nombre_tramo, ev, preds, modelos, rng, tgt) -> list[str]:
    y = ev[tgt].to_numpy()
    lin = []
    for mod in ["constante"] + list(modelos):
        p = np.clip(preds[mod], EPS, 1 - EPS)
        auc = roc_auc_score(y, p) if (mod != "constante" and len(np.unique(y)) == 2) else np.nan
        lin.append(f"  {mod:16s} log_loss {ll_media(y, p):.4f}  brier {brier_score_loss(y, p):.4f}"
                   + (f"  auc {auc:.3f}" if mod != "constante" else ""))
    dm, lo, hi = delta_bootstrap(ev["fecha"], y, preds["constante"], preds["global"], rng)
    lin.append(f"  mejora global vs constante:  {dm:+.4f}  IC95 [{lo:+.4f}, {hi:+.4f}]")
    if "global+regional" in modelos:
        dm, lo, hi = delta_bootstrap(ev["fecha"], y, preds["global"], preds["global+regional"], rng)
        lin.append(f"  mejora regional vs global:   {dm:+.4f}  IC95 [{lo:+.4f}, {hi:+.4f}]  -> "
                   + ("APORTA" if lo > 0 else "no demostrado"))
        lin.append(sensibilidad_bloques(ev, y, preds["global"], preds["global+regional"], rng))
    return lin


# --------------------------------------------------------------------------
def descriptivos(dev: pd.DataFrame, regionales: list[str]) -> list[str]:
    lin = ["##### DESCRIPTIVOS (antes de cualquier modelo) #####"]
    t = dev.assign(anio=dev["fecha"].str[:4]).groupby("anio").agg(
        eventos=("fecha", "size"), A=("A_continuacion", "mean"), B=("B_reversion", "mean"),
        neutro=("resultado", lambda x: (x == "neutro").mean()), C=("C_fragilidad", "mean"))
    lin.append(t.round(3).to_string())
    f = pd.to_datetime(dev["fecha"]).sort_values()
    solapados = (f.diff().dt.days <= 3).mean()
    lin.append(f"Eventos con otro evento en los 3 días anteriores (ventanas de 72 h solapadas): {solapados:.1%}")
    meses = f.dt.to_period("M").value_counts()
    lin.append(f"Eventos por mes: mediana {meses.median():.0f}, máximo {meses.max()} ({meses.idxmax()})")
    if regionales:
        lin.append("Correlaciones entre variables regionales (alineadas):")
        lin.append(dev[regionales].corr().round(2).to_string())
        lin.append("Faltantes por variable regional: " + ", ".join(f"{c}={dev[c].isna().sum()}" for c in regionales))
    return lin


def multinomial_walk_forward(d, globales, regionales, rng) -> list[str]:
    """Análisis SECUNDARIO: un solo modelo de 3 estados (continuación / reversión / neutro)."""
    modelos = {"global": globales}
    if regionales:
        modelos["global+regional"] = globales + regionales
    fechas = pd.to_datetime(d["fecha"])
    clases = ["continuacion", "reversion", "neutro"]
    ll = {m: [] for m in ["constante"] + list(modelos)}
    for q in TRIMESTRES:
        fit = d[fechas < q.start_time - pd.Timedelta(days=EMBARGO_DIAS)]
        ev = d[(fechas >= q.start_time) & (fechas <= q.end_time)]
        if len(ev) == 0:
            continue
        y_ev = ev["resultado"].map({c: i for i, c in enumerate(clases)}).to_numpy()
        frec = fit["resultado"].value_counts(normalize=True).reindex(clases).fillna(EPS).to_numpy()
        ll["constante"].append(-np.log(np.clip(frec[y_ev], EPS, 1)))
        for mod, cols in modelos.items():
            prep = Preparador(cols).ajustar(fit)
            y_fit = fit["resultado"].map({c: i for i, c in enumerate(clases)}).to_numpy()
            m = LogisticRegression(C=0.1, max_iter=5000).fit(prep.transformar(fit), y_fit)
            p = m.predict_proba(prep.transformar(ev))
            p_full = np.full((len(ev), 3), EPS)
            p_full[:, m.classes_] = p
            ll[mod].append(-np.log(np.clip(p_full[np.arange(len(ev)), y_ev], EPS, 1)))
    lin = ["", "##### SECUNDARIO: modelo multinomial de 3 estados (C fijo = 0,1; no decide el veredicto) #####"]
    for mod in ll:
        lin.append(f"  {mod:16s} log_loss multiclase {np.concatenate(ll[mod]).mean():.4f}")
    return lin


def walk_forward(d, globales, regionales, rng) -> list[str]:
    modelos = {"global": globales}
    if regionales:
        modelos["global+regional"] = globales + regionales
    lin = ["##### WALK-FORWARD 2023-T1 -> 2024-T4 (8 pliegues trimestrales) #####"]
    fechas = pd.to_datetime(d["fecha"])
    for tgt, nombre in TARGETS.items():
        trozos, Cs = [], {m: [] for m in modelos}
        signos = []
        for q in TRIMESTRES:
            ini, fin = q.start_time, q.end_time
            fit = d[fechas < ini - pd.Timedelta(days=EMBARGO_DIAS)]
            ev = d[(fechas >= ini) & (fechas <= fin)]
            if len(ev) == 0:
                continue
            preds = {"constante": np.full(len(ev), fit[tgt].mean())}
            for mod, cols in modelos.items():
                preds[mod], C = ajustar_y_predecir(fit, ev, cols, tgt)
                Cs[mod].append(C)
            if "global+regional" in modelos:
                y = ev[tgt].to_numpy()
                signos.append(ll_media(y, preds["global"]) - ll_media(y, preds["global+regional"]) > 0)
            trozos.append((ev, preds))
        ev_all = pd.concat([t[0] for t in trozos])
        preds_all = {k: np.concatenate([t[1][k] for t in trozos]) for k in trozos[0][1]}
        lin.append("")
        lin.append(f"=== {nombre} | {len(ev_all)} eventos fuera de muestra | tasa real {ev_all[tgt].mean():.3f} ===")
        lin += resumen_predicciones("walk-forward", ev_all, preds_all, modelos, rng, tgt)
        lin.append("  C elegidos por pliegue: " + " | ".join(f"{m}: {Cs[m]}" for m in modelos))
        if signos:
            lin.append(f"  trimestres en que lo regional mejora: {sum(signos)}/{len(signos)}")
    return lin


def test_bloqueado(d, globales, regionales, rng) -> list[str]:
    if not CANDADO.exists():
        sys.exit(f"Test bloqueado: falta {CANDADO}. Congela la señal antes de abrirlo.")
    modelos = {"global": globales}
    if regionales:
        modelos["global+regional"] = globales + regionales
    fit = d[d["fecha"] < FIN_DESARROLLO]
    ev = d[(d["fecha"] >= INI_TEST) & (d["fecha"] < FIN_TEST)]
    lin = ["##### TEST BLOQUEADO 2025-01-04 -> 2026-06-30 (único intento) #####"]
    for tgt, nombre in TARGETS.items():
        preds = {"constante": np.full(len(ev), fit[tgt].mean())}
        for mod, cols in modelos.items():
            preds[mod], C = ajustar_y_predecir(fit, ev, cols, tgt)
        lin.append("")
        lin.append(f"=== {nombre} | {len(ev)} eventos | tasa real {ev[tgt].mean():.3f} ===")
        lin += resumen_predicciones("test", ev, preds, modelos, rng, tgt)
    return lin


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--abrir-test", action="store_true")
    ap.add_argument("--exploratorio", action="store_true")
    ap.add_argument("--retardo-flujos", type=int, default=0,
                    help="sensibilidad: usar los flujos regionales de t - N días")
    args = ap.parse_args()
    if args.abrir_test and args.exploratorio:
        sys.exit("El test solo se abre con las variables prerregistradas (sin --exploratorio).")

    d, globales, regionales = construir_variables(args.exploratorio, args.retardo_flujos)
    rng = np.random.default_rng(SEMILLA)
    dev = d[d["fecha"] < FIN_DESARROLLO]

    lin = ["0xLongitude - Evaluación H1 (prerregistro v3)"
           + ("  [EXPLORATORIO: 20 variables regionales]" if args.exploratorio else "")
           + (f"  [SENSIBILIDAD: flujos con {args.retardo_flujos} día(s) de retardo]" if args.retardo_flujos else ""), ""]
    lin.append(f"Eventos 2022-2024: {len(dev)}")
    lin.append(f"Variables globales ({len(globales)}): {', '.join(globales)}")
    lin.append(f"Variables regionales ({len(regionales)}): {', '.join(regionales) if regionales else 'NINGUNA (faltan datos de Dune)'}")
    lin.append("")
    if args.abrir_test:
        lin += test_bloqueado(d, globales, regionales, rng)
    else:
        lin += descriptivos(dev, regionales)
        lin.append("")
        lin += walk_forward(dev, globales, regionales, rng)
        lin += multinomial_walk_forward(dev, globales, regionales, rng)

    txt = "\n".join(lin)
    RES.mkdir(parents=True, exist_ok=True)
    nombre = ("evaluacion_h1_test.txt" if args.abrir_test else
              "evaluacion_h1_exploratorio.txt" if args.exploratorio else
              f"evaluacion_h1_walkforward_retardo{args.retardo_flujos}.txt" if args.retardo_flujos else
              "evaluacion_h1_walkforward.txt")
    (RES / nombre).write_text(txt, encoding="utf-8")
    print(txt)
    print(f"\nGuardado en {RES / nombre}")


if __name__ == "__main__":
    main()

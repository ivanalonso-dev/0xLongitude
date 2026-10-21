# 0xLongitude — Ideas de ampliación (aparcadas)

> Regla: nada de aquí entra hasta que la hipótesis base (H1, `00_PLAN_VALIDACION.md`) tenga resultado.
> Cada idea se convierte en una hipótesis que se prueba por separado, nunca se mezcla con H1 antes de saber si H1 funciona sola.

## Reencuadre: no "predecir el precio", sino calificar el movimiento
El dolor real no es "¿hacia dónde va BTC?" (nadie lo resuelve de forma fiable), sino:

> **"Este movimiento, ¿aguanta o me va a atrapar?"**

Un movimiento empujado por compra al contado de una región con dinero nuevo tiende a sostenerse; uno empujado por apalancamiento o por una sola región tiende a revertirse. 0xLongitude califica la calidad del movimiento.

## H2 — Contado frente a apalancamiento (prioridad 1)
- **Dolor:** cascadas de liquidaciones; entrar largo en una subida que era solo apalancamiento.
- **Datos (gratis):** funding rate y open interest de Binance, Bybit y OKX.
- **Hipótesis:** subida con flujo/prima regional positiva y funding neutro → se sostiene; subida con funding alto y sin flujo de contado → se revierte.
- **Encaje:** usa el cubo OFFSHORE, que es mayoritariamente derivados.

## H3 — Relevo de sesión (prioridad 2)
- **Dolor:** Asia sube de madrugada y EE. UU. lo deshace al abrir (o al revés).
- **Hipótesis:** si la región que abre confirma (su prima/flujo va en la misma dirección), el movimiento continúa; si no, se revierte.
- **Datos:** ya los tenemos (primas horarias).

## H4 — Flujos de ETF spot de EE. UU. (prioridad 3)
- **Dolor:** no saber si el institucional americano está entrando.
- **Datos:** flujos diarios publicados de los ETF spot de BTC/ETH.
- **Hipótesis:** ETF + Coinbase premium en la misma dirección = demanda institucional de EE. UU. confirmada.

## Descartado por ahora
- Predicción de precio exacto u objetivos de precio.
- Altcoins (empezar solo con BTC, luego ETH).

## Staking de ETH — afecta a H1 y puede ser señal propia (apuntado 2026-10-18)
**1. Contamina los flujos de ETH de H1:**
- No toda salida de ETH de un exchange es acumulación: puede ir a staking (contrato de depósito de la Beacon Chain, Lido…).
- Los propios exchanges hacen staking por sus clientes (Coinbase con cbETH, Binance con wBETH): mueven ETH de sus wallets al contrato de depósito. Eso aparece como **salida** pero es una operación interna del exchange, no un cliente retirando.
- Desde Shapella (abril de 2023) se puede retirar del staking: ETH que sale de la cola de retirada y entra en exchanges = posible venta.
- **Acción en H1:** identificar y separar los flujos exchange → contrato de depósito / protocolos de staking antes de calcular el neto de ETH.

**2. Puede ser una señal propia (H5):**
- Cola de entrada y salida del staking (cuánto ETH quiere entrar o salir y cuánto tarda).
- Retiradas de staking que acaban en exchanges en pocos días → presión vendedora.
- LSTs (stETH, cbETH, wBETH) entrando en exchanges.
- Fuente probable: tablas de staking de Ethereum en Dune (depósitos, retiradas y entidades). Verificar nombres exactos el día 20.

## Tras la auditoría externa (18-10-2026) — visión a largo plazo, NO para la Fase 0
- **Motor de divergencias entre mercados:** detectar cuándo precio, contado, apalancamiento, liquidez y región cuentan historias incompatibles. Es la mejor formulación del producto final; cada contradicción = una hipótesis separada.
- **Presión spot ejecutada por plaza (CVD regional):** Coinbase, Kraken, Upbit. Historial inviable gratis (Upbit da 7 días de operaciones). Opción: empezar a grabar en vivo.
- **Libro de órdenes: absorción, reposición de liquidez, resiliencia, profundidad a 10/25/50 pb.** Historial solo de pago (Tardis, Kaiko). Opción: grabar en vivo desde ya, sin coste.
- **Índice de fragilidad por apalancamiento:** OI, funding, basis, liquidaciones, profundidad, volatilidad; pesos aprendidos, no manuales.
- **Movilidad de capital como grafo:** emisión → bridge → depósito → conversión, deduplicando el mismo dinero.
- **Detector de régimen:** reglas transparentes primero; HMM solo si mejora fuera de muestra.
- **Infraestructura de producción:** Parquet + DuckDB, versiones de etiquetas con fecha de conocimiento, puntuación de calidad de datos y abstención si faltan datos, registro de cada predicción con versión de modelo.

## H6 — Riesgos competitivos: tiempo hasta la barrera (auditoría 2, 18-10-2026)
- En vez de "¿toca la barrera en 72 h?", modelar P(T ≤ h, J = continuación | X): cuánto tarda y cuál toca primero.
- Útil para alertas que pierden valor con el tiempo. Requiere prerregistro propio; no se toca H1.
- Los datos ya existen: `horas_hasta_barrera` en `data/processed/eventos_etiquetados.csv`.


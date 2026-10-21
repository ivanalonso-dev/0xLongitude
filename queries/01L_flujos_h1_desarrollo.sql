-- 0xLongitude · 01L · Versión LIGERA para H1 (ahorro de créditos)
-- Solo el periodo de DESARROLLO (nov-2021 a dic-2024): lo necesario para el walk-forward.
-- El periodo de test (2025-2026) se descarga más adelante con otra query, cuando haya créditos:
-- así además el test sigue sin verse hasta congelar la señal.
--
-- Ahorros frente a la 01 completa:
--   * Un solo recorrido de cex.flows (sin la detección de direcciones de depósito:
--     la sensibilidad "neto_externo_limpio" se calcula en otra ejecución).
--   * Activos agrupados en 2 grupos (stables = USDT+USDC, riesgo = ETH+WBTC): mitad de filas.
--   * Importes redondeados a dólares enteros y solo las columnas necesarias: CSV más pequeño.
--   * Sin la matriz 01b ni la cobertura 02 (no hacen falta para el veredicto de H1).
--
-- Exportar con:  python src/descargar_dune.py <ID> data/raw/dune/01_flujos_diarios_region.csv
-- (src/flujos_dune.py acepta este formato directamente)

WITH regiones (cex, region) AS (
    VALUES
        ('coinbase','US'),('kraken','US'),('gemini','US'),('robinhood','US'),('binance us','US'),
        ('coinbase prime','US_PRIME'),
        ('bitstamp','EU'),('bitvavo','EU'),('bitpanda','EU'),
        ('upbit','ASIA'),('bithumb','ASIA'),('bitflyer','ASIA'),('coincheck','ASIA'),
        ('binance','BINANCE'),
        ('okx','OFFSHORE'),('bybit','OFFSHORE'),('bitget','OFFSHORE'),('htx','OFFSHORE'),
        ('kucoin','OFFSHORE'),('bitfinex','OFFSHORE')
),
etiquetas AS (
    SELECT address, lower(min(cex_name)) AS cex
    FROM cex.addresses
    WHERE blockchain = 'ethereum'
    GROUP BY address
),
flujos AS (
    SELECT
        date_trunc('day', f.block_time) AS fecha,
        r.region,
        CASE WHEN upper(f.token_symbol) IN ('USDT', 'USDC') THEN 'stables' ELSE 'riesgo' END AS grupo,
        f.flow_type,
        f.amount_usd,
        lower(f.cex_name) AS cex,
        CASE WHEN f.flow_type = 'Inflow' THEN f."from" ELSE f."to" END AS contraparte
    FROM cex.flows f
    JOIN regiones r ON lower(f.cex_name) = r.cex
    WHERE f.blockchain = 'ethereum'
      AND f.block_time >= TIMESTAMP '2021-11-01'
      AND f.block_time <  TIMESTAMP '2025-01-01'
      AND upper(f.token_symbol) IN ('ETH', 'WETH', 'WBTC', 'USDT', 'USDC')
      AND f.flow_type IN ('Inflow', 'Outflow')
      AND f.amount_usd IS NOT NULL
      AND f.amount_usd < 1e10
),
clasificados AS (
    SELECT
        fl.fecha, fl.region, fl.grupo, fl.flow_type, fl.amount_usd,
        CASE
            WHEN fl.contraparte = 0x00000000219ab540356cbb839cbe05303d7705fa THEN 'staking'
            WHEN e.cex IS NULL THEN 'externo'
            WHEN e.cex = fl.cex THEN 'interno'
            ELSE 'otro_exchange'
        END AS tipo,
        CASE WHEN fl.flow_type = 'Inflow' THEN fl.amount_usd ELSE -fl.amount_usd END AS neto
    FROM flujos fl
    LEFT JOIN etiquetas e ON e.address = fl.contraparte
)
SELECT
    fecha,
    region,
    grupo,
    ROUND(SUM(CASE WHEN tipo = 'externo' AND flow_type = 'Inflow'  THEN amount_usd ELSE 0 END)) AS entrada_externo,
    ROUND(SUM(CASE WHEN tipo = 'externo' AND flow_type = 'Outflow' THEN amount_usd ELSE 0 END)) AS salida_externo,
    ROUND(SUM(CASE WHEN tipo = 'externo' THEN neto ELSE 0 END))       AS neto_externo,
    ROUND(SUM(CASE WHEN tipo = 'otro_exchange' THEN neto ELSE 0 END)) AS neto_otro_exchange,
    ROUND(SUM(CASE WHEN tipo = 'staking' THEN neto ELSE 0 END))       AS neto_staking,
    ROUND(SUM(neto))                                                   AS neto_total,
    COUNT_IF(tipo = 'externo')                                         AS transferencias_externo
FROM clasificados
GROUP BY 1, 2, 3
ORDER BY 1, 2, 3

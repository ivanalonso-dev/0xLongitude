-- 0xLongitude · 01 · Flujos netos diarios por región y activo (Ethereum)
-- Ejecutar TERCERO, después de corregir nombres con 00a y estructura con 00b.
-- Exportar a: data/raw/dune/01_flujos_diarios_region.csv
--
-- Una fila por día × región × activo:
--   entrada_usd  = dinero que entra en exchanges de esa región (presión vendedora potencial)
--   salida_usd   = dinero que sale (acumulación / retirada a custodia propia)
--   neto_usd     = entrada - salida
--
-- Notas de método:
--   * Las transferencias internas de un mismo exchange aparecen como entrada y
--     salida a la vez del mismo exchange: se anulan en el neto (el bruto sí se infla).
--   * Un movimiento Binance -> Coinbase cuenta como salida de BINANCE y entrada en US:
--     es justo el desplazamiento regional que queremos medir.
--   * Se descargan todas las fechas; el análisis en Python solo usa 2022-2024
--     hasta congelar la señal (2025+ es fuera de muestra).
--
-- AJUSTAR tras 00a: nombres en la tabla 'regiones' (en minúsculas).
-- AJUSTAR tras 00b: valores de flow_type y símbolos de token si difieren.

WITH regiones (cex, region, subregion) AS (
    VALUES
        ('coinbase',  'US',       'US'),
        ('kraken',    'US',       'US'),
        ('gemini',    'US',       'US'),
        ('robinhood', 'US',       'US'),
        ('bitstamp',  'EU',       'EU'),
        ('bitvavo',   'EU',       'EU'),
        ('bitpanda',  'EU',       'EU'),
        ('upbit',     'ASIA',     'KR'),
        ('bithumb',   'ASIA',     'KR'),
        ('bitflyer',  'ASIA',     'JP'),
        ('coincheck', 'ASIA',     'JP'),
        ('binance',   'BINANCE',  'GLOBAL'),
        ('okx',       'OFFSHORE', 'GLOBAL'),
        ('bybit',     'OFFSHORE', 'GLOBAL'),
        ('bitget',    'OFFSHORE', 'GLOBAL'),
        ('htx',       'OFFSHORE', 'GLOBAL'),
        ('huobi',     'OFFSHORE', 'GLOBAL'),
        ('kucoin',    'OFFSHORE', 'GLOBAL'),
        ('bitfinex',  'OFFSHORE', 'GLOBAL')
),

flujos AS (
    SELECT
        date_trunc('day', f.block_time) AS fecha,
        r.region,
        r.subregion,
        CASE
            WHEN upper(f.token_symbol) IN ('ETH', 'WETH')  THEN 'ETH'
            WHEN upper(f.token_symbol) = 'WBTC'            THEN 'WBTC'
            WHEN upper(f.token_symbol) = 'USDT'            THEN 'USDT'
            WHEN upper(f.token_symbol) = 'USDC'            THEN 'USDC'
        END AS activo,
        f.flow_type,
        f.amount_usd
    FROM cex.flows f
    JOIN regiones r
      ON lower(f.cex_name) = r.cex
    WHERE f.blockchain = 'ethereum'
      AND f.block_time >= TIMESTAMP '2022-01-01'
      AND upper(f.token_symbol) IN ('ETH', 'WETH', 'WBTC', 'USDT', 'USDC')
      AND f.flow_type IN ('Inflow', 'Outflow')
      AND f.amount_usd IS NOT NULL
      AND f.amount_usd < 1e10            -- descarta precios corruptos
)

SELECT
    fecha,
    region,
    subregion,
    activo,
    SUM(CASE WHEN flow_type = 'Inflow'  THEN amount_usd ELSE 0 END) AS entrada_usd,
    SUM(CASE WHEN flow_type = 'Outflow' THEN amount_usd ELSE 0 END) AS salida_usd,
    SUM(CASE WHEN flow_type = 'Inflow'  THEN amount_usd ELSE -amount_usd END) AS neto_usd,
    COUNT(*) AS transferencias
FROM flujos
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2, 4

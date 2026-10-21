-- 0xLongitude · 01b · Matriz diaria origen -> destino entre exchanges (Ethereum)
-- Contabilidad por pares (auditoría): un traspaso Coinbase -> Binance es salida de US y
-- entrada en BINANCE; aquí se ve como UN movimiento, sin contarlo dos veces.
-- También es la base de los ARCOS del globo (Fase 2).
-- Exportar a: data/raw/dune/01b_matriz_regiones.csv
--
-- Se usa solo el lado 'Outflow' del exchange de origen para no duplicar
-- (cada traspaso aparece como salida del origen y entrada del destino).

WITH regiones (cex, region) AS (
    VALUES
        ('coinbase','US'),('kraken','US'),('gemini','US'),('robinhood','US'),('binance us','US'),
        ('coinbase prime','US_PRIME'),
        ('bitstamp','EU'),('bitvavo','EU'),('bitpanda','EU'),
        ('upbit','ASIA'),('bithumb','ASIA'),('bitflyer','ASIA'),('coincheck','ASIA'),
        ('binance','BINANCE'),
        ('okx','OFFSHORE'),('bybit','OFFSHORE'),('bitget','OFFSHORE'),('htx','OFFSHORE'),
        ('huobi','OFFSHORE'),('kucoin','OFFSHORE'),('bitfinex','OFFSHORE')
),
etiquetas AS (
    SELECT address, lower(min(cex_name)) AS cex
    FROM cex.addresses
    WHERE blockchain = 'ethereum'
    GROUP BY address
),
-- destinos = hot wallets etiquetadas + direcciones de depósito probables (ver query 01)
depositos AS (
    SELECT "from" AS address, lower(min(cex_name)) AS cex
    FROM cex.flows
    WHERE blockchain = 'ethereum' AND flow_type = 'Inflow' AND block_time >= TIMESTAMP '2022-01-01'
    GROUP BY 1
    HAVING COUNT(DISTINCT lower(cex_name)) = 1 AND COUNT(*) >= 3
),
destinos AS (
    SELECT address, cex, 'etiqueta' AS fuente FROM etiquetas
    UNION ALL
    SELECT d.address, d.cex, 'deposito' AS fuente
    FROM depositos d LEFT JOIN etiquetas e ON e.address = d.address
    WHERE e.address IS NULL
)
SELECT
    date_trunc('day', f.block_time)       AS fecha,
    ro.region                             AS region_origen,
    COALESCE(rd.region, 'OTRO_CEX')       AS region_destino,
    CASE
        WHEN upper(f.token_symbol) IN ('ETH', 'WETH') THEN 'ETH'
        ELSE upper(f.token_symbol)
    END                                   AS activo,
    e.fuente                              AS fuente_destino,
    SUM(f.amount_usd)                     AS usd,
    COUNT(*)                              AS transferencias
FROM cex.flows f
JOIN regiones ro  ON lower(f.cex_name) = ro.cex
JOIN destinos e   ON e.address = f."to"
LEFT JOIN regiones rd ON rd.cex = e.cex
WHERE f.blockchain = 'ethereum'
  AND f.block_time >= TIMESTAMP '2022-01-01'
  AND upper(f.token_symbol) IN ('ETH', 'WETH', 'WBTC', 'USDT', 'USDC')
  AND f.flow_type = 'Outflow'
  AND f.amount_usd IS NOT NULL
  AND f.amount_usd < 1e10
  AND e.cex <> lower(f.cex_name)          -- fuera la operativa interna
GROUP BY 1, 2, 3, 4, 5
ORDER BY 1, 2, 3, 4, 5

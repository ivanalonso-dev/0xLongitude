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
        ('coinbase','US'),('kraken','US'),('gemini','US'),('robinhood','US'),
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
)
SELECT
    date_trunc('day', f.block_time)       AS fecha,
    ro.region                             AS region_origen,
    COALESCE(rd.region, 'OTRO_CEX')       AS region_destino,
    CASE
        WHEN upper(f.token_symbol) IN ('ETH', 'WETH') THEN 'ETH'
        ELSE upper(f.token_symbol)
    END                                   AS activo,
    SUM(f.amount_usd)                     AS usd,
    COUNT(*)                              AS transferencias
FROM cex.flows f
JOIN regiones ro  ON lower(f.cex_name) = ro.cex
JOIN etiquetas e  ON e.address = f."to"
LEFT JOIN regiones rd ON rd.cex = e.cex
WHERE f.blockchain = 'ethereum'
  AND f.block_time >= TIMESTAMP '2022-01-01'
  AND upper(f.token_symbol) IN ('ETH', 'WETH', 'WBTC', 'USDT', 'USDC')
  AND f.flow_type = 'Outflow'
  AND f.amount_usd IS NOT NULL
  AND f.amount_usd < 1e10
  AND e.cex <> lower(f.cex_name)          -- fuera la operativa interna
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2, 3, 4

-- 0xLongitude · 02 · Cobertura mensual por exchange (control de calidad)
-- Ejecutar CUARTO. Sirve para ver si algún exchange "desaparece" algún mes
-- (cambio de wallets no etiquetado), lo que falsearía su flujo.
-- Exportar a: data/raw/dune/02_cobertura_mensual.csv

WITH regiones (cex, region) AS (
    VALUES
        ('coinbase','US'),('kraken','US'),('gemini','US'),('robinhood','US'),('binance us','US'),
        ('coinbase prime','US_PRIME'),
        ('bitstamp','EU'),('bitvavo','EU'),('bitpanda','EU'),
        ('upbit','ASIA'),('bithumb','ASIA'),('bitflyer','ASIA'),('coincheck','ASIA'),
        ('binance','BINANCE'),
        ('okx','OFFSHORE'),('bybit','OFFSHORE'),('bitget','OFFSHORE'),('htx','OFFSHORE'),
        ('huobi','OFFSHORE'),('kucoin','OFFSHORE'),('bitfinex','OFFSHORE')
)
SELECT
    date_trunc('month', f.block_time) AS mes,
    r.region,
    lower(f.cex_name)                 AS exchange,
    COUNT(*)                          AS transferencias,
    SUM(f.amount_usd)                 AS usd_bruto,
    COUNT(DISTINCT CASE WHEN f.flow_type = 'Inflow'  THEN f."to"   END) AS direcciones_activas_entrada,
    COUNT(DISTINCT CASE WHEN f.flow_type = 'Outflow' THEN f."from" END) AS direcciones_activas_salida
FROM cex.flows f
JOIN regiones r ON lower(f.cex_name) = r.cex
WHERE f.blockchain = 'ethereum'
  AND f.block_time >= TIMESTAMP '2022-01-01'
  AND upper(f.token_symbol) IN ('ETH', 'WETH', 'WBTC', 'USDT', 'USDC')
  AND f.flow_type IN ('Inflow', 'Outflow')
GROUP BY 1, 2, 3
ORDER BY 3, 1

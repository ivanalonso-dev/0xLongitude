-- 0xLongitude · 00b · Comprobar la estructura de cex.flows
-- Ejecutar SEGUNDO. Solo mira 7 días de Ethereum para que sea barata.
-- Exportar a: data/raw/dune/00b_estructura_flows.csv
--
-- Sirve para confirmar:
--   1) qué valores tiene flow_type (se espera 'Inflow' / 'Outflow' y quizá otros)
--   2) cómo aparecen los tokens (ETH nativo, WETH, USDT, USDC, WBTC)
-- Si alguna columna no existe, el error lo dirá: copia el mensaje y lo ajustamos.

SELECT
    flow_type,
    token_symbol,
    COUNT(*)              AS transferencias,
    SUM(amount_usd)       AS usd_total,
    COUNT(DISTINCT cex_name) AS exchanges
FROM cex.flows
WHERE blockchain = 'ethereum'
  AND block_time >= now() - interval '7' day
GROUP BY 1, 2
ORDER BY usd_total DESC NULLS LAST
LIMIT 100

-- 0xLongitude · 01 · Flujos diarios por región, activo y TIPO DE CONTRAPARTE (Ethereum)
-- Versión 2 (18-10-2026): separa el dinero de clientes de los traspasos entre exchanges,
-- la operativa interna y el staking (auditoría: "depósito en exchange ≠ compra").
-- Nombres de exchanges VERIFICADOS con la 00a el 21-10-2026.
-- Ejecutar después de revisar la estructura con 00b.
-- Exportar a: data/raw/dune/01_flujos_diarios_region.csv
--
-- Una fila por día × región × activo. Columnas en USD:
--   entrada_externo / salida_externo / neto_externo
--        -> contraparte NO es ningún exchange etiquetado: clientes, custodia propia, DeFi...
--           ESTE es el candidato a flujo orgánico (la señal de H1).
--   neto_otro_exchange -> traspasos con otros exchanges (arbitraje, market makers, reequilibrio)
--   neto_interno       -> el exchange consigo mismo (hot <-> cold); debería ser ~0
--   neto_staking       -> ETH hacia/desde el contrato de depósito de la Beacon Chain
--   neto_total         -> todo junto (lo que publican la mayoría de paneles)
--   neto_externo_limpio-> neto_externo sin salidas a direcciones de depósito de otros exchanges
--   neto_salida_a_otro_cex -> esas salidas, aparte (traspasos entre exchanges vía depósito)
-- Valores de flow_type verificados con la 00b: Inflow, Outflow, Internal, Cross-CEX.
--   'Internal' (mismo exchange) y 'Cross-CEX' (muy pequeño) quedan fuera por el filtro.
-- Signo: entrada - salida (positivo = entra en exchanges de la región).
--
-- Limitaciones conocidas (docs/04_LIMPIEZA_FLUJOS.md):
--   * las etiquetas de cex.addresses son las de HOY: wallets etiquetadas después
--     pueden "ver el futuro" en 2022-2024 (no se puede corregir del todo en la Fase 0)
--   * un exchange que no está en cex.addresses cuenta como "externo"
--   * market makers sin etiqueta también caen en "externo"

WITH regiones (cex, region, subregion) AS (
    VALUES
        ('coinbase',  'US',       'US'),
        ('kraken',    'US',       'US'),
        ('gemini',    'US',       'US'),
        ('robinhood', 'US',       'US'),
        ('binance us','US',       'US'),
        ('coinbase prime','US_PRIME','US'),   -- custodia institucional (ETF): cubo propio, fuera de US en H1
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

-- Direcciones de depósito PROBABLES (no etiquetadas en Dune): direcciones que envían
-- a un único exchange, al menos 3 veces desde 2022. Hallazgo 00b (21-10-2026): los traspasos
-- entre exchanges casi nunca salen como 'Cross-CEX'; pasan por direcciones de depósito y
-- aparecen como Outflow de A + Inflow de B, ambos con contraparte "externa".
-- Heurística imperfecta: también captura wallets de usuarios o market makers fieles a un exchange.
depositos AS (
    SELECT "from" AS address, lower(min(cex_name)) AS cex
    FROM cex.flows
    WHERE blockchain = 'ethereum'
      AND flow_type = 'Inflow'
      AND block_time >= TIMESTAMP '2022-01-01'
    GROUP BY 1
    HAVING COUNT(DISTINCT lower(cex_name)) = 1 AND COUNT(*) >= 3
),

-- una sola etiqueta por dirección (evita duplicar filas si una dirección tiene varias)
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
        r.subregion,
        lower(f.cex_name) AS cex,
        CASE
            WHEN upper(f.token_symbol) IN ('ETH', 'WETH') THEN 'ETH'
            WHEN upper(f.token_symbol) = 'WBTC'           THEN 'WBTC'
            WHEN upper(f.token_symbol) = 'USDT'           THEN 'USDT'
            WHEN upper(f.token_symbol) = 'USDC'           THEN 'USDC'
        END AS activo,
        f.flow_type,
        f.amount_usd,
        CASE WHEN f.flow_type = 'Inflow' THEN f."from" ELSE f."to" END AS contraparte
    FROM cex.flows f
    JOIN regiones r ON lower(f.cex_name) = r.cex
    WHERE f.blockchain = 'ethereum'
      AND f.block_time >= TIMESTAMP '2022-01-01'
      AND upper(f.token_symbol) IN ('ETH', 'WETH', 'WBTC', 'USDT', 'USDC')
      AND f.flow_type IN ('Inflow', 'Outflow')
      AND f.amount_usd IS NOT NULL
      AND f.amount_usd < 1e10
),

clasificados AS (
    SELECT
        fl.*,
        CASE
            WHEN fl.contraparte = 0x00000000219ab540356cbb839cbe05303d7705fa THEN 'staking'
            WHEN e.cex IS NULL     THEN 'externo'
            WHEN e.cex = fl.cex    THEN 'interno'
            ELSE                        'otro_exchange'
        END AS tipo_contraparte,
        -- en salidas: ¿la contraparte "externa" es en realidad un depósito de OTRO exchange?
        (e.cex IS NULL AND fl.flow_type = 'Outflow'
         AND dp.cex IS NOT NULL AND dp.cex <> fl.cex) AS salida_a_deposito_otro_cex,
        -- en entradas: ¿la contraparte es una dirección de depósito de ESTE exchange? (dinero de cliente)
        (e.cex IS NULL AND fl.flow_type = 'Inflow' AND dp.cex = fl.cex) AS entrada_desde_deposito_propio,
        CASE WHEN fl.flow_type = 'Inflow' THEN fl.amount_usd ELSE -fl.amount_usd END AS neto
    FROM flujos fl
    LEFT JOIN etiquetas e  ON e.address = fl.contraparte
    LEFT JOIN depositos dp ON dp.address = fl.contraparte
)

SELECT
    fecha,
    region,
    subregion,
    activo,
    SUM(CASE WHEN tipo_contraparte = 'externo' AND flow_type = 'Inflow'  THEN amount_usd ELSE 0 END) AS entrada_externo,
    SUM(CASE WHEN tipo_contraparte = 'externo' AND flow_type = 'Outflow' THEN amount_usd ELSE 0 END) AS salida_externo,
    SUM(CASE WHEN tipo_contraparte = 'externo'       THEN neto ELSE 0 END) AS neto_externo,
    SUM(CASE WHEN tipo_contraparte = 'otro_exchange' THEN neto ELSE 0 END) AS neto_otro_exchange,
    SUM(CASE WHEN tipo_contraparte = 'interno'       THEN neto ELSE 0 END) AS neto_interno,
    SUM(CASE WHEN tipo_contraparte = 'staking'       THEN neto ELSE 0 END) AS neto_staking,
    SUM(neto) AS neto_total,
    -- SENSIBILIDAD (prerregistrada): neto externo sin las salidas que van a depósitos de otros exchanges
    SUM(CASE WHEN tipo_contraparte = 'externo' AND NOT salida_a_deposito_otro_cex THEN neto ELSE 0 END) AS neto_externo_limpio,
    SUM(CASE WHEN salida_a_deposito_otro_cex THEN neto ELSE 0 END) AS neto_salida_a_otro_cex,
    COUNT(*)  AS transferencias,
    COUNT_IF(tipo_contraparte = 'externo') AS transferencias_externo
FROM clasificados
GROUP BY 1, 2, 3, 4
ORDER BY 1, 2, 4

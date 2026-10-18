-- 0xLongitude · 00a · Verificar cómo se llaman nuestros exchanges en Dune
-- Ejecutar PRIMERO (el día 20). Es barata: solo lee la tabla de etiquetas.
-- Exportar a: data/raw/dune/00a_nombres_cex.csv
--
-- Devuelve, para cada nombre de exchange que se parezca a los nuestros,
-- cuántas direcciones etiquetadas tiene y en qué cadenas.
-- Si un exchange aparece con otro nombre (p. ej. HTX como 'Huobi'), se anota
-- en data/raw/entidades_region.csv, columna dune_cex_name_verificar.

SELECT
    cex_name,
    blockchain,
    COUNT(*) AS direcciones
FROM cex.addresses
WHERE regexp_like(
    lower(cex_name),
    'coinbase|kraken|gemini|robinhood|bitstamp|bitvavo|bitpanda|upbit|bithumb|korbit|coinone|bitflyer|coincheck|bitbank|hashkey|osl|binance|okx|okex|bybit|bitget|htx|huobi|kucoin|gate|mexc|crypto\.com|bitfinex'
)
GROUP BY 1, 2
ORDER BY 1, 3 DESC

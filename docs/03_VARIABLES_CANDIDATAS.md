# 0xLongitude — Variables candidatas

Regla: **descargar sí, mezclar no.** Se adelanta la descarga mientras esperamos a Dune, pero cada grupo se prueba como hipótesis separada (H1 → H2 → H3 → H4). Nada se combina con H1 antes de tener su resultado.

## Estado
| Grupo | Variable | Fuente | Hipótesis | Estado |
|-------|----------|--------|-----------|--------|
| Primas | Coinbase premium (ajustada / sin ajustar), USDT-USD | Coinbase, Binance | H1 | ✅ descargado — débil (H-01) |
| Primas | Kimchi premium | Upbit, BCE | H1 | ✅ descargado — sin poder solo (H-03) |
| Flujos on-chain | Neto diario por región y activo | Dune `cex.flows` | **H1 (núcleo)** | ⏳ queries listas, día 20 |
| Apalancamiento | Funding rate BTCUSDT | Binance API | H2 | 🟡 script listo (`descargar_contexto.py`) |
| Apalancamiento | Open interest, ratio largos/cortos, compras/ventas agresoras | data.binance.vision | H2 | 🟡 script listo |
| Pólvora seca | Oferta y emisión diaria de USDT y USDC | DefiLlama | H1 (contexto) | 🟡 script listo |
| Sesiones | Retorno de BTC en horario Asia / Europa / EE. UU. | precios horarios ya descargados | H3 | 🟢 sin descarga, se calcula |
| Staking ETH | Depósitos/retiradas de staking, cola de salida, LSTs a exchanges | Dune (tablas de staking) | H1 (limpieza) + H5 | ⚪ apuntado, ver `91_IDEAS.md` |
| Institucional EE. UU. | Flujos diarios de ETF spot BTC/ETH | sin API gratuita limpia | H4 | ⚪ pendiente de fuente |

## Por qué estas y no otras
- **Funding + open interest:** distinguen una subida de contado (sana) de una de apalancamiento (trampa). Es el núcleo del posicionamiento "¿aguanta o me atrapa?".
- **Ratio compras/ventas agresoras (taker):** quién está cruzando el spread con urgencia.
- **Emisión de stablecoins:** dinero nuevo listo para comprar; en Dune se podrá ver además **a qué región va**.
- **Sesiones:** gratis con lo que ya tenemos; prueba directa de H3 (relevo de sesión).

## Descartadas por ahora
- Índice de miedo y codicia: es un derivado de precio y volatilidad, no aporta información nueva.
- Redes sociales / Google Trends: ruidoso, difícil de sostener en producción.
- Altcoins: primero BTC; ETH después.

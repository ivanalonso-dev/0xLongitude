# 0xLongitude — Criterio de asignación de exchanges a regiones

Archivo de datos: `data/raw/entidades_region.csv`

## Regla principal
**La región es donde está la demanda fiat del usuario, no la sede legal.**
Un exchange cuenta como regional solo si sus usuarios entran con moneda local (USD, EUR, KRW, JPY, HKD). Eso es lo que hace que sus flujos representen a una región.

## Cubos
| Cubo | Qué contiene | Uso en la señal |
|------|--------------|-----------------|
| US | Exchanges con rampa USD y usuarios de EE. UU. | Señal regional |
| EU | Exchanges con rampa EUR | Señal regional |
| ASIA (KR / JP / HK) | Exchanges con rampa KRW, JPY, HKD | Señal regional, con subregión |
| BINANCE | Binance solo | Bloque propio; contexto de liquidez global |
| OFFSHORE | OKX, Bybit, Bitget, HTX, KuCoin, Bitfinex… | Flujo "offshore" agregado; **no** se asigna a Asia |
| OTHER | LatAm, Turquía, Indonesia | Fuera de la Fase 0 |

## Corrección respecto al plan inicial
En `00_PLAN_VALIDACION.md` OKX, Bitget y HTX aparecían como Asia. Se corrige: no hay forma de demostrar desde la cadena qué parte de sus usuarios es asiática, así que meterlos en Asia contaminaría la señal regional. Van al cubo OFFSHORE.
Consecuencia: el cubo ASIA queda dominado por Corea y Japón, que es justo donde las primas (kimchi, Japón) permiten verificar la señal.

## Columnas
- `dune_cex_name_verificar`: nombre esperado en las etiquetas CEX de Dune. **Hay que comprobarlo el día 20** contra la tabla real; los nombres pueden variar en mayúsculas o sufijos.
- `confianza`: lo seguro que es que el flujo represente a esa región (alta = rampa fiat local exclusiva).
- `incluir_fase0`: si entra en el primer backtest. Los "no" son exchanges pequeños o fuera de alcance.
- `feed_prima`: par de precio para calcular la prima regional.

## Casos dudosos (decidir con datos, no ahora)
- **Kraken:** usuarios repartidos EE. UU./Europa. Asignado a US con confianza media. Si con datos se ve que mueve la señal de EE. UU. en horario europeo, se revisa.
- **Bitstamp:** ahora propiedad de Robinhood, pero usuarios mayoritariamente europeos. Se queda en EU.
- **Coinbase:** mezcla minorista e institucional (custodia de ETF). Puede convenir separar las wallets de custodia institucional del resto más adelante.

## Pendiente para el día 20 (cuando haya acceso a Dune)
1. Listar los nombres CEX disponibles en las etiquetas de Dune y cuadrar la columna `dune_cex_name_verificar`.
2. Contar cuántas direcciones etiquetadas tiene cada exchange y en qué cadenas (Ethereum, Bitcoin).
3. Marcar los exchanges sin etiquetas suficientes (cobertura insuficiente = no entran).

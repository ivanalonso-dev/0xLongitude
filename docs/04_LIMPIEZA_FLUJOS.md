# 0xLongitude — Flujos que parecen señal y no lo son

Principio: **solo cuenta como señal el flujo orgánico** (clientes que meten o sacan dinero por decisión de mercado).
Todo lo demás se identifica, se separa y se guarda aparte: a veces es ruido, a veces es una señal distinta.
Aplica a **todos los activos y cadenas**, no solo a ETH.

## A. Operativa interna de los exchanges (ruido → eliminar)
| Fuente | Qué pasa | Cómo detectarlo |
|--------|----------|-----------------|
| Hot ↔ cold wallet | El exchange mueve fondos entre sus propias wallets | Origen y destino del mismo exchange (se anula en el neto; vigilar etiquetas incompletas) |
| Migración de wallets | El exchange estrena wallets aún sin etiquetar → parece una salida enorme | Query 02: meses en que un exchange "desaparece" o se dispara |
| Staking por cuenta de clientes | ETH, SOL… del exchange al contrato de staking (cbETH, wBETH) | Destino = contrato de staking / validadores de la entidad |
| Reequilibrio entre cadenas | Recibe USDT en Tron y lo saca en Ethereum (o al revés) | Mirar el neto **sumando cadenas**, no una sola |
| Prueba de reservas | Movimientos a fin de mes/trimestre para auditorías | Patrón de calendario + mismo exchange |

## B. Intermediarios que no son demanda regional (separar)
| Fuente | Qué pasa | Tratamiento |
|--------|----------|-------------|
| Market makers (Wintermute, Jump, Cumberland…) | Mueven inventario entre exchanges para arbitrar | Etiquetar sus wallets; flujo aparte |
| Custodia de ETF | Creaciones/reembolsos de ETF pasan por Coinbase Custody | Es institucional de EE. UU. → variable propia (H4), no mezclar con el minorista de Coinbase |
| OTC / prime brokers | Grandes operaciones que no tocan wallets de exchange | Punto ciego: documentarlo |
| DeFi (Aave, Morpho…) | Salida de exchange para usar como colateral | No es acumulación pura; seguir el destino |

## C. Creación y destrucción de oferta (señal distinta → variable propia)
| Fuente | Qué pasa |
|--------|----------|
| Emisión/quema de stablecoins | Tether/Circle emiten directamente a exchanges = dinero nuevo (y a qué región va) |
| Emisión/quema de wrapped (WBTC, cbBTC) | El custodio crea o destruye BTC envuelto: no es compra ni venta |
| Desbloqueos de tokens | Tokens de equipo/inversores que se liberan y van a exchanges (relevante si se amplía a altcoins) |

## D. Eventos especiales (marcar en calendario)
Movimientos enormes y únicos que dominan cualquier media. Se marcan en `data/raw/eventos_conocidos.csv` para excluirlos o analizarlos aparte.
Tipos: hackeos de exchanges, quiebras, distribuciones de liquidaciones (Mt. Gox), ventas de gobiernos, lanzamientos de ETF, cambios de protocolo.

## Orden de aplicación en H1
1. Eliminar A (operativa interna).
2. Separar B y C como variables propias.
3. Marcar D y comprobar que el resultado no depende de esos días.
4. Lo que queda = flujo orgánico regional → la señal.

# Queries de Dune — orden de ejecución (a partir del día 20)

| # | Archivo | Para qué | Exportar a |
|---|---------|----------|------------|
| 1 | `00a_verificar_nombres_cex.sql` | Cómo se llaman nuestros exchanges en Dune y cuántas direcciones tienen | `data/raw/dune/00a_nombres_cex.csv` |
| 2 | `00b_explorar_cex_flows.sql` | Confirmar columnas, `flow_type` y símbolos de tokens | `data/raw/dune/00b_estructura_flows.csv` |
| 3 | `01_flujos_diarios_region.sql` | **La principal (v2):** flujo diario por región y activo, separado por tipo de contraparte (externo = candidato a orgánico, otro exchange, interno, staking) | `data/raw/dune/01_flujos_diarios_region.csv` |
| 3b | `01b_matriz_entre_regiones.sql` | Matriz origen → destino entre exchanges, sin doble conteo (base de los arcos del globo) | `data/raw/dune/01b_matriz_regiones.csv` |
| 4 | `02_cobertura_mensual_exchange.sql` | Control: detectar meses en que un exchange "desaparece" | `data/raw/dune/02_cobertura_mensual.csv` |

**Importante:** ejecuta 00a y 00b, guarda los CSV y avísame **antes** de lanzar la 01.
Con esos dos resultados ajusto los nombres y la estructura para que la 01 (la cara) salga bien a la primera.

## Alcance de esta primera versión
- Solo **Ethereum** (ETH, WETH, WBTC, USDT, USDC). Es donde las etiquetas de Dune son más completas.
- **BTC nativo** queda fuera de momento: la cobertura de etiquetas de exchanges en la cadena de Bitcoin es más irregular. Se valorará tras ver 00a (columna `blockchain`).
- Stablecoins en Tron (gran parte del USDT asiático) también fuera de momento; se valorará igual.

## Pendiente: staking de ETH
Las salidas de ETH de un exchange pueden ser staking del propio exchange (contrato de depósito, cbETH, wBETH), no clientes retirando. Antes de dar por buenos los netos de ETH de la 01 hay que separar esos flujos. Ver `docs/91_IDEAS_AMPLIACION.md`.

## Estado (21-10-2026)
- 00a ✅ (query 8985850) y 00b ✅ (query 8985902) ejecutadas y descargadas con `src/descargar_dune.py`.
- 01 y 01b actualizadas con nombres verificados, Binance US, Coinbase Prime y detección de direcciones de depósito.
- **Coste:** 01 y 01b recorren `cex.flows` desde 2022; son las más pesadas. Si con el plan gratuito fallan por tiempo o créditos, se dividen por año.
- Descarga: `python src/descargar_dune.py <ID> data/raw/dune/<archivo>.csv` (o sin argumentos, modo preguntas).

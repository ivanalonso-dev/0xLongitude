# 0xLongitude — Plan de validación (Fase 0)

## Hipótesis
El flujo neto regional de capital hacia exchanges (EE. UU. frente a Asia), combinado con las primas regionales, predice el retorno de BTC a 1–3 días mejor que una referencia simple, **fuera de muestra**.

## Criterio para archivar el proyecto (decidido ANTES de ver resultados)
- Si la señal no supera a la referencia (momentum de precio a 1–3 días) en el tramo fuera de muestra → se archiva.
- Si solo funciona en un régimen (solo alcista, solo bajista) → se documenta como hallazgo, no como producto.

## Periodo
- Entrenamiento / exploración: 2022-01-01 → 2024-12-31 (incluye bajista 2022, recuperación 2023, alcista 2024)
- Fuera de muestra: 2025-01-01 → hoy. **No se mira hasta tener la señal congelada.**

## Datos necesarios
| # | Dato | Fuente | Frecuencia |
|---|------|--------|------------|
| D1 | Direcciones etiquetadas de CEX con región | Dune (`cex.addresses` / `labels`) + tabla manual entidad→región | estática |
| D2 | Entradas/salidas diarias de BTC, ETH, USDT, USDC por exchange | Dune | diaria |
| D3 | Precio BTC en Coinbase (USD) y Binance (USDT) | APIs públicas de exchanges | horaria/diaria |
| D4 | Precio BTC en Upbit (KRW) + tipo USD/KRW | API Upbit + FX | diaria |
| D5 | Emisión/quema de USDT y USDC | Dune | diaria |
| D6 | Precio de cierre BTC | API pública | diaria |

## Tabla entidad → región
Ver `docs/01_ENTIDADES.md` y `data/raw/entidades_region.csv`.
Regla: la región es donde está la demanda fiat, no la sede legal. Cubos: US, EU, ASIA (KR/JP/HK), BINANCE (bloque propio) y OFFSHORE (OKX, Bybit, Bitget, HTX…, que **no** cuentan como Asia).

## Pasos
1. [x] Construir tabla entidad → región (`data/raw/entidades_region.csv`) — v1, falta verificar nombres en Dune
2. [ ] Query Dune: flujos netos diarios por exchange y activo (D2)
3. [x] Descargar primas: Coinbase premium (D3) y kimchi premium (D4) — hecho, ver `docs/02_HALLAZGOS.md`; script: `src/descargar_primas.py` (prima de Japón pendiente: bitFlyer no da histórico público de velas)
4. [ ] Query Dune: emisión de stablecoins (D5)
4b. [ ] Limpiar flujos según `docs/04_LIMPIEZA_FLUJOS.md` (operativa interna, intermediarios, emisiones, eventos de `data/raw/eventos_conocidos.csv`)
5. [ ] Unir todo en un dataset diario (`data/processed/dataset_diario.csv`)
6. [ ] Análisis exploratorio en entrenamiento: correlaciones con retorno a 1, 2 y 3 días + gráfico de acumulación por región y activo (base visual de la columna del globo). Parte kimchi hecha: sin poder predictivo por sí sola (H-03)
7. [ ] Congelar la definición de la señal (documentar en `docs/01_SENAL.md`)
8. [ ] Test fuera de muestra frente a la referencia
9. [ ] Decisión: seguir / archivar

## Límites conocidos
- Movimientos internos entre wallets del mismo exchange: hay que filtrarlos.
- La sede legal no es el mercado real de los usuarios.
- Solo una fracción del volumen está etiquetada; hay que medir y publicar qué porcentaje.
- Bitcoin nativo tiene peor cobertura de etiquetas en Dune que Ethereum.

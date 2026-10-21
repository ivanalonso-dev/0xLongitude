# 0xLongitude — Registro de auditorías metodológicas de H1

Propósito: que ninguna auditoría mejore el modelo "hacia atrás" hasta encontrar un resultado favorable.
Cada cambio se clasifica en una de cuatro categorías y se fecha. Solo la categoría **D** cambia el experimento, y solo si se hace antes de ver datos de flujos.

| Categoría | Qué es | ¿Cambia el veredicto? |
|---|---|---|
| A · Aclaración de implementación | Resuelve una ambigüedad sin cambiar hipótesis ni criterio | No |
| B · Análisis de sensibilidad | Resultado adicional publicado junto al veredicto | No |
| C · Hipótesis nueva | Requiere prerregistro propio y evaluación posterior | No (va aparte) |
| D · Cambio de diseño previo a los datos | Modifica el experimento antes de ver ningún dato de flujos | Sí, y se declara |

Estado de los datos de flujos on-chain a 18-10-2026: **no existe ningún dato** (Dune disponible a partir del 20-10-2026).

---

## Auditoría 1 (externa, 18-10-2026)
| Punto | Categoría | Resolución | Dónde |
|---|---|---|---|
| Depósito en exchange ≠ compra ejecutada | A | Query 01 v2 separa contraparte externa / otro exchange / interno / staking; matriz 01b | `queries/` |
| Objetivo de retorno ≠ "¿aguanta el movimiento?" | D | Targets A continuación, B reversión, C fragilidad con barreras | `05_PREREGISTRO_H1.md` v2 |
| Referencia demasiado débil (solo momentum) | D | Modelo global de precio, volumen, derivados y primas | v2 |
| Abandono si lo regional no aporta sobre el modelo global | D | Adoptado tal cual | v2, §8 |
| Tipo de cambio aplicado antes de publicarse | A | Point-in-time: cada hora usa el último tipo del BCE publicado | `src/descargar_primas.py` |
| Falta agresión compradora/vendedora | A | `binance_spot_imbalance` (global); regional inviable sin historial | `src/descargar_primas.py` |
| Sesiones solapadas | C | Pendiente para H3 | `91_IDEAS.md` |
| Libro de órdenes, absorción, motor de divergencias | C | Visión a largo plazo; inviable en Fase 0 | `91_IDEAS.md` |

## Cambio de diseño propio (18-10-2026) — prerregistro v3
| Punto | Categoría | Resolución |
|---|---|---|
| Potencia insuficiente (H-04: 95 eventos de validación, 20 variables) | D | Umbral 0,5σ (519 eventos), 4 variables regionales fijadas, walk-forward trimestral. Comprobado con señal plantada en datos sintéticos: el diseño v3 detecta un efecto de ≈1 desviación típica que el v2 no detectaba, y no da falsos positivos con ruido puro |

Lo visto antes de decidir: solo la línea base global con eventos de 1σ (sin mejora sobre la tasa base).

## Auditoría 2 (externa, 18-10-2026, revisó la v2)
| Punto | Categoría | Resolución | Dónde |
|---|---|---|---|
| Reglas de barrera ambiguas (máx/mín o cierres, misma vela, entrada, huecos, sin toque) | A | Ya fijadas en el anexo v2.1: máximos y mínimos horarios; ambas en la misma hora = reversión; entrada = cierre de la vela de las 23:00 UTC; > 3 horas sin dato = evento descartado; sin toque = neutro (tres estados excluyentes) | v2.1, puntos 1–4 |
| Veinte variables regionales son demasiadas | D | Ya resuelto en la v3: 4 variables | v3 |
| Disponibilidad real de los datos on-chain (indexación, confirmaciones, etiquetas) | B | Sensibilidad obligatoria con flujos de **t − 1** (`--retardo-flujos 1`). El sesgo de etiquetas retroactivas ya era una prueba de robustez obligatoria (v2, §9) | `src/modelo_h1.py` |
| Eventos solapados | B | Se publica el porcentaje de eventos con ventanas solapadas (86,5 % en 2022–2024) y el IC con bloques de 5, 10, 20 y 30 días | `src/modelo_h1.py` |
| Prevalencias, número de eventos, distribución por año, correlaciones | B | Tabla de descriptivos antes de cualquier modelo | `src/modelo_h1.py` |
| A y B como binarios independientes pueden dar probabilidades incoherentes | B | Análisis secundario multinomial de 3 estados; no decide el veredicto | `src/modelo_h1.py` |
| Efectos de cola de la kimchi | C | Cualquier hipótesis de colas sobre la kimchi es **exploratoria**: ya se vieron sus resultados | — |
| Modelo de supervivencia / riesgos competitivos (tiempo hasta la barrera) | C | Registrado como H6 para después de H1 | `91_IDEAS.md` |

## Auditoría 3 (externa, 18-10-2026) — Camino B
| Punto | Categoría | Resolución | Dónde |
|---|---|---|---|
| Investigar contradicciones contado / derivados / liquidez como línea independiente | C | Prerregistrada como H2 (`07_PREREGISTRO_H2.md`) antes de ejecutarla; resultado: sin evidencia (H-05), archivada | `src/modelo_h2.py` |
| Tres niveles de éxito: información nueva → señal operativa → alpha comercializable | — | Adoptado como marco; H1 y H2 solo evalúan el nivel 1 | — |
| Adquirir trades con lado agresor y libro de órdenes | C | Ya en la lista de inviables; la agresión global de Binance ya se usa | `91_IDEAS.md` |

## Verificación de nombres en Dune (query 00a, 21-10-2026) — ANTES de ver ningún flujo
| Punto | Categoría | Resolución |
|---|---|---|
| Nombres de exchanges en `cex.addresses` | A | Todos los de la Fase 0 existen con el nombre esperado (en minúsculas coinciden con la query 01) |
| Dune separa **Binance US** de Binance | A | Binance US → cubo US (usuarios de EE. UU. con USD), según la regla de `01_ENTIDADES.md` |
| Dune separa **Coinbase Prime** (custodia institucional, incluye ETF) | A | Cubo propio `US_PRIME`, **fuera** de las variables US de H1; reservado para H4. Ya estaba previsto separar la custodia en `01_ENTIDADES.md` |
| Cobertura en Bitcoin y Tron | A | Bitcoin: Coinbase 13 direcciones, Upbit 1, Bithumb y bitFlyer 0. Tron: ningún exchange de US, EU ni Corea/Japón. Se confirma **solo Ethereum** en H1 |

## Verificación de estructura de `cex.flows` (query 00b, 21-10-2026) — ANTES de ver ningún flujo
| Punto | Categoría | Resolución |
|---|---|---|
| `flow_type` tiene 4 valores: Inflow, Outflow, Internal, Cross-CEX | A | El filtro Inflow/Outflow ya excluye la operativa interna (Internal). Cross-CEX es marginal (~0,3 mil M$ en 7 días frente a ~22 mil M$ de entradas) y queda fuera |
| Los traspasos entre exchanges pasan por **direcciones de depósito sin etiquetar** y aparecen como Outflow de A + Inflow de B, ambos "externos" | B | La variable principal de H1 **no cambia** (`neto_externo`, prerregistrada). Se añade la sensibilidad obligatoria `neto_externo_limpio`: sin las salidas a direcciones de depósito probables de otros exchanges (heurística: direcciones que envían a un único exchange, ≥ 3 veces desde 2022). Se ejecuta con `--flujos-limpios` y se publica junto al veredicto |
| Símbolos | A | ETH aparece como `ETH`; WBTC existe pero con poco volumen (~50 M$/semana); USDT y USDC dominan |

## Reglas para auditorías futuras
1. Una vez existan datos de flujos, **no se admiten cambios de categoría D** en H1. Cualquier mejora pasa a ser una hipótesis nueva (C).
2. Los análisis B se publican siempre junto al veredicto, sean favorables o no.
3. El test bloqueado se abre una sola vez.

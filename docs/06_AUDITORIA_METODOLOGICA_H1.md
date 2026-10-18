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
| Sesiones solapadas | C | Pendiente para H3 | `91_IDEAS_AMPLIACION.md` |
| Libro de órdenes, absorción, motor de divergencias | C | Visión a largo plazo; inviable en Fase 0 | `91_IDEAS_AMPLIACION.md` |

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
| Modelo de supervivencia / riesgos competitivos (tiempo hasta la barrera) | C | Registrado como H6 para después de H1 | `91_IDEAS_AMPLIACION.md` |

## Reglas para auditorías futuras
1. Una vez existan datos de flujos, **no se admiten cambios de categoría D** en H1. Cualquier mejora pasa a ser una hipótesis nueva (C).
2. Los análisis B se publican siempre junto al veredicto, sean favorables o no.
3. El test bloqueado se abre una sola vez.

# 0xLongitude — Prerregistro de H1 (versión 2)

**Fecha de congelación:** 2026-10-18, ANTES de tener ningún dato de flujos on-chain.
**Motivo de la v2:** auditoría externa del 18-10-2026. La v1 medía el retorno a 1–3 días, pero el producto promete calificar si un movimiento aguanta. No es lo mismo.
**Regla:** nada de este documento se cambia después de ver resultados de flujos. Si se cambia algo, se crea una v3 con fecha y motivo, y se declara en los resultados.

---

## 1. Pregunta

¿Los flujos regionales orgánicos añaden información, **por encima de un modelo global** de precio, volumen y derivados, para anticipar si un movimiento de BTC continúa, se revierte o sufre un retroceso fuerte?

## 2. Eventos (qué es "un movimiento")

- Volatilidad de referencia: σ_t = desviación típica de los retornos logarítmicos diarios de BTC de los 30 días **anteriores** a t (sin incluir t).
- Hay evento el día t si |r_t| > 1,0 · σ_t. Dirección del movimiento: d_t = signo(r_t).
- Se evalúa desde el cierre de t (00:00 UTC de t+1) con la trayectoria **horaria** de BTC (Binance en dólares reales).

## 3. Objetivos (targets)

Barreras ajustadas a volatilidad, horizonte H = 3 días (72 h), b = 1,0 · σ_t · √3:

| Target | Definición | Tipo |
|--------|------------|------|
| **A · Continuación** | El precio toca primero la barrera a favor de d_t (+b) | Binario |
| **B · Reversión** | El precio toca primero la barrera en contra (−b) | Binario |
| (Neutro) | No toca ninguna en 72 h | — |
| **C · Fragilidad** | Excursión adversa máxima (MAE) en 72 h > 1,5 · σ_t · √3, aunque el resultado final sea positivo | Binario |
| Secundario | Retorno logarítmico a 1, 2 y 3 días, multiplicado por d_t | Continuo (IC) |

También se registran MFE y MAE de cada evento para análisis descriptivo.

## 4. Variables

**Modelo global (referencia a batir):**
- Momentum: r_t, retorno de 3 días.
- Volatilidad: σ_t y rango intradía de t.
- Agresión spot global: `binance_spot_imbalance` (compras − ventas agresoras / volumen).
- Derivados: funding anualizado, cambio de open interest, ratio compras/ventas agresoras en futuros.
- Primas: Coinbase premium ajustada, cambio diario de la kimchi.

**Variables regionales (lo que se prueba):**
- `neto_externo` por región (US, EU, ASIA, BINANCE, OFFSHORE) y grupo de activo (stablecoins = USDT+USDC; riesgo = ETH+WBTC), del día t.
- Normalización: neto / media de 30 días anteriores del flujo bruto externo (entrada + salida) de esa región → elimina el efecto tamaño.
- Variante z-score: (neto normalizado − media 30 d) / desviación 30 d.
- Total: 5 regiones × 2 grupos × 2 variantes = **20 variables regionales**.

Todas las variables usan solo información disponible al cierre de t (point-in-time). El tipo de cambio usa el último dato publicado (corregido el 18-10-2026).

## 5. Modelos

- Regresión logística con regularización L2, una por target (A, B, C).
- Modelo global vs. modelo global + regionales. Mismo procedimiento, mismos hiperparámetros elegidos solo en el tramo de validación.
- Nada más complejo (árboles, redes) hasta que la logística demuestre información incremental.

## 6. Partición temporal

| Tramo | Fechas | Uso |
|-------|--------|-----|
| Diseño | 2022-01-01 → 2023-12-31 | Exploración, normalizaciones |
| Validación | 2024-01-04 → 2024-12-31 | Elegir regularización; embargo de 3 días al inicio |
| Test bloqueado | 2025-01-04 → 2026-06-30 | **Un único test** con todo congelado; embargo de 3 días |
| Prospectivo | Desde la congelación en adelante | Señales registradas antes del resultado |

Nota de transparencia: el 18-10-2026 se vieron por error medias mensuales de primas de 2025–2026 (niveles, no su relación con retornos). No se usaron para ninguna decisión.

## 7. Métricas y criterio de éxito

- Log loss y Brier score fuera de muestra; AUC como apoyo; curva de calibración.
- **Mejora incremental:** Δlog loss = global − (global + regional). Intervalo de confianza al 95 % por bootstrap de bloques (bloques de 10 días, 2.000 réplicas).
- **Éxito de H1:** Δlog loss > 0 con el intervalo al 95 % por encima de 0 en el test bloqueado, en al menos uno de los targets A, B o C, y con el mismo signo de efecto en validación.
- Corrección por pruebas múltiples: 3 targets → umbral de Holm.

## 8. Condición de abandono (adoptada de la auditoría)

**Si los datos regionales no añaden información al modelo global, la atribución regional deja de ser el núcleo predictivo** y se conserva solo como capa descriptiva (mapa, contexto, contenido).
El criterio anterior (batir al momentum) queda sustituido por este, que es más exigente.

## 9. Robustez obligatoria (no cambia el veredicto, se publica junto a él)

- Repetir sin los días de `data/raw/eventos_conocidos.csv`.
- Repetir por año (2022, 2023, 2024) dentro de diseño + validación.
- Índice **estricto** (solo exchanges con confianza alta en `entidades_region.csv`) frente a **ampliado** (todos).
- Etiquetas: si `cex.addresses` trae fecha de alta (`added_date`), repetir usando solo direcciones etiquetadas antes de cada periodo, para medir el sesgo de etiquetas retroactivas.
- Comparar `neto_externo` con `neto_total`: si el total funciona y el externo no, la señal viene de traspasos entre exchanges, no de demanda orgánica.

## 10. Checklist de aceptación (auditoría)

- [ ] La señal regional conserva valor al retirar las primas.
- [ ] Mejora incremental frente a momentum, volatilidad y flujo spot global.
- [ ] Resultados consistentes entre regímenes.
- [ ] Sin fuga temporal; etiquetas reproducibles.
- [ ] Probabilidades calibradas y estables fuera de muestra.
- [ ] Ventaja económica neta de costes (solo si se vende como señal operativa).
- [ ] Alertas auditables con explicación y nivel de confianza.
- [ ] Capacidad de abstenerse cuando faltan datos.

---

## Anexo v2.1 — Detalles de implementación (18-10-2026, fijados ANTES de ejecutar ningún modelo)
Aclaraciones que la v2 no especificaba. Se fijan antes de calcular ninguna etiqueta ni ningún resultado del modelo global.

1. **Precio de referencia:** velas horarias de Binance BTCUSDT × USDT-USD de Coinbase (dólares reales). Máximos y mínimos se convierten igual.
2. **Cierre diario:** cierre de la vela de las 23:00 UTC del día t. Retorno diario = log(cierre_t / cierre_{t−1}).
3. **Toque de barrera:** se usan máximo y mínimo horarios. Si en la misma hora se tocan las dos barreras, se cuenta como **reversión** (criterio conservador).
4. **Horas sin dato** en la ventana de 72 h: si faltan más de 3, el evento se descarta.
5. **Alineación con la dirección:** las variables con signo (momentum, desequilibrio agresor, flujos netos, cambios de prima, funding, cambio de open interest) se multiplican por d_t, para que "a favor del movimiento" sea siempre positivo. Se incluyen también |r_t| / σ_t y σ_t sin alinear.
6. **Datos faltantes en variables:** se imputa la mediana del tramo de ajuste y se añade un indicador de ausencia por variable (afecta sobre todo a los ratios de Binance de enero a mayo de 2022).
7. **Estandarización:** media y desviación del tramo de ajuste, aplicadas tal cual a los tramos posteriores.
8. **Regularización:** C ∈ {0,01; 0,03; 0,1; 0,3; 1; 3}, elegida por log loss en validación (2024); después se reajusta con diseño + validación antes del test.
9. **Referencia mínima:** modelo constante (tasa base del tramo de ajuste). El modelo global debe mejorarla para ser una referencia útil; si no, se informa y se mantiene igualmente como referencia.
10. **Candado del test:** el código no evalúa 2025-01-04 → 2026-06-30 salvo que exista `docs/SENAL_CONGELADA.md` y se pase la opción `--abrir-test`.

---

## Versión 3 — Cambio por potencia estadística (18-10-2026, ANTES de tener datos de Dune)
**Motivo:** H-04 mostró que con 95 eventos de validación y 20 variables regionales solo se detectarían efectos enormes (prueba con señal plantada en datos sintéticos). El cambio responde a la potencia de la prueba, no a ningún resultado de flujos: todavía no existe ningún dato de flujos. Decisión del autor el 18-10-2026.
**Lo que se vio antes de decidir:** solo la línea base global con eventos de 1σ (sin mejora sobre la tasa base). Se declara.

Cambios respecto a la v2 / v2.1 (todo lo demás sigue igual):

1. **Umbral de evento:** |r_t| > **0,5** · σ_t (antes 1,0). ≈ 519 eventos en 2022–2024 (antes 252). Barreras y fragilidad sin cambios.
2. **Variables regionales:** solo **4**, elegidas de antemano: `us_stables_z`, `asia_stables_z`, `us_riesgo_z`, `asia_riesgo_z` (z-score a 30 días del neto externo normalizado). Las otras 16 se calculan pero solo para análisis descriptivo; si se usan en el modelo, es exploración y se declara como tal.
3. **Validación walk-forward** en 2022–2024 (sustituye diseño/validación):
   - Trimestres de evaluación: 2023-T1 a 2024-T4 (8 pliegues).
   - Cada pliegue se ajusta con todos los eventos anteriores al inicio del trimestre, con embargo de 3 días.
   - C se elige dentro de cada pliegue: últimos 25 % de los eventos de ajuste como validación interna, mismo grid; después se reajusta con todo el tramo de ajuste.
   - Se juntan las predicciones fuera de muestra de los 8 trimestres y se calcula la mejora de log loss con bootstrap de bloques de 10 días.
4. **Test bloqueado** sin cambios (2025-01-04 → 2026-06-30): modelo final ajustado con 2022–2024, C elegido con la misma regla, un único intento.
5. **Éxito de H1:** mejora regional vs. global con IC 95 % > 0 en el test bloqueado, en al menos un objetivo (Holm sobre 3), **y** mejora media positiva en el walk-forward de 2023–2024 para ese mismo objetivo.

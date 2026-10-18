# 0xLongitude — Prerregistro de H2: divergencia contado / derivados (Camino B)

**Fecha de congelación:** 2026-10-18, ANTES de ejecutar ningún análisis de H2.
**Independiente de H1:** H1 sigue congelada (`05_PREREGISTRO_H1.md` v3). H2 no modifica nada de H1.
**Origen:** auditoría externa 3 (Camino B) y `91_IDEAS_AMPLIACION.md` (H2 contado vs. apalancamiento).

**Lo que ya se ha visto con estas variables (se declara):** en la línea base global de H1 v3, las variables globales en forma lineal y por separado no mejoran a la tasa base (H-04). H2 prueba algo distinto: una **combinación concreta** (contradicción), definida aquí antes de mirarla.

---

## 1. Pregunta
Cuando BTC se mueve sin apoyo de compras/ventas agresoras al contado pero con el apalancamiento empujando en la misma dirección, ¿es más probable que el movimiento se revierta o sea frágil?

## 2. Eventos y objetivos
Los mismos que H1 v3: |r_t| > 0,5 σ_t; barreras de 72 h; **B · reversión** y **C · fragilidad**. (A · continuación no se prueba en H2.)

## 3. Definición de divergencia (día t, d_t = dirección del movimiento)
Un evento es **divergente** si se cumplen las tres condiciones:

1. **Contado en contra o neutro:** `binance_spot_imbalance` × d_t ≤ 0 (el movimiento no lo empujan compradores/vendedores agresores al contado).
2. **Apalancamiento creciendo:** `oi_cambio_pct` > 0 (se abren posiciones en perpetuos).
3. **Derivados a favor:** log(`taker_buy_sell` de futuros) × d_t > 0 (los agresores en futuros empujan en la dirección del movimiento).

Eventos con alguna de las tres variables ausente (sobre todo enero–mayo de 2022, sin ratio de futuros) **se excluyen** de H2.

## 4. Pruebas
**Principal (por objetivo B y C):** diferencia de tasas divergente − no divergente en 2022–2024, IC 95 % por bootstrap de bloques de 10 días (2.000 réplicas).
**Incremental:** walk-forward trimestral 2023-T1 → 2024-T4 (mismo procedimiento que H1 v3): modelo global de H1 frente a global + indicador de divergencia; mejora de log loss con IC 95 %.
**Test bloqueado:** 2025-01-04 → 2026-06-30, un único intento, solo con `docs/SENAL_CONGELADA_H2.md`.

## 5. Criterio de éxito
- **Exploración (2022–2024):** diferencia de tasa positiva con IC 95 % > 0 en B o en C (Holm sobre 2), **y** mejora incremental media positiva en el walk-forward para ese objetivo.
- **Confirmación:** lo mismo en el test bloqueado.
- Si no se cumple en 2022–2024, H2 se archiva sin abrir el test.

## 6. Sensibilidad (se publica, no cambia el veredicto)
- Variantes de umbral: imbalance × d ≤ −0,01; OI > +1 %.
- Solo subidas y solo bajadas por separado.
- Número de eventos divergentes por año (si hay menos de 30 en total, el resultado se declara no concluyente).

## 7. Pruebas múltiples
H1 y H2 comparten el periodo de test. Cada una se abre una sola vez y se publica junto a la otra; no se elige a posteriori "la que funcionó".

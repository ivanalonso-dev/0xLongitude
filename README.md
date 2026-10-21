# 0xLongitude

**Proyecto 013**

## Qué es
Índice de flujos de capital cripto por región (EE. UU., Asia, Europa). Responde cada día a una pregunta:

> ¿Quién está moviendo el precio ahora mismo —Asia, EE. UU. o Europa— y está entrando dinero nuevo o saliendo?

## Posicionamiento
**No predice el precio: califica el movimiento.** Responde a: *"Este movimiento, ¿aguanta o me va a atrapar?"*
Un movimiento empujado por compra al contado de una región con dinero nuevo tiende a sostenerse; uno empujado por apalancamiento o por una sola región tiende a revertirse.

## La herida que cura
- **Ceguera sobre el origen del movimiento:** el trader ve el precio moverse pero no sabe qué región lo empuja.
- **Información fragmentada:** flujos de exchanges, Coinbase premium, kimchi premium, emisión de stablecoins… repartidos en varias herramientas.
- **Sesgo occidental:** Corea, Japón y Hong Kong están mal cubiertos.

## Cliente objetivo
Swing traders de BTC/ETH, mesas pequeñas y fondos cripto que operan a 1–3 días vista.

## Capas de la señal
1. Flujo neto a exchanges por región (BTC, ETH, stablecoins)
2. Primas regionales: Coinbase premium y kimchi premium
3. Pólvora seca: emisión de USDT/USDC y destino
4. Atribución del movimiento por sesión (Asia / Europa / EE. UU.)

## Estado
**Fase 0 — Validación.** No se construye producto hasta que el backtest pase. Ver `docs/00_PLAN_VALIDACION.md`.

## Estructura
```
0XLongitude/
├── README.md
├── docs/        plan de validación, decisiones
├── data/
│   ├── raw/     datos descargados (Dune, APIs)
│   └── processed/
├── queries/     SQL de Dune
├── src/         scripts Python
├── tests/       pruebas con datos sintéticos (python tests/test_sinteticos.py)
└── results/     salidas del backtest
```

## Hoja de ruta
- **Fase 0 — Validación:** primas + flujos on-chain + backtest. **Cerrada el 21-10-2026: H1 no aporta información (H-08); H2 archivada (H-05).** La atribución regional queda como capa descriptiva.
- **Fase 1 — Señal en vivo:** cálculo diario automático e historial público sin retocar.
- **Fase 2 — Globo (capa visual):** solo si la Fase 0 pasa. Ver `docs/90_IDEA_GLOBO.md`.
- Ideas aparcadas: `docs/91_IDEAS_AMPLIACION.md`.

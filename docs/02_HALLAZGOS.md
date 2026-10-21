# 0xLongitude — Hallazgos (solo periodo de entrenamiento 2022–2024)

## H-01 · La Coinbase premium "clásica" es casi entera el precio de USDT
*Fecha: 2026-10-18 · Datos: `data/processed/primas_diarias.csv`*

- Prima sin ajustar (Coinbase BTC-USD frente a Binance BTCUSDT): correlación **0,995** con el precio USDT-USD en Coinbase.
- Días extremos sin ajustar = crisis de stablecoins: LUNA (2022-05-12, −0,79 %), FTX (2022-11-10, −0,36 %), USDC/SVB (2023-03-11/12, +0,80 % / +1,02 %).
- Pasando Binance a dólares reales (× USDT-USD), la prima queda casi plana: desviación típica **0,008 %**, rango −0,09 % / +0,05 %. El arbitraje de BTC entre Coinbase y Binance es prácticamente perfecto a escala horaria.

**Conclusión:** a esta resolución (cierre horario, media diaria), la Coinbase premium no mide demanda de EE. UU. por sí misma; mide sobre todo el tipo USDT/USD.
**Consecuencia para el diseño:** la pata de EE. UU. dependerá más de los flujos on-chain (Dune) y de los flujos de ETF (H4) que de la prima de precio.
**Variables que se conservan para el backtest** (que decida el test, no la intuición):
- `coinbase_premium_pct` (ajustada)
- `coinbase_premium_sin_ajuste_pct`
- `usdt_usd` (como variable propia: demanda de USDT frente a dólar)

## H-02 · La kimchi premium sí es una señal regional real
- Media +1,88 %, mediana +1,59 %, rango −1,98 % / +10,72 % (2022–2024).
- Pico en marzo de 2024 (+10,7 % el 19/03), coincidiendo con máximos de BTC y entrada minorista coreana.
- Muy persistente (autocorrelación diaria ≈ 0,95): la información útil probablemente está en los **cambios** o en el nivel relativo a su media reciente, no en el nivel bruto.
- Motivo estructural: los controles de capital en Corea impiden que el arbitraje cierre el hueco, a diferencia de EE. UU.

## Calidad de datos
- 26.303 horas en entrenamiento. Faltan 3 h de Coinbase (0,01 %) y 43 h de Upbit (0,16 %).

## H-03 · La kimchi premium sola NO anticipa el retorno diario de BTC
*Fecha: 2026-10-18 · Script: `src/analisis_kimchi.py` · Resultados: `results/analisis_kimchi.txt`*

- 4 variantes (nivel, cambio 1 d, cambio 3 d, z-score 30 d) × 3 horizontes (1, 2, 3 días) = 12 pruebas.
- Ninguna significativa: todos los p_boot > 0,27; todos los |t| (controlando por momentum) < 2; |IC| ≤ 0,035.
- Los quintiles no son monótonos: no hay relación ordenada entre nivel de prima y retorno futuro.
- La referencia (momentum) tampoco predice: mom_1 a 1 día IC −0,05 (p 0,10), ligera reversión a corto plazo.

**Pista débil (no es evidencia):** un pico de la kimchi (quintil más alto de `kimchi_d1`) va seguido de retorno medio negativo a 1, 2 y 3 días (−0,24 %, −0,42 %, −0,28 %), y "BTC sube + kimchi baja" rinde +0,48 % a 2 días frente a +0,03 % con "BTC sube + kimchi sube". Es coherente con la tesis (los movimientos empujados por el minorista coreano se agotan antes), pero la interacción no es significativa (t −0,83 a 2 días).

**Conclusión:** la prima de precio, por sí sola, no basta. Igual que con la Coinbase premium (H-01), el peso de la validación recae en los **flujos on-chain** (Dune). H1 sigue abierta: el criterio de archivo se aplica a la señal completa, no a una pieza.
**Qué se hará con la kimchi:** se conserva como variable de contexto/confirmación para combinar con los flujos, no como señal autónoma.

## Actualización 18-10-2026 (tras corregir el tipo de cambio y la auditoría externa)

### Reconciliación de H-01 con la auditoría
La auditoría externa obtuvo correlación **0,971** entre prima bruta y USDT; aquí se publicó **0,995**. No se contradicen: miden cosas distintas.

| Medida (solo entrenamiento 2022–2024) | Horaria | Diaria (media de horas) | Auditoría (horaria, 2022–2026) |
|---|---|---|---|
| Correlación prima bruta ~ USDT-USD | 0,968 | 0,995 | 0,971 |
| Desviación típica prima bruta (pp) | 0,0891 | 0,0813 | 0,0808 |
| Desviación típica prima ajustada (pp) | 0,0223 | 0,0084 | 0,0196 |
| p1 / mediana / p99 ajustada (%) | −0,041 / +0,005 / +0,057 | — | −0,037 / +0,003 / +0,048 |

La media diaria elimina el ruido horario de microestructura (asincronía de cierres, spread), por eso la correlación diaria es mayor y la dispersión menor. **H-01 queda reproducida de forma independiente.** La prima ajustada se mueve en pocos puntos básicos: a escala horaria es sobre todo microestructura.

Huecos horarios coinciden con la auditoría (Upbit 67 h, Coinbase BTC-USD 13 h en el periodo completo). Cambio aplicado: USDT-USD ya no se rellena indefinidamente; como máximo 2 horas.

### H-03 tras corregir el tipo de cambio (point-in-time)
- Kimchi media 1,879 % → 1,893 %; máximo 10,72 % → 10,99 %. Cambio pequeño, como se esperaba.
- **Conclusión sin cambios:** ninguna prueba significativa (p_boot mínimo 0,098; |t| máximo 1,77; |IC| máximo 0,039).
- **La "pista débil" no es robusta:** "BTC sube + kimchi baja" frente a "BTC sube + kimchi sube" a 2 días pasa de +0,48 % / +0,03 % a +0,36 % / +0,20 % (la diferencia cae de 0,45 a 0,16 puntos) solo por corregir el horario del tipo de cambio, y a 3 días el caso "kimchi sube" rinde más (+0,53 % frente a +0,35 %). Se descarta como indicio.
- Los quintiles del cambio diario de la kimchi ahora son casi monótonos (Q1 +0,34 % → Q5 −0,14 % a 1 día), pero el IC es ~0 y el t es −1,77: el efecto, si existe, está en las colas y no es significativo. Se conserva `kimchi_d1` en el modelo global del prerregistro v2.

## H-04 · Línea base del prerregistro v2: el modelo global no mejora a la tasa base, y la prueba tiene poca potencia
*Fecha: 2026-10-18 · Scripts: `src/etiquetas_eventos.py`, `src/modelo_h1.py` · Resultados: `results/eventos_resumen.txt`, `results/evaluacion_h1_validacion.txt`*

**Eventos (2022–2024):** 252 movimientos (|r| > 1σ), 23,7 % de los días; 141 subidas y 111 bajadas.
Tasas base: continuación 27,8 %, reversión 30,2 %, neutro 42,1 %, fragilidad 15,9 %.
Las bajadas se revierten más (35,1 %) y son más frágiles (20,7 %) que las subidas (26,2 % y 12,1 %).

**Modelo global (diseño 2022–2023 → validación 2024):** no mejora al modelo constante en ningún objetivo. La regularización elegida es siempre la máxima (C = 0,01), es decir, el modelo se encoge hasta la tasa base.

| Objetivo | Mejora de log loss global vs. constante | IC 95 % | AUC |
|---|---|---|---|
| A · continuación | −0,003 | [−0,027, +0,020] | 0,56 |
| B · reversión | +0,004 | [−0,006, +0,014] | 0,55 |
| C · fragilidad | +0,004 | [−0,003, +0,011] | 0,60 |

**Problema de diseño detectado (potencia):** solo hay 155 eventos de diseño y 95 de validación. Prueba con datos sintéticos de Dune y una señal plantada en un flujo regional:
- Señal enorme (desplazamiento ≈ 3 desviaciones típicas): detectada (mejora +0,24, IC [+0,15, +0,32]).
- Señal de ≈ 1 desviación típica, que sería muy valiosa en la práctica: **no detectada** (IC [−0,025, +0,046]).

Conclusión: tal como está el prerregistro v2, la prueba de H1 solo detectaría efectos regionales enormes. Hay que decidir una **v3 ANTES de tener datos de Dune** para que el cambio sea legítimo. Ver opciones en el informe y en la conversación del 18-10-2026.

### H-04 · Actualización con el diseño v3 (umbral 0,5σ, walk-forward, 4 variables)
- 519 eventos en 2022–2024; 360 evaluados fuera de muestra en el walk-forward 2023–2024.
- Tasas: continuación 27,6 %, reversión 27,0 %, neutro 45,5 %, fragilidad 12,5 %.
- **El 86,5 % de los eventos tiene otro evento en los 3 días anteriores:** las ventanas de 72 h se solapan mucho y el tamaño efectivo de la muestra es bastante menor que 519.
- Modelo global vs. constante (walk-forward): A +0,003 [−0,010, +0,017]; B −0,007 [−0,019, +0,003]; C −0,002 [−0,014, +0,010] (con la logística en numpy: −0,0019; con scikit-learn: −0,0018). **El modelo global sigue sin mejorar a la tasa base.**
- Potencia con señal plantada en datos sintéticos: efecto de ≈1 desviación típica detectado (+0,034 [+0,012, +0,055], 8/8 trimestres); efecto de ≈0,5 no detectado; ruido puro sin falsos positivos.
- Lectura: si los flujos regionales tienen un efecto útil, el diseño v3 puede verlo; si el efecto es pequeño, no.

## H-05 · H2 (divergencia contado/derivados, prerregistro 07): sin evidencia, y con un defecto de definición
*Fecha: 2026-10-18 · Script: `src/modelo_h2.py` · Resultados: `results/evaluacion_h2_exploracion.txt`*

- 462 eventos con las tres variables (57 excluidos, sobre todo enero–mayo de 2022); **60 divergentes** (7 en 2022, 30 en 2023, 23 en 2024).
- Reversión: divergentes 28,3 % vs. resto 25,6 % → diferencia +2,7 pp, IC 95 % [−9,9, +14,8]. **No significativa.**
- Fragilidad: 10,0 % vs. 12,9 % → −2,9 pp, IC [−10,8, +5,9]. **No significativa** (signo contrario al esperado).
- Walk-forward: añadir la divergencia no mejora al modelo global (reversión −0,0009 [−0,0032, +0,0013]; fragilidad −0,0058 [−0,0129, −0,0003], es decir, empeora).
- Veredicto según el prerregistro: **H2 v1 no cumple el criterio en 2022–2024 → archivada sin abrir el test.**

**Defecto detectado al revisar el resultado:** el ratio de compras/ventas agresoras en futuros de Binance (`taker_buy_sell`) está sesgado por encima de 1 (mediana 1,099; solo 5 de 969 días por debajo de 1). La condición 3 ("derivados a favor") exige ratio < 1 en las bajadas, así que **ninguna bajada puede ser divergente** (0 eventos). La definición solo mide subidas.
Corregirlo (centrar el ratio frente a su mediana de 30 días) sería un cambio **posterior a ver el resultado**: si se hace, es una hipótesis nueva (H2 v2) de carácter exploratorio, y solo contaría como evidencia si se confirma en el test bloqueado.

## H-06 · Cobertura de etiquetas de exchanges en Dune (query 00a)
*Fecha: 2026-10-21 · Datos: `data/raw/dune/00a_nombres_cex.csv` (650 filas: 27 exchanges × hasta 39 cadenas)*

- **Ethereum:** están todos los exchanges de la Fase 0. Direcciones etiquetadas: Bithumb 494, Coinbase 241, Kraken 231, HTX 219, OKX 217, Coinbase Prime 175, Binance 136, Bitstamp 60, KuCoin 58, Bybit 45, Bitvavo 37, Bitfinex 36, Bitget 35, Upbit 24, Gemini 19, Bitpanda 17, Robinhood 14, Binance US 11, bitFlyer 8, Coincheck 5.
- **Bitcoin:** cobertura pobre para US y Asia (Coinbase 13, Upbit 1, Bithumb 0, bitFlyer 0) → BTC nativo fuera de H1.
- **Tron:** solo exchanges offshore y Binance → no ayuda a medir Asia regulada.
- Número de direcciones ≠ cobertura de volumen: los exchanges grandes usan pocas hot wallets. La cobertura real se medirá con la query 02 (volumen mensual por exchange).
- Japón (bitFlyer 8, Coincheck 5) es el punto más débil de ASIA; si la query 02 muestra volumen marginal, ASIA será en la práctica Corea.

## H-07 · Estructura de los flujos de exchanges en Dune (query 00b, últimos 7 días)
*Fecha: 2026-10-21 · Datos: `data/raw/dune/00b_estructura_flows.csv`*

- Tipos de flujo: Inflow 22,4 mil M$, Outflow 22,4 mil M$, Internal 14,6 mil M$, Cross-CEX 0,3 mil M$ (7 días, Ethereum).
- **Las entradas y salidas brutas casi se igualan**: el neto es una diferencia pequeña entre dos cifras enormes, lo que hace la señal sensible a errores de etiquetado.
- **Cross-CEX es casi nulo**: los traspasos entre exchanges no se ven como tales; pasan por direcciones de depósito sin etiquetar. Por eso se añade la sensibilidad `neto_externo_limpio`.
- Stablecoins dominan: USDT ~9,3 mil M$ y USDC ~6,9 mil M$ por lado; ETH ~4,6 mil M$; WBTC ~0,05 mil M$.

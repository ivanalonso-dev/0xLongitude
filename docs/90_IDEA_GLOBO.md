# 0xLongitude — Idea: visualización en globo (Fase 2)

> Aparcada a propósito. **No se construye hasta que la Fase 0 (validación) pase.**
> Origen: el globo de seesrc.si (capas de vuelos, terremotos, cables submarinos).

## Concepto
Globo 3D con los datos de 0xLongitude como capas, igual que seesrc.si usa vuelos o terremotos.

## Capas previstas
| Capa | Qué muestra | Dato de origen |
|------|-------------|----------------|
| Nodos regionales | Un punto por región (Nueva York, Europa, Seúl, Tokio, Hong Kong) + Binance y Offshore fuera del mapa o en el océano | `entidades_region.csv` |
| Pulso de flujo neto | Tamaño/brillo del nodo = flujo neto a exchanges (entrando = presión vendedora, saliendo = acumulación) | flujos on-chain (Dune) |
| Color de prima | Verde/rojo según Coinbase premium y kimchi premium | `primas_diarias.csv` |
| Arcos | Movimientos grandes de stablecoins/BTC entre exchanges de regiones distintas | transferencias on-chain |
| Línea día/noche | Qué sesión está activa (Asia, Europa, EE. UU.) | calculada |
| Emisión de stablecoins | Pulsos desde Tether/Circle hacia los exchanges que reciben | Dune |

## Tecnología
- **globe.gl** (sobre three.js): puntos, arcos animados y anillos en pocas líneas.
- Página HTML que lee un JSON diario generado por el pipeline.

## Por qué después y no ahora
El globo es escaparate. Si la señal no funciona, el globo enseña ruido bonito. Si funciona, el globo multiplica su atractivo para portfolio, X y clientes.

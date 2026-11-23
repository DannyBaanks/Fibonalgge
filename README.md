# Fibonalgge — COMPOSE MAL-E01

Investigación matemática y experimental sobre **Classic Malbolge**: estructura de `crz`, recurrencia de inicialización, autocifrado, observables de ejecución y falsación de predictores.

El nombre no presupone el resultado. Fibonacci se usa como inspiración y como predictor de control; no se implementa una secuencia Fibonacci para fingir un descubrimiento espontáneo.

## Alcance

- Classic Malbolge de 59 049 palabras de diez trits, semántica estricta de Olmstead.
- Piloto exhaustivo de los nueve pares de trits y comparación íntegra del relleno de memoria.
- VM instrumentada con eventos, escrituras, checkpoints y snapshots periódicos.
- Corpus separado por programa en `discovery` y `validation`.
- Predictores triviales, Markov de orden 1/2, recurrencias modulares y reglas locales derivadas de la especificación.
- Resultados positivos, negativos y contraejemplos con la misma evidencia.

No se estudian Malbolge Unshackled, Malbolge Free ni extensiones. No se modifica ningún repositorio de producción.

## Entregables

- [`RESEARCH_REPORT.md`](RESEARCH_REPORT.md): método, resultados, límites y gates.
- [`HYPOTHESES.md`](HYPOTHESES.md): estados H1–H5 y falsadores.
- [`ALGEBRA.md`](ALGEBRA.md): demostraciones y tablas exhaustivas.
- [`COUNTEREXAMPLES.md`](COUNTEREXAMPLES.md): hipótesis fallidas y rupturas.
- [`RESULTS.json`](RESULTS.json): medidas estructuradas de la corrida final.
- [`evidence/`](evidence/): trazas comprimidas, snapshots, casos y resultados por corrida.
- [`GUIA.md`](GUIA.md): reproducción exacta y presupuesto.

## Implementación

Python 3.10+ y biblioteca estándar. El oráculo externo es `../BolgeForge/mb_ref`; el control Python independiente es `../Malbolge-PureEpoch/baseline/epoch_probe.py`. Las fuentes originales se leen en su ubicación y se identifican por SHA-256; no se copian ni reescriben.

La recurrencia rápida sólo sustituye el **cálculo** de la inicialización, no su semántica. Cada programa de la corrida compara las 59 049 celdas del modelo rápido contra el relleno literal antes de ejecutar.

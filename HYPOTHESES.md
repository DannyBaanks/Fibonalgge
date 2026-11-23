# Hipótesis, falsadores y estados

Etiquetas: `DEMONSTRATED`, `INFERRED`, `NOT_DEMONSTRATED`, `FALSIFIED`. El alcance forma parte del estado.

## H1 — Estructura algebraica de `crz`

**Predicción comprobable.** Las nueve entradas y las 27 ternas bastan para aceptar/refutar identidades, absorción, idempotencia, conmutatividad y asociatividad.

**Resultado: `DEMONSTRATED`.** No hay identidades, absorbentes ni idempotencia. No hay conmutatividad ni asociatividad. Se conservan todos los contraejemplos en `RESULTS.json` y un resumen en `ALGEBRA.md`.

**Falsador aplicado.** Enumeración completa, incluida `crz(crz(0,0),0)≠crz(0,crz(0,0))`.

## H2 — Recurrencia y periodicidad de memoria inicial

**Predicción comprobable.** El grafo de nueve pares determina ciclos, transitorios, cuencas y período conjunto de diez trits.

**Resultado: `DEMONSTRATED`.** Ciclos 2, 2 y 3; transitorio máximo 1; período conjunto 6. Las seis primeras palabras generadas forman la caché periódica exacta, sin excepción para la primera.

**Falsadores aplicados.** Los nueve pares uniformes a memoria completa, casos reales no uniformes, 720 predicciones por trit contra iteración y comparación celda por celda contra `naive_memory`. Ninguna discrepancia en la corrida final.

**Límite.** Es caracterización de una regla ya especificada, no una recurrencia nueva descubierta en ejecución.

## H3 — Islas de predictibilidad durante ejecución

**Predicción comprobable.** Los observables pueden admitir reglas exactas con dominio explícito o mejoras fuera de muestra sobre baselines.

**Resultado: `DEMONSTRATED` para reglas locales conocidas.** Los incrementos de `C`/`D` módulo 94 son exactos fuera de salto, wrap y parada; todos los fallos quedan clasificados por esas causas. La alta persistencia de `A mod 3` es estadística, no exacta.

**Resultado global: `NOT_DEMONSTRATED`.** Ningún observable estudiado produce una recurrencia exacta global de ejecución. El corpus y presupuesto limitan este negativo.

**Falsadores.** Programas completamente held-out, predictores mayoría/persistencia, Markov 1/2, contraejemplos por programa y análisis de causas de fallo.

## H4 — Representaciones alternativas

### H4a — Cola de inicialización

**Resultado: `DEMONSTRATED`.** `φ` almacena fuente + seis celdas generadas; `F` es indexación modular desde la primera celda de la cola. Hay predicción y salto de trabajo exactos.

### H4b — Autocifrado

**Resultado: `DEMONSTRATED`.** `φ(v)=(cycle_id,phase)` y `F` rota la fase en uno de los seis ciclos de `XLAT2`. Se verifican 94×3061 casos.

### H4c — Ejecución completa

**Resultado: `NOT_DEMONSTRATED`.** No se encontró un `Z=φ(S)` autónomo, más pequeño y cerrado bajo toda `T`. Las representaciones anteriores no predicen por sí solas control de flujo, entrada o escrituras externas a su subsistema.

**Falsador pendiente para cualquier candidata futura.** Igualdad exacta en programas e inputs no usados para construirla, con contabilización de información del modelo y fallos fuera de dominio.

## H5 — Analogía Fibonacci y recurrencias pequeñas

**Predicción comprobable.** `next=(prev+prev2) mod 3`, la recurrencia `crz` y 27 recurrencias lineales `α·prev+β·prev2+γ (mod 3)` se comparan con baselines en observables de `A`.

**Resultado: `FALSIFIED` para Fibonacci como regla exacta o competitiva en este corpus.** Presenta errores abundantes en validación y no supera persistencia. La recurrencia `crz` aplicada a `A` también falla. La búsqueda lineal selecciona persistencia (`α=1,β=γ=0`), no Fibonacci.

**Resultado para otros módulos/modelos: `NOT_DEMONSTRATED`.** No se exploró un espacio ilimitado de recurrencias ni se afirma imposibilidad.

**Control de selección.** Las 27 recurrencias se eligen sólo en `discovery`; `validation` queda separado por programa. No se ajusta después de ver validación.

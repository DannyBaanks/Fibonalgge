# MAL-E01 — Estructuras en el caos de Malbolge

**Corrida principal:** `MAL-E01_20261123T024848Z`

**Lenguaje:** Classic Malbolge, 59 049 palabras de diez trits

**Resultado central:** estructuras exactas locales demostradas; reducción global de ejecución no demostrada.

## Resumen ejecutivo

La investigación distingue los tres resultados que no deben confundirse:

1. **Programar Fibonacci:** no se usó como evidencia. El artefacto histórico toolkit-only quedó fuera del corpus.
2. **Patrones en trazas:** se midieron contra baselines, programas held-out y un control nulo barajado. Hay dependencias estadísticas, pero ninguna recurrencia exacta global.
3. **Transformaciones matemáticas:** se demostraron dos, con dominio limitado:
   - la recurrencia de inicialización se reduce a seis palabras y indexación módulo 6;
   - `XLAT2` se representa por ciclo+fase y permite saltar autocifrados.

La primera da predicción, compresión de representación y aceleración exactas para la **cola generada**. La segunda da predicción/aceleración para el **autocifrado aislado**. Ninguna predice por sí sola la ejecución completa.

En ejecución, la mejor interpretación es una combinación de **A local**, **B estadística acotada** y **D consecuencia conocida de la especificación**. No se encontró una dinámica Fibonacci espontánea.

## 1. Método

### 1.1 Fases ejecutadas

- **A — Validación:** tabla `crz`, rotación exhaustiva, loader estricto, inicialización literal, ejecución y comparación con `mb_ref` y PureEpoch.
- **B — Álgebra exhaustiva:** nueve pares de trits, ciclos/cuencas/transitorios, 94 estados de `XLAT2` y 27 ternas para asociatividad.
- **C — Corpus:** diez programas distintos, once ejecuciones, inputs y presupuestos registrados.
- **D — Observables:** opcode, `A mod 3`, trit alto de A, `C/D mod 94`, clase de escritura.
- **E — Falsación:** programas held-out, denominadores alineados, micro/macro, baselines, control nulo, contraejemplos, mecanismo por opcode y revisor independiente.
- **F — Predicción/compresión/aceleración:** evaluadas por separado; no se atribuyen propiedades de inicialización a runtime.

### 1.2 Entorno y procedencia

- Python 3.12.3; Zig 0.16.0 registrado, no usado como dependencia.
- Linux 7.0.0-43-generic x86_64.
- BolgeForge: `0f4b3a5dc3e87d77b318a730d168160758881ad7`.
- PureEpoch: `9ff4c5c53ab30af43debf74ae63ba38d8ca12cba`.
- MALBOLGE: `31bc39def75e90738a4924182645464567d944d2`.
- Base MB: `2c8bcfa9e7711a9f23511cffb2f46bf8ef7df936`.
- Oráculo `mb_ref`: SHA-256 `463723a2484d1ea384472c232cfe89fdce7a19aa73d4d2396c2cc68f6d45889a`.
- Fuente del oráculo: `cabe58e60077b78a030839f3165ed5d1d508c3ec40c5263a94dfbbfbb95a718c`.

Fibonalgge era un repositorio nuevo sin commit al ejecutar. Sus diez archivos Python ejecutados están identificados individualmente por SHA-256 en `environment.executed_source_sha256`. El estado del árbol padre incluía una modificación ajena ya existente; no se tocó.

## 2. Gate A — Integridad semántica

### Pruebas

- Tabla canónica de `crz` con orden de operandos explícito.
- Rotación de diez trits verificada para las 59 049 palabras.
- Loader estricto y rechazo de entradas inválidas.
- Modelo rápido contra relleno literal: 20 casos × 59 049 = **1 180 980 celdas**, sin discrepancias.
- Once ejecuciones contra `mb_ref`: salida byte-exacta y terminal compatible en 11/11; en `MAX_STEPS`, presupuesto exacto.
- Causas de STALL comparadas por prefijo concreto, no sólo por exit code.
- Prefijos contra la `Machine` independiente de PureEpoch: registros, input, salida y memoria completa.
- Dieciséis pruebas ejecutadas tras la revisión; salida cruda en `evidence/.../logs/`.

`mb_ref` no expone registros ni pasos finales al encontrar HALT; no se declara esa comparación inexistente. La paridad de memoria/registros se cubre con el control Python y snapshots.

**Gate A: PASS para el alcance medido.**

## 3. H1 — Álgebra de `crz`

La tabla completa y las 27 ternas demuestran ausencia de identidades, absorbentes, idempotencia, conmutatividad y asociatividad. Hay cuatro contraejemplos de conmutatividad y 15 de asociatividad.

No se impuso una estructura algebraica convencional. Las permutaciones parciales y todos los contraejemplos están en `RESULTS.json` y `ALGEBRA.md`.

**Estado: DEMONSTRATED.**

## 4. H2 — Recurrencia de memoria inicial

El grafo completo de `R(x,y)=(y,crz(y,x))` tiene:

- ciclo A de longitud 2, cuenca de cuatro estados;
- ciclo B de longitud 2, cuenca de dos;
- ciclo C de longitud 3, cuenca de tres;
- transitorios `(0,0)` y `(1,1)`, ambos de longitud 1;
- período conjunto `mcm(2,2,3)=6`.

La revisión adversarial refinó el resultado: incluso los transitorios producen una secuencia generada periódica desde `G0`. Por tanto, con `G0..G5=M[N..N+5]`:

\[
M[i]=G_{(i-N)\bmod 6},\qquad i>=N.
\]

Se comprobaron 720 predicciones por trit contra iteración y toda la memoria en los nueve pares uniformes más once fuentes reales. La demostración exhaustiva por trit se extiende composicionalmente a palabras sin enumerar `59049²` pares.

**Estado: DEMONSTRATED; consecuencia exacta de la regla conocida.**

## 5. H4a — Predicción, compresión y aceleración de inicialización

Estas propiedades se miden por separado:

| Propiedad | Resultado | Dominio |
|---|---|---|
| Predicción | `M[i]` exacto por índice modular | Cola generada, `i>=N` |
| Compresión | 6 palabras de caché frente a 59 047 para N=2; alternativa: 2 semillas + algoritmo | Representación de cola, no trazas |
| Trabajo | 6 llamadas `crazy` frente a 59 047 | Última celda, N=2 |
| Razón exacta de llamadas | 9 841,1667× | Ese objetivo |
| Wall time mediano | 0,067044 s convencional vs 0,000025348 s modelo | Cinco repeticiones en este host |
| Speedup mediano medido | 2 644,9467× | No extrapolado a otros hosts |

La diferencia entre razón de llamadas y speedup se conserva deliberadamente. El código compartido y la tabla `crz` no se contabilizan como ahorro de información.

## 6. H4b — Autocifrado como fase

`XLAT2` es una permutación de 94 imprimibles con ciclos de longitudes 68, 9, 6, 5, 4 y 2. `φ(v)=(cycle_id,phase)` cumple `φ(XLAT2(v))=F(φ(v))`, donde `F` incrementa la fase.

- Período conjunto: 3 060.
- Verificación: 94×3 061 = **287 734** estados/pasos, sin errores.
- Predicción: `XLAT2^k(v)` por acceso a fase, sin k cifrados intermedios.
- Compresión de estados: **no demostrada**; la representación conserva 94 posibilidades.
- Alcance: no incluye `p`, `*`, saltos, entrada ni elección de la próxima celda.

**Estado: DEMONSTRATED para autocifrado aislado; conocido en el ecosistema y reverificado aquí.**

## 7. Corpus de ejecución

| Caso | Split | Pasos | Terminal | Paridad C |
|---|---|---:|---|---|
| hello | discovery | 47 | HALT | PASS |
| sort2 | discovery | 812 | HALT | PASS |
| cat | discovery | 9 433 | HALT | PASS |
| clock | discovery | 1 806 | HALT | PASS |
| add | discovery | 614 | HALT | PASS |
| rot13 | validation | 20 000 | MAX_STEPS | PASS |
| truth_0 | validation | 38 | HALT | PASS |
| truth_1 | validation | 5 000 | MAX_STEPS | PASS |
| rev | validation | 362 | HALT | PASS |
| rule90 | validation | 322 | HALT | PASS |
| bottles | validation | 20 000 | MAX_STEPS | PASS |

Total observado: 58 434 pasos y 58 442 eventos. Hay 32 checkpoints con memoria completa. Las trazas JSONL ocupan 15 680 101 bytes antes de gzip y 1 637 488 después; esto es compresión de registros, no evidencia de compresión semántica de Malbolge.

## 8. H3/H5 — Resultados fuera de muestra

Todos los modelos se ajustan y puntúan desde el tercer valor de cada secuencia: **45 713 predicciones por modelo** en validación. Los dos programas largos aportan 87,4937 % del total; por eso se reportan micro y macro.

### 8.1 Observables de A

| Modelo, `A mod 3` | Micro | Macro por caso | Nulo barajado |
|---|---:|---:|---:|
| Mayoría | 33,1153 % | 32,9650 % | 33,1262 % |
| Persistencia / Markov / mejor lineal | 80,0604 % | 88,2752 % | 41,3121 % |
| Fibonacci mod 3 | 28,8233 % | 29,7742 % | 29,8121 % |
| Recurrencia `crz` | 15,6804 % | 9,4783 % | 30,1599 % |

Las 27 recurrencias `α·prev+β·prev2+γ mod 3` se seleccionaron sólo en discovery. La ganadora es persistencia (`1,0,0`). Fibonacci queda falsado como regla exacta o competitiva aquí.

La persistencia tiene explicación mecánica: 32 784/45 713 transiciones son opcodes que garantizan preservar A. En `p` sólo 10,7980 % conserva `A mod 3`; en `*`, 42,4361 %. Es una consecuencia del ISA, no una recurrencia oculta.

### 8.2 Opcodes

| Modelo | Micro | Macro | Nulo |
|---|---:|---:|---:|
| Mayoría | 30,5887 % | 49,0458 % | 30,5843 % |
| Markov-1 | 38,9102 % | 54,8766 % | 30,2474 % |
| Markov-2 | 33,6338 % | 56,1590 % | 30,1074 % |

Hay dependencia temporal estadística sobre el nulo, pero no exactitud. Markov-2 sobreajusta: 66,5303 % discovery frente a 33,6338 % micro validation. No se construyó un compresor modelo+residual; no se afirma compresión.

### 8.3 Reglas locales de C/D

La regla `+1 mod 94` sin condiciones falla en saltos, wrap y HALT. En su dominio exacto —paso completado, sin `i` para C o `j` para D, sin dirección 59 048—:

- discovery: C 11 620/11 620; D 10 318/10 318;
- validation: C 43 235/43 235; D 31 070/31 070;
- fallos inexplicados: cero.

**Estado: DEMONSTRATED como regla local conocida; no como modelo autónomo global.**

## 9. Revisión adversarial

El revisor independiente no falsó la tabla, el grafo, la VM ni la separación mecánica. Sí detectó y documentó:

1. hash inicial aliasado al final en 11/11 recibos;
2. redundancia de la séptima palabra y una justificación incorrecta del transitorio;
3. desfase entre H3 escrito y evidencia archivada;
4. 81 candidatos declarados cuando había 27;
5. gate demasiado laxo para causas de STALL;
6. dominio de programas largos en micro-promedios.

Se corrigieron los seis, se añadieron pruebas de regresión, macro-promedios, controles nulos y una corrida nueva. Las anteriores se conservan, pero no respaldan el informe final. Detalle: `ADVERSARIAL_REVIEW.md` y `COUNTEREXAMPLES.md`.

## 10. Gates finales

| Gate | Resultado | Evidencia |
|---|---|---|
| 1 — Semantic integrity | PASS acotado | 11/11 C, control PureEpoch, 16 tests |
| 2 — Mathematical reproducibility | PASS | Enumeración exhaustiva, hashes, código |
| 3 — Pattern validity | PASS para claims acotados | Baselines, nulos, mecanismo ISA, contraejemplos |
| 4 — Out-of-sample prediction | PASS local; global NO | Programas held-out; ningún modelo global exacto |
| 5 — Adversarial review | PASS tras correcciones | Seis hallazgos y regresiones |
| 6 — Evidence integrity | PASS tras manifiesto | Logs, comandos, snapshots, SHA-256 por artefacto |

“PASS” no significa verdad universal fuera del dominio indicado.

## 11. Limitaciones y trabajo abierto

- Corpus pequeño y presupuesto máximo agregado de 100 000 pasos; no se trazó una quine completa.
- `rot13` y `bottles` no llegaron a HALT dentro de 20 000 pasos.
- Sólo se exploraron observables y modelos pequeños declarados; no se descartan representaciones de otras clases.
- Los intervalos Wilson son descriptivos: pasos consecutivos no son independientes.
- No se midió aceleración end-to-end con `XLAT2` ni compresión modelo+residual.
- Las estructuras exactas encontradas caracterizan reglas de la especificación; no prueban emergencia.
- Una reducción autónoma `φ(T(S))=F(φ(S))` para ejecución completa sigue **NOT_DEMONSTRATED**.

## 12. Reproducción

```bash
cd '/home/danny/Development/ISyCo Git/Fibonalgge'
python3 -m unittest discover -s tests -v
python3 mal_e01.py pilot
python3 mal_e01.py run --run-id MAL-E01_NUEVO_IDENTIFICADOR
python3 tools/hash_run.py evidence/MAL-E01_NUEVO_IDENTIFICADOR
python3 tools/hash_run.py evidence/MAL-E01_NUEVO_IDENTIFICADOR --verify
```

No reutilizar el identificador de la corrida principal: el programa rechaza sobrescribir evidencia. La guía completa está en `GUIA.md`.

## Conclusión

Sí hay orden demostrable, pero su alcance importa. La inicialización tiene una representación exacta de seis palabras y el autocifrado una representación exacta de fase. En cambio, las regularidades de ejecución medidas son estadísticas o consecuencias directas del ISA. Fibonacci no sobrevive la falsación. La transformación verdaderamente general de la dinámica de Malbolge no fue encontrada bajo este alcance.

# Revisión adversarial — MAL-E01

## Alcance

Revisor independiente en dos pasadas, sin asumir las hipótesis del investigador y con instrucción de sólo lectura. Revisó tabla y orden de `crz`, grafo, `TailModel`, VM, oráculos, separación de muestras, métricas, recibos y controles.

## Primera pasada

### Lo que resistió falsación

- Tabla `crz` y orden de operandos: control independiente contra `mb_ref.c` sobre 117 978 palabras, sin divergencias.
- Grafo: ciclos 2, 2 y 3; transitorios `(0,0)` y `(1,1)`; período conjunto 6.
- VM: registros, salida y memoria completa contra PureEpoch en las once ejecuciones, sin divergencias.
- Separación mecánica discovery/validation: validation no se usa para ajuste.
- Hashes de 43 trazas/snapshots: correctos; el defecto encontrado estaba en un campo derivado del recibo.

### Hallazgos y resolución

| Severidad | Hallazgo | Resolución verificable |
|---|---|---|
| Alta | `initial_memory_sha256` contenía el hash final por aliasing en 11/11 casos | Hash calculado antes de ejecutar; VM recibe `initial.copy()`; aserción contra checkpoint; prueba de regresión |
| Media | Séptima palabra redundante y excepción transitoria incorrecta | Modelo reducido a seis; fórmula desde G0; prueba exhaustiva de periodicidad en nueve pares |
| Media | H3 escrito antes de existir en el artefacto | Nueva corrida con `register_local_rules`; recomputación completa desde trazas |
| Media | 81 candidatos declarados cuando `3³=27` | Código, JSON y documentos corregidos a 27 |
| Media | Gate C mezclaba causas de STALL | `terminal_parity` exige prefijo concreto de stderr; prueba cruzada negativa |
| Baja | Micro-promedio dominado por dos programas largos | Macro por caso, conteos y cuota 87,4937 % añadidos; denominadores alineados |

La primera corrida quedó preservada como evidencia de desarrollo, no como respaldo del informe final.

## Segunda pasada — corrida `MAL-E01_20261123T024848Z`

**Veredicto global: PASS. Sin defectos restantes dentro del alcance revisado.**

1. **Hash inicial:** 11/11 coincide con checkpoint inicial y difiere del final.
2. **Modelo de seis:** 9/9 pares verificados independientemente, `G[6:]==G[:-6]` y `G0==G6`.
3. **Reglas locales:** discovery C 11 620/11 620, D 10 318/10 318; validation C 43 235/43 235, D 31 070/31 070; cero fallos inexplicados.
4. **Candidatos:** 27 en ambos modelos y textos actuales.
5. **STALL:** combinaciones cruzadas y STALL sin causa son rechazados.
6. **Métricas:** 12 707 predicciones discovery y 45 713 validation/nulo por modelo; macro recomputado como media no ponderada de seis casos.

### Controles nuevos revisados

- **Nulo barajado:** determinista, conserva longitudes/marginales por programa, usa la misma permutación para todos los modelos y no participa en ajuste. La recomputación completa de `execution_analysis` fue igual al JSON archivado.
- **Mecanismo de persistencia:** sumas discovery 10 941/12 707 y validation 36 598/45 713; todos los opcodes que no modifican A tienen exactamente `correct==total`.
- **Pruebas:** 16/16.
- **Fuentes:** diez hashes de archivos ejecutados coinciden con el código actual.
- **Artefactos:** 43 trazas/snapshots con hashes correctos.
- **Raíz:** `RESULTS.json` idéntico al de la corrida principal.

## Límites del veredicto

- El nulo es una única permutación descriptiva, no una estimación de significancia.
- En HALT, `mb_ref` compara salida y terminal; memoria/registros finales se validan por el control Python, no por una exportación inexistente de C.
- PASS cubre los artefactos y el alcance examinados; no demuestra ausencia universal de otros errores ni una reducción global de ejecución.

# Guía de reproducción — MAL-E01

## Requisitos

- Linux, Python 3.10+ y `zig` sólo para registrar la versión del entorno; el experimento no compila Zig.
- Repositorios hermanos `BolgeForge` y `Malbolge-PureEpoch` en las rutas indicadas por `fibonalgge/experiment.py`.
- `../BolgeForge/mb_ref` compilado. Su binario y `oracle/mb_ref.c` quedan hasheados en cada `RESULTS.json`.
- Sin paquetes Python externos, red, GPU ni servicios.

Desde esta carpeta:

```bash
python3 -m unittest discover -s tests -v
python3 mal_e01.py pilot
```

## Corrida completa

Usar siempre un identificador nuevo; el programa se niega a reutilizar un directorio de evidencia:

```bash
run_id=$(date -u +MAL-E01_%Y%m%dT%H%M%SZ)
python3 mal_e01.py run --run-id "$run_id"
```

Salidas:

```text
RESULTS.json                         copia de la última corrida
 evidence/<run_id>/RESULTS.json      resultado inmutable de esa corrida
 evidence/<run_id>/cases.json        recibos intermedios por programa
 evidence/<run_id>/traces/*.jsonl.gz eventos y escrituras por paso
 evidence/<run_id>/snapshots/…       memoria uint16-LE gzip inicial/final y cada 5000 pasos
```

Cada evento incluye `event`, `step`, registros antes/después, instrucción, valores de `mem[C]`/`mem[D]`, escrituras `[address,old,new,cause]`, entrada/salida y estado terminal. `step` cuenta instrucciones completadas como `mb_ref`; `event` incluye también HALT o fallo terminal.

## Corpus y presupuesto

Hay once ejecuciones de diez programas distintos (`truth_0` y `truth_1` comparten programa y split). El presupuesto configurado suma 100 000 pasos como máximo; los programas que terminan consumen menos. El tope por caso está declarado en `default_corpus()` y dentro de cada recibo.

- `discovery`: `hello`, `sort2`, `cat`, `clock`, `add`.
- `validation`: `rot13`, `truth_0`, `truth_1`, `rev`, `rule90`, `bottles`.
- No se mezclan pasos contiguos entre entrenamiento y validación.
- Las trazas se comprimen con gzip nivel 9 y los snapshots son reconstruibles como 59 049 enteros sin signo de 16 bits little-endian.

## Verificación de una corrida

1. `pilot.memory_parity.pass` y `pilot.trit_prediction.pass` deben ser verdaderos.
2. Todos los casos deben tener `parity.pass=true`: salida byte-exacta y terminal compatible con `mb_ref`; para `MAX_STEPS`, también el presupuesto exacto.
3. Los hashes de fuentes, entrada, memoria inicial/final, trazas y snapshots deben coincidir con los archivos.
4. Los modelos se seleccionan sólo con `discovery`; las cifras de `validation` no se reutilizan para ajustar parámetros.
5. Los tiempos medidos son del host registrado. Las razones de llamadas `crazy` son exactas; no se extrapolan a otros hosts.

`mb_ref` no expone el número de pasos ni los registros finales cuando encuentra HALT. Por eso la paridad C en ese caso cubre salida y terminal, no se inventa una comparación de pasos. Los prefijos de VM y estados completos se contrastan por separado con la `Machine` independiente de PureEpoch en las pruebas.

## Política de evidencia

- No editar resultados dentro de una corrida. Una corrección genera otra `run_id` y una errata en el informe.
- Un `PASS` es finito y condicionado al corpus/presupuesto, nunca una prueba universal de ejecución.
- Las afirmaciones del grafo de nueve estados y de la permutación de 94 imprimibles sí tienen enumeración exhaustiva.
- Las predicciones estadísticas no se llaman transformaciones exactas si tienen un solo contraejemplo.

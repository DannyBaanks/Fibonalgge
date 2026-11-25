# Guía de reproducción — MAL-E02

## Requisitos

- Linux, Python 3.10+.
- Runner C original de Classic Malbolge en
  `../MALBOLGE-MB-DATABASE/runners/malbolge-original/malbolge`.
  Se puede cambiar con `MALBOLGE_ORIGINAL_RUNNER`.
- `../BolgeForge/mb_ref` para el control de cargador estricto.
- Sin paquetes Python externos, red, GPU ni servicios.

## Pruebas y modelo

```bash
cd '/home/danny/Development/ISyCo Git/Fibonalgge'
python3 -m unittest discover -s tests -v
python3 mal_e02.py pilot
```

`pilot` imprime el dominio de 59 049 palabras, el resultado de escritura exacta, el
rearme y la secuencia modelada. No escribe evidencia.

## Corrida completa

Usar siempre un identificador nuevo; el programa se niega a reutilizar un directorio:

```bash
run_id=$(date -u +MAL-E02_%Y%m%dT%H%M%SZ)
python3 mal_e02.py run --run-id "$run_id"
python3 tools/hash_run.py --verify "evidence/$run_id"
```

La corrida final documentada es `MAL-E02_20261125T002802Z`.

## Qué genera

```text
RESULTS_MAL_E02.json                  copia de la última corrida
evidence/<run_id>/RESULTS.json       resultado inmutable
evidence/<run_id>/cases.json         resumen por caso
evidence/<run_id>/programs/*.mb      imágenes Classic ejecutables
evidence/<run_id>/traces/*.jsonl     eventos completos por paso
evidence/<run_id>/ARTIFACT_MANIFEST.json
evidence/<run_id>/SHA256SUMS.txt
```

## Cómo leer el resultado

- `positive_29645` y `positive_31713`: el slot guarda `H-1`, el salto aterriza en `H`
  después del incremento de `c`, la celda del aterrizaje se cifra y el programa termina
  en `HALT`.
- `negative_29645` y `negative_31713`: el slot guarda `29524`; el salto aterriza en
  `29525`, no en el target. Sirve para descartar que el destino sea una coincidencia del
  layout.
- `model.exact_write_ok` y `model.rearm_ok`: identidades algebraicas para las 59 049
  palabras.
- `model_sequence`: modelo de dos ciclos; **no** es una imagen de dos ciclos.

## Límites

- La imagen de un ciclo termina en `HALT`; no rearma el slot después del retorno.
- El builder sólo construye payloads sin trits 0; las palabras con 0 quedan cubiertas
  por el modelo, no por la imagen.
- `mb_ref` rechaza la imagen en carga porque exige que toda celda fuente sea un opcode
  válido. El runner C original y la VM instrumentada sí la ejecutan.
- La composición con P12 no se ejecutó en esta etapa.

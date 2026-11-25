# Procedencia y límites de fuentes

## Oráculos y semántica

- **BolgeForge `oracle/mb_ref.c` / `mb_ref`**: oráculo C estricto. La corrida registra SHA-256 de ambos, comando, exit code, stdout y stderr.
- **PureEpoch `baseline/epoch_probe.py`**: implementación Python independiente usada por las pruebas para comparar prefijos, registros, salida y memoria completa.
- **Classic Malbolge**: 59 049 celdas, diez trits por palabra, EOF=59 048, cifrado posterior con `C` ya actualizado por `i`, y HALT sin cifrado/incremento.

## Corpus

Las rutas relativas y presupuestos están en `fibonalgge/experiment.py::default_corpus`. Cada recibo guarda ruta absoluta resuelta, bytes, celdas cargadas, SHA-256 e input hexadecimal. Los originales permanecen fuera de este repositorio y no se modifican.

Se excluye deliberadamente `Autobolge/artifacts/fibonacci.mal`: la genealogía lo clasifica como salida finita precomputada y toolkit-only, no como evidencia canónica de estructura espontánea.

## Historial de Git

Cada corrida captura HEAD, estado de cambios tracked y número de untracked para Fibonalgge, BolgeForge, PureEpoch, MALBOLGE, MALBOLGE-MB-DATABASE y el padre de genealogía. La corrida principal ocurrió con repositorio nuevo sin commit: `git rev-parse HEAD` devolvió el literal `HEAD` junto a un exit code distinto de cero. Ese literal no es un SHA y no se presenta como tal; la procedencia del código se fija mediante los diez hashes de fuentes ejecutadas. No se atribuye retroactivamente el commit posterior a la corrida.

La genealogía fue utilizada como mapa de rutas, no como evidencia primaria. Las afirmaciones finales proceden del código y las corridas locales de esta investigación.

## MAL-E02: planificador y runner

- **`fibonalgge/planner.py`**: adaptación local del planificador de
  `MALBOLGE-MB-DATABASE/vm_malbolge/evidence/epoch_resolver_word_v1/plan.py`
  (SHA-256 `9685514d1ad67756e46b52e7afd3d5c8eb121fba26138b9e4cfb9defabdb805b`).
  Se conservaron las reglas de rutado y placement; se sustituyó el oráculo externo por
  `fibonalgge.classic.crazy` y `fibonalgge.classic.rotate`. La adaptación se identifica
  por su propio SHA-256 en `RESULTS.json`.
- **`MALBOLGE-MB-DATABASE/runners/malbolge-original/malbolge`**: runner C original usado
  para la paridad de ejecución de MAL-E02. Acepta celdas de dato que no son opcodes
  válidos, a diferencia del cargador estricto de `mb_ref`.
- **`../BolgeForge/mb_ref`**: se ejecuta como control de cargador estricto. En MAL-E02
  rechaza la imagen en carga con `INVALID_OPCODE: cell 41`; no se usa como evidencia de
  ejecución de esa imagen. Los casos de MAL-E01 que sí cumplen su cargador siguen
  usando `mb_ref` como oráculo.
- La corrida `MAL-E02_20261125T002802Z` registra SHA-256 de `address_slot.py`,
  `planner.py`, `mal_e02.py`, las pruebas y el planificador original.

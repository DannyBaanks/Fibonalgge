# MAL-E02 — Slot reutilizable de direcciones completas en Classic Malbolge

**Estado:** cierre de la primera etapa. Una imagen Classic real guarda una dirección
completa de diez trits, salta indirectamente a través de ella, aterriza en el destino
respetando el incremento obligatorio de `c`, cifra la celda del nuevo `c` y termina en
`HALT`. La escritura exacta y el rearme se demuestran de forma exhaustiva **en el modelo
algebraico**; la repetición dentro de la misma imagen queda explícitamente fuera de este
resultado.

- **Corrida final:** `MAL-E02_20261125T002802Z`
- **Evidencia:** `evidence/MAL-E02_20261125T002802Z/`
- **Manifiesto:** 10 artefactos, `HASH_MANIFEST_OK`
- **Pruebas:** 23/23 en la suite completa
- **Repositorio:** `DannyBaanks/Fibonalgge`

## 1. Pregunta y alcance

La pregunta era concreta:

> ¿Puede un slot Classic almacenar una dirección completa de diez trits, restaurarla,
> usarla como destino indirecto con el incremento de `c` y el cifrado del aterrizaje, y
> rearmarse para otro destino?

El alcance se separó en tres capas para no confundir una identidad algebraica con una
imagen ejecutable:

1. **Modelo del slot:** escritura exacta desde `29524`, conservación del vecino y rearme
   a `29524` para las 59 049 palabras.
2. **Imagen de un ciclo:** una imagen Classic real con un slot de dirección completa y
   dos destinos altos.
3. **Repetición y composición:** el modelo de varios ciclos se calcula, pero no se
   atribuye a la imagen; la conexión con la pila de dos slots de P12 no se ejecutó.

No se estudiaron Malbolge Unshackled, Malbolge Free ni variantes. No se modificó ningún
programa de producción. La semántica es la de Classic Malbolge de 59 049 palabras.

## 2. Resultado en una tabla

| Afirmación | Estado | Evidencia |
|---|---|---|
| Escritura exacta de las 59 049 palabras en el modelo | `DEMONSTRATED` | `model.exact_write_ok=true`, 0 fallos |
| Rearme del slot a `29524` para las 59 049 palabras | `DEMONSTRATED` | `model.rearm_ok=true`, 0 fallos |
| Imagen Classic de un ciclo con dirección completa | `DEMONSTRATED` | dos destinos, VM + runner C original |
| Incremento de `c` y cifrado de la celda de aterrizaje | `DEMONSTRATED` | traza `jump_events` y `first_target_event` |
| Valor de slot incorrecto aterriza fuera del target | `DEMONSTRATED` | dos controles negativos |
| Rearme y repetición dentro de la misma imagen | `NOT_DEMONSTRATED` | sólo `model_sequence` |
| Composición con los dos slots de retorno de P12 | `NOT_DEMONSTRATED` | diseño pendiente, sin ejecución |
| Cargador estricto de `mb_ref` acepta la imagen | `FALSIFIED` | `INVALID_OPCODE: cell 41` |
| Modelo global reducido de ejecución | `NOT_DEMONSTRATED` | sin cambios respecto de MAL-E01 |

## 3. Álgebra del slot

### 3.1 Escritura exacta

La construcción usa la máscara

```text
M = 29524 = 1111111111_3
```

y el protocolo de dos `p`:

```text
A = V
p sobre A con old = 29524   ->  A = swap01(V)
p sobre S con old = 29524   ->  S = V
```

`swap01` intercambia los trits 0 y 1 y deja los 2 intactos. Para cualquier palabra de
diez trits, la segunda operación recupera exactamente `V`. El modelo se comprobó para
las 59 049 palabras:

```python
from fibonalgge.address_slot import model_exhaustive
report = model_exhaustive()
assert report["exact_write_ok"]
assert report["rearm_ok"]
assert not report["write_failures"]
assert not report["rearm_failures"]
```

**Matiz importante:** la imagen real construye `V` poniendo máscaras de trit 2 sobre
`29524`. Por eso el builder de imágenes exige que `V` no tenga trits 0. El modelo
exhaustivo cubre todas las palabras, incluidas las que contienen 0; construir esas
palabras en una imagen requiere un protocolo adicional de puesta a cero que no forma
parte de esta etapa. La distinción está registrada en el informe y no se oculta.

### 3.2 Rearme

Para un slot que contiene `V`, el rearme es:

```text
p con A = 29524 sobre S   ->  extract2(V)
p con A = extract2(V) sobre S -> 29524
```

La segunda operación funciona porque `crz(2,2)=1` y `crz(0,0)=1`; si `V` no tiene
trits 2, la primera operación produce 0 y la segunda también produce `29524`. Esto
cubre las 59 049 palabras, no sólo las que tienen trits 2.

### 3.3 Secuencia modelada

`model_sequence([29645, 31713])` escribe el primer valor, calcula el aterrizaje
`slot + 1`, rearma, escribe el segundo y vuelve a rearmar. Las dos filas dan
`written_ok`, `landing_ok` y `rearm_ok` verdaderos. Esto es un modelo, no una imagen de
dos ciclos; por eso la repetición en la misma imagen sigue en `NOT_DEMONSTRATED`.

## 4. Imagen Classic de un ciclo

### 4.1 Layout

La imagen usa datos en `41..126` y código principal en la zona B (`>=127`). Las celdas
fijas del protocolo son:

| Celda | Papel | Valor inicial |
|---|---|---|
| `41` | `M`, fuente invariante de `29524` | `36` |
| `42` | `A`, scratch de escritura | `36` |
| `43` | `P`, payload que se construye | `36` |
| `44` | `S`, slot de dirección | `36` |
| `45` | `PTR = S+1`, puntero al descriptor del target | `T-1` |
| `100` | `T`, descriptor leído por el `DLOAD` del target | `R-1 = 109` |
| `110` | `R`, `OUT` del retorno | `enc(110, OUT)` |
| `111` | `RH`, `HALT` | `enc(111, END)` |
| `target+2` | centinela aislado | `42` |

El bootstrap usa el `DLOAD` de `pc=0`: su propia celda vale `40`, así que `d` cae en
`41 = M`. Después `M` pasa de `36` a `29524` con un `p`, y el planificador salta a la
zona B antes de construir el payload.

### 4.2 Aritmética del salto

Para un destino alto `H` con `H % 94 = 35`, la celda `H` codifica `DLOAD` como `99`.
Entonces `T = enc(H, DLOAD) + 1 = 100`.

El slot guarda

```text
V = H - 1
```

porque `i` hace `c = mem[d]` y después el incremento obligatorio lleva la ejecución a
`c + 1`. En la traza del destino `29645`:

```text
i en c=352, d=44, mem[44]=29644
  -> cifra mem[29644]: 34 -> 122
  -> c = 29644 + 1 = 29645
  -> d = 45
```

La celda `29644` es la celda del **nuevo `c`** antes del incremento; se cifra y no se
ejecuta. La primera instrucción ejecutada es la de `29645`, que es `DLOAD`.

En `H`:

```text
j en c=29645, d=45, mem[45]=99
  -> d = 99, luego d++ = 100 = T
  -> cifra mem[29645]: 99 -> 86
  -> c = 29646
```

En `H+1`:

```text
i en c=29646, d=100, mem[100]=109
  -> c = 109, cifra mem[109]: 83 -> 94, luego c++ = 110 = R
```

`R` ejecuta `OUT`, que emite el byte bajo de `A`. `A` sigue siendo `V`, así que la
salida es `V & 0xff`; para `29645` es `0xcc`, para `31713` es `0xe0`. El `HALT` está en
`111`. La celda `H+1` no se cifra, porque el nuevo `c` del `i` es `109`, no `H+1`.

### 4.3 Dos destinos

| Destino `H` | Slot `V=H-1` | Trits de `V` (alto→bajo) | Posiciones con 2 | Imagen | Salida | Pasos VM | Pasos C |
|---:|---:|---|---|---:|---:|---:|---:|
| `29645` | `29644` | `1111122221` | 1,2,3,4 | 29 648 B | `0xcc` | 236 | 237 |
| `31713` | `31712` | `1121111112` | 0,7 | 31 716 B | `0xe0` | 107 | 108 |

El runner C original reporta `HALTED` y un paso más porque cuenta el `HALT`; la VM
instrumentada usa la convención de `mb_ref` y no lo cuenta. La comparación de salida es
byte-exacta tras retirar el salto de línea que añade el runner al imprimir.

### 4.4 Controles de aislamiento

En ambas imágenes positivas:

- `S == V` y `P == V`.
- `A == swap01(V)`.
- `M == 29524`.
- `PTR == 99`, sin cambios.
- El centinela `H+2 == 42`, sin cambios.
- `H` cambia de `99` a `86`.
- `H+1` permanece en `62`.
- La celda de aterrizaje `V` cambia de `34` a `122`.
- `R` cambia de `83` a `94`.
- La primera instrucción ejecutada es exactamente `H`.

### 4.5 Control negativo

El control negativo guarda `29524` en el mismo slot. El salto aterriza en `29525`, no
en `29645` ni en `31713`. La VM y el runner C original siguen ejecutando y terminan,
pero por un camino distinto; el chequeo `wrong_landing_not_target` es verdadero. Esto
demuestra que el valor exacto del slot, no una coincidencia de layout, es lo que
selecciona el destino.

## 5. Evidencia y reproducción

### 5.1 Corrida

```bash
cd '/home/danny/Development/ISyCo Git/Fibonalgge'
python3 -m unittest discover -s tests -v
python3 mal_e02.py pilot
run_id=$(date -u +MAL-E02_%Y%m%dT%H%M%SZ)
python3 mal_e02.py run --run-id "$run_id"
python3 tools/hash_run.py --verify "evidence/$run_id"
```

La corrida final es `MAL-E02_20261125T002802Z`. El manifiesto contiene 10 artefactos:
`RESULTS.json`, `cases.json`, cuatro programas `.mb`, cuatro trazas `.jsonl`,
`ARTIFACT_MANIFEST.json` y `SHA256SUMS.txt`.

Se conserva también `MAL-E02_20261125T002640Z` como corrida exploratoria previa a la
captura de hashes de fuentes. No se usa para las afirmaciones finales; la corrida de
referencia es la `002802`.

### 5.2 Artefactos principales

```text
evidence/MAL-E02_20261125T002802Z/
├── RESULTS.json
├── cases.json
├── ARTIFACT_MANIFEST.json
├── SHA256SUMS.txt
├── programs/
│   ├── positive_29645.mb
│   ├── positive_31713.mb
│   ├── negative_29645.mb
│   └── negative_31713.mb
└── traces/
    ├── positive_29645.jsonl
    ├── positive_31713.jsonl
    ├── negative_29645.jsonl
    └── negative_31713.jsonl
```

Cada `RESULTS.json` registra:

- SHA-256 de las fuentes del experimento y del planificador original.
- SHA-256 y ruta del runner C original y de `mb_ref`.
- Comando, salida, stderr y estado de cada ejecución.
- Checks individuales de la VM.
- Evento de salto, evento del primer target y memoria final.
- Modelo exhaustivo y secuencia modelada.

### 5.3 Pruebas

La suite completa pasa 23/23. Las siete pruebas nuevas cubren:

- escritura exacta y rearme para 59 049 palabras;
- secuencia modelada de dos ciclos;
- dos imágenes positivas;
- dos controles negativos;
- aislamiento de slot, payload, máscara y centinela;
- paridad con el runner C original.

## 6. Límites explícitos

1. **La imagen termina en `HALT`.** No rearma el slot después del retorno. El rearme
   está demostrado en el modelo, no en esta imagen.
2. **No hay imagen de dos ciclos.** `model_sequence` no sustituye una ejecución real.
3. **No hay composición con P12.** La pila de dos slots y los retornos físicos de P12
   no se conectaron a este slot.
4. **El builder exige payloads sin trits 0.** Las palabras con 0 están cubiertas por el
   modelo, pero no por la imagen actual.
5. **`mb_ref` rechaza la imagen en carga.** Su cargador exige que toda celda fuente sea
   un opcode válido; la celda de dato `41` vale `36` y no lo es. El runner C original y
   la VM instrumentada sí ejecutan la imagen. Esto es una diferencia de cargador, no
   una discrepancia semántica observada.
6. **No se demostró un modelo global reducido de ejecución.** Sigue siendo
   `NOT_DEMONSTRATED`, igual que en MAL-E01.

## 7. Siguiente paso natural

La siguiente etapa no es "repetir el salto" por decreto. Es construir una imagen de dos
ciclos con:

- un segundo destino alto y su propio descriptor;
- un trampolín bajo que devuelva a un punto de continuación;
- rearme real de `S` y `P` en la imagen;
- un segundo salto después del rearme;
- control negativo del segundo aterrizaje.

Sólo después de eso tiene sentido conectar el slot con la pila de dos slots de P12. La
composición debe ejecutarse, no inferirse de que ambas piezas funcionan por separado.

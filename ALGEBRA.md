# Álgebra de `crz`, recurrencia y autocifrado

## 1. Convención

`crz(x,y)` tiene como filas el trit izquierdo `x` y como columnas el derecho `y`:

| `x \ y` | 0 | 1 | 2 |
|---:|---:|---:|---:|
| **0** | 1 | 1 | 2 |
| **1** | 0 | 0 | 2 |
| **2** | 0 | 2 | 1 |

Para palabras de diez trits, cada posición se calcula con esta tabla y no existe acarreo. En la inicialización, `M[i]=crz(M[i-1],M[i-2])`; por eso el estado se define como `P=(x,y)=(M[i-2],M[i-1])` y su transición es

\[
R(x,y)=(y,crz(y,x)).
\]

El orden es esencial: `crz(0,1)=1`, pero `crz(1,0)=0`.

## 2. Propiedades exhaustivas de `crz`

La enumeración de las nueve entradas y de las 27 ternas demuestra:

- no hay identidad izquierda ni derecha;
- no hay elemento absorbente izquierdo ni derecho;
- ningún trit es idempotente: `crz(0,0)=1`, `crz(1,1)=0`, `crz(2,2)=1`;
- no es conmutativa: cuatro pares ordenados son contraejemplos;
- no es asociativa: 15 de 27 ternas son contraejemplos;
- fijando `x=2`, el mapa `y ↦ crz(2,y)` sí es una permutación: `[0,2,1]`;
- fijando `y=1`, el mapa `x ↦ crz(x,1)` sí es una permutación: `[1,0,2]`.

Contraejemplo asociativo mínimo:

\[
crz(crz(0,0),0)=crz(1,0)=0,
\]
\[
crz(0,crz(0,0))=crz(0,1)=1.
\]

Estas propiedades son `DEMONSTRATED` por enumeración finita; no se infiere una estructura de grupo o semigrupo.

## 3. Grafo completo de nueve pares

| Estado | Siguiente | Transitorio | Ciclo atractor |
|---|---|---:|---|
| (0,0) | (0,1) | 1 | A |
| (0,1) | (1,0) | 0 | A |
| (1,0) | (0,1) | 0 | A |
| (1,1) | (1,0) | 1 | A |
| (0,2) | (2,0) | 0 | B |
| (2,0) | (0,2) | 0 | B |
| (1,2) | (2,2) | 0 | C |
| (2,2) | (2,1) | 0 | C |
| (2,1) | (1,2) | 0 | C |

Los tres ciclos son

\[
A=(0,1)\rightarrow(1,0)\rightarrow(0,1),\qquad |A|=2;
\]
\[
B=(0,2)\rightarrow(2,0)\rightarrow(0,2),\qquad |B|=2;
\]
\[
C=(1,2)\rightarrow(2,2)\rightarrow(2,1)\rightarrow(1,2),\qquad |C|=3.
\]

Las cuencas tienen cuatro, dos y tres estados. Los únicos estados no cíclicos desde el inicio son `(0,0)` y `(1,1)`, ambos a una transición de A. No existen puntos fijos en este grafo de pares.

**Prueba:** la tabla anterior contiene los nueve estados posibles y su único sucesor. La enumeración es, por tanto, una demostración completa, no una muestra estadística.

## 4. Periodicidad composicional de palabras

Cada uno de los diez trits evoluciona en uno de esos tres ciclos tras a lo sumo una transición. El período conjunto es

\[
\operatorname{mcm}(2,2,3)=6.
\]

Sea `N` la longitud fuente y sean `P0=(M[N-2],M[N-1])` los dos últimos trits fuente en una posición cualquiera:

- si `P0` ya pertenece a un ciclo, la secuencia generada tiene período 2 o 3 desde `M[N]`;
- si `P0=(0,0)`, la secuencia generada comienza `1,0,1,…`; si `P0=(1,1)`, comienza `0,1,0,…`. En ambos casos tiene período 2 **desde la primera celda generada**, aunque el par inicial fuera transitorio.

En todos los casos, para cada trit y para `i>=N`:

\[
M[i+6]=M[i].
\]

El transitorio del grafo de pares no obliga a guardar una excepción en la secuencia generada: las dos enumeraciones anteriores demuestran que `G0=G2`, y los períodos 2 y 3 dividen 6.

## 5. Predictor de acceso aleatorio

Calculamos literalmente seis palabras: `G0..G5=M[N..N+5]`. Entonces

\[
M[i]=G_{(i-N)\bmod 6}\qquad(i>=N).
\]

La representación `φ` conserva las `N` celdas fuente y una caché de seis palabras generadas. La regla reducida para la cola es sólo indexación módulo 6.

Consecuencias, limitadas a la inicialización:

- **Predicción exacta:** una posición lejana sin las recurrencias intermedias.
- **Aceleración exacta:** para `N=2`, la última celda requiere 59 047 llamadas `crazy` en el método literal y seis en el modelo; razón de trabajo 9 841,1667×. El speedup de wall time se registra aparte y no se confunde con esta razón exacta.
- **Compresión de la cola:** seis palabras de caché frente a 59 047, o dos palabras semilla más el algoritmo compartido. No se contabiliza la tabla `crz` como ahorro y no se afirma compresión de ejecuciones.

Verificación experimental: los nueve pares uniformes cubren todas las clases posibles de cada trit y se comparan las 59 049 celdas con el método literal. Se añaden casos reales no uniformes y pruebas no uniformes con semilla fija. La prueba composicional anterior es la que cubre todos los productos de pares; las comparaciones son su control de implementación.

## 6. `XLAT2` como espacio de fases

`XLAT2` es una permutación de los 94 caracteres imprimibles. Su descomposición tiene seis ciclos, de longitudes

\[
68,\ 9,\ 6,\ 5,\ 4,\ 2,
\]

y período conjunto `mcm=3060`.

Para una celda `v`, sea `φ(v)=(cycle_id,phase)`. Si la única operación aplicada es el autocifrado,

\[
φ(XLAT2(v))=F(φ(v)),
\]

donde `F` incrementa `phase` módulo la longitud del ciclo. Después de precomputar las 94 fases:

\[
XLAT2^k(v)=cycle[(phase+k)\bmod cycle\_length].
\]

Esto es una transformación exacta del tipo buscado por H4, pero **sólo para el subsistema de autocifrado**. No comprime los 94 estados ni predice saltos, entradas, escrituras `p`/`*` o decodificación. El control exhaustivo recorre los 94 valores y `k=0..3060` (287 734 comprobaciones), sin discrepancias.

## 7. Reglas locales de registros

Del ciclo canónico se desprende, sin ajuste estadístico:

- `C_after mod 94 = (C_before+1) mod 94` en pasos completados con opcode distinto de `i` y `C_before≠59048`;
- `D_after mod 94 = (D_before+1) mod 94` en pasos completados con opcode distinto de `j` y `D_before≠59048`.

Fuera de esos dominios hay que conocer `mem[D]`, el wrap o la parada. Los conteos por split y todos los motivos de fallo se derivan de las trazas en `execution_analysis.register_local_rules`. Son consecuencias directas de la especificación, no una nueva dinámica emergente.

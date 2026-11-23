# Contraejemplos y resultados negativos

Corrida principal: `MAL-E01_20261123T024848Z`. Las predicciones estadísticas usan 45 713 posiciones de validación por modelo, salvo el análisis de dominio que tiene denominadores propios.

## 1. `crz` no forma una estructura conmutativa o asociativa

- `crz(0,1)=1`, pero `crz(1,0)=0`.
- `crz(crz(0,0),0)=0`, pero `crz(0,crz(0,0))=1`.
- Hay cuatro contraejemplos de conmutatividad y 15 de asociatividad en la enumeración completa.

No se encontraron identidades, absorbentes ni valores idempotentes.

## 2. Corrección algebraica: el transitorio no exige una excepción en G0

Una versión anterior de esta investigación guardaba `G0` aparte y siete palabras. El revisor falsó esa justificación con:

- par `(0,0)`: generados `1,0,1,0,1,0,1,…`;
- par `(1,1)`: generados `0,1,0,1,0,1,0,…`.

En ambos `G0=G2`; en los ciclos de longitud 2/3 también `G0=G6`. Por tanto, la fórmula mínima es `M[i]=G[(i-N) mod 6]` desde `i=N`, con seis palabras. La fórmula antigua era exacta pero redundante; se corrigieron código, pruebas, informe y ratios.

## 3. Fibonacci módulo 3 no predice `A`

Primer contraejemplo held-out para `a_mod3`, en `rot13`, índice 2:

```text
contexto [0,0] -> esperado 1; Fibonacci predice 0
```

| Predictor | Micro accuracy | Macro por caso | Control barajado |
|---|---:|---:|---:|
| Mayoría | 33,1153 % | 32,9650 % | 33,1262 % |
| Persistencia | 80,0604 % | 88,2752 % | 41,3121 % |
| Fibonacci mod 3 | 28,8233 % | 29,7742 % | 29,8121 % |
| Recurrencia `crz` sobre A | 15,6804 % | 9,4783 % | 30,1599 % |
| Mejor lineal mod 3 | 80,0604 % | 88,2752 % | 41,3121 % |

La mejor de las 27 recurrencias lineales es `α=1,β=0,γ=0`: persistencia, no Fibonacci. Para el trit alto, Fibonacci obtiene 40,5027 % micro y persistencia 80,9332 %. La analogía queda `FALSIFIED` como regla exacta o competitiva en este corpus.

## 4. La persistencia de A se explica por el ISA

En validación hay 32 784 transiciones de 45 713 (71,7170 %) cuyo opcode garantiza preservar `A`: `<`, `i`, `j`, `o`, NOP y `v` (conteo exacto en `a_persistence_mechanism`). En ellas la persistencia es 100 % por especificación.

- `p`: sólo 571/5 288 (10,7980 %) conserva `A mod 3`.
- `*`: 3 240/7 635 (42,4361 %).
- `/`: 3/6, denominador demasiado pequeño para inferencia.

La persistencia agregada no es una recurrencia espontánea: es principalmente la consecuencia de que sólo `p`, `*` y `/` pueden modificar `A`.

## 5. `+1 mod 94` falla en saltos, wrap y parada

Ejemplos held-out:

- `C`, `rot13`, índice 640: contexto `[79,80]`, esperado 74, predicción 81; la causa es `i`.
- `D`, `rot13`, índice 4: contexto `[41,42]`, esperado 40, predicción 43; la causa es `j`.

Al restringir el dominio a pasos completados sin salto ni wrap:

- discovery: C 11 620/11 620; D 10 318/10 318;
- validation: C 43 235/43 235; D 31 070/31 070;
- fallos sin explicación: cero.

La regla global sin condiciones queda falsada; la regla condicionada queda demostrada como consecuencia directa de la especificación.

## 6. Markov no es una transformación exacta

Primer contraejemplo de Markov-2 en opcode, `rot13`, índice 2:

```text
contexto [i,j] -> esperado *; predicción i
```

- Markov-1: 38,9102 % micro y 54,8766 % macro en validación; 30,2474 % en el control nulo.
- Markov-2: 33,6338 % micro y 56,1590 % macro; 30,1074 % en el nulo.
- Mayoría: 30,5887 % micro y 49,0458 % macro.

Existe dependencia temporal estadística aprovechable sobre el nulo, pero ninguna exactitud global y sobreajuste temporal de Markov-2 (66,5303 % discovery frente a 33,6338 % micro validation). No se demostró compresión con modelo+residual.

## 7. Peso de los programas largos

`rot13` y `bottles` aportan 87,4937 % de las transiciones agregadas de validación. Por eso `RESULTS.json` incluye micro y macro por caso. La conclusión Fibonacci no depende sólo del micro-promedio: también pierde en macro y frente a persistencia en los casos individuales.

## 8. Defectos experimentales detectados y corregidos

La revisión adversarial encontró un hash inicial aliasado al final en 11/11 recibos, una etiqueta de 81 candidatos cuando había 27, y un gate que agrupaba STALLs distintos. Esos defectos invalidaban recibos, no la VM ni el grafo. Se añadieron pruebas de regresión y se generó una corrida nueva. Las corridas anteriores se conservan sin reescribir; sólo la corrida identificada arriba respalda el informe final.

## 9. Negativo principal

Ningún modelo evaluado sobre ejecución completa es exacto fuera de muestra. Esto no demuestra que no exista una transformación mejor: demuestra que, con estos observables, modelos, programas y presupuestos, una reducción autónoma global queda `NOT_DEMONSTRATED`.

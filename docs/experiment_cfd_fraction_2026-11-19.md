# MiniNeutron: barrido pareado de fracción CFD

Fecha: 19 de noviembre de 2026.

Este estudio utiliza únicamente señales sintéticas de MiniNeutron. No contiene
datos, código ni parámetros de adquisición DRS4 y no constituye una calibración
de detector.

## Motivación y pregunta

El primer estudio temporal utilizó de forma convencional una fracción CFD de
0,5. En vez de asumir que ese valor es óptimo, se investigó:

> ¿Cómo influye la fracción utilizada por un CFD digital en el *time walk* y el
> jitter de señales sintéticas bajo distintas amplitudes, niveles de ruido y
> frecuencias de muestreo?

La revisión educativa anterior de formas de onda experimentales motivó la
pregunta general sobre reconstrucción temporal. La implementación y los datos
publicados aquí son independientes y sintéticos.

## Diseño pareado

Se compararon las fracciones:

\[
0{,}2,\ 0{,}3,\ 0{,}4,\ 0{,}5,\ 0{,}6,\ 0{,}7,\ 0{,}8.
\]

Cada una fue aplicada a exactamente la misma forma de onda dentro de cada
repetición. Por tanto, las diferencias entre fracciones no provienen de haber
generado ruidos o fases distintos.

Se conservaron las condiciones del estudio anterior:

- amplitudes de 0,2, 0,5 y 1,0 V;
- ruido gaussiano con \(\sigma\) de 0, 10 y 30 mV;
- muestreo a 500, 1.000 y 2.000 Hz;
- ADC ideal de 12 bits y 3,3 V;
- cinco semillas independientes;
- 200 repeticiones por configuración.

En total se generaron 27.000 formas de onda y se realizaron 189.000
estimaciones CFD. Todas las fracciones encontraron un cruce en las condiciones
probadas. Esto no representa eficiencia física.

## Métricas

Para cada semilla, frecuencia, ruido y fracción se calcularon:

- *time walk*: rango de la latencia media entre las tres amplitudes;
- jitter medio entre amplitudes;
- peor jitter entre amplitudes;
- menor fracción de cruces encontrados.

Después se calcularon la media y dispersión entre cinco semillas. No se definió
una puntuación combinada arbitraria. Una fracción se marcó como dominada cuando
otra presentó simultáneamente *time walk* no mayor, peor jitter no mayor y una
proporción de cruces no menor, con al menos una mejora estricta.

## Reproducción

```sh
python analysis/study_cfd_fraction.py \
  --output-dir results/cfd_fraction_otra_corrida \
  --trials 200
python -m unittest tests.test_study_cfd_fraction -v
```

La configuración y hashes de la ejecución documentada están en
[`data/cfd_fraction_20261119.json`](data/cfd_fraction_20261119.json). El resumen
compacto está en
[`data/cfd_fraction_20261119.tsv`](data/cfd_fraction_20261119.tsv). Las 189.000
filas por estimación son regenerables y permanecen ignoradas por Git.

## Resultados

Las fracciones no dominadas cambiaron con las condiciones:

| Muestreo | Ruido | Fracciones no dominadas |
| ---: | ---: | --- |
| 500 Hz | 0 mV | 0,5; 0,6 |
| 500 Hz | 10 mV | 0,2; 0,3 |
| 500 Hz | 30 mV | 0,4; 0,5 |
| 1.000 Hz | 0 mV | 0,4; 0,6 |
| 1.000 Hz | 10 mV | 0,2 |
| 1.000 Hz | 30 mV | 0,4; 0,5 |
| 2.000 Hz | 0 mV | 0,2; 0,3; 0,4; 0,5 |
| 2.000 Hz | 10 mV | 0,2 |
| 2.000 Hz | 30 mV | 0,4; 0,5 |

No apareció una fracción universalmente no dominada. Con 30 mV de ruido, las
fracciones 0,4 y 0,5 formaron el compromiso en las tres frecuencias. Con 10 mV,
las fracciones bajas 0,2–0,3 resultaron favorables en este modelo. Sin ruido,
las diferencias pequeñas dependen también de muestreo, fase y cuantización.

Para 1.000 Hz y 10 mV:

| Fracción | Time walk medio | Desv. entre semillas | Peor jitter medio | No dominada |
| ---: | ---: | ---: | ---: | :---: |
| 0,2 | 0,043 ms | 0,016 ms | 0,187 ms | Sí |
| 0,3 | 0,077 ms | 0,015 ms | 0,207 ms | No |
| 0,4 | 0,113 ms | 0,011 ms | 0,234 ms | No |
| 0,5 | 0,156 ms | 0,013 ms | 0,286 ms | No |
| 0,6 | 0,221 ms | 0,018 ms | 0,343 ms | No |
| 0,7 | 0,340 ms | 0,018 ms | 0,457 ms | No |
| 0,8 | 0,503 ms | 0,030 ms | 0,664 ms | No |

En cambio, con 30 mV la fracción 0,2 fue especialmente sensible al ruido: el
*time walk* medio superó 6 ms en 500 Hz y aumentó con la frecuencia en las
condiciones estudiadas. Las fracciones 0,4–0,5 ofrecieron un compromiso más
estable. Esto muestra por qué una fracción favorable bajo poco ruido no debe
trasladarse automáticamente a otra condición.

## Interpretación

El resultado no identifica una fracción física óptima para un instrumento. Sí
demuestra, dentro del modelo, que la elección de fracción es parte del algoritmo
y que su efecto depende del ruido y del muestreo. También muestra el valor de
aplicar todas las alternativas sobre señales idénticas y conservar métricas
separadas en vez de seleccionar una configuración por inspección visual.

## Límites

- Se utiliza una única familia de pulsos de diferencia de exponenciales.
- No se modelan deriva de baseline, *pile-up*, saturación ni jitter de reloj.
- El CFD es un cruce digital respecto del máximo observado, no un circuito CFD.
- El frente de Pareto se calcula sobre medias de cinco semillas y no incorpora
  intervalos de confianza en su regla de dominancia.
- Tres amplitudes no describen continuamente la dependencia con amplitud.
- Ningún resultado constituye eficiencia, resolución o calibración de un
  detector de neutrones real.

## Continuación

El siguiente paso es estudiar por qué las fracciones bajas fallan con ruido
alto mediante ejemplos de formas de onda, y después incorporar deriva de
baseline y pulsos superpuestos. Antes de aumentar la complejidad, Alex debe
reproducir este barrido y explicar el criterio de dominancia.

Desarrollo asistido por Codex y revisado mediante pruebas automatizadas. La
responsabilidad de autoría requiere revisión y comprensión personal del código
y de sus limitaciones.

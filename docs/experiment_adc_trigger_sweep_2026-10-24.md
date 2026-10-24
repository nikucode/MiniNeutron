# Sensibilidad del trigger a la resolución ADC — 2026-10-24

## Pregunta y diseño

Se compararon tres semillas (`12345`, `12346`, `12347`) y cuatro resoluciones
ADC (`4`, `6`, `8`, `10` bits). Para cada semilla, `run_pipeline.py` generó una
sola forma de onda y su referencia truth. El estudio conservó exactamente las
muestras `voltage_V` y volvió a cuantizarlas para cada resolución mediante
`rint(voltage_V / Vref × (2^bits−1))`, la misma regla del generador. El modo
analógico se ejecutó una vez por semilla; cada variante ADC usó los mismos
umbrales en voltios, `trigger = 0,80 V` y `rearm = 0,65 V`.

Los pares de ventanas DAQ se forman cuando sus intervalos tienen solapamiento
positivo. Este criterio registra ventanas exclusivas y fusiones sin asumir
que los identificadores DAQ representan el mismo evento. Por separado, la
clasificación truth/reco reutiliza la ventana temporal del comparador
existente (`pre_window = 0,004 s`). Ambas operaciones son asociaciones
temporales, no atribuciones físicas causales.

Comando desde la raíz del repositorio:

    python analysis/study_adc_trigger.py --output-root results/parameter_studies/20261024_adc_trigger_v1

El script exige un directorio de salida nuevo o vacío, guarda `study.json`,
manifiestos del pipeline, formas de onda, logs, tablas truth/reco y
`window_pairs.csv` por variante. La tabla compacta incluida en Git es
[`data/adc_trigger_study_20261024.tsv`](data/adc_trigger_study_20261024.tsv).
Las salidas completas están bajo `results/parameter_studies/` y se ignoran en
Git. El hash SHA-256 de `summary.csv` fue
`523f11c35a3f6299a33956541632e4b4718c731951866c534718aacbc38274dc`.

## Entrada y resultados

El CSV Geant4 local tuvo hash SHA-256
`6c3920ffaf80b73790eab6752ffebb97d0733ef89bd417ebaf581265dbda47d9`:
639 pasos con depósito y 82 eventos truth. No es la corrida histórica de
1.156 pasos y 165 eventos. Cada semilla conserva esos 82 eventos, pero cambia
sus tiempos sintéticos y el ruido de la forma de onda.

| Semilla | Bits | DAQ voltaje | DAQ ADC | Solo voltaje | Solo ADC | Fusiones ADC | Truth con estado distinto |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 12345 | 4 | 21 | 17 | 0 | 0 | 3 | 13 |
| 12345 | 6 | 21 | 21 | 0 | 0 | 0 | 0 |
| 12345 | 8 | 21 | 23 | 0 | 2 | 0 | 2 |
| 12345 | 10 | 21 | 21 | 0 | 1 | 1 | 2 |
| 12346 | 4 | 21 | 19 | 2 | 0 | 0 | 19 |
| 12346 | 6 | 21 | 19 | 2 | 0 | 0 | 2 |
| 12346 | 8 | 21 | 21 | 0 | 0 | 0 | 0 |
| 12346 | 10 | 21 | 21 | 0 | 0 | 0 | 2 |
| 12347 | 4 | 19 | 18 | 0 | 0 | 1 | 8 |
| 12347 | 6 | 19 | 19 | 0 | 0 | 0 | 1 |
| 12347 | 8 | 19 | 19 | 0 | 0 | 0 | 0 |
| 12347 | 10 | 19 | 19 | 0 | 0 | 0 | 0 |

«Fusiones ADC» cuenta ventanas ADC que se solapan con más de una ventana de
voltaje; no cuenta depósitos físicos fusionados. «Truth con estado distinto»
cuenta eventos cuya etiqueta temporal (`individual`, `merged`, `missed` o
`ambiguous`) cambió entre los dos modos.

En 4 bits, el paso de cuantización es `5/15 ≈ 0,333 V`; por eso los umbrales
efectivos sobre el voltaje reconstruido son bastante gruesos. Aun en 10 bits
hubo cambios para dos semillas. Una igualdad en el número de eventos DAQ, o
incluso en los totales por clase truth, puede ocultar cambios de asociación
evento por evento.

## Límites y uso del resultado

Son 12 variantes ADC sobre tres realizaciones sintéticas del mismo CSV
Geant4. No constituyen una estimación estadística de eficiencia, resolución
óptima ni incertidumbre experimental. Tampoco se modelan fotones de
centelleo, fotodetector ni electrónica real. El resultado sí muestra que la
decisión de trigger depende de dónde se aplica la histéresis y de la
resolución ADC; esto importa al definir qué parte de un sistema de adquisición
es analógica y cuál opera después de la digitalización.

# MiniNeutron: sensibilidad inicial de la DAQ simulada

Fecha: 24 de octubre de 2026. Este es un experimento computacional exploratorio,
no una medición de eficiencia de detección de neutrones.

## Pregunta y método

Se estudió cómo cambian las **asociaciones temporales** truth–reco al variar
por separado el umbral de trigger, el ruido o la duración de adquisición.
Todas las corridas utilizaron el mismo `build/detector_hits.csv` (1.156 pasos
con depósito, 165 eventos Geant4 con depósito), cuyo SHA-256 es:

`8a7834f61d49139e9bc367785359792b90b5fcfd302e072adb60d5300b05e14b`

Se ejecutaron 7 configuraciones con las semillas 12345, 12346 y 12347: 21
corridas independientes del pipeline Python. Los parámetros base fueron:
duración 10 s, muestreo 500 Hz, ganancia 1 V/MeV, baseline 0,5 V, ruido
gaussiano σ = 0,03 V, decaimiento τ = 0,03 s, ADC de 10 bits con Vref = 5 V,
trigger = 0,80 V, rearme = 0,65 V y ventana previa de asociación = 0,004 s.

Para repetir el barrido desde la raíz del proyecto:

    python analysis/study_daq_sensitivity.py \
      --input-hits build/detector_hits.csv \
      --output-root results/parameter_studies/otra_corrida

El directorio de salida debe estar vacío. Cada caso conserva su manifiesto,
tablas y log. El resumen de esta ejecución está en
`results/parameter_studies/20261024_truth_reco_v1/summary.csv` (datos de trabajo
ignorados por Git). Para revisar los conteos sin ejecutar el estudio se
conservan una [tabla de 21 corridas](data/daq_sensitivity_20261024.tsv) y su
[configuración](data/daq_sensitivity_20261024.json). Los manifiestos de las 21
corridas terminaron con estado `completed`. La versión usada fue Python
3.14.8; cada manifiesto registra los hashes de entrada y scripts.

## Resultados

La tabla muestra el promedio de tres semillas; entre paréntesis, mínimo y
máximo observados. `Sin candidato` significa que ningún truth cayó en la
ventana temporal asignada al evento reconstruido.

| Configuración | Eventos DAQ | Truth `merged` | Truth `missed` | DAQ sin candidato |
| --- | ---: | ---: | ---: | ---: |
| Base | 39,3 (34–45) | 68,7 (62–75) | 81,0 (77–89) | 0 |
| Trigger 0,70 V | 49,0 (41–56) | 69,7 (62–76) | 76,7 (73–83) | 5,7 (1–9) |
| Trigger 1,00 V | 33,0 (29–36) | 62,3 (58–67) | 91,0 (87–96) | 0 |
| Ruido σ = 0 V | 38,3 (34–43) | 71,0 (64–75) | 80,0 (74–88) | 0 |
| Ruido σ = 0,06 V | 47,0 (44–51) | 60,7 (56–65) | 83,7 (81–89) | 3,0 (2–4) |
| Duración 5 s | 24,7 (22–28) | 105,7 (102–109) | 54,3 (52–58) | 0 |
| Duración 20 s | 43,7 (42–45) | 34,0 (31–36) | 103,0 (101–106) | 0 |

Al concentrar los mismos 165 pulsos en 5 s, disminuyeron los eventos DAQ y
aumentaron las asociaciones múltiples. Al repartirlos en 20 s ocurrió lo
contrario. Esto es consistente con mayor o menor superposición temporal del
modelo. Que `missed` baje en 5 s **no** significa que el detector sea más
eficiente: un pulso débil puede quedar asociado a una región disparada por
otro pulso.

En las tres corridas base, todos los truth clasificados como `missed` tenían
amplitud aislada inferior a 0,30 V, que es la diferencia entre trigger y
baseline. También hubo 41, 41 y 29 truth por debajo de esa amplitud que
quedaron temporalmente asociados. Esos casos muestran por qué la coincidencia
temporal no equivale a detectar individualmente cada pulso.

Con trigger de 0,70 V o ruido σ = 0,06 V aparecieron eventos DAQ sin truth en
la ventana de 4 ms. En los ejemplos inspeccionados, la señal ideal en la
muestra de trigger estaba por debajo del umbral y el ruido era positivo; había
colas de pulsos anteriores fuera de la ventana. Por ello no se clasificaron
como falsos positivos físicos ni como pulsos de ruido puro.

## Límites de interpretación

- Las tres semillas muestran sensibilidad a realizaciones aleatorias; no
  establecen una incertidumbre estadística general ni validación experimental.
- La fuente temporal contiene un número **fijo** de 165 eventos con depósito,
  distribuidos uniformemente dentro de cada duración. No es un proceso de
  llegada de todos los 1.000 neutrones primarios ni una tasa calibrada.
- Al variar duración cambian la separación de pulsos, el número de muestras y
  su alineación con la grilla temporal. La comparación no aísla cada efecto.
- Al variar trigger con rearme fijo en 0,65 V también cambia el ancho de la
  histéresis. El efecto no se atribuye exclusivamente al umbral de disparo.
- La DAQ dispara actualmente sobre `voltage_V`, no sobre `adc_raw`; esta prueba
  no evalúa pérdidas causadas por cuantización ADC.
- `merged`, `missed` y `sin candidato` dependen de una ventana de 4 ms aún no
  validada para una electrónica o detector específicos.

## Próximo experimento

Conservar por muestra las contribuciones de pulsos y ruido, y estudiar las
decisiones de trigger frente a contrafactuales controlados. Eso permitiría
separar mejor cruces por un pulso aislado, superposición, ruido y colas previas.
Después corresponde repetir el barrido con más semillas y evaluar sensibilidad
a la ventana de asociación y al nivel de rearme.

# MiniNeutron: contribuciones a las muestras de trigger

Fecha: 24 de octubre de 2026. Este estudio continúa el
[barrido inicial de DAQ](experiment_daq_sensitivity_2026-10-24.md). Describe
señales y decisiones de un **modelo simulado**; no mide la eficiencia ni la
respuesta calibrada de un detector físico.

## Pregunta y método

Queremos distinguir la contribución de pulsos anteriores y ruido en los
triggers reconstruidos. Se reutilizaron las 21 corridas del barrido anterior:
7 configuraciones y 3 semillas, todas derivadas del mismo CSV de Geant4.
No se modificaron los parámetros ni se repitió Geant4.

Para cada muestra donde la DAQ abrió un evento se reconstruyó la suma de
pulsos usada por el generador de forma de onda:

`V_ideal(t) = B + Σ Aᵢ exp[-(t − tᵢ)/τ]`, para cada pulso con `t ≥ tᵢ`.

Aquí `B` es el baseline, `Aᵢ` la amplitud en voltios, `tᵢ` el tiempo sintético
del pulso y `τ` la constante de decaimiento. La suma calculada se comparó con
`voltage_ideal_V` del CSV; los 21 diagnósticos terminaron sin discrepancias
en las muestras de trigger. La señal observada es
`clip(V_ideal + ruido, 0, Vref)`.

Se hicieron además dos **corridas completas de la misma DAQ** por cada forma
de onda original:

1. **Sin ruido:** se conserva `V_ideal` y se fija el ruido en cero.
2. **Sin pulsos:** se conserva el ruido y se reemplaza `V_ideal` por `B`.

Un indicador por muestra marca `ruido necesario` si `V_ideal` está bajo el
umbral y la señal observada lo cruza. Otro marca `pulsos necesarios` si
`B + ruido` está bajo el umbral y la señal observada lo cruza. Ambos describen
**esa muestra**, no la causa única de todo el evento DAQ: sin un componente,
el algoritmo podría disparar en otro instante o cambiar su estado de rearme.

Para reproducir desde la raíz del proyecto, primero se genera el barrido DAQ
en un directorio vacío y luego sus diagnósticos en otro directorio vacío:

    python analysis/study_daq_sensitivity.py \
      --input-hits build/detector_hits.csv \
      --output-root results/parameter_studies/repeticion_daq

    python analysis/study_trigger_contributions.py \
      --study-summary results/parameter_studies/repeticion_daq/summary.csv \
      --output-root results/trigger_diagnostics/repeticion_trigger

La ejecución original se conserva localmente en
`results/trigger_diagnostics/20261024_v1/` (ignorada por Git). En el
repositorio quedan la [tabla compacta de 21 corridas](data/trigger_contributions_20261024.tsv)
y su [trazabilidad](data/trigger_contributions_20261024.json).

## Resultados

Promedios de las tres semillas por configuración. Las cifras de la columna
`ruido necesario` cuentan triggers cuya **muestra registrada** no alcanzaría
el umbral sin ruido.

| Configuración | Eventos observados | DAQ sin ruido | DAQ sin pulsos | Ruido necesario en la muestra |
| --- | ---: | ---: | ---: | ---: |
| Base | 39,3 | 38,3 | 0 | 0,7 |
| Trigger 0,70 V | 49,0 | 42,3 | 0 | 6,7 |
| Trigger 1,00 V | 33,0 | 32,3 | 0 | 0,7 |
| Ruido σ = 0 V | 38,3 | 38,3 | 0 | 0 |
| Ruido σ = 0,06 V | 47,0 | 38,3 | 0 | 5,3 |
| Duración 5 s | 24,7 | 24,0 | 0 | 0,7 |
| Duración 20 s | 43,7 | 43,3 | 0 | 0 |

La DAQ sin pulsos produjo cero eventos en todas las corridas estudiadas.
Esto muestra que el ruido por sí solo, **con estas realizaciones y umbrales**,
no produjo un trigger. No predice la probabilidad de triggers de ruido para
otras duraciones, semillas o distribuciones de ruido.

En las 21 corridas hubo **26 eventos DAQ sin truth dentro de la ventana de
asociación** de 4 ms. En las 26 muestras de trigger, tanto los pulsos previos
como el ruido fueron necesarios para cruzar el umbral según los indicadores
locales. La suma de colas de pulsos estaba entre 0,120 y 0,286 V, y el ruido
en esas muestras entre 0,007 y 0,176 V. El pulso con mayor contribución había
comenzado entre 10,5 y 88,2 ms antes del trigger, fuera de la ventana usada
para truth–reco. Esto explica por qué `sin candidato temporal` no equivale a
`sin señal de partículas`.

## Límites y siguiente decisión

Los conteos `observado` y `sin ruido` son resultados de **corridas distintas
del algoritmo con histéresis**. Su diferencia no cuenta directamente eventos
individuales causados por ruido. Tampoco hemos estudiado aquí la probabilidad
de detección de cada pulso, una tasa de fuente calibrada o efectos de ADC:
el trigger aún usa `voltage_V` antes de cuantización.

El siguiente incremento puede estudiar el trigger sobre cuentas ADC y comparar
sus decisiones con las obtenidas sobre voltaje analógico. Antes de atribuir
pérdidas a resolución digital conviene fijar explícitamente la regla de
conversión del umbral en voltios a cuentas y probar sus casos de borde.

# Comparación controlada de trigger analógico y ADC — 2026-10-24

## Pregunta

¿Cambian los eventos reconstruidos si la histéresis se aplica a la muestra
analógica o al código ADC digitalizado?

## Método

Se ejecutó `run_pipeline.py` dos veces sobre el mismo
`build/detector_hits.csv`, con los parámetros por defecto y semilla 12345.
Solo se cambió `--trigger-source` de `voltage` a `adc`. Ambos manifiestos
terminaron con estado `completed`. El hash SHA-256 del CSV de entrada fue
`6c3920ffaf80b73790eab6752ffebb97d0733ef89bd417ebaf581265dbda47d9`;
ambas formas de onda tuvieron hash
`5db6cf42e693a1c86d3f203fe4bb8e5aeb8a0f05297d05cd0e3536a7bcb079ae`.
Las salidas originales de esta comprobación están en
`/tmp/minineutron_adc_validation/` y no se incluyen en Git.

Parámetros relevantes: `Vref = 5 V`, `bits = 10`, trigger `0,80 V`, rearme
`0,65 V`, muestreo `500 Hz`. El modo ADC abre con código ≥ 164 y rearma con
código ≤ 132. Un código representa aproximadamente 4,89 mV. La conversión
de umbrales usa techo para abrir y piso para cerrar; son comparaciones sobre
la tensión reconstruida desde el código, no sobre la muestra analógica.

## Resultados observados

El CSV Geant4 local de esta prueba dio 639 pasos con depósito y 82 eventos
con energía depositada. Es distinto del conjunto histórico de 1.156 pasos y
165 eventos; por tanto, estas cifras no reproducen esa corrida anterior.

| Modo | Eventos DAQ | Truth individual | Truth merged | Truth missed | Truth ambiguous |
| --- | ---: | ---: | ---: | ---: | ---: |
| Voltaje | 21 | 13 | 18 | 51 | 0 |
| ADC | 21 | 13 | 19 | 50 | 0 |

Aunque ambos modos dieron 21 eventos, las ventanas no son iguales. En voltaje
hubo ventanas `1,908–1,956 s` y `1,962–2,012 s`; el modo ADC produjo una
sola ventana `1,908–2,012 s`. Además, ADC produjo una ventana
`4,542–4,556 s` ausente en voltaje. Otras ventanas difirieron hasta algunos
milisegundos en el cierre. La cuantización puede desplazar la decisión de
rearme o trigger cerca de un umbral; no basta comparar solo el total de eventos.

## Alcance y siguiente comprobación

Este es un contraste controlado de software sobre una sola entrada y una
semilla. No mide eficiencia física del detector ni establece qué depósito
causó cada trigger. Falta repetir la comparación con varias semillas y
resoluciones ADC, conservando las mismas formas de onda analógicas por par de
modos y verificando las asociaciones evento a evento.

Ese barrido posterior se documenta en
`experiment_adc_trigger_sweep_2026-10-24.md`.

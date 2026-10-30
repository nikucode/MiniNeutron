# Banco óptico: software y estudio sintético (2026-10-30)

## Qué se implementó

Se añadió una entrada óptica educativa a la DAQ existente de MiniNeutron:
importación estricta de secuencia, tiempo de dispositivo y ADC; captura serial
opcional; firmware de referencia Uno R3; manifiestos y procedimiento de montaje
hasta placa perforada soldada. Se reutiliza `daq/analyze_pulses.py`, sin modificar
su criterio de trigger o el pipeline Geant4. Sólo se generalizó el título de la gráfica.

**No se construyó el circuito ni se adquirieron señales físicas en este avance.**
No se dispone aquí de Arduino CLI/core AVR ni de una placa conectada. Se comprobó
la lógica del firmware con un doble de Arduino compilado en el host: esto no es
una compilación para Uno ni una validación de tiempos o niveles eléctricos.

## Método reproducible

Desde la raíz, usando las dependencias de `requirements.txt`:

```sh
python -m daq.optical_bench study --output-dir results/optical_study_new
python -m unittest discover -s tests -v
```

El directorio del estudio debe ser nuevo. Python 3.14.8, NumPy 2.5.3 y Pandas
3.0.6 en esta ejecución. Semillas: 20261030, 20261031, 20261032.

Cada stream tiene 5000 muestras, 10 s nominales, 20 flancos y ruido gaussiano
sigma 8 o 120 códigos. Se comparan tres pares trigger/rearme: 1.5/1.0, 3.0/2.0 y
4.8/4.0 V con Vref nominal 5 V y ADC de 10 bits. Los tres pares comparten el
mismo stream para cada semilla/ruido. Total: seis streams, 18 análisis, sin Geant4.
Los detalles y límites del modelo están en la [guía](hardware/optical_bench.md).

Evidencias compactas versionadas:

- [Resumen CSV](experiments/optical_bench_2026-10-30/summary.csv).
- [Parámetros, flancos truth y hashes](experiments/optical_bench_2026-10-30/study.json).
- [Gráfica de ejemplo, fuente sintética](experiments/optical_bench_2026-10-30/clean_fixture.png).

## Resultados observados

Rangos entre las tres semillas; 20 flancos esperados en cada corrida:

| Ruido sigma [códigos] | Trigger/rearme [V] | Asociados | Omitidos | Triggers no asociados |
| --- | --- | --- | --- | --- |
| 8 | 1.5/1.0 | 20 | 0 | 0 |
| 8 | 3.0/2.0 | 20 | 0 | 0 |
| 8 | 4.8/4.0 | 0 | 20 | 0 |
| 120 | 1.5/1.0 | 20 | 0 | 327–350 |
| 120 | 3.0/2.0 | 20 | 0 | 0–1 |
| 120 | 4.8/4.0 | 7–11 | 9–13 | 63–78 |

Con ruido bajo y trigger 3 V, el máximo error absoluto de asociación temporal
fue aproximadamente 1.10 ms. Esta cifra corresponde al fixture muestreado, no
a la precisión de una placa o del chopper. No se calcula error cuando no hay
asociaciones. Los pares de umbrales varían juntos: no es un estudio aislado del
ancho de histéresis ni una selección óptima para hardware desconocido.

El nivel alto ideal es 850 códigos, unos 4.15 V según la escala usada. Por eso
4.8 V pierde todos los pulsos con ruido bajo. Con ruido alto puede disparar
fragmentos tardíos dentro del pulso, que no representan flancos independientes.
Con trigger bajo aparecen muchos eventos no asociados. Estos resultados
muestran por qué contar eventos sin conservar la señal y la referencia es
insuficiente para evaluar una DAQ.

El matching es uno a uno dentro de ±10 ms y no demuestra causalidad: incluso
ruido próximo al flanco puede asociarse. No se interpreta como eficiencia de
neutrones ni como validación de un sistema de tiempo de vuelo.

## Regresión del pipeline existente

Se ejecutó `run_pipeline.py --trigger-source adc` contra el CSV local ya existente
`build/detector_hits.csv`, SHA-256
`6c3920ffaf80b73790eab6752ffebb97d0733ef89bd417ebaf581265dbda47d9`.

- 639 filas de depósitos de entrada.
- 82 eventos con depósito resumidos.
- 5000 muestras de forma de onda.
- 21 eventos reconstruidos con trigger ADC, semilla 12345 y parámetros por defecto.

**No se ejecutó una nueva simulación Geant4.** Estos resultados no reproducen
la corrida histórica de 1156/165/5000/39 porque no se ha demostrado identidad
de entrada ni configuración. El CSV local no se publica como una nueva corrida
Geant4 caracterizada. El banco óptico sí se reproduce sin depender de ese CSV.

## Pruebas y pendientes

La suite anterior tenía 17 pruebas. Se añadieron pruebas del protocolo, rechazo
de errores, rollover, pérdidas de muestras, captura fragmentada/timeout,
asociación uno a uno y análisis integrado. La prueba C++ en host comprueba
inicio/parada, slots omitidos, buffer lleno, rollover y límite de sesión.
Resultado final: **31 pruebas aprobadas**, sin omisiones, incluidas 14 nuevas.
El [log de la suite](experiments/optical_bench_2026-10-30/tests.txt) se conserva junto a este informe.

Se añadió un workflow para ejecutarlas en GitHub Actions. Su ejecución remota
queda pendiente de publicación y disponibilidad de las dependencias en el runner.

Pendientes físicos: confirmar componentes, compilar para AVR, cargar firmware,
medir alimentación y niveles, realizar tres capturas en protoboard, soldar,
repetir y comparar. Usar el [registro de construcción](hardware/build_record_template.md).
No añadir «banco óptico construido/soldado» al CV hasta completar esa evidencia.

## Alcance para el portafolio

Este avance demuestra software reproducible de adquisición/análisis y preparación
de una implementación electrónica. El desarrollo se realizó con asistencia de
herramientas de IA y pruebas automatizadas; el autor debe revisar y poder explicar
el protocolo, la histéresis, el tratamiento de tiempos y las limitaciones antes
de presentarlo como competencia propia. El montaje y la soldadura siguen pendientes.

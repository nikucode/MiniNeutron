# MiniNeutron DAQ Bench

MiniNeutron DAQ Bench es una extensión experimental del proyecto MiniNeutron orientada a aprender y desarrollar una cadena básica de adquisición de datos.

La primera versión no utiliza un detector de neutrones real. En su lugar, utiliza señales analógicas simuladas para desarrollar y validar el software de adquisición y análisis antes de incorporar hardware físico.

## Objetivo

Construir progresivamente una cadena de adquisición:

señal analógica → ADC → almacenamiento → análisis

La idea es poder reutilizar posteriormente este flujo con sensores y electrónica reales.

## DAQ Bench v0.1

La primera versión incluye:

- simulación de una señal analógica;
- conversión a un ADC configurable;
- almacenamiento en CSV;
- análisis estadístico con Python;
- visualización de voltaje en función del tiempo;
- histograma de valores ADC;
- análisis independiente con ROOT;
- exportación de objetos de análisis a un archivo ROOT.

## Archivos

- `simulate_adc.py`: genera la señal y simula la cuantización ADC.
- `analyze_adc.py`: analiza el CSV con Python y genera figuras.
- `root_adc_analysis.C`: analiza el mismo dataset con ROOT.
- `data/`: resultados generados por las pruebas DAQ.

## Primera prueba

Configuración:

- duración: 10 s;
- frecuencia de muestreo: 50 Hz;
- resolución ADC: 10 bits;
- voltaje de referencia: 5 V;
- muestras: 500.

Resultados:

- voltaje medio: 2.5026 V;
- voltaje mínimo: 1.4112 V;
- voltaje máximo: 3.5923 V;
- ADC medio: 512.02;
- ADC mínimo: 289;
- ADC máximo: 735.

Los resultados obtenidos con Python y ROOT fueron consistentes.

## Ejecución

Generar los datos:

    python daq/simulate_adc.py

Analizar con Python:

    python daq/analyze_adc.py

Analizar con ROOT:

    root -l -b -q daq/root_adc_analysis.C

Generar la señal pulsada:

    python daq/simulate_pulses.py

Analizar y reconstruir eventos:

    python daq/analyze_pulses.py

También es posible modificar los thresholds desde terminal:

    python daq/analyze_pulses.py --trigger 0.80 --rearm 0.65

El análisis usa `voltage_V` por defecto. Para aplicar la misma histéresis a
los códigos digitalizados de `adc_raw`, se puede ejecutar:

    python daq/analyze_pulses.py --trigger-source adc --trigger 0.80 --rearm 0.65 --vref 5 --bits 10

Los umbrales se expresan en voltios y se convierten a códigos inclusivos:
`adc_raw >= ceil(trigger/Vref × (2^bits−1))` abre el evento y
`adc_raw <= floor(rearm/Vref × (2^bits−1))` lo cierra. En este modo,
`peak_voltage_V` es el voltaje reconstruido desde `peak_adc`; no es la muestra
analógica original. Se debe indicar el mismo `Vref` y número de bits que se
utilizaron al generar el CSV. El pipeline integrado transmite esos parámetros
automáticamente.

## DAQ Bench v0.2 — Señales pulsadas

La segunda versión introduce una forma de onda pulsada sintética para comenzar a estudiar lógica de trigger y reconstrucción de eventos.

Se agregó:

- `simulate_pulses.py`: generación de baseline, ruido y pulsos gaussianos sintéticos;
- `analyze_pulses.py`: análisis de la waveform y reconstrucción de eventos.

La corrida de referencia utiliza:

- duración: 10 s;
- frecuencia de muestreo: 500 Hz;
- 5000 muestras;
- baseline: 0.5 V;
- ruido gaussiano: sigma = 0.03 V;
- ADC: 10 bits;
- Vref: 5 V;
- 12 componentes de pulso generadas.

La detección utiliza histéresis:

- trigger: 0.80 V;
- rearm: 0.65 V.

Un evento comienza cuando la señal supera el threshold de trigger y termina cuando vuelve a bajar hasta el threshold de rearme.

Mientras el evento está activo se registra el peak de la señal.

Para cada evento se almacenan:

- `event_id`;
- `trigger_time_s`;
- `peak_time_s`;
- `peak_voltage_V`;
- `peak_adc`;
- `end_time_s`;
- `duration_s`.

En la corrida de referencia se reconstruyeron 10 eventos.

El simulador había generado 12 componentes de pulso, pero este número no debe compararse directamente con la cantidad de eventos reconstruidos, ya que dos o más pulsos pueden superponerse y formar una única región continua para la lógica de trigger.

La corrida se conserva en:

`daq/reference/v0.2/`

Esta simulación utiliza pulsos gaussianos artificiales con fines de aprendizaje y no representa la respuesta de un detector de neutrones específico.

## Próximos pasos

- conectar una entrada analógica física;
- adquirir datos desde un microcontrolador por comunicación serial;
- mantener un formato compatible con Python y ROOT;
- incorporar señales pulsadas, ruido, umbral y detección de eventos;
- explorar acondicionamiento analógico y adquisición de señales reales.

## Extensión óptica de referencia

El importador `python -m daq.optical_bench` transforma streams de secuencia,
`micros()` y ADC al esquema común. `python -m daq.capture_serial` prepara
la captura USB con pySerial (dependencia opcional). El origen se etiqueta
explícitamente como `synthetic` o `hardware`. El trigger se ejecuta offline.

Ver la [guía de montaje y soldadura](../docs/hardware/optical_bench.md) y el
[estudio sintético](../docs/experiment_optical_bench_2026-10-30.md). El firmware
está preparado para revisión y pruebas en Uno R3; aún no se ha validado en placa.

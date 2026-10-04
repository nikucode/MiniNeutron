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

## Próximos pasos

- conectar una entrada analógica física;
- adquirir datos desde un microcontrolador por comunicación serial;
- mantener un formato compatible con Python y ROOT;
- incorporar señales pulsadas, ruido, umbral y detección de eventos;
- explorar acondicionamiento analógico y adquisición de señales reales.
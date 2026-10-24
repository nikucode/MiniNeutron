# MiniNeutron

MiniNeutron es un proyecto autodirigido de aprendizaje sobre transporte de neutrones, simulación Monte Carlo, análisis científico e instrumentación.

El proyecto comenzó como una forma de retomar Geant4 desde una base sencilla y entender qué ocurre con un neutrón durante su transporte dentro de un material moderador.

Con el tiempo se fue ampliando hacia una plataforma de aprendizaje que conecta distintas etapas de una cadena experimental:

`fenómeno físico -> simulación -> datos -> análisis -> adquisición -> instrumentación`

Actualmente MiniNeutron combina simulaciones en Geant4, análisis con Python y ROOT, y un primer banco DAQ simulado para comenzar a estudiar adquisición de señales antes de incorporar hardware físico.

## Estado actual

Actualmente están implementadas dos ramas principales y una integración
experimental entre ellas:

### 1. Simulación y análisis de neutrones

La simulación utiliza Geant4 para estudiar neutrones monoenergéticos de 2 MeV atravesando un bloque de polietileno.

El flujo actual es:

`fuente de neutrones`
`-> Geant4`
`-> transporte e interacciones`
`-> Event / Track / Step`
`-> CSV`
`-> Python`
`-> ROOT`

Se registran variables como:

- evento;
- track;
- parent ID;
- número de step;
- volumen;
- posición;
- energía cinética antes y después del step;
- disminución de energía cinética del neutrón durante el step;
- proceso físico;
- estado de frontera del step.

Esto permite distinguir, entre otras cosas, neutrones capturados y neutrones que abandonan el mundo de simulación.

### 2. MiniNeutron DAQ Bench

También se comenzó a desarrollar un banco simplificado de adquisición de datos.

Su primera versión utiliza una señal analógica simulada:

`señal simulada`
`-> ADC simulado`
`-> CSV`
`-> Python`
`-> ROOT`

Esta etapa permite desarrollar y validar el software de adquisición antes de incorporar microcontroladores, sensores y electrónica física.

El DAQ Bench todavía no utiliza un detector de neutrones real.

Más información:

`daq/README.md`

---

## Simulación Geant4

La geometría actual contiene:

- un mundo de aire de 1 m x 1 m x 1 m;
- un bloque de polietileno de 20 cm x 20 cm x 10 cm;
- un detector virtual de plástico centellador de 10 cm x 10 cm x 2 cm,
  situado entre z = 6 cm y z = 8 cm, tras una separación de aire de 1 cm.

La fuente genera:

- neutrones;
- energía inicial de 2 MeV;
- posición inicial en z = -30 cm;
- dirección +z.

La simulación utiliza una lista de física con tratamiento de neutrones de alta precisión.

Para esta etapa se utiliza un `RunManager` serial debido a problemas encontrados anteriormente entre Qt/OpenGL y el modo multihilo.

---

## Corrida de referencia

Se conserva una corrida de referencia de:

`1000 neutrones primarios`

Resultados:

- 39904 steps registrados;
- 37142 interacciones `hadElastic`;
- promedio de 37.142 colisiones elásticas por track primario;
- mediana de 17 colisiones;
- 240 tracks clasificados como `CAPTURE`;
- 758 clasificados como `ESCAPE`;
- 2 clasificados como `INELASTIC`;
- 0 clasificados como `OTHER`.

La energía final media de los tracks primarios fue aproximadamente:

`0.34175 MeV`

y la mediana:

`3.60496e-07 MeV`

Estos resultados corresponden solamente a esta configuración y corrida Monte Carlo. No representan una validación experimental ni una caracterización general del polietileno.

La corrida se encuentra en:

`results/runs/run_1000_tracks_v1/`

---

## Análisis con Python

El script principal se encuentra en:

`analysis/analyze_steps.py`

El análisis utiliza principalmente:

- Pandas;
- NumPy;
- Matplotlib.

Entre los análisis realizados se encuentran:

- distribución del número de colisiones;
- distribución de energía final;
- energía final en escala logarítmica;
- relación entre colisiones y energía final;
- clasificación del resultado de tracks primarios;
- identificación de capturas y escapes.

---

## Análisis con ROOT

También se desarrolló un pipeline independiente utilizando ROOT.

Se utiliza `RDataFrame` para analizar los datos y se creó un archivo ROOT con un árbol resumido de los tracks primarios.

La corrida de referencia contiene:

`minineutron_tracks.root`

con variables como:

- event;
- track_id;
- collisions;
- final_energy_MeV;
- final_process;
- final_step_status;
- outcome.

El análisis batch puede ejecutarse con:

    root -l -b -q analysis/root_analysis.C

ROOT reproduce la clasificación obtenida con Python para la corrida de referencia.

---

## MiniNeutron DAQ Bench

La primera prueba del DAQ Bench utiliza:

- duración de 10 s;
- frecuencia de muestreo de 50 Hz;
- ADC simulado de 10 bits;
- Vref de 5 V;
- 500 muestras.

La señal contiene:

- nivel medio de 2.5 V;
- componente sinusoidal de 0.5 Hz;
- ruido gaussiano.

Resultados de referencia:

- voltaje medio: 2.5026 V;
- voltaje mínimo: 1.4112 V;
- voltaje máximo: 3.5923 V;
- ADC medio: 512.02;
- ADC mínimo: 289;
- ADC máximo: 735.

Los resultados fueron analizados independientemente con Python y ROOT y fueron consistentes entre ambos pipelines.

---

### DAQ de señales pulsadas v0.2

También se implementó una segunda etapa del DAQ Bench utilizando señales pulsadas sintéticas.

Actualmente incluye:

- baseline y ruido gaussiano;
- pulsos gaussianos sintéticos;
- cuantización ADC;
- threshold de trigger;
- histéresis mediante un threshold separado de rearme;
- reconstrucción de eventos;
- timestamp de trigger y peak;
- voltaje y valor ADC del peak;
- duración del evento.

La configuración de referencia utiliza un trigger de 0.80 V y un nivel de rearme de 0.65 V.

Esta etapa está orientada al aprendizaje de conceptos de adquisición y no representa la respuesta de un detector de neutrones específico.

---

### Integración Geant4 → señal → DAQ → comparación

La etapa integrada parte de `build/detector_hits.csv`, generado al ejecutar
Geant4 desde el directorio `build`:

    cd build
    ./minineutron ../macros/run_detector_1000.mac
    cd ..

Después se ejecuta, desde la raíz del proyecto:

    python run_pipeline.py

Cada ejecución crea un directorio en `results/pipeline_runs/` con un
`manifest.json`, resúmenes de los depósitos, respuesta del detector, forma de
onda, tabla de eventos reconstruidos y dos tablas de comparación. El pipeline
analiza un CSV existente; no ejecuta Geant4 ni verifica cómo se generó ese CSV.
El manifiesto registra los parámetros, la versión de Python y hashes SHA-256
del CSV de entrada y los scripts del pipeline. Esos hashes permiten comparar
archivos entre corridas, pero no registran todavía la configuración completa
ni la semilla de la ejecución anterior de Geant4.
Los resultados de trabajo se ignoran en Git por defecto.

Por cada evento Geant4 con energía depositada en el detector, el modelo suma
los depósitos de todos los tipos de partículas y calcula una amplitud mediante
`A [V] = ganancia [V/MeV] × energía depositada [MeV]`. Se asigna un tiempo de
fuente sintético, reproducible con `--seed`, y se añade el tiempo local del
primer depósito Geant4 (ns convertidos a s). Cada evento se representa con un
pulso exponencial de constante `--tau` en segundos. La señal suma los pulsos,
baseline y ruido gaussiano, se limita a `[0, Vref]` y se cuantiza al ADC.

Por defecto, el trigger de la DAQ utiliza `voltage_V`, antes de cuantización,
con umbrales `--trigger` y `--rearm` en voltios. Con
`--trigger-source adc` utiliza `adc_raw`: el trigger exige un código mayor o
igual a `ceil(trigger/Vref × (2^bits−1))` y el rearme uno menor o igual a
`floor(rearm/Vref × (2^bits−1))`. En este modo, `peak_voltage_V` se reconstruye
desde el código ADC y representa un valor cuantizado. La configuración elegida
queda en el manifiesto y en la tabla de eventos. Ejemplo:

    python run_pipeline.py --trigger-source adc --bits 10 --vref 5

En el modo por defecto, cambiar `--bits` no cambia por sí solo qué eventos
dispara el algoritmo. La comparación temporal
usa `--pre-window` (4 ms por defecto): un pulso truth es candidato a un evento
DAQ si su tiempo está entre `trigger_time_s - pre_window` y `end_time_s`,
inclusive. Los truth se clasifican como `individual`, `merged`, `missed` o
`ambiguous` si caen en más de una ventana. Una asociación temporal no demuestra
qué pulso causó el trigger. Estas cifras tampoco son una eficiencia física de
detección de neutrones.

Para comprobar las pruebas automáticas disponibles:

    python -m unittest discover -s tests -v

El primer barrido reproducible de umbral, ruido y duración se ejecuta con
`analysis/study_daq_sensitivity.py`. Su método, resultados y límites están en
`docs/experiment_daq_sensitivity_2026-10-24.md`.
El análisis de contribuciones al trigger usa
`analysis/study_trigger_contributions.py` y está documentado en
`docs/experiment_trigger_contributions_2026-10-24.md`.
La comparación controlada entre triggers de voltaje y ADC está en
`docs/experiment_adc_trigger_2026-10-24.md`.
El barrido reproducible de tres semillas y cuatro resoluciones se ejecuta con
`analysis/study_adc_trigger.py`; su método y resultados están en
`docs/experiment_adc_trigger_sweep_2026-10-24.md`.

Este modelo no incluye producción y transporte de luz, quenching, respuesta de
fotodetector ni electrónica calibrada. La tasa de fuente, ganancia y ventana de
asociación son hipótesis de estudio pendientes de validación.

---


## Estructura

    MiniNeutron/
    ├── analysis/
    │   ├── analyze_detector_hits.py
    │   ├── analyze_steps.py
    │   ├── build_detector_waveform.py
    │   ├── compare_truth_reco.py
    │   ├── detector_response.py
    │   ├── diagnose_trigger_contributions.py
    │   ├── study_daq_sensitivity.py
    │   ├── study_adc_trigger.py
    │   ├── study_trigger_contributions.py
    │   ├── validate_data.py
    │   └── root_analysis.C
    │
    ├── daq/
    │   ├── analyze_adc.py
    │   ├── analyze_pulses.py
    │   ├── root_adc_analysis.C
    │   ├── simulate_adc.py
    │   ├── simulate_pulses.py
    │   ├── README.md
    │   └── data/
    │
    ├── docs/
    │   └── bitacora.md
    │
    ├── include/
    │   ├── ActionInitialization.hh
    │   ├── DetectorConstruction.hh
    │   ├── PrimaryGeneratorAction.hh
    │   └── SteppingAction.hh
    │
    ├── macros/
    │   └── run_detector_1000.mac
    │
    ├── results/
    │   ├── pipeline_runs/ (salidas locales ignoradas por Git)
    │   └── runs/
    │       └── run_1000_tracks_v1/
    │
    ├── src/
    │   ├── ActionInitialization.cc
    │   ├── DetectorConstruction.cc
    │   ├── PrimaryGeneratorAction.cc
    │   └── SteppingAction.cc
    │
    ├── tests/
    ├── run_pipeline.py
    ├── CMakeLists.txt
    ├── miniNeutron.cc
    ├── requirements.txt
    └── README.md

---

## Compilación

Primero se debe cargar el entorno de Geant4:

    source ~/geant4/install/bin/geant4.sh

Crear el directorio de compilación:

    mkdir -p build
    cd build

Configurar:

    cmake ..

Compilar:

    make

Ejecutar:

    ./minineutron

La ruta exacta de instalación de Geant4 puede variar entre sistemas.

---

## Entorno de Python

Se puede crear un entorno virtual con:

    python -m venv .venv

Activarlo:

    source .venv/bin/activate

Instalar dependencias:

    pip install -r requirements.txt

---

## DAQ Bench

Generar la señal simulada:

    python daq/simulate_adc.py

Analizar con Python:

    python daq/analyze_adc.py

Analizar con ROOT:

    root -l -b -q daq/root_adc_analysis.C

---

## Limitaciones actuales

MiniNeutron se encuentra en desarrollo.

Actualmente:

- la geometría es deliberadamente simple;
- el polietileno corresponde al material NIST utilizado por Geant4 y no representa necesariamente una formulación exacta de HDPE;
- los resultados todavía no han sido comparados con mediciones experimentales;
- el DAQ Bench utiliza señales simuladas;
- todavía no existe un detector físico de neutrones;
- todavía no se ha implementado una cadena real de acondicionamiento y adquisición de señal;
- los resultados dependen de la configuración específica de la simulación.

El objetivo actual es aprender y validar cada etapa de la cadena antes de aumentar su complejidad.

---

## Próximos pasos

Las siguientes etapas consideradas son:

- inventariar el hardware disponible;
- incorporar adquisición analógica desde un microcontrolador;
- comunicación serial hacia Python;
- definir un formato común para datos simulados y físicos;
- generar señales pulsadas y estudiar threshold y trigger;
- explorar acondicionamiento analógico;
- estudiar sensores y sistemas de detección apropiados de forma segura;
- relacionar progresivamente simulación, electrónica y adquisición experimental.

---

## Bitácora

El proceso completo de desarrollo, errores, pruebas y aprendizajes está documentado en:

`docs/bitacora.md`

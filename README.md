# MiniNeutron

MiniNeutron es un proyecto autodirigido de aprendizaje sobre transporte de neutrones, simulación Monte Carlo, análisis científico e instrumentación.

El proyecto comenzó como una forma de retomar Geant4 desde una base sencilla y entender qué ocurre con un neutrón durante su transporte dentro de un material moderador.

Con el tiempo se fue ampliando hacia una plataforma de aprendizaje que conecta distintas etapas de una cadena experimental:

`fenómeno físico -> simulación -> datos -> análisis -> adquisición -> instrumentación`

Actualmente MiniNeutron combina simulaciones en Geant4, análisis con Python y ROOT, y un primer banco DAQ simulado para comenzar a estudiar adquisición de señales antes de incorporar hardware físico.

## Estado actual

Actualmente están implementadas dos ramas principales:

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
- un bloque de polietileno de 20 cm x 20 cm x 10 cm.

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

## MiniNeutron DAQ Bench v0.1

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

## Estructura

    MiniNeutron/
    ├── analysis/
    │   ├── analyze_steps.py
    │   └── root_analysis.C
    │
    ├── daq/
    │   ├── analyze_adc.py
    │   ├── root_adc_analysis.C
    │   ├── simulate_adc.py
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
    ├── results/
    │   └── runs/
    │       └── run_1000_tracks_v1/
    │
    ├── src/
    │   ├── ActionInitialization.cc
    │   ├── DetectorConstruction.cc
    │   ├── PrimaryGeneratorAction.cc
    │   └── SteppingAction.cc
    │
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

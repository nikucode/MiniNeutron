# Bitácora de desarrollo — MiniNeutron

Esta bitácora registra el desarrollo y aprendizaje asociado a MiniNeutron.

MiniNeutron comenzó como un proyecto para retomar Geant4 desde una base simple y entender de manera práctica cómo funciona una simulación Monte Carlo de transporte de partículas. Con el avance del proyecto, la idea se amplió hacia una plataforma didáctica de instrumentación científica, conectando simulación, adquisición de datos, análisis y eventualmente electrónica y hardware físico.

---

## 3–18 de agosto de 2026 — Instalación de Geant4 y primeros experimentos

### Objetivo

Instalar Geant4 correctamente en Linux y comenzar a comprender su arquitectura mediante ejemplos oficiales antes de crear un proyecto propio.

### Configuración

Se instaló Geant4 11.4.2 con soporte para:

- Qt
- OpenGL
- GDML
- multithreading
- datasets de física, incluyendo G4NDL

La instalación quedó ubicada en:

`~/geant4/install`

Para cargar el entorno se utiliza:

`source ~/geant4/install/bin/geant4.sh`

### Primer aprendizaje con B1

Se utilizó el ejemplo oficial B1 para comprender algunos conceptos fundamentales de Geant4:

- Run
- Event
- Track
- Step
- DetectorConstruction
- PrimaryGeneratorAction
- SteppingAction
- EventAction
- RunAction

También se estudió la estructura:

`Solid -> Logical Volume -> Physical Volume`

Se modificó inicialmente la energía de la partícula del ejemplo y se analizaron valores de energía depositada para distintas cantidades de eventos.

Esto permitió observar una característica importante de los métodos Monte Carlo: al aumentar la cantidad de eventos, los resultados estadísticos comienzan a estabilizarse.

---

## 8 de septiembre de 2026 — Inicio de MiniNeutron

### Objetivo

Crear desde cero una simulación sencilla de neutrones atravesando un material moderador.

### Geometría inicial

Se creó:

- un mundo de aire de 1 m x 1 m x 1 m;
- un bloque moderador de polietileno de 20 cm x 20 cm x 10 cm.

El moderador se ubicó en el centro del mundo.

### Fuente

Se configuró una fuente monoenergética de neutrones:

- partícula: neutrón;
- energía inicial: 2 MeV;
- posición: z = -30 cm;
- dirección: +z.

De esta forma los neutrones viajan directamente hacia el moderador.

### Física

Se utilizó una lista de física con tratamiento de neutrones de alta precisión para estudiar sus interacciones a bajas energías.

### Visualización

Se configuró OpenGL para visualizar:

- geometría;
- moderador;
- trayectorias de partículas.

Durante las primeras pruebas se encontró un problema entre la visualización Qt/OpenGL y el modo multihilo.

Se resolvió utilizando un RunManager serial para esta etapa del desarrollo.

---

## 8–9 de septiembre de 2026 — Seguimiento de neutrones

### Objetivo

Dejar de observar solamente las trayectorias gráficas y comenzar a estudiar numéricamente qué ocurre con cada neutrón.

Se implementó `SteppingAction`.

Para cada step del neutrón se comenzó a registrar:

- número de evento;
- número de step;
- volumen;
- posición;
- energía cinética antes del step;
- energía cinética después del step;
- proceso físico responsable.

### Primer evento observado

Uno de los primeros neutrones mostró:

`2.000 MeV -> 1.53447 MeV`

mediante el proceso:

`hadElastic`

La pérdida de energía fue:

`0.46553 MeV`

Después de esta interacción, el neutrón cambió ligeramente de dirección y salió del moderador.

Esto permitió relacionar por primera vez:

`trayectoria visual -> proceso físico -> cambio de energía`

Otro evento presentó múltiples dispersiones elásticas sucesivas:

`2.000 MeV`
`-> 1.668 MeV`
`-> 1.444 MeV`
`-> 0.502 MeV`
`-> 0.213 MeV`

Esto mostró directamente el proceso de moderación mediante múltiples interacciones.

---

## 11 de septiembre de 2026 — Exportación de datos

### Objetivo

Crear un puente entre la simulación de Geant4 y herramientas externas de análisis.

Se modificó `SteppingAction` para guardar automáticamente los steps en:

`minineutron_steps.csv`

Las columnas iniciales son:

- event
- step
- volume
- x_mm
- y_mm
- z_mm
- energy_before_MeV
- energy_after_MeV
- delta_energy_MeV
- process

La disminución de energía cinética registrada para el neutrón se calcula como:

`delta_energy = energy_before - energy_after`

Este valor representa la disminución de energía cinética del neutrón
seguido durante ese step. No debe interpretarse directamente como
energía depositada en el material, ya que parte de la energía puede ser
transferida a partículas secundarias.

Esto permitió transformar la salida de Geant4 desde información mostrada solamente en terminal a un conjunto de datos estructurado.

La arquitectura comenzó a convertirse en:

`Geant4 -> CSV -> análisis`

---

## 19 de septiembre de 2026 — Primer análisis con Python

### Objetivo

Leer automáticamente los datos producidos por Geant4 y obtener información estadística.

Se creó:

`analysis/analyze_steps.py`

Se configuró un entorno virtual de Python en:

`analysis/.venv`

Debido a que Arch Linux utiliza un entorno de Python administrado por el sistema, se evitó modificar `/usr/bin/python` y se instalaron las dependencias dentro del entorno virtual.

Principales librerías utilizadas:

- Pandas
- Matplotlib
- NumPy

Las dependencias fueron registradas en:

`requirements.txt`

### Primer dataset

Se simularon:

`10 eventos`

El análisis obtuvo:

- 269 steps totales;
- 241 interacciones `hadElastic`;
- 13.3705 MeV de pérdida energética acumulada en estas interacciones;
- pérdida media por interacción de aproximadamente 0.05548 MeV.

### Primera visualización

Se generó automáticamente:

`results/figures/energy_loss_histogram.png`

El histograma muestra la distribución de energía perdida por interacción elástica.

En esta pequeña muestra se observa una gran concentración de interacciones con transferencias pequeñas de energía y una cantidad reducida de colisiones con transferencias mucho mayores.

Debido a que solamente se utilizaron 10 eventos, estos resultados todavía se consideran una prueba del pipeline de análisis y no una caracterización estadística del moderador.

---

## Estado del proyecto al 19 de septiembre de 2026

El proyecto actualmente implementa:

`fuente de neutrones`
`-> transporte Geant4`
`-> moderación en polietileno`
`-> seguimiento de steps`
`-> exportación CSV`
`-> análisis con Python`
`-> generación automática de figuras`

La siguiente etapa será aumentar la cantidad de eventos y comenzar a estudiar estadísticamente la moderación.

A futuro se busca extender la arquitectura hacia:

`Geant4`
`-> datos simulados`
`-> análisis`
`-> electrónica simplificada`
`-> microcontrolador / ADC`
`-> comunicación`
`-> adquisición`
`-> comparación entre datos simulados y físicos`

También se planea incorporar documentación en LaTeX, hardware didáctico, soldadura y posiblemente diseño CAD.

### Relacion entre numero de colisiones y energia final

Se comparo el numero de interacciones `hadElastic` de cada evento
con la energia final registrada del neutron.

Los resultados mostraron una tendencia clara en esta pequeña muestra:
los neutrones que experimentaron pocas colisiones generalmente
conservaron una mayor fraccion de sus 2 MeV iniciales, mientras que
los eventos con muchas interacciones alcanzaron energias mucho menores.

Algunos ejemplos fueron:

- Evento 2: 1 colision -> 1.93775 MeV.
- Evento 3: 15 colisiones -> aproximadamente 57.4 eV.
- Evento 5: 80 colisiones -> captura.
- Evento 8: 25 colisiones -> aproximadamente 0.0926 eV.
- Evento 9: 92 colisiones -> aproximadamente 0.0712 eV.

El grafico `collisions_vs_final_energy.png` permite visualizar esta
relacion directamente.

### Identificacion de capturas

Al revisar el ultimo proceso registrado de cada evento se observo que
los eventos 5 y 7 terminaron dentro del moderador mediante:

`nCaptureHP`

Por lo tanto, las energias finales de 0 MeV de estos dos eventos no
correspondian simplemente a valores numericamente pequenos, sino a
tracks que finalizaron mediante un proceso de captura de neutrones.

Esto mostro la importancia de revisar el proceso fisico asociado al
ultimo step antes de interpretar solamente la energia final.

Los otros eventos terminaron con `Transportation` en el volumen
`World`. En una etapa posterior se registrara tambien el estado de
frontera del step para distinguir de manera explicita los neutrones
que abandonan el mundo de simulacion.

### Interpretacion preliminar

La muestra actual contiene solamente 10 eventos, por lo que la
relacion observada todavia no se utiliza como una caracterizacion
estadistica del moderador.

Por ahora, el resultado demuestra que el pipeline permite relacionar:

`historia de interacciones`
`-> numero de colisiones`
`-> energia final`
`-> proceso final`

y distinguir historias individuales muy diferentes aun cuando todos
los neutrones parten con las mismas condiciones iniciales.

Se aumentó la simulación desde 10 hasta 100 neutrones iniciales de 2 MeV.

También se corrigió el análisis de colisiones por evento. Inicialmente,
los eventos sin interacciones `hadElastic` no aparecían en el agrupamiento
de Pandas, por lo que el promedio se calculaba solamente sobre 96 eventos.

Después de incluir explícitamente los eventos con cero colisiones se obtuvo:

- 100 eventos simulados;
- 3477 colisiones `hadElastic`;
- promedio de 34.77 colisiones por evento;
- mínimo de 0 colisiones;
- máximo de 208 colisiones;
- 4 eventos sin ninguna colisión `hadElastic`;
- los 4 conservaron una energía final de 2 MeV;
- 21 eventos terminaron mediante `nCaptureHP`;
- fracción de captura observada: 0.21;
- porcentaje de captura observado: 21 %;
- energía final media: aproximadamente 0.38665 MeV.

Estos valores corresponden solamente a esta corrida Monte Carlo de
100 eventos y todavía no se consideran una caracterización estadística
definitiva del sistema.

---

## 28 de septiembre de 2026 — Análisis estadístico 

### Corridas de mayor tamaño

Se amplió progresivamente la simulación para pasar desde pruebas con
historias individuales hacia un análisis estadístico de la moderación.

Después de validar una corrida de 100 eventos, se realizó una corrida
de 1000 neutrones iniciales de 2 MeV.

Para esta corrida se obtuvo:

- 1000 eventos simulados;
- 39904 steps registrados;
- 37142 interacciones `hadElastic`;
- promedio de 37.142 colisiones elásticas por evento;
- mediana de 17 colisiones;
- mínimo de 0 colisiones;
- máximo de 375 colisiones;
- 52 eventos sin interacciones `hadElastic`;
- 5.2 % de los eventos sin colisiones elásticas;
- 240 neutrones terminaron mediante `nCaptureHP`;
- fracción de captura observada de 0.24;
- porcentaje de captura observado de 24 %.

La energía final media fue aproximadamente:

`0.34175 MeV`

mientras que la mediana fue:

`3.60496e-07 MeV`

Esto mostró que la distribución de energías finales es fuertemente
asimétrica. Una cantidad importante de neutrones alcanza energías muy
bajas, mientras que una fracción más pequeña conserva energías mucho
mayores y eleva considerablemente el valor de la media.

### Análisis mediante distribuciones

Al aumentar la cantidad de eventos se dejó de representar cada neutrón
individual mediante gráficos de barras y se comenzaron a utilizar
distribuciones estadísticas.

Se generaron:

- `energy_loss_histogram.png`
- `collisions_distribution.png`
- `final_energy_distribution.png`
- `final_energy_log_distribution.png`
- `collisions_vs_final_energy.png`
- `capture_summary.png`

La distribución del número de colisiones presentó una cola hacia
valores altos. Esto explica la diferencia entre una mediana de
17 colisiones y una media de 37.142.

También se utilizó una escala logarítmica para representar la energía
final, ya que los resultados cubren varios órdenes de magnitud.

Inicialmente se aplicó una escala logarítmica solamente al eje de un
histograma con bins lineales, lo cual concentraba artificialmente una
gran cantidad de datos en el primer intervalo.

Esto se corrigió utilizando bins espaciados logarítmicamente mediante
`numpy.logspace`.

### Registro de runs

Se comenzó a conservar cada corrida de simulación de forma separada,
incluyendo:

- CSV completo de steps;
- resumen por evento;
- salida textual del análisis;
- figuras generadas.

Esto permite comparar distintas corridas sin sobrescribir resultados
anteriores.

### Mejora de la estructura del CSV

Se amplió `SteppingAction` para registrar tres nuevas variables:

- `track_id`
- `parent_id`
- `step_status`

El objetivo es distinguir correctamente entre:

`Event -> Track -> Step`

ya que un evento puede contener múltiples tracks y cada track puede
contener múltiples steps.

`parent_id = 0` permite identificar el track primario generado por la
fuente.

También se comenzó a registrar el estado final de cada step para
distinguir entre cruces de geometría y salida del mundo de simulación.

Por ejemplo:

`Transportation + GeomBoundary`

indica un cruce entre volúmenes, mientras que:

`Transportation + WorldBoundary`

indica que el neutrón abandonó el mundo de simulación.

Las primeras pruebas confirmaron correctamente el registro de estas
variables.

## 29 de septiembre de 2026 - Mejora del registro de tracks

### Estado actual de la arquitectura

La cadena implementada actualmente es:

`fuente de neutrones`
`-> Geant4`
`-> transporte e interacciones`
`-> identificación de events / tracks / steps`
`-> CSV`
`-> análisis estadístico con Python`
`-> generación automática de figuras`

La siguiente etapa será adaptar el análisis de Python para utilizar
explícitamente `track_id`, `parent_id` y `step_status`, y clasificar
mejor los resultados finales de los neutrones primarios.

### Validacion de la clasificacion por track

Se adapto el analisis de Python para trabajar explicitamente con:

- `event`
- `track_id`
- `parent_id`
- `step_status`

En lugar de asumir que cada evento contiene una sola trayectoria, el
analisis ahora agrupa los datos por evento y track.

Los neutrones primarios se identifican mediante:

`parent_id = 0`

y el resultado final de cada track se clasifica como:

- `CAPTURE` si el proceso final es `nCaptureHP`;
- `ESCAPE` si el ultimo step presenta `WorldBoundary`;
- `OTHER` para cualquier terminacion que no corresponda a las categorias anteriores.

Se realizo una prueba con 10 eventos.

Resultados:

- 10 tracks primarios;
- 241 colisiones `hadElastic`;
- 2 neutrones clasificados como `CAPTURE`;
- 8 neutrones clasificados como `ESCAPE`;
- 0 casos `OTHER`.

Esta prueba confirmo que la nueva estructura permite distinguir de
forma explicita entre captura y salida del mundo de simulacion. 

## 3 de octubre de 2026 — Inicio de MiniNeutron DAQ Bench

### Objetivo

Comencé una nueva etapa del proyecto orientada a adquisición de datos e instrumentación. La idea es desarrollar primero un banco DAQ simplificado y seguro, separado del sistema de detección real, para aprender la cadena completa:

señal analógica → ADC → adquisición → almacenamiento → análisis.

La primera versión utiliza una señal simulada para poder desarrollar y validar el software antes de depender de hardware físico.

### Estructura inicial

Se creó una nueva carpeta:

`daq/`

con los archivos:

- `simulate_adc.py`
- `analyze_adc.py`
- `root_adc_analysis.C`
- `README.md`
- `data/`

### Simulación del ADC

Se implementó `simulate_adc.py`, que genera una señal analógica sintética formada por:

- nivel medio de 2.5 V;
- señal sinusoidal de 0.5 Hz;
- ruido gaussiano;
- ADC configurable en resolución y voltaje de referencia.

La prueba inicial utilizó:

- duración: 10 s;
- frecuencia de muestreo: 50 Hz;
- ADC: 10 bits;
- Vref: 5 V;
- muestras: 500.

El resultado se almacena en:

`daq/data/simulated_adc.csv`

con las columnas:

`sample,timestamp_s,adc_raw,voltage_V`

### Análisis con Python

Se implementó `analyze_adc.py` para leer el CSV y calcular estadísticas básicas.

Resultados de la primera corrida:

- muestras: 500;
- duración: 9.980 s;
- frecuencia estimada: 50.000 Hz;
- voltaje medio: 2.5026 V;
- desviación estándar: 0.7103 V;
- voltaje mínimo: 1.4112 V;
- voltaje máximo: 3.5923 V;
- ADC medio: 512.02;
- ADC mínimo: 289;
- ADC máximo: 735.

Se generaron:

- `voltage_vs_time.png`
- `adc_histogram.png`

Durante la primera ejecución Matplotlib produjo un error relacionado con el backend gráfico GTK/GDK. Se corrigió configurando el backend `Agg`, permitiendo ejecutar el análisis en modo batch y guardar las figuras sin abrir ventanas gráficas.

### Análisis con ROOT

Se creó `root_adc_analysis.C` para analizar el mismo CSV mediante ROOT y RDataFrame.

Inicialmente ROOT detectó `adc_raw` como `Long64_t`, mientras el código intentaba leerlo como `double`. Se corrigió utilizando el tipo correspondiente para las operaciones sobre la columna ADC.

Resultados obtenidos con ROOT:

- muestras: 500;
- voltaje medio: 2.50258 V;
- voltaje mínimo: 1.41119 V;
- voltaje máximo: 3.5923 V;
- ADC medio: 512.022;
- ADC mínimo: 289;
- ADC máximo: 735.

Los resultados son consistentes con los obtenidos mediante Python.

ROOT generó:

- `root_adc_histogram.png`
- `root_voltage_vs_time.png`
- `minineutron_daq.root`

### Estado del DAQ bench al 3 de octubre 

El flujo DAQ v0.1 funciona de extremo a extremo:

señal simulada → ADC simulado → CSV → análisis Python → análisis ROOT.

El siguiente paso será definir el formato común para adquisición física y luego reemplazar la señal simulada por una entrada analógica real desde un microcontrolador.

---

## 4 de octubre de 2026 — DAQ Bench v0.2: señales pulsadas y reconstrucción de eventos

### Objetivo

Después de validar el flujo básico de adquisición con una señal sinusoidal, se comenzó una segunda versión del DAQ Bench orientada a señales pulsadas.

El objetivo de esta etapa fue estudiar de forma simplificada conceptos como:

- baseline;
- ruido;
- pulsos;
- muestreo;
- threshold;
- trigger;
- histéresis;
- reconstrucción de eventos;
- amplitud máxima.

Esta etapa continúa utilizando señales completamente sintéticas y no representa todavía la respuesta física de un detector de neutrones.

### Generación de señales pulsadas

Se creó:

`daq/simulate_pulses.py`

El simulador genera una forma de onda compuesta por:

- baseline de 0.5 V;
- ruido gaussiano con sigma de 0.03 V;
- pulsos gaussianos con posición, amplitud y ancho variables;
- cuantización mediante un ADC ideal.

Para la primera corrida se utilizaron:

- duración: 10 s;
- frecuencia de muestreo: 500 Hz;
- muestras: 5000;
- ADC: 10 bits;
- Vref: 5 V;
- 12 componentes de pulso generadas.

La salida fue almacenada inicialmente en:

`daq/data/simulated_pulses.csv`

con las columnas:

`sample,timestamp_s,adc_raw,voltage_V`

### Análisis de la forma de onda

Se creó:

`daq/analyze_pulses.py`

La señal obtenida presentó:

- duración analizada: 9.998 s;
- frecuencia estimada: 500.000 Hz;
- voltaje medio: 0.6060 V;
- desviación estándar: 0.3450 V;
- voltaje mínimo: 0.3892 V;
- voltaje máximo: 2.7877 V;
- ADC medio: 124.00;
- ADC mínimo: 80;
- ADC máximo: 570.

Se generó una visualización de la forma de onda completa para comprobar el baseline, el ruido y los pulsos.

### Primer trigger por threshold

Inicialmente se implementó un trigger simple detectando cruces ascendentes sobre:

`0.80 V`

La primera prueba detectó 12 cruces.

Sin embargo, uno de ellos correspondía a un re-trigger cercano a la cola de un pulso, mostrando que un threshold simple puede interpretar ruido o pequeñas oscilaciones como eventos adicionales.

### Prueba con dead time

Se probó posteriormente un dead time fijo de:

`0.150 s`

Esta estrategia eliminó el re-trigger, pero redujo la cantidad de eventos aceptados a 10 y también eliminó una estructura cercana que podía corresponder a un pulso distinguible.

Esto mostró que un dead time demasiado largo puede evitar re-triggers, pero también puede reducir la resolución temporal del sistema.

### Trigger con histéresis

Se reemplazó el dead time fijo por un sistema de trigger con histéresis.

Se utilizaron:

- trigger threshold: 0.80 V;
- rearm threshold: 0.65 V.

La lógica implementada es:

`armed`
`-> señal >= trigger`
`-> abrir evento`
`-> seguir la forma de onda`
`-> señal <= rearm`
`-> cerrar evento`
`-> volver a armed`

Esta estrategia evita volver a disparar el trigger mientras la señal no haya regresado suficientemente cerca del baseline.

### Event builder

El análisis se modificó para que cada evento permanezca abierto desde el trigger hasta que la señal cruza el nivel de rearme.

Durante ese intervalo se registra el valor máximo observado.

Para cada evento se almacenan:

- `event_id`;
- `trigger_time_s`;
- `peak_time_s`;
- `peak_voltage_V`;
- `peak_adc`;
- `end_time_s`;
- `duration_s`.

Los eventos reconstruidos se guardan en:

`detected_events.csv`

La primera corrida con trigger e histéresis produjo:

`10 eventos reconstruidos`

a partir de una forma de onda generada usando 12 componentes de pulso.

Esto no se interpreta como una eficiencia física de 10/12.

Los pulsos pueden superponerse y producir una única estructura continua por encima de los thresholds. Por lo tanto:

`pulso generado != pico visible != evento reconstruido`

Por ejemplo, uno de los eventos reconstruidos tuvo una duración de aproximadamente:

`0.244 s`

considerablemente mayor que varios de los demás eventos, debido a estructuras cercanas que permanecieron conectadas antes de que la señal bajara hasta el nivel de rearme.

### Estado del DAQ Bench al 4 de octubre 

La cadena implementada actualmente es:

`señal sintética`
`-> baseline + ruido + pulsos`
`-> ADC simulado`
`-> waveform CSV`
`-> trigger`
`-> histéresis`
`-> event builder`
`-> extracción de peak`
`-> tabla de eventos`

La corrida actual se conserva como referencia en:

`daq/reference/v0.2/`

Una mejora futura será guardar también la información original de cada pulso generado por el simulador para poder comparar:

`ground truth`
`-> waveform`
`-> eventos reconstruidos`

y estudiar formalmente superposición, pulsos perdidos y resolución temporal.
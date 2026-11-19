# MiniNeutron: reconstrucción temporal de formas de onda sintéticas

Fecha: 19 de noviembre de 2026.

Este es un experimento computacional controlado de MiniNeutron. No utiliza
registros DRS4, no calibra un detector y no estima tiempo de vuelo de neutrones.

## Motivación y procedencia

La pregunta surgió después de revisar, con fines de aprendizaje, registros
experimentales DRS4 compartidos por colaboradores de SAPHIR. Esa experiencia
mostró la importancia de distinguir línea base, ruido, saturación y diferentes
definiciones temporales. Los registros, macros y resultados externos conservan
su autoría y no se incluyen en MiniNeutron.

El estudio publicado aquí es independiente: genera señales sintéticas propias,
conserva un tiempo de inicio conocido (`truth`) e implementa sus algoritmos en
segundos y voltios sin copiar ventanas, umbrales ni constantes de la adquisición
DRS4. El objetivo es evaluar decisiones del modelo educativo de MiniNeutron.

## Pregunta

¿Cómo varían la latencia, la dispersión temporal y la dependencia con la
amplitud al reconstruir un pulso sintético mediante:

1. tiempo de la muestra máxima;
2. primer cruce interpolado de un umbral fijo;
3. cruce interpolado del 50 % del máximo observado (CFD simplificado)?

Se usa *time walk* para la diferencia entre la mayor y la menor latencia media
al comparar amplitudes bajo una misma frecuencia de muestreo y nivel de ruido.

## Método

El pulso controlado es una diferencia de exponenciales normalizada:

\[
p(t) = A\left(1-e^{-(t-t_0)/\tau_r}\right)
       e^{-(t-t_0)/\tau_d},\qquad t\ge t_0.
\]

Los parámetros del estudio fueron:

- amplitudes de 0,2, 0,5 y 1,0 V;
- ruido gaussiano con \(\sigma\) de 0, 10 y 30 mV;
- muestreo a 500, 1.000 y 2.000 Hz;
- 200 realizaciones por configuración;
- cinco semillas independientes: 20261119–20261123;
- baseline de 0,5 V;
- subida de 6 ms y decaimiento de 30 ms;
- ADC ideal de 12 bits y 3,3 V;
- umbral relativo de 0,10 V;
- fracción CFD de 0,50;
- fase del pulso aleatoria dentro de un período de muestreo;
- semillas reproducibles registradas en el manifiesto.

En total se generaron 27.000 formas de onda. Los tres métodos produjeron 81.000
intentos de estimación. La búsqueda de cruces comienza después de la región
reservada para estimar la línea base, para no confundir una fluctuación previa
con el pulso estudiado.

La latencia informada es:

\[
\Delta t = t_{\mathrm{estimado}}-t_0.
\]

No debe interpretarse como error respecto de una llegada experimental
calibrada: cada estimador responde a una característica temporal diferente.

## Reproducción

Desde la raíz del repositorio:

```sh
python analysis/study_waveform_timing.py \
  --output-dir results/waveform_timing_otra_corrida \
  --trials 200
python -m unittest tests.test_waveform_features \
  tests.test_study_waveform_timing -v
```

El código principal está en:

- `analysis/waveform_features.py`;
- `analysis/study_waveform_timing.py`.

La configuración y los hashes de la ejecución documentada están en
[`data/waveform_timing_20261119.json`](data/waveform_timing_20261119.json). El
resumen compacto de *time walk* se conserva en
[`data/waveform_timing_20261119.tsv`](data/waveform_timing_20261119.tsv).
Las formas de onda y tablas completas son productos regenerables ignorados por
Git.

## Resultados

Los tres métodos entregaron una estimación en todas las configuraciones
probadas. Esto caracteriza este conjunto sintético; no es una eficiencia de
detección.

Con ruido nulo, el *time walk* medio del CFD estuvo entre 0,0007 y 0,0038 ms
para las tres frecuencias. El umbral fijo presentó entre 1,89 y 2,26 ms porque una misma
tensión se cruza antes en pulsos de mayor amplitud. Con ruido de 30 mV, el CFD
presentó entre 0,34 y 0,55 ms, mientras el umbral fijo presentó entre 1,50 y
2,32 ms. Estos valores son medias entre las cinco semillas.

Para 1.000 Hz y ruido de 10 mV:

| Amplitud | Método | Latencia media entre semillas | Jitter medio dentro de semilla |
| ---: | --- | ---: | ---: |
| 0,2 V | CFD 50 % | 2,458 ms | 0,286 ms |
| 0,5 V | CFD 50 % | 2,337 ms | 0,106 ms |
| 1,0 V | CFD 50 % | 2,302 ms | 0,057 ms |
| 0,2 V | Umbral fijo | 2,285 ms | 0,253 ms |
| 0,5 V | Umbral fijo | 0,782 ms | 0,074 ms |
| 1,0 V | Umbral fijo | 0,318 ms | 0,077 ms |
| 0,2 V | Máximo | 11,155 ms | 2,089 ms |
| 0,5 V | Máximo | 10,923 ms | 1,352 ms |
| 1,0 V | Máximo | 10,841 ms | 0,950 ms |

En esa condición, los *time walk* medios entre semillas fueron:

- CFD: 0,156 ± 0,013 ms;
- tiempo del máximo: 0,322 ± 0,160 ms;
- umbral fijo: 1,966 ± 0,018 ms.

La diferencia marginal observada entre máximo y CFD en una sola semilla no se
mantuvo al repetir las realizaciones. Esta comprobación evita interpretar una
fluctuación específica como una ventaja general del método.

En esta configuración, el umbral fijo puede tener poca dispersión para pulsos
grandes, pero su latencia depende fuertemente de la amplitud. El CFD reduce esa
dependencia a costa de usar el máximo observado, cuya estimación también es
sensible al ruido. El tiempo del máximo caracteriza otra parte de la forma del
pulso y presenta una latencia mayor respecto del inicio; no es un reemplazo
directo de los otros dos métodos.

## Límites

- La forma de pulso es educativa y no representa todavía un fotodetector
  caracterizado.
- El CFD implementado es un cruce fraccional sobre el máximo del mismo pulso,
  no una electrónica CFD ni un filtro digital optimizado.
- Solo se estudiaron tres amplitudes, tres ruidos, tres frecuencias y una forma
  de pulso.
- No se modelan *pile-up*, deriva de baseline, jitter de reloj ni respuesta
  analógica completa.
- Las cinco semillas permiten observar variación entre realizaciones, pero no
  constituyen por sí solas una estimación universal de incertidumbre.
- No hubo saturación en las configuraciones elegidas.

## Continuación

El próximo paso científico es incorporar deriva de línea base y pulsos
superpuestos, comparar estimadores de baseline y relacionar cada forma de onda
con la tabla `truth/reco` existente. Solo después conviene evaluar una versión
muestra a muestra orientada a recursos limitados.

El desarrollo de esta extensión fue asistido por Codex. La autoría responsable
requiere que Alex revise el código, reproduzca el estudio y pueda explicar las
decisiones antes de presentarlo como dominio personal.

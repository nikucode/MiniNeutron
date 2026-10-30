# Primer experimento: conocer el trimmer y preparar la entrada ADC

Estado: guía preparada; mediciones y montaje físicos pendientes.
Se basa en el [inventario recuperado](inventory.md), sin asumir que existe una
placa de adquisición disponible. No es necesario comprar un sensor óptico todavía.

## 1. Qué puedes hacer hoy con el multímetro

Un trimmer es una resistencia ajustable con dos extremos y un cursor móvil.
El objetivo inicial es identificar esas tres conexiones y medir su resistencia,
no alimentarlo. «3296» identifica una familia; no significa 3296 ohmios ni fija
el patillaje de todas las variantes.

1. Trabaja con la pieza suelta, desconectada de alimentación y de otros circuitos.
2. Fotografía todas sus inscripciones y etiqueta provisionalmente las patas A/B/C.
3. Conecta las puntas del multímetro a COM y V/ohmios; selecciona resistencia,
   empezando por autorango o una escala alta. No uses el borne de corriente.
4. Mide A–B, A–C y B–C. Anota el valor y la escala. «OL» puede indicar que la escala
   es insuficiente o que no hay contacto; no equivale automáticamente a pieza dañada.
5. Gira suavemente el ajuste algunas vueltas y repite. No fuerces el mecanismo.
6. El par cuya resistencia permanece aproximadamente constante corresponde a
   los extremos; la tercera conexión es el cursor. Las otras dos resistencias
   deben variar de forma complementaria. Confirma con marcaje y hoja de datos.
7. Registra al menos tres posiciones. No atribuyas automáticamente al pin que
   parece estar en el centro la función de cursor.

Plantilla de registro (rellenar con mediciones, no con valores esperados):

| Posición del ajuste | A–B [ohmios] | A–C [ohmios] | B–C [ohmios] | Observación |
| --- | --- | --- | --- | --- |
| Inicial | | | | |
| Tras girar | | | | |
| Otra posición | | | | |

Fuente de identificación: [Bourns 3296](https://www.bourns.com/pdfs/3296.pdf).
Usarla como referencia de familia; verificar fabricante y variante de tu pieza.
Nunca medir resistencia en un circuito alimentado.

## 2. Qué falta para adquirir muestras

Conseguir prestados o confirmar una placa con ADC/USB, cable y protoboard.
La referencia preparada es **Uno R3 de 5 V**, no cualquier Arduino o Teensy.
Antes de conectar el trimmer, confirmar su resistencia y potencia admisible.
Para una primera prueba con Uno, un trimmer de alrededor de 10 kohm es una
referencia habitual; no dar ese valor por medido en tu componente.
La corriente entre extremos es aproximadamente Vcc/Rtotal y la potencia Vcc²/Rtotal:
un componente de resistencia muy baja no debe conectarse como si fuera de 10 kohm.

```text
Vcc de la placa ---- extremo del trimmer
                            |
                      cursor identificado ---- A0
                            |
GND de la placa ---- otro extremo
```

Esta disposición es un divisor de tensión. Sin carga apreciable:
`V_A0 ≈ Vcc × R(cursor–GND) / Rtotal`.
El ADC muestrea esa tensión; el puerto USB transmite los números al PC.

El firmware de `daq/hardware/optical_bench` ya lee A0: puede usarse para el
trimmer sin cambiar su protocolo. Su nombre conserva el origen del banco, pero
no presupone un sensor óptico. La impedancia del trimmer y el ADC pueden afectar
la medida real: el ejemplo ideal no demuestra precisión ni calibración.

Referencia: [Arduino Analog Read Serial](https://docs.arduino.cc/built-in-examples/basics/AnalogReadSerial/).
El ejemplo oficial ilustra lectura de un potenciómetro; nuestro firmware añade
secuencia y tiempo del dispositivo para detectar problemas de adquisición.

## 3. Experimento ya ejecutable sin placa

Con el entorno Python del repositorio activado:

```sh
python -m daq.demo_trimmer --output-dir results/trimmer_001
```

Usar una carpeta nueva. Se generan 3000 muestras sintéticas: cinco posiciones
ideales (10, 30, 50, 70 y 90 %), mantenidas un segundo, y retorno al 10 %.
Se reutiliza la importación estricta y el trigger ADC de MiniNeutron.

El programa comprueba que se conservan todos los códigos y que hay un evento
entre 3 y 5 s con los umbrales 3/2 V. Eso enseña la histéresis: pasar del 70 al
90 % no genera un evento nuevo porque el trigger sigue activo hasta el rearme.
Las cinco posiciones no deben confundirse con cinco pulsos.

`summary.json` informa posición ideal, código, voltaje reconstruido y diferencia
por redondeo. Es un chequeo de software y convención de escala, **no un error
medido del multímetro o del ADC real**. Se omiten ruido, tolerancia, carga, rebote
mecánico y dinámica del ADC. No se modela la velocidad de giro de una persona.

## 4. Cuando dispongamos de la placa

- Verificar conexiones sin alimentación y luego medir Vcc y A0.
- Usar cinco posiciones estables, lejos de los extremos de alimentación.
- Medir V_A0 con el multímetro y capturar cada posición en una carpeta distinta.
  Anotar la tensión de referencia usada; no asumir que USB entrega exactamente 5 V.
- Comparar media y dispersión ADC con la tensión del multímetro. Sin calibración
  e incertidumbre conocidas, llamarlo comparación funcional, no calibración trazable.
- Revisar huecos de secuencia y tiempos. Registrar condiciones y resultados,
  incluidos los que no concuerden con lo esperado.

La captura y el análisis usan los comandos de la [guía DAQ](optical_bench.md).
No elegir el umbral para que «salga bien»: primero guardar señal y mediciones,
luego justificar qué cruces se desea detectar.

## 5. LDR y soldadura después

La siguiente entrada será un divisor con la LDR y una resistencia elegida a
partir de sus valores medidos en luz/oscuridad. Primero debe caracterizarse;
no le atribuimos las prestaciones de un fototransistor ni de un trigger rápido.

Sólo tras comprobar el circuito en protoboard se transfiere a placa perforada:
conectores rotulados, puntos de prueba, inspección de soldaduras, continuidad
sin alimentación y repetición de mediciones. Usar el [registro de construcción](build_record_template.md).
No hay que soldar la pieza para realizar el paso 1 ni desarmar dispositivos.

## Resultado de referencia del software

Ejecución del 30 de octubre de 2026: 3000 códigos conservados, un evento entre
3 y 5 s, máximo error absoluto de la convención de redondeo ≈ 2.444 mV.
Los [valores y hashes](trimmer_synthetic_reference.json) son exclusivamente
sintéticos. Las 31 pruebas de regresión existentes pasaron después de este cambio.

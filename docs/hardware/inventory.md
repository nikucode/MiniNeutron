# Inventario recuperado del historial de MiniNeutron

Fuente: exportación de la conversación «Integrador 1», páginas 1294–1301.
Recuperado el 30 de octubre de 2026. Es un inventario histórico, no una nueva
inspección física ni una comprobación del funcionamiento de las piezas.

## Declarado directamente por el autor

En la página 1294 se mencionan kit completo de soldadura/cautín, lupa, cinta
aislante, pinzas para sujetar piezas pequeñas y multímetro, además de un teléfono
averiado. En la página 1301 se confirma que hay diodos y se indica que no hay
más de los elementos que se estaban buscando; se propone conseguir piezas en
el laboratorio universitario. El teléfono no forma parte del banco propuesto.

## Identificaciones registradas por el asistente anterior a partir de fotos

Estas referencias aparecen en las páginas 1298–1301. En esta recuperación se
leyó el texto de la conversación, sin volver a identificar las piezas en las
imágenes originales. Verificar marcaje, patillaje y estado antes de conectar.

- SN74HC595N.
- Optoacoplador 4N35.
- Trimmer multivueltas marcado 3296; resistencia nominal pendiente de comprobar.
- Transistor 2N2222A.
- Capacitores electrolíticos de 10 uF/50 V y 100 uF/50 V.
- LDR/fotoresistencia.
- Buzzer piezoeléctrico.
- Resistencias, otros capacitores y LEDs, sin valores/referencias completos.

Las páginas 1295–1296 también describen cables, placas recuperadas de juguetes,
pequeños motores y un posible módulo de alimentación tipo MB102. Esa descripción
procedía de videos y era provisional; no considerar confirmado el modelo MB102,
su tensión de salida ni su funcionamiento.

## No confirmado como disponible

- Arduino, PIC, ESP32 u otra placa/microcontrolador para adquisición.
- Protoboard y placa perforada.
- Adaptador USB–serial/programador, si la placa elegida los requiere.
- Amplificadores operacionales y referencias exactas de reguladores.
- Fototransistor externo para el circuito óptico de referencia.
- Fuente de laboratorio u osciloscopio en casa: experiencia académica no implica
  disponibilidad personal.

Haber usado Arduino/PIC en proyectos anteriores no acredita tenerlos actualmente.
El 4N35 se registra como optoacoplador; no se da por disponible el sensor óptico
externo de la guía basándose en ese componente.

## Adaptación del siguiente montaje

1. Conservar el banco óptico como diseño de referencia, no como compra obligatoria.
2. Identificar y medir el trimmer y las resistencias; documentar componentes,
   valores y conexiones con el multímetro disponible.
3. Una vez conseguida la placa y un medio de montaje, empezar por una entrada
   analógica ajustable con el trimmer y confirmar adquisición/serial/CSV.
4. Evaluar después la LDR como entrada óptica lenta, con un circuito y pruebas
   adaptados a su respuesta. No atribuirle la respuesta temporal del fototransistor
   ni del fixture rectangular sintético.
5. Transferir el circuito probado a placa perforada y registrar la soldadura
   cuando se disponga del material y se haya validado el montaje.

El formato y análisis ya implementados pueden reutilizarse para señales de un
trimmer o LDR. Faltan la selección final de placa, el circuito adaptado y las
mediciones físicas; no se presentan como etapas realizadas.

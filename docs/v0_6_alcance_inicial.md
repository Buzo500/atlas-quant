# v0.6 · Primer contrato del laboratorio

**Ampliación vigente:** cuatro tareas posteriores implementan API/Laboratorio, CSV nativo EUR con evidencia, reserva temporal y benchmarks en `0.6.0-dev.1`. [Alcance, uso y validación](v0_6_laboratorio.md). Los límites anteriores son antecedentes.

11/09/2026. **Primer bloque implementado por autorización posterior:** contrato restringido, evaluador puro SMA 20/50 y casos de referencia/paridad. [Uso, semántica y límites](v0_6_evaluador.md). El usuario autoriza comenzar esta referencia al aceptar los cinco siguientes pasos; sustituye el estado anterior de «solo definición». Una nueva petición de continuar mientras no puede usar el portátil autoriza el siguiente bloque: [simulación económica EUR offline implementada](v0_6_simulacion.md). El adaptador de datos reales y la validación temporal siguen pendientes. McClellan continúa en STRAT-001, con datos de amplitud y reglas pendientes de concretar.

## Primera estrategia declarativa

Identificador propuesto `sma-cross-long-v1`. Un instrumento y una cotización EUR elegidos explícitamente por el usuario; precios diarios brutos, calendario y disponibilidad verificados, versiones congeladas. Primera prueba con un CSV sintético, seguido de un CSV propio contrastado. Sin conexión a proveedor o bróker como requisito.

- Parámetros iniciales: media simple rápida 20, lenta 50; exigir enteros `2 <= rápida < lenta <= 250`. Se calcula sobre cierres de sesiones consecutivas válidas, sin rellenar huecos.
- Estado inicial fuera del mercado. Se consumen 50 cierres de calentamiento. La primera comprobación de **cruce** requiere 51 cierres: hacen falta las dos medias de la sesión actual y de la anterior. Estar por encima al terminar el calentamiento no se considera un cruce inventado.
- Entrada: rápida anterior ≤ lenta anterior y rápida actual > lenta actual. Salida: rápida anterior ≥ lenta anterior y rápida actual < lenta actual. Igualdad actual sin cruce mantiene el estado anterior. Sin cortos ni apalancamiento.
- Salida del evaluador: intención de exposición larga del 100 % del **presupuesto de esa estrategia**, o 0 %. Es un objetivo de instrumento; no una orden ni 100 % de la cartera completa. Construcción de cartera y riesgo aplican los límites globales; un objetivo incompatible se rechaza con causa, no se relajan los límites.
- La decisión solo usa barras cerradas y disponibles en `decision_at`. Ejecución simulada, como pronto, en la apertura de la siguiente sesión declarada, estrictamente posterior a la decisión. Si el dato llegó después de esa apertura o falta su precio, la intención expira sin fill; se registra el motivo. No ejecutar al cierre que produjo la señal ni reutilizar una intención dos veces.
- Un hueco abierto o dato no acreditado bloquea la evaluación y reinicia el calentamiento tras el hueco; no genera una salida artificial. El estado de exposición no cambia por un dato ausente; el riesgo registra el bloqueo y puede vetar nuevas compras. Política y motivo visibles.
- Primera candidata sin eventos corporativos dentro del tramo. Split o dividendo conocido exige un tratamiento declarado antes de admitir ese tramo; no comparar precios ajustados contra libro bruto. Es una restricción del caso de referencia, no una promesa de cobertura global.

## Límites y contratos entre módulos

Especificación validada con campos enumerados y sin código arbitrario: identidad/versión de estrategia, parámetros, instrumentos, fuentes, políticas temporales y de ejecución. No `eval`, Python libre, red, disco ni llamadas a modelos desde la regla. JSON canónico y huella; versión del evaluador, código, datos y costes forman parte del experimento.

Una función de evaluación compartida consume especificación, estado previo y observaciones disponibles. Devuelve estado nuevo y cero o una intención con fecha, motivo y clave idempotente. Mismo resultado en replay por lotes y recepción incremental, también tras guardar/recuperar un checkpoint. Mantener módulos separados en el monolito; no copiar el motor contable ni crear microservicios.

El simulador convierte objetivos a cantidades con lotes configurados, redondeo conservador, comisiones fijas/proporcionales y deslizamiento declarado. Cobra costes en el fill simulado y comprueba efectivo/posición antes del commit atómico. El libro nativo y el evaluador de riesgo existentes siguen siendo la autoridad económica. La ejecución diaria inicial es una simplificación declarada; un OHLC no permite reconstruir la secuencia intradía ni simular límites con prioridad de cola.

## Validación inicial propuesta

1. Casos pequeños calculados a mano: calentamiento 50/51, igualdad, cruce, salida, sin cruce inicial, duplicado, hueco, llegada tardía y siguiente apertura ausente. Cambiar una barra futura no cambia decisiones anteriores.
2. Paridad exacta entre replay e incremental: mismas intenciones, estados y claves; orden temporal, reinicio y repetición de eventos no duplican efectos.
3. Simulación económica de referencia EUR: efectivo más posiciones y costes conservados, sin sobregiro, ventas sin cortos y rechazo de objetivos fuera de límites. Recuperación idéntica del informe y su evidencia.
4. Protocolo temporal congelado antes de ver el resultado: por ejemplo, 500 sesiones válidas, 400 de desarrollo y las 100 finales reservadas. El calentamiento puede usar el pasado anterior a cada tramo; no los resultados del tramo reservado para seleccionar parámetros. Si se abre el reservado y se retoca la regla, se registra como consumido y se necesita otro periodo para evaluación independiente.
5. Comparación declarada con permanecer en efectivo y buy-and-hold bajo las mismas fechas, capital y costes. Sensibilidad de parámetros solo en desarrollo; conservar intentos negativos y cantidad de variantes ensayadas. No convertir significación o rentabilidad histórica en autorización operativa.

La primera autorización cubría **contrato restringido + evaluador puro + casos de referencia/paridad**. La petición posterior «sigue desarrollando lo siguiente» amplía al simulador económico offline, ya implementado sobre datos ficticios explícitos. Siguen pendientes adaptador de datos reales/caso de uso persistente, protocolo temporal y registro de candidatas. Esto no declara walk-forward, Monte Carlo, memoria de IA o LaTeX implementados.

## Decisiones posteriores

SMA 20/50 se usa como primera referencia sintética autorizada. Queda elegir CSV real e instrumento, fijar presupuesto/lotes/costes del caso y el protocolo temporal antes de optimizar. No necesita claves, GPU ni gasto en API. Paper externo y OMS/mandatos siguen en v0.7; automatización real en v1.3. El ensayo de 48 horas, operaciones personales, móvil y ejecución remota permanecen aplazados.

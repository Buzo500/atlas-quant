# v0.6 · Primer bloque del evaluador SMA

11/09/2026. El usuario autoriza los cinco siguientes pasos, incluido **comenzar SMA 20/50 con contrato restringido, evaluador puro y pruebas de paridad**. Sustituye la restricción anterior de «solo definición». Desarrollo en `codex/v0.6-evaluador`, separado de la PR #12 de v0.5.

## Alcance implementado

Módulos `strategy_spec.py` y `strategy_evaluator.py`, versión semántica `sma-cross-evaluator-v1`. Contratos Pydantic estrictos, inmutables y sin campos adicionales. Un instrumento, cotización EUR, fuente/versión/huella, base bruta acreditada y calendario explícito con mercado, zona y aperturas/cierres. Parámetros enteros `2 <= fast < slow <= 250`; referencia 20/50.

La verificación de evidencia es una **declaración del límite de datos**. El módulo comprueba estructura, identidad de contexto y tiempo; no consulta ni certifica un proveedor. El futuro caso de uso deberá contrastar la huella con la fuente congelada y admitir sus calendarios/eventos antes de construir la especificación. Las etiquetas sintéticas no acreditan datos reales.

`evaluate(spec, state, observation)` es una transición pura. `replay` la llama para cada observación; no hay otra implementación de la regla por lotes. Los cierres se aceptan como cadenas decimales positivas, máximo doce dígitos enteros y doce decimales. La comparación de medias usa enteros escalados y productos cruzados, sin redondeo de medias ni dependencia del contexto Decimal del proceso.

- Cincuenta cierres calientan SMA20/50; el primer cruce requiere el 51. Estar inicialmente por encima no inventa una entrada. Igualdad actual mantiene el objetivo.
- Entrada por cruce ascendente y salida por descendente. El objetivo es 0 o 100 % del **presupuesto de la estrategia**. `target_weight` es el estado lógico de la regla, no una posición realmente ejecutada ni una asignación global de cartera.
- Datos no cerrados o todavía no disponibles devuelven `waiting` sin consumir la sesión. La llegada posterior puede evaluarse con un reloj explícito; no modifica las decisiones anteriores.
- Una sesión omitida se detecta por el índice del calendario. Un hueco o dato sin verificar bloquea la evaluación, reinicia el calentamiento y conserva el objetivo lógico. Una barra válida recibida después de un salto es la primera del nuevo calentamiento.
- Un evento corporativo detectado deja el estado bloqueado incluso si llegan más precios: resolverlo exige una nueva fuente/especificación y replay explícito. No basta esperar otras cincuenta sesiones.
- Las intenciones tienen huella de contexto, prefijo de observaciones, fecha, motivo y clave idempotente. Si la decisión llega a partir de la siguiente apertura, o no hay siguiente sesión declarada, nacen expiradas.
- `opening_eligibility` solo comprueba la oportunidad temporal: apertura exacta, precio disponible en ese instante, sin usar un precio futuro. No produce fills. `eligible` no es aprobación de riesgo ni consumo de una intención.
- Repetir la última observación idéntica no emite otra intención, incluso con un reloj posterior. Un evento más antiguo o una corrección de una sesión consumida causa conflicto; requiere replay desde un checkpoint anterior sobre la versión adecuada. No se guarda un registro ilimitado de eventos en memoria.
- Checkpoints JSON con formato, versión, contexto y checksum. Recuperación exacta; corrupción o cambio de parámetros/datos/calendario/evidencia se rechazan. El checksum detecta corrupción, no autentica documentos hostiles. Un checkpoint es dato local validado, nunca autorización operativa.

Límites: 20.000 sesiones declaradas, 100.000 observaciones por replay y ventana incremental de como máximo 250 cierres. No hay I/O, reloj global, ejecución de código ni modelos de IA dentro de la transición.

## Uso reproducible

Desde la raíz del proyecto, sin arrancar ATLAS ni introducir claves:

```powershell
.\.venv\Scripts\python.exe tools\run_sma_reference.py --output output\validation\v06-sma-reference.json
```

Genera un informe sintético con especificación, observaciones, decisiones, dos intenciones, checkpoint y hashes del código. El caso tiene 50 cierres a 100, luego 110, 90 y 80: entrada en la observación 51, igualdad en la 52 y salida en la 53. La recuperación del checkpoint entre todas las observaciones conserva exactamente el replay. No escribe SQLite ni añade datos a las carteras.

## Integración y pendientes

Esta entrega es un **núcleo de investigación utilizable desde Python y la referencia por CLI**. La interfaz y `/api/...` conservan v0.5.0-dev.3; no se cambia el esquema 5 ni hay nueva etiqueta de aplicación v0.6. Los tipos HTTP no cambian. El build canónico anterior sigue siendo válido.

El Laboratorio y los experimentos antiguos mantienen sus reglas y resultados: su cruce previo comprobaba nivel de medias, no este cruce con estado. No se sustituye silenciosamente. El siguiente caso de uso deberá adoptar este evaluador en ambos recorridos nuevos y conservar las políticas legacy.

Quedan fuera: adaptador de datasets reales, servicio persistente/API/editor, simulador económico de cantidades/lotes/costes, consumo transaccional de intenciones, validación fuera de muestra y registro de candidatas. El libro, riesgo y futura ejecución son los responsables de posiciones efectivas, límites y consumo exactamente una vez. No duplicar sus motores ni simular que existen reservas OMS.

McClellan, ensayo de 48 horas, movimientos personales, IA de pago, bróker, móvil/remoto y LaTeX permanecen aplazados. [Datos NVIDIA y evidencia pendiente](diagnostico_nvidia_20260911.md).

## Validación

53 pruebas específicas: referencias manuales 2/3 y 20/50, oráculo independiente con fracciones y cuatro pares de ventanas, paridad incremental con recuperación en cada paso, igualdad decimal exacta, pureza, anticipación de datos, huecos, eventos corporativos, orden/duplicados, expiración, contexto y corrupción. Referencia CLI ejecutada con dos intenciones y paridad correcta. Regresión completa: **861 Python y 91 subcasos**, 84,49 s; dos avisos de deprecación previos. Evidencia `output/validation/v06-python.log`. Contratos HTTP y manifiesto del build comprobados. La interfaz no cambia; la CI de v0.5 no valida este bloque posterior.

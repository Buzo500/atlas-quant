# Diagnóstico de API en D5/D6 · 10/09/2026

## Actualización posterior · descarga Yahoo validada

En el arranque habitual de `v0.5.0-dev.2`, a las 19:55:01 UTC del 10/09, el adaptador existente descarga y publica los dos históricos NVD.DE hasta el 09/09, con TLS verificado. Ambos avanzan a versión 2, añaden una sesión y conservan exactamente las versiones/barras anteriores. Carteras, libro y respuestas EUR siguen iguales a la copia previa. [Evidencia e identificadores](v0_5_planificacion.md). La sonda directa de las 19:27 recibió 429; es un antecedente distinto, no el resultado del adaptador. La validación acredita esta descarga, no disponibilidad futura o estabilidad prolongada.

## Corrección del transporte local · v0.5.0-dev.1

La autorización de cinco tareas permite corregir la API. Se sustituye el proxy de producción por transporte Node mantenido, con propietario único de los streams y destino fijo 127.0.0.1:8000. Se conservan rutas, cuerpos, controles y plazos del cliente, sin actualizar dependencias ni reintentar operaciones. El arranque usa el bucle Python original; el cambio experimental a Selector se descartó.

**Hallazgos reproducidos:**

1. El proxy anterior deja abierto upstream cuando el cliente cancela antes de cabeceras. Reproducción contra las funciones de vinext instaladas en `output/validation/proxy-cancellation-before.mjs`: el cliente cierra y upstream continúa abierto a 300 ms. Las regresiones nuevas cubren cancelación antes de cabeceras y durante el cuerpo.
2. Una primera corrección con `agent:false` también reproduce esperas. `e2e-b3cb45bbe5684474b3e2ad5e61606ed6`, correlación `proxy-41604-38`: ASGI finaliza en 15 ms; Node recibe cabeceras de 120.536 bytes pero solo 65.516 bytes de socket, sin pausa ni buffer pendiente, hasta el aborto a 10,3 s. Forzar cierre en el navegador tampoco lo corrige.
3. Transferencia TCP de 2 MiB sin ATLAS ni HTTP: 11/24 incompletas al cerrar inmediatamente el emisor; 24/24 completas cuando el receptor confirma antes del cierre. El caso también falla con Selector y fuera del aislamiento de Codex. No demuestra un defecto concreto de Python o de Windows; no se cambian ajustes del sistema.
4. Comparación Uvicorn → proxy → cliente con 40 respuestas de 2,1 MB: el transporte que pide `Connection: close` se atasca en la primera tanda de ocho (`output/validation/v05-proxy-before-large.log`); el transporte final recibe las 40 completas. Regresión permanente `backend/tests/test_proxy_transport.py`. Un prototipo previo con `http.server` tuvo una espera y posteriores tandas correctas; se conserva su registro y se valida finalmente contra Uvicorn, que es el servidor real.

**Implementación final:** un agente HTTP por petición pide mantener upstream abierto mientras se recibe el cuerpo completo. Se destruye al finalizar o cancelar; ninguna conexión se reutiliza en otra petición. Conserva el flujo nativo, las longitudes/codificaciones, errores y cookies. El plazo incluye el cuerpo; una respuesta truncada falla, nunca se presenta como completa. La conexión del navegador mantiene su comportamiento normal. [Ciclo de vida del agente en Node](https://nodejs.org/docs/latest-v24.x/api/http.html#agentdestroy).

**Evidencia local:** ocho pruebas Node (cancelaciones, 60 POST/GET, 24 respuestas de 2 MiB, errores, plazo y rutas); prueba Python/Uvicorn de 40 × 2,1 MB; suite completa `e2e-77fe4731a54d495d8249ed0b323f5189`, **19/19 en 1,3 min**, integridad/base ordinaria/limpieza correctas. Sondas: 727 respuestas API finalizadas, máximo 134,674 ms y cero cuerpos pendientes más de un segundo. El recorrido ampliado del editor pasa también en `e2e-fe9b6e29f6e84d838c821dcb865be3f2`. 739 Python + 91 subcasos en conjunto.

Esto acredita las correcciones y los recorridos citados; no equivale a haber realizado el ensayo de 48 horas ni a identificar retrospectivamente la causa de cada error histórico. CI y operación final se registran en continuidad. Sondas solo optativas sobre base aislada, sin cuerpos, consultas ni credenciales.

## Antecedentes anteriores a la corrección

## Actualización: espera original reproducida antes de ASGI

Durante D6 completo, `e2e-6df81e53a5f148e1a1ba9a1f36166d5b` reproduce la espera de 10 s: GET `/api/state`, `proxy-38548-52`, 16:05:58 UTC. Creación/envío de cabeceras upstream inmediato, `bodySent` a 10008,9 ms y aborto del cliente a 10015 ms con `UND_ERR_SOCKET`. No existe entrada ASGI con esa correlación. Reutiliza el socket del POST demo anterior, terminado en ~98 ms. La evidencia acota el fallo al envío/transporte previo al motor; no identifica la causa exacta ni acredita una reparación.

La siguiente suite `e2e-72c2b7425cbb4fa083222032ef47fa2a` pasa 19/19. Otro error de socket de ~5 s sigue asociado a cancelación anterior. La sonda optativa añade exclusivamente encuadre HTTP (content-length, transfer-encoding, connection, expect), cork y tamaño de cola: no cuerpos ni credenciales. No se modifican tiempos del producto ni dependencias. Incidencia abierta; una suite correcta no sustituye su diagnóstico.

## Ampliación posterior: consumo de cuerpo y aborto del cliente

Autorizada dentro de las cinco tareas de D6.1/D6.2. Se instrumentan las lecturas existentes (`fromWeb`, lectores y Body mixin), sin `tee`, lectura anticipada, contenido ni nuevos reintentos. El stream que entrega vinext no conserva la identidad del objeto `body` obtenido por fetch; se correlaciona mediante el contexto de petición y se declara `upstream_body_identity=false`. Se mide la entrega de ese stream, no se presupone que sea el objeto original. El contexto se guarda en WeakMap para poder observar después de un aborto sin retener peticiones finalizadas.

Primero se realizaron dos capturas dirigidas sobre D5: `e2e-c07c691f1fdf48bea068509708eb1950` (18/18, 1,1 min) y `e2e-92c5c213fa0c46f3b97ef82214547d3f` (3/3 D5, 16,4 s). Confirmaron abortos pero no asociaron consumidores por identidad; esa ausencia no acredita que el cuerpo no se consumiera. Se amplió la correlación por contexto antes de la captura útil siguiente.

**Validación de la aplicación D6.1/D6.2:** `e2e-aa269c16968c47c2b37c78e23289edff`, **18/18 E2E, 1,1 min**, integridad `ok`, base ordinaria intacta y puertos liberados. Registra 568 consumidores del stream de entrega y 568 finales/cierres, 1.083 entradas, 1.067 respuestas finalizadas y 16 abortos. Máximo de `/api/state` 125,620 ms (121 respuestas); precios 60,642 ms (35), calidad 45,620 ms (26). Un 502 al preparar el arranque corresponde a `ECONNREFUSED` antes de que el backend esté listo, no a la incidencia de diez segundos.

| Correlación | Aborto cliente | Final del cuerpo ASGI | Error upstream |
|---|---:|---:|---:|
| `proxy-2212-96` | 68,295 ms | 78,682 ms | `UND_ERR_SOCKET`, 5.095,834 ms |
| `proxy-2212-592` | 100,898 ms | 105,643 ms | `UND_ERR_SOCKET`, 5.118,093 ms |

Cada columna usa el reloj relativo de su etapa; UTC/correlación permiten ordenar los eventos. Los clientes ya habían abortado antes de recibir cabeceras. La primera versión del registro de entrega liberaba su contexto al cerrar el cliente: por ello no se interpreta la ausencia de consumidor en estas dos correlaciones como prueba de cuerpo abandonado. Se sustituyó por referencia débil, sin cambiar el producto.

**Comprobación final de la sonda:** `e2e-268f9c4f9e6d4e779a24fd1a1ee53252`, **3/3 D5, 16,3 s** y limpieza/integridad correctas. 232 respuestas fetch y 232 consumidores asociados; 224 finales y 225 cierres de cuerpo, ocho abortos. `proxy-29368-103` muestra cabeceras → consumidor → aborto → cierre del cliente → `ERR_STREAM_PREMATURE_CLOSE` (12,650 ms) → error/cierre del cuerpo. No se observó error tardío de cinco segundos ni espera visible de diez en este recorrido. No se infiere de la diferencia entre contadores un origen concreto de las cancelaciones restantes.

**Conclusión:** la sonda ahora distingue entrega completa y cuerpo interrumpido de un cliente que ya canceló. La causa de la demora original **continúa abierta**. No hay base para cambiar el proxy, sus dependencias o los tiempos de espera con esta evidencia. El arranque habitual no activa las sondas. El siguiente dato útil es una captura de la acción que vuelva a mostrar la espera, con su hora/correlación; no repetir suites indefinidamente.

Evidencia local: logs de los cuatro runs citados, `output/validation/d6-api-body-summary.json`, `d6-e2e-traced.log` y `d6-api-final-traced.log`. No contienen datos personales de cartera. La sonda de Yahoo se documenta por separado en [D6.1/D6.2](v0_4_d6_implementacion.md).

## Antecedente: primera captura D5

**La espera original de unos 10 segundos no se ha reproducido en esta captura y sigue abierta.** La nueva evidencia permite separar dos errores de socket asociados a lecturas abandonadas de una respuesta lenta del motor. No se ha corregido la aplicación, cambiado dependencias, ampliado tiempos ni añadido reintentos.

## Contexto y ejecución

El usuario autoriza diagnosticar la API, comprobar D5 en uso habitual, concretar D6 y preparar referencias. D5 publicado `v0.4.0-dev.4`, árbol de aplicación del squash `a91f077`; documentación posterior `a93bf8d`. Sobremesa Windows nativo. Antecedentes: [diagnóstico inicial](diagnostico_api_20260909.md) y fallos de precios/calidad/pago registrados en [continuidad](CONTINUIDAD.md).

Con ATLAS habitual detenido, una ejecución de la suite actual con las trazas optativas ya existentes:

```powershell
.\.venv\Scripts\python.exe tools/diagnostics/run_api_diagnostic.py --timeout 300
```

Ejecución `e2e-2df628fc57124fa1a4b6a9f8d09f92a7`, 13:47:32–13:48:40 UTC. **18/18 E2E correctos en 1,1 min**. El límite 300 s corresponde al supervisor de diagnóstico, no cambia los límites de petición, comprobación o test. Sin reintentos ni ensayo prolongado. Al terminar: código 0, integridad `ok`, base habitual intacta según huellas del harness, puertos liberados y procesos cerrados.

## Tiempos y errores observados

Las mediciones del proxy van desde la entrada hasta `finish`; no son latencias completas del navegador. ASGI mide el envío desde la aplicación, no acredita por sí solo la recepción del cliente.

| Grupo | Respuestas completadas | p95 | Máximo |
|---|---:|---:|---:|
| `/api/state` en proxy | 105 | 76,678 ms | 134,168 ms |
| Rutas de precios en proxy | 35 | 35,748 ms | 62,287 ms |
| Rutas de calidad en proxy | 26 | 38,947 ms | 43,454 ms |
| Aplicación ASGI, todas las peticiones trazadas | 557 | 84,367 ms | 127,273 ms |

Proxy: 1.057 entradas de todas las rutas, 1.044 finalizadas; 1.037 con 200, cinco con 201, una con 409 y una con 422. Las respuestas 409/422 forman parte de recorridos que comprueban rechazos; no hubo `finish` 502 en esta captura. Trece cierres de respuesta sin finalizar. Cuatro errores de transporte hacia el motor: los dos sockets de la tabla y dos `ERR_STREAM_PREMATURE_CLOSE` de ~10 ms. Ningún evento de retraso del bucle registrado por las sondas (umbral 100 ms).

| Correlación | Cierre de respuesta al cliente sin finalizar | Envío ASGI completo | Error posterior de upstream |
|---|---:|---:|---:|
| `proxy-28044-93` | 64,647 ms | 68,004 ms | `UND_ERR_SOCKET`, 5.074,109 ms |
| `proxy-28044-578` | 71,370 ms | 87,144 ms | `UND_ERR_SOCKET`, 5.108,473 ms |

Ambas son GET de la misma cartera sintética. El cierre del lado cliente ocurre antes de las cabeceras upstream (69,183 y 96,372 ms desde creación de la petición upstream); ASGI envía el cuerpo en menos de 90 ms. El error aparece unos cinco segundos después. **Estos dos errores no corresponden a un cliente que siguiera esperando diez segundos ni a cinco segundos de cómputo ASGI.** Los identificadores permiten demostrar esa separación; la mera presencia de `UND_ERR_SOCKET` en un log no la permitía.

Los otros errores son `proxy-28044-806` (lectura de libro; ASGI 4,361 ms) y `proxy-28044-844` (derechos; ASGI 6,324 ms). Sus respuestas también cierran sin finalizar; por el orden/timing de las trazas no se atribuye una causa exacta del cierre. No se observó aquí la demora original.

**Hipótesis acotada:** el cierre de lecturas por cambios/navegación puede dejar una respuesta upstream sin consumir hasta el cierre de la conexión. La cronología es compatible con ello; no demuestra qué componente inició la cancelación ni que esa situación cause la intermitencia anterior. No justificaría por sí sola una actualización del proxy o sus dependencias.

## Decisión y siguiente captura útil

Mantener la incidencia de latencia abierta. Esta ejecución cubre los nuevos recorridos D5 que no estaban en la captura inicial; no repetir bucles genéricos indefinidamente ni presentar una suite correcta como reparación.

Si reaparece una espera visible, conservar acción, hora, run y correlación. Clasificar por separado: envío al motor, cabeceras, final del cuerpo ASGI, entrega del cuerpo en proxy y cierre/aborto del cliente. Una siguiente sonda dirigida debe distinguir cliente aún esperando de cliente que ya canceló, y medir consumo/cancelación de cuerpo; no incluir cuerpos, claves ni archivos personales. El diagnóstico optativo solo se activa sobre una nueva base aislada. El arranque habitual mantiene trazas desactivadas.

No hay hallazgo que permita cerrar la causa original. Tampoco hay evidencia de corrupción en esta captura. El ensayo de 48 horas, seguimiento automático y nueva CI remota siguen sin iniciarse.

## Evidencia local

- `var/validation/e2e-2df628fc57124fa1a4b6a9f8d09f92a7/{frontend.log,backend.log,playwright.log,run.json}`.
- `output/validation/d5-api-diagnostic-20260910.log`.
- `output/validation/d5-api-diagnostic-summary-20260910.json`: percentiles por rango más las cuatro correlaciones completas.

Logs e identificadores de fixtures son locales y quedan fuera de Git. Este documento conserva la conclusión verificable para otro equipo. La [comprobación posterior en uso normal](comprobacion_d5_20260910.md) usa otra ejecución; no confundirla con la base E2E ni atribuir una nueva validación física del escalado.

## Cierre de D7/D8: transporte todavía abierto

La primera CI D7/D8 (34506888529) falló una lectura real de precios D3 mediante proxy con `ECONNRESET`. El fallo D7 separado era un remontaje del panel por auditoría y claves duplicadas; está corregido. La segunda CI 34509155203 pasa 19/19 E2E sin cambios de transporte, reintentos o ampliación de tiempos. No permite declarar reparada la incidencia de red.

Nueva captura local `e2e-08ce8cbf7a7244b08809830f5119639f`: 19/19, respuestas proxy finalizadas máximo 170,18 ms. `proxy-32412-104` y `proxy-32412-609`: cliente aborta en 74,07/80,51 ms; ASGI termina cuerpo en 94,63/110,51 ms; error upstream después de 5101,48/5137,30 ms. Son cancelaciones anteriores al error, no clientes esperando cinco segundos. Evidencia `output/validation/d8-proxy-ci-fix.json`. Falta capturar el `ECONNRESET` visible con trazas equivalentes y probar su causa; no atribuirlo sin evidencia al cálculo contable.

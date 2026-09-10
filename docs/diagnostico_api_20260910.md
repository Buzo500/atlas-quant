# Diagnóstico de API en D5 · 10/09/2026

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

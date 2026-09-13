# Diagnóstico API y recursos TCP · 13/09/2026

Autorizado junto con aceptación del PDF, publicación dev.8 y dos definiciones.
No se cambia el transporte del producto ni se amplían timeouts o reintentos.

## Hallazgo sobre el fallo D3

La traza conservada de `e2e-57412c0d68d046338ba0a7bafc488e55`, prueba D3,
registra el fallo del recurso `/_next/static/chunks/app-elements-H_Dr48wG.js`:
`net::ERR_NO_BUFFER_SPACE`, estado -1, unos 24 ms desde la petición.
El navegador no llega a emitir consultas API. Las consultas de comprobación
del contexto Playwright sí terminan: health 200 en 10,86 ms, state 200 en 42,65 ms.
La espera posterior de «Motor conectado» no mide latencia ASGI: falta JavaScript.

Registro System de Windows, proveedor **Tcpip**, evento **4231**, registro **57153**,
UTC **2026-09-13T17:47:56.0708076Z**: no se pudo asignar un puerto efímero porque
todos los puertos TCP globales estaban en uso. La petición fallida se inició a
17:47:56.050Z. La coincidencia temporal y ambos errores explican este fallo de
carga por falta de recursos TCP. No identifican al proceso que agotó los puertos.

[Evidencia mínima conservada](evidence/windows-tcp-20260913.json): campos del
evento, error del recurso y SHA-256 de ambas trazas; sin cuerpos, claves o consultas.

[Chromium](https://chromium.googlesource.com/chromium/src/net/+/285728c206d899dd545dbe0b77d473594bce51f7)
relaciona WSAENOBUFS con ese código. [Microsoft](https://learn.microsoft.com/en-us/troubleshoot/windows-client/networking/tcp-ip-port-exhaustion-troubleshooting)
incluye el evento 4231 en el diagnóstico de agotamiento y advierte que contar
TIME_WAIT por sí solo no basta. No se modifica registro, rango, firewall o pila TCP.

Comprobación posterior de solo lectura: rango IPv4 TCP 49152–65535 (16.384 puertos).
Netstat: 133 TIME_WAIT totales; 68 loopback y 102 puertos locales loopback distintos.
Esto describe el momento de la consulta, no reconstruye el estado del fallo.

## D4: conservar la distinción

La prueba D4 del mismo run registra un timeout real de APIRequestContext en
`GET /api/state` tras 10 segundos. También hay varias peticiones del navegador
de aproximadamente diez segundos. No dispone de correlación proxy/ASGI para
ese intento: el agotamiento del mismo episodio es una hipótesis sustentada,
pero no queda demostrada como causa de cada petición ni de incidentes anteriores.
Algunos campos HAR asignan tiempo a SSL en HTTP: no interpretarlos como TLS real.

Por tanto, **D3 queda localizado; D4 y la incidencia API histórica siguen abiertas**.
No usar el arreglo de reemplazo JSON de dev.8 como explicación de estos sockets.

## Captura y reproducción acotada

La captura opcional ahora observa también recursos estáticos, tipo de recurso y
códigos canónicos `net::ERR_*` de `requestfailed`. Antes solo observaba `/api/`.
No imprime consultas, cuerpos, credenciales ni descripciones arbitrarias de error.
El informe correlacionado reconoce NO_BUFFER_SPACE sin atribuirlo a ASGI.
Tres regresiones frontend y una Python comprueban esa evidencia y sus límites.
No se alteran respuestas, timeout de 10 s, número de workers o reintentos E2E.

Un primer filtro `D3:|D4:` en base vacía pasó D3 y falló D4 porque este último
presuponía una cartera creada por los recorridos anteriores. Run
`e2e-6c026696dbce4ed19b845ba57b15b449`; fallo de precondición del filtro, no de API.
Se conserva y se ejecuta la suite completa con sus preparaciones existentes.
Para aislar D4 en el futuro, incluir primero el recorrido que carga demostración.

La comprobación final se realiza sin otra regresión local concurrente. No prueba
que pytest fuera el consumidor de puertos ni que serializar elimine toda incidencia.
La CI ya ejecuta sus fases secuencialmente. Ninguna prueba usa la base habitual.

Resultado local final: 25/25 E2E, run `e2e-6ced188b297e41e3add95b36d5e84145`,
1.887 grupos y 78 incidencias cortas, ninguna ≥1 s. Base habitual intacta y
servidores aislados detenidos correctamente.

CI 34774872432 correcta sobre `2091ea1`: 25/25 E2E, run
`e2e-334f3ec90502429eb43b1c3c639b65ec`. Captura de 1.910 grupos y 73 incidencias,
23 ≥1 s (8 API, 15 estáticos), máximo 1.547,308 ms. Veintiuna lentas completan
la lectura del cliente; dos peticiones de cartera muestran cierre previo del proxy
y fin de envío ASGI posterior. Sin timeout de 10 s ni NO_BUFFER_SPACE en esta
ejecución. Son observaciones de etapas, no una nueva causa demostrada. Informe
correlacionado sin truncar; las colas adicionales de servidor sí están truncadas.
[Publicación, cuota y verificación](publicacion_v06_dev8.md).

## Siguiente captura si reaparece

Conservar el instante UTC y los tres niveles de la petición. En ese momento,
leer eventos 4227/4231 y distribución por estado/PID con `netstat -anoq`, incluyendo
BOUND; guardar únicamente agregados necesarios. Identificar primero el consumidor
antes de cambiar política de conexiones. No cerrar procesos ajenos ni ampliar
rangos como sustituto del diagnóstico. La captura ampliada queda en la CI manual.

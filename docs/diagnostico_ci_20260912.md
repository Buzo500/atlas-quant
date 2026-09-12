# Diagnóstico del servidor E2E · 12/09/2026

El usuario autoriza los tres primeros pasos: diagnosticar la pérdida del servidor,
corregir la causa con regresión y repetir CI gratuita. Rama `codex/v0.6-evaluador`,
dev.4 y esquema 5 conservados. No incluye revisión manual, PR, fusión o etiqueta.

Antecedente: [CI 34610747174](https://github.com/Buzo500/atlas-quant/actions/runs/34610747174)
abortó después de 14 recorridos sin retener el código de salida ni stderr del
servidor. [Evidencia anterior](diagnostico_api_20260911.md).

Primera ampliación: la excepción de propiedad captura PID creado, propietario
del listener, pertenencia al grupo y código de salida antes de la limpieza.
Los controles y abortos se conservan. La salida final incluye códigos de ambos
servidores y parada forzada; el wrapper retiene hasta 16 KiB de cola por servidor,
omitiendo trazas JSON ya incluidas en el informe. También captura fallos previos
al arranque de Playwright. Un error al generar evidencia no sustituye el resultado.
Los logs provienen exclusivamente del entorno E2E aislado sin credenciales.

Validación dirigida: 33 pruebas de aislamiento/informe correctas, incluidas seis
regresiones nuevas. E2E completo local `e2e-4237f2b2c12d447b81722b70b3ebae90`:
23/23 en 1,7 min; códigos backend/frontend 0, integridad correcta, sin parada
forzada, puertos liberados y base habitual intacta. No reproduce el fallo remoto.
Motor y frontend habituales estaban detenidos antes de editar; no se arrancan.

La [CI de diagnóstico 34690769777](https://github.com/Buzo500/atlas-quant/actions/runs/34690769777)
pasó sobre `647be92`: 1.010 Python + 91 subcasos, 322 frontend, ocho Node,
23/23 E2E (4,5 min) y arranque/parada. Los dos servidores salieron con código 0.
Usaba todavía Node 24.15.0: el pase no acredita corregir su fallo intermitente.
Cuota previa 405/2.000 minutos, 0 USD facturables y bloqueo de pago comprobado.

## Cierre nativo reproducido y corrección de dependencia

El supervisor habitual conservó la salida inesperada del frontend a las 13:57:54 UTC
del 11/09: `3221226505` (`0xC0000409`), run `94f976d38cc343e390bcfcb3343f2e6f`.
Backend salió con 0 durante la parada posterior; stderr del frontend solo contiene
el arranque. No hay evento Application Error 1000 en la ventana consultada.

El [informe Node #63620](https://github.com/nodejs/node/issues/63620) describe un
cierre silencioso de Windows en conexiones HTTP cortas de Node 24.15.0 y no lo
reproduce con 24.16.0. Es evidencia externa, no una traza de nuestro proceso.
La sonda independiente `http_connection_probe.mjs` usa solo HTTP nativo a loopback,
sin ATLAS ni dependencias: el binario 24.15.0 termina con **el mismo 0xC0000409 a
los 13,407 s**, sin excepción JavaScript. Evidencia excluida de Git:
`output/validation/node-24.15-http-probe-confirm.json` y su log.

Con el mismo código inicial, Node 24.21.0 completa los 60 s sin cierre nativo,
pero la carga sin pausa provoca 27.227 errores de transporte y devuelve 1; **no se
presenta como una prueba correcta**. Se conserva ese código inicial en
`output/validation/http-connection-probe-initial.mjs`. La sonda final limita las
ráfagas a 64 y separa 500 ms por conexión de cada trabajador; informa códigos de
error y exige cero fallos, algún resultado y finalización normal. Con Node 24.21.0
completa 3.477 conexiones en 30 s sin errores. Se incluye como regresión en CI.

Corrección: Node **24.21.0 LTS**, versión oficial actual consultada en
[su entrega](https://nodejs.org/en/blog/release/v24.21.0), fijada en Actions.
`tools/node_runtime.py` selecciona el mismo ejecutable para instalación, build,
arranque y E2E, y rechaza Node 24.0–24.15 en Windows antes de arrancar procesos.
Mantiene la compatibilidad mínima anterior en las demás ramas; eso no amplía la
matriz de plataformas verificadas. No cambia conexiones, timeouts, políticas,
estrategias, contratos o esquema SQLite. [Instalación local](node_windows.md).

Esta reproducción identifica un fallo nativo de la dependencia usada por ATLAS.
Es compatible con el aborto remoto anterior, pero ese job no conservó código de
salida ni dump: no se atribuye con certeza el mismo fallo a la CI 34610747174.
La espera histórica de diez segundos sigue siendo una incidencia distinta abierta.

Otras comprobaciones acotadas: 23/23 E2E en dos CPU lógicas (2,3 min), run
`e2e-7295f8aa92594835b406bedff67a6ff9`, códigos 0 e integridad/limpieza correctas.
401 peticiones a servidor de prueba con cancelaciones y trazas conservaron la
lectura de salud; no reprodujeron el cierre. No se modifica la afinidad de otros
procesos ni se activa un monitor.

## Validación local de la corrección

Node 24.21.0: **1.024 Python + 91 subcasos, 322 frontend, ocho Node**, contratos,
TypeScript, lint y compilación canónica correctos. E2E completo
`e2e-995a316cf2534b0180eed3d6c5b381d7`: **23/23 en 1,7 min**, versión/ruta de Node
registradas, códigos backend/frontend 0, sin parada forzada, integridad `ok`,
puertos liberados y hashes de la base habitual sin cambios. Artefactos excluidos
de Git: `output/validation/node-24.21-*` y el directorio aislado de ese run.

La app habitual ya estaba detenida por el fallo anterior; no se arranca en este
turno ni se modifica su base. La instalación privada y el build están preparados
para el siguiente arranque.

## CI final de la corrección · correcta

Código `e1628b230a2f0e7b2630588361abe79fad21c108`, rama subida y verificada.
[CI 34691977950](https://github.com/Buzo500/atlas-quant/actions/runs/34691977950),
job 103548728567, `workflow_dispatch`, **correcta**, 12/09 11:47–11:59 UTC.
El log confirma Node **24.21.0**. Pasan **1.024 Python + 91 subcasos, 322 frontend,
ocho Node**, contratos, TypeScript, lint y build. La nueva sonda HTTP completa
**3.659 conexiones, cero errores**, en 30,361 s.

E2E `e2e-c9ea6dd9267e45caa68e867651e055f6`: **23/23 en 2,9 min**, códigos
backend/frontend 0, sin fallo de propietario ni parada forzada, integridad `ok`,
puertos liberados y base habitual del runner intacta. Arranque, recorrido sintético
por el proxy y parada posteriores también correctos. Esa comprobación de ciclo
completo pertenece al runner, no a una nueva ejecución habitual en este sobremesa.
Las colas de servidor están limitadas a 16 KiB y marcadas como truncadas;
los parámetros de consulta aparecen ocultos. Log local excluido de Git:
`output/validation/ci-34691977950.log`.

La CI anterior 34690769777 valida la instrumentación con Node 24.15.0;
la que acredita la corrección es **34691977950 sobre e1628b2**. El cierre posterior
solo modifica Markdown; no hay nueva PR, fusión o etiqueta. Se mantienen los
aplazamientos de portátil, PR #12, ensayo y movimientos personales.

Facturación comprobada con sesión de GitHub: **405 → 426,7 → 446,7 de 2.000
minutos** incluidos tras las dos ejecuciones de este turno. Lectura final:
2,68 USD brutos cubiertos por 2,68 USD de descuentos, **0 USD facturables**,
almacenamiento 0/0,5 GB. Antes de cada ejecución se comprobó presupuesto Actions
0 USD y `Stop usage: Yes`; no se modificó la facturación.

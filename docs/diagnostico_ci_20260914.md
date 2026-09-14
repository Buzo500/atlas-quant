# CI dev.9: plazo del recorrido D2

El usuario autoriza reproducir, diagnosticar, corregir, conservar evidencias y
subir/repetir la CI gratuita. Se conserva 0.6.0-dev.9 y esquema 5; no se cambia
el motor, la API, el método estadístico ni las carteras habituales.

## Ejecución original

[34821956088](https://github.com/Buzo500/atlas-quant/actions/runs/34821956088),
commit `12d262b742560cc5efa59548c72d8973dcb87e1d`, lanzada por el usuario.
Pasan 1.194 Python + 91 subcasos, 344 frontend y 24/25 E2E. D2 agota
el plazo total de 45 s mientras espera registrar un instrumento. El smoke
posterior de arranque/parada se omite; la limpieza del entorno E2E sí termina
con backend/frontend 0/0, sin parada forzada ni pérdida de propietario.

Los logs completos sitúan la navegación inicial a las 08:26:55.634 UTC y la
última vuelta a Datos alrededor de las 08:27:35.751: aproximadamente 40 s después.
No aparece un POST `/api/catalog/instruments` en la captura del cliente.
Para `client-4556-594`, GET catálogo, el cliente observa 8.207 ms, pero el
proxy tarda 6,085 ms desde su recepción y ASGI 3,985 ms hasta enviar el cuerpo.
La mayor espera ocurre antes de recibir la petición en el proxy, no calculando
el catálogo. Esto no identifica la causa de esa espera ni prueba un fallo del
registro. La traza/captura de Playwright no se había publicado como artefacto.
TCP: 39 muestras, pico 792 sockets, sin eventos 4227/4231; no acredita saturación.

## Reproducción y corrección acotada

- `e2e-4c01d06feb494edcb9506634a029f2e2`: fallo local distinto al consultar
  `/api/state` después de crear demo; timeout de 10 s. Base intacta y limpieza correcta.
- `e2e-23c3da2d359e48b7945809576a826b2b`: D2 original correcto, 8,6 s.
- Un ensayo intermedio de instrumentación falló por usar una propiedad inexistente
  de TestInfo. Se corrigió el reloj local; no es una reproducción del fallo remoto.
- D2 instrumentado antes de separarlo: 8,8 s; demo 761 ms, importación 1.791 ms,
  vínculos 3.719 ms, histórico 3.902 ms, registro completado a los 4.623 ms.
- `e2e-e0140a74f80b4ac2afa4a5d33d3bf4bb`: el registro independiente sí responde;
  falla la lectura posterior GET catálogo a los 10 s. La captura muestra entrada
  en proxy a las 09:55:40.329 UTC y conexión upstream a las 09:55:50.339;
  ASGI responde en 5,523 ms. Se conserva como incidencia de transporte pendiente.

Se separa el registro de instrumentos en un test autónomo, sin depender de la
demo ni de la importación y modificación de vínculos del primer recorrido.
Se conservan sus aserciones de persistencia/unicidad, todas las comprobaciones
de libro/histórico del primero y sus tamaños 390/1.280/3.440 px. No se amplía el
timeout de 45 s ni se habilitan reintentos. La respuesta POST se espera junto
al clic, con límite propio de 10 s y validación previa del formulario.
Se registran tiempos de las fases para distinguir preparación, histórico y UI.
Esta corrección reduce el alcance excesivo del test; no declara resuelta la
latencia histórica de Windows ni garantiza que no pueda volver a fallar por ella.

El workflow conserva en caso de fallo E2E trazas, capturas e informes/logs de
la base sintética aislada, con retención de un día. Lista explícita de rutas;
no incluye bases SQLite, `.env`, datos habituales o archivos de otras tareas.
`actions/upload-artifact` v4 fijada al commit oficial
`ea165f8d65b6e75b540449e92b4886f43607fa02`.

## Presupuesto y validación

14/09: GitHub muestra 578,3/2.000 minutos, 0/0,5 GB y 0 USD facturables.
Actions mantiene presupuesto 0 USD y `Stop usage: Yes`. No se cambian ajustes.
TypeScript, contratos, lint del test y build canónico correctos.
Validación local final: **26/26 E2E**, sin reintentos ni omitidos, 109,33 s;
`e2e-74a8c849c2394b27a2752bd45948477f`. D2 cartera 6,626 s; registro 0,887 s.
Backend/frontend 0/0, sin parada forzada, integridad correcta, puertos liberados
y base habitual intacta. No se repite la suite Python/frontend local porque
solo se modifica un test y el workflow; la CI ejecutará la regresión completa.
## Primera CI de la corrección y segunda causa comprobada

Código `34322e02a492608c013585d5fcee7834e0c7a3ee` subido; CI
[34831025722](https://github.com/Buzo500/atlas-quant/actions/runs/34831025722)
fallida. **D2 pasa en 19,0 s y registro en 2,8 s**. Python 1.194 + 91 subcasos,
344 frontend, transporte Node, build, contratos, TypeScript y lint correctos.
El test de precios adaptables falla; luego el harness agota sus 300 s y corta
la suite (21 recorridos terminados correctamente, uno fallido y cuatro sin
resultado final). No existe informe Playwright final. Smoke omitido; base
conservada y puertos liberados, pero `forced_stop: true` para el runner E2E.

La subida de artefactos funciona: ID `10342209270`, 52 archivos, 8.531.955 bytes,
retención de un día; ZIP SHA-256
`cbf7176a4b4e6fec68f71a85bbf3be696f53020be51436fbc9a663a69cf5c57c`.
Descargado bajo `var/validation/ci-34831025722/`, sin incluirlo en Git.
La traza confirma que las aserciones de cuatro resoluciones pasan: etapas
16,220 s (3440), 5,504 s (1920), 11,430 s (1366), 3,985 s (390).
El cambio de activo y la aserción de su cierre también pasan: el timeout se
registra en la lectura final de la fuente original (línea 814 del test anterior),
que comprueba que no se han cambiado sus datos. Acciones Home/focus tardan 7,937 y
7,066 s respectivamente; no se demuestra un error de datos de las fichas.

Corrección adicional: parametrizar una prueba independiente por resolución,
conservando ambas velas, valores originales, teclado, captura, ausencia de
desbordamiento y cambio de activo en **cada** resolución. Mantener 45 s por
test y cero reintentos. La CI usa el parámetro ya existente `--timeout 600`
para el conjunto: 29 recorridos y una instalación remota más lenta ya no caben
de forma fiable en el presupuesto global local de cinco minutos. El default
local sigue en 300 s y el job mantiene su techo de 20 minutos.
Segunda validación local: **29/29**, sin reintentos ni omitidos, 112,88 s;
`e2e-2526395ba74b481f93ee591fce607d30`, backend/frontend 0/0, sin parada forzada,
base intacta y puertos liberados. Build canónico, TypeScript y lint correctos.
Antes de la segunda CI: 601,7/2.000 minutos incluidos y 0 USD facturables;
0/0,5 GB mostrado por GitHub. Se conserva el bloqueo de pago.
Segunda publicación: `371020e42187452a7eabf2bbffd33130169473f8`, CI
[34832891702](https://github.com/Buzo500/atlas-quant/actions/runs/34832891702)
fallida antes de E2E. Pasan 343/344 frontend: `corporate-panel.test.tsx:119`
consulta síncronamente la opción `Activo` después de abrir el selector y no
la encuentra. No es un fallo de los gráficos ni acredita su validación remota.
Se sustituye esa consulta por `findByRole`, que espera la aparición accesible
con el límite habitual de Testing Library, sin reintentar el clic ni cambiar
la lógica del formulario o sus aserciones de previsualización/invalidación.
La suite frontend completa local pasa: **344/344**, 42 archivos, 34,16 s.
Build canónico, TypeScript y lint correctos. Los E2E no se repiten localmente
tras este cambio exclusivo del test de componente: los 29/29 anteriores siguen
siendo la validación del mismo código de aplicación y recorridos de navegador.
Tercera publicación: pendiente en esta tarea.

Los archivos concurrentes de IA/riesgo y su documentación se conservan sin
incluirlos. Ensayo, portátil, PR #12 y datos personales siguen aplazados.

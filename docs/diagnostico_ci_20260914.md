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
La subida y el resultado remoto se consignarán después de verificarlos.

Los archivos concurrentes de IA/riesgo y su documentación se conservan sin
incluirlos. Ensayo, portátil, PR #12 y datos personales siguen aplazados.

# Revisión Windows durante dev.8 · 13/09/2026

## Escritura atómica del estado

Las regresiones reprodujeron dos rechazos de Windows (`WinError 5`) al sustituir
un JSON de estado mediante `os.replace`: uno en `summary.json` del monitor con
reloj ficticio y otro en `runtime.json` del lanzador. El segundo ocultaba el
código de salida del frontend que debía conservar la prueba.

Esto demuestra el fallo de reemplazo, no identifica al proceso que denegaba el
acceso. Puede producirse mientras un lector mantiene un handle incompatible;
no se atribuye al antivirus ni a una aplicación sin evidencia.

`tools/atlas_runtime.py` mantiene el temporal único, escritura/flush/fsync y
reemplazo atómico. Solo en Windows y para errores 5/32/33, repite **el mismo
reemplazo** con esperas 10/20/40/80/160 ms: seis intentos y 310 ms de espera
acumulada como máximo. No vuelve a serializar, ejecutar ni reintentar una acción
HTTP, contable o de bróker. El propietario de cada estado sigue serializando
sus escrituras mediante los bloqueos existentes.

Un error persistente u otro error de E/S se propaga; no se borra el estado
anterior ni se recurre a escritura parcial. El temporal se limpia al finalizar.
Seis regresiones específicas incluyen un lector real de Windows sin permiso de
compartir borrado, liberado antes de la sustitución; negativas para error
persistente y error ajeno al caso. Con lanzador/monitor: 37 pruebas correctas.

La primera regresión también invocó por error el Node global antiguo y reprodujo
su cierre `0xC0000409`. Las siguientes usan Node 24.21.0 portable ya fijado;
no se cambia el Node global ni se atribuye ese cierre al exportador LaTeX.

## Espera de API

Primera ejecución de navegador dev.8, `e2e-57412c0d68d046338ba0a7bafc488e55`:
23/25, dos timeouts de diez segundos al esperar conexión o `GET /api/state`
en recorridos antiguos D3/D4. LaTeX pasa. Coincidió con pruebas Python, pero
esa coincidencia no demuestra la causa.

Repetición con captura y sin regresión Python concurrente,
`e2e-d1de8648e2a14c6db79183952989401f`: 25/25 en 1,8 min, 1.887 grupos
correlacionados y 77 marcas de fallo/cancelación, todas por debajo de 190 ms;
ninguna espera marcada de un segundo. Cierre y limpieza correctos.

La incidencia histórica de API permanece abierta: hay síntomas observados y
una captura posterior sin reproducción, no una causa o corrección demostrada.
La [continuidad](CONTINUIDAD.md) recoge el pase final posterior a la corrección
atómica y los logs locales de cada intento.

Estas pruebas usan bases/relojes ficticios. **No se ha iniciado el ensayo real
de 48 horas ni se ha modificado la base habitual.**

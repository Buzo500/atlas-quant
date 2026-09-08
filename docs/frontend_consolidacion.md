# Consolidación del frontend

**Actualización posterior · rc.2, 08/09/2026:** [escalado físico 125 %/150 % comprobado](validacion_escalado_windows.md) en el monitor 3440 × 1440 de este sobremesa; restaurado el 100 % inicial. Los apartados siguientes conservan el trabajo y las pruebas de la revisión anterior. El ensayo de 48 horas sigue aplazado.

Trabajo del 8 de septiembre de 2026 sobre la interfaz crema y cobre. Mantiene las cinco secciones existentes y la versión **0.2.0-rc.1**. Refuerza los recorridos, la trazabilidad, los contratos y las pruebas; no inicia el ensayo de 48 horas ni declara v0.2 estable.

Este documento complementa [frontend_crema_cobre.md](frontend_crema_cobre.md). Las afirmaciones de aquella entrega sobre contratos y dependencias describen su alcance anterior: esta consolidación sí añade infraestructura de pruebas de frontend y amplía los contratos indicados a continuación.

## 1. Confirmación de movimientos vinculada a la previsualización

La previsualización de un CSV devuelve `preview_token`. Confirmar exige devolver ese token junto al mismo contenido. El motor calcula la precondición con el identificador y versión del conjunto, sus barras reales, los movimientos existentes y el CSV. Comprueba la coincidencia y guarda los movimientos dentro de una única transacción. Si otro cliente cambia los datos o el ledger, rechaza la confirmación y exige revisar de nuevo.

El token es una precondición de consistencia, no una credencial de autenticación. La ruta HTTP requiere revisión previa; las importaciones internas de confianza deben declarar expresamente cualquier excepción.

`features/data/ledger-import.tsx` separa ese recorrido del formulario general. Cambiar conjunto, versión o contenido invalida la previsualización visible. Las lecturas tardías de archivos y las respuestas de una confirmación desmontada no sustituyen el estado del nuevo contexto. Un envío pendiente bloquea otro envío; una confirmación fallida o de resultado incierto exige una nueva revisión. No se repiten escrituras automáticamente.

## 2. Identidad de las ejecuciones del Laboratorio

`POST /api/research` devuelve `execution`: identificador de ejecución, conjunto y nombre, versión, huella del manifiesto, activo, costes, periodo y fechas de inicio y finalización. La identidad se obtiene del snapshot utilizado por el cálculo y se incluye en la auditoría de investigación.

El Laboratorio conserva la configuración enviada mientras trabaja. Si después se cambia el conjunto, su versión, el activo o los costes, el resultado sigue identificando la ejecución original y aparece el aviso «Resultado de otra configuración». La respuesta del servidor determina los datos realmente utilizados; el formulario no atribuye sus valores actuales a un cálculo anterior.

Las investigaciones históricas sin este campo siguen siendo representables. Añadir trazabilidad a la comparación manual no convierte los experimentos anteriores en ejecuciones con metadatos que nunca guardaron.

## 3. Pruebas de interfaz y CI

Se incorpora Vitest con React Testing Library, `user-event` y jsdom. La configuración de pruebas no carga los plugins de producción de Sites, Cloudflare o Vinext. Los fixtures reproducen contratos del motor y el entorno de pruebas bloquea cualquier `fetch` no simulado expresamente.

Las pruebas cubren confirmación de movimientos, cambios de contexto, respuestas tardías, borradores y navegación, controles de experimentos, creación acotada sin IA, actualizaciones parciales de ajustes, formatos, curvas y paginación. Los tests de componentes no equivalen a comprobar distribución, pintura o accesibilidad completa en un navegador real; jsdom no calcula layout.

Desde la raíz:

```powershell
pnpm --dir frontend run test:run
pnpm --dir frontend run lint
pnpm --dir frontend exec tsc --noEmit
.\.venv\Scripts\python.exe tools\export_contracts.py --check
```

El workflow de Windows incluye las pruebas de frontend, Python, TypeScript, contratos, lint de la aplicación mantenida, compilación y un recorrido sintético. Se activa manualmente o mediante una etiqueta candidata `v*-rc.*`; no necesita secretos ni llamadas a proveedores de IA o mercado. **La configuración de CI no significa que esta revisión haya pasado CI remota.** Antes de publicar una etiqueta o lanzar el workflow hay que verificar cuota y bloqueo del gasto de GitHub Actions para mantener el presupuesto cero. No se autoriza consumo de pago implícitamente.

## 4. Lecturas, errores y concurrencia de controles

`shared/use-read.ts` asigna una secuencia a cada lectura y usa cancelación HTTP. Descarta éxitos y errores antiguos aunque el transporte termine después de recibir la cancelación. Cambiar de recurso nunca muestra como suyos los datos de la selección anterior. Un callback de refresco capturado antes de cambiar de expediente no cancela la lectura vigente.

Si falla una actualización del mismo recurso, se conserva su última respuesta correcta con el error y la fecha de consulta. `QueryStatus` distingue carga, actualización y error, y ofrece reintento de lectura. El estado de conexión no se deduce únicamente de haber recibido datos alguna vez. El sondeo espera a que termine la lectura vigente; un refresco manual también reinicia ese intervalo.

`shared/use-action.ts` impide solicitudes duplicadas por clics mientras una acción sigue pendiente. Las mutaciones no se reintentan automáticamente, ni un fallo de conexión se presenta como confirmación de éxito. Los errores de validación HTTP muestran ubicación y explicación sin serializar los campos `input` o `ctx` del error, que podrían contener CSV o hipótesis.

Los controles de experimentos consultan el estado canónico después de actuar. Se mantienen las restricciones de reanudar durante una operación activa o con una reserva de API pendiente.

**Ajustes aplica cambios parciales:** el interruptor envía solo `kill_switch`; guardar un límite envía solo `max_position_weight`. `SettingsInput` admite omisiones y la ruta utiliza `model_dump(exclude_unset=True)`; la transacción conserva los demás valores vigentes. Así, guardar un peso desde una pestaña atrasada no desactiva una parada aplicada por otra. Esto no implementa resolución de conflictos entre dos cambios concurrentes sobre el mismo campo.

## 5. Borradores y navegación

Los paneles permanecen montados al cambiar de pestaña. CSV, hipótesis, costes y selección de activo por conjunto se conservan durante esa navegación, sin volver a enviarlos. Los paneles ocultos se excluyen visualmente y del recorrido normal de foco; las consultas específicas de cartera y expediente se activan en su sección.

La URL conserva únicamente sección, conjunto y experimento mediante `tab`, `dataset` y `experiment`. Permite recuperar esas selecciones al recargar y navegar atrás. Los identificadores se validan y un conjunto inexistente produce un aviso.

**No hay persistencia de borradores después de recargar o cerrar la página.** No se guardan CSV, hipótesis, claves ni autorizaciones en la URL, `localStorage` o `sessionStorage`. La simulación automática de un experimento nuevo vuelve a estar desactivada tras recargar. La navegación no crea ni reanuda trabajos por sí sola.

## 6. Organización por funcionalidades

`app/page.tsx` coordina navegación, conjunto seleccionado y estado general. Las pantallas residen en `features/portfolio`, `features/research`, `features/experiments`, `features/data` y `features/settings`.

`shared/` reúne transporte de estado, acciones, navegación, formatos, selección de activos, formularios comunes, tablas y paginación. `components/atlas/curve.tsx` mantiene la representación de curvas. `components/ui/` conserva las primitivas visuales. `lib/api.ts` trata el transporte HTTP y `lib/api-types.ts` contiene los contratos generados.

El backend sigue siendo un monolito modular con un ejecutor por base. La extracción de paneles no introduce servicios distribuidos ni cambia la lógica financiera. Al cambiar contratos, regenerar con `tools/export_contracts.py` y ejecutar `--check`; no editar manualmente los tipos generados.

El manifiesto generado por `tools/build_frontend.py` incorpora `features/`, `shared/` y `test/`. Las regresiones del lanzador comprueban que añadir o modificar un módulo de esas carpetas invalida la compilación anterior.

## 7. Formatos y unidades

`shared/format.ts` reutiliza instancias de `Intl` con configuración `es-ES`. Distingue importes EUR, USD y gasto/reservas API en USD con cuatro decimales. Los porcentajes reciben ratios; Sharpe, cantidades y contadores se presentan como números con la precisión correspondiente.

Un cero sigue siendo un dato válido. `null` y `undefined` se muestran como ausencia; NaN e infinito, como «Dato no válido». No se sustituye un dato ausente por cero. Una métrica matemáticamente no definida puede conservar su etiqueta específica.

Las fechas civiles `YYYY-MM-DD` mantienen el día de sesión, sin conversión de zona. Los instantes requieren un offset y se muestran en **Europe/Madrid**, indicada en pantalla, con sus reglas de horario de verano. Los datos no se convierten de divisa al formatearlos. La cartera muestra también la fecha del precio utilizado y señala precios anteriores al último día del conjunto.

## 8. Contraste y alternativa a los gráficos

Las curvas incluyen eje vertical con unidades EUR, fechas, leyenda, título y descripción accesibles. Estrategia y benchmark se distinguen por color y trazo; no dependen solo del color. Se declara escala lineal y distribución horizontal por observaciones: la distancia entre puntos no representa proporcionalmente días naturales.

«Ver datos de la curva» abre una tabla de valores originales, con encabezados, región desplazable accesible por teclado y páginas de 50 observaciones. La tabla se monta al abrirla y no utiliza la reducción visual del SVG. Las series de un punto, ceros, valores negativos y datos inválidos tienen tratamiento explícito. Los identificadores de títulos y tablas son únicos entre curvas.

No se incorporan velas, zoom, indicadores, inspección avanzada del cursor ni otras funciones del backlog. La alternativa tabular y las pruebas automatizadas no constituyen por sí solas una certificación de accesibilidad.

## 9. Rendimiento y evidencia medible

Se limita el dibujo SVG mediante extremos por tramo, conservando primer y último punto y los índices horizontales originales. El dominio, las métricas y los datos accesibles siguen usando la serie completa. El recorrido de los datos continúa siendo lineal; no se reduce la información recibida del motor.

La medición local `output/validation/frontend_curve_bench.json` compara preparación y serialización reales de React con `renderToStaticMarkup`, viewport inicial de 640 × 280, un calentamiento y cinco muestras con GC antes de cada una:

| Observaciones | Mediana anterior | Mediana con reducción | HTML anterior | HTML con reducción |
| --- | ---: | ---: | ---: | ---: |
| 1.000 | 1,79 ms | 1,89 ms | 38.827 bytes | 16.337 bytes |
| 10.000 | 7,33 ms | 3,07 ms | 372.680 bytes | 17.908 bytes |
| 100.000 | 55,49 ms | 7,77 ms | 3.704.195 bytes | 17.774 bytes |

No hay mejora universal del tiempo para series pequeñas. Estas cifras miden **SSR**, no pintura, respuesta a clics, red o fluidez en el navegador.

`output/validation/frontend_panels_bench_before.json` conserva la línea base anterior a paginar: con 1.000 registros, los mínimos SSR fueron 86,72 ms en Agente y 54,94 ms en la tabla de posiciones, serializando todas las filas. Las medias presentan variación amplia; no deben utilizarse como una garantía de latencia. A partir de esa evidencia, el listado de experimentos y las tablas compartidas se paginan en bloques de 50. La selección de un experimento revela su página; cambiar de página no selecciona ni controla otro experimento. La paginación limita el DOM, pero mantiene el conjunto completo en memoria y no añade paginación al API.

Los benchmarks repetibles están en `components/atlas/curve.bench.tsx` y `test/panels.bench.tsx`. Desde `frontend`:

```powershell
node node_modules/vitest/vitest.mjs bench --config vitest.config.ts --run components/atlas/curve.bench.tsx --reporter=verbose
node node_modules/vitest/vitest.mjs bench --config vitest.config.ts --run test/panels.bench.tsx --reporter=verbose
```

La medición repetible de Vitest emplea otra metodología de calentamiento y repetición: no sustituir las medianas anteriores por sus medias. La evidencia final está en `output/validation/frontend_bench_final.json`, con diez mediciones y los archivos de benchmark ejecutados secuencialmente. Con 1.000 registros:

| Panel | Filas HTML antes → después, incluida cabecera | HTML antes → después | p75 SSR antes → después |
| --- | ---: | ---: | ---: |
| Experimentos | 1.001 → 51 | 2.264.999 → 118.317 bytes | 102,32 → 6,63 ms |
| Tabla de posiciones | 1.001 → 51 | 886.527 → 47.992 bytes | 59,21 → 3,02 ms |

Son medidas orientativas de serialización; el formateo inicial de filas de posiciones queda fuera del cronómetro y el recolector de memoria añade variabilidad. No se declara paginación del API ni capacidad ilimitada: el cliente todavía recibe los registros completos.

## Verificación de la entrega

Validación final en este sobremesa, Windows nativo, 08/09/2026:

- **421 pruebas del motor y 91 subtests**, 32,87 segundos; dos avisos previos de TestClient.
- **126 pruebas de interfaz en 14 archivos**, 12,49 segundos. TypeScript, lint de la aplicación mantenida y contratos generados correctos.
- Compilación y manifiesto generados/verificados con `tools/build_frontend.py`.
- **35 comprobaciones de tamaño**: cinco secciones en 3440×1440, 2752×1152, 2560×1440, 2293×960, 1920×1080, 1366×768 y 390×844. Sin desbordamiento horizontal global; un único panel visible por pestaña. Revisión visual de Laboratorio ultrapanorámico y Cartera estrecha; consola sin errores.
- Recorrido de navegador con base aislada: demo, cálculo del Laboratorio e identidad, cambio de costes y aviso, tabla accesible/paginación, CSV editado que retira confirmación, nueva revisión e importación, borradores entre pestañas, selección tras recarga y autorización automática desactivada, guardar peso manteniendo parada, pausa/reanudación/cancelación de un expediente desechable.

La base de esos recorridos es `var/validation/frontend-hardening-20260908/data`, con `run_worker=False` y sin claves. El expediente se configuró a una hora, se canceló inmediatamente y nunca se ejecutó: fue una prueba de controles, no un ensayo de duración. Los servidores de prueba terminaron con código 0.

Se arrancó después ATLAS normalmente con `Start-Atlas.ps1`. Integridad SQLite correcta y misma huella persistente/prefijo de auditoría que `backups/atlas-20260908T131709657852Z-125c578f`. Cartera original: NAV 25.118,66876 EUR, tres posiciones, conjunto y experimento conservados; parada activada y presupuesto/gasto/reserva cero. **Queda funcionando en http://127.0.0.1:3000/**. Abrir: `Abrir-ATLAS.cmd`; detener ambos servidores: `Detener-ATLAS.cmd`. Cerrar la pestaña no detiene el motor.

Evidencia local, excluida de Git: `frontend-hardening.json`, `frontend-hardening-backend.xml`, `frontend-hardening-ui-tests.json`, `frontend-hardening-viewports.json`, `frontend-hardening-preservation.json` y capturas `frontend-hardening-390.png`, `frontend-hardening-1920.png` y `frontend-hardening-main.png`, bajo `output/validation/`.

**CI posterior superada el 08/09/2026:** las fuentes y la corrección de pruebas están publicadas en `codex/fix-local-health-resources`; [ejecución 34241300060](https://github.com/Buzo500/atlas-quant/actions/runs/34241300060) sobre `3f1d990ac15c391e638302828d1a720d99d78003`. Pasan 421 pruebas Python, 91 subtests y 126 pruebas de interfaz, instalación limpia, build, TypeScript, contratos, lint, arranque y parada. El primer intento reveló plazos insuficientes en dos recorridos complejos y un posible cruce entre pruebas: se acotan las consultas por render, los workers según CPU y los plazos de esos recorridos, conservando las aserciones. Detalle en [candidata_v0_2.md](candidata_v0_2.md). La CI comprueba HTTP/proxy y datos sintéticos; las comprobaciones visuales corresponden al navegador local, no a GitHub.

Tras esa corrección se volvió a generar el manifiesto y arrancar ATLAS: ejecución `a0e040c188c1410d93449bdf4367e97a`, base habitual conservada y salud correcta. La documentación posterior registra el SHA validado sin modificar el producto. Presupuesto de API cero y ensayo de 48 horas aplazado.

Detener ATLAS antes de modificar código o reconstruir. Usar `tools/build_frontend.py` para generar el manifiesto requerido por el arranque diario; un build directo no lo sustituye. Las pruebas que escriban datos deben utilizar una base aislada. Comprobar la preservación de datos habituales antes de dar por terminada la actualización.

La validación de viewports CSS no equivale a probar el escalado físico de Windows: al cerrar esta revisión anterior quedaron pendientes las comprobaciones al 125 % y 150 %. La comprobación posterior de rc.2 se enlaza al inicio de este documento. El ensayo sostenido permanece aplazado. Presupuesto de API cero, sin claves nuevas, llamadas pagadas, bróker real, aprendizaje, móvil o acceso remoto.

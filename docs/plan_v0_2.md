# ATLAS Quant · Plan de v0.2

**Estado actual · 8 de septiembre de 2026:** candidata `0.2.0-rc.2` **en preparación**. La [PR #1](https://github.com/Buzo500/atlas-quant/pull/1) está fusionada en `master`, commit `e1f6e020a1d75a81bff97eefcbebe726d47bcdb3`. Este bloque añade recorridos de integración/E2E y correcciones de teclado, foco y anuncios accesibles. La nueva CI y la comprobación del escalado físico de Windows al 125 % y 150 % siguen pendientes. El ensayo de 48 horas y su seguimiento continúan aplazados; v0.2 no es estable.

La candidata `0.2.0-rc.1` y sus comprobaciones se conservan como evidencia histórica en [candidata_v0_2.md](candidata_v0_2.md). Las cifras de los bloques anteriores no certifican por sí solas las fuentes de rc.2.

**Cierre local previo a CI:** 446 pruebas Python y 91 subtests, 140 Vitest y cinco E2E con API real y Chromium superados; TypeScript, contratos, lint, `pip check` y compilación correctos. Se han corregido el foco, los anuncios por sondeo, la identificación de procesos E2E y el aislamiento antes de la colección de pytest. La base habitual conserva el contenido completo de la copia de referencia. El control automatizado de Windows bloqueó el cambio de escala; 125 %/150 % continúan sin validar y no se sustituyen por los 35 viewports CSS históricos. ATLAS y el entorno manual están detenidos antes del commit; la etiqueta rc.2 queda condicionada a su CI. Detalles e incidencias preservadas en el registro de candidata.

Fecha: 6 de septiembre de 2026. Estado: implementación inicial completada y probada localmente; cierre de v0.2 pendiente. Este documento define los criterios de aceptación; la evidencia ejecutada se recoge en la [auditoría](auditoria_v0_2.md).

**Consolidación del núcleo implementada:** CORE-001, controles concurrentes, contratos prioritarios y transacciones han sido corregidos y comprobados con 328 pruebas y 91 subtests. Garantías y deuda restante en [consolidacion_core.md](consolidacion_core.md). La revisión posterior `3f1d990` supera CI de Windows con 421 pruebas Python, 91 subtests y 126 pruebas de interfaz. H6 sigue pendiente, con el ensayo de 48 horas aplazado; la [revisión inicial](revision_core_arquitectura.md) se conserva como diagnóstico histórico.

## Objetivo y punto de partida

Hacer que la instalación local se pueda iniciar, detener, actualizar y recuperar con instrucciones reproducibles, conservando cartera, conjuntos, experimentos y controles. La prioridad actual procede de la [hoja de ruta](hoja_de_ruta.md).

Al comenzar este trabajo, la v0.1 estaba instalada y verificada en el sobremesa con Windows nativo, Python 3.14.4, Node 24.15.0 y pnpm 11.19.0. Tenía lanzadores PowerShell, dependencias fijadas, SQLite WAL, pruebas de motor/API y recuperación de experimentos interrumpidos; usaba el servidor de desarrollo y no disponía de backup automático. Las pruebas históricas están en [CONTINUIDAD](CONTINUIDAD.md). El estado operativo posterior está en la [guía de Windows](operacion_windows.md).

## Alcance

- Arranque/parada con instancia única, diagnóstico de dependencias y puertos, comprobación de salud y errores útiles; acceso directo como comodidad de instalación.
- Ejecución de la interfaz compilada y proxy local al motor, manteniendo servicios en loopback y claves fuera del proceso frontend.
- Copias automáticas consistentes de SQLite, con verificación, retención acotada y restauración controlada.
- Versión explícita del esquema, migraciones transaccionales y procedimiento de actualización con copia previa.
- Validación automática y documentación de instalación, actualización, recuperación, soporte y cambios de la entrega.

Se conservan demo y proveedor `none`, sin claves y con gasto cero. Quedan fuera gráficos nuevos, memoria/aprendizaje, descargas de modelos, conexión a bróker, órdenes reales, exposición de red y cambios en reglas de inversión. Un servicio Windows, autoinicio al encender y un instalador binario independiente no son requisitos de esta primera v0.2: se evaluarán después de estabilizar el lanzador y documentar las limitaciones.

## Hitos pequeños y verificables

Los hitos describen unidades de aceptación. H0–H4 tienen implementación y evidencia local; H5 cuenta con instalación independiente y [CI de Windows superada para la revisión anterior `3f1d990`](https://github.com/Buzo500/atlas-quant/actions/runs/34241300060). La CI de rc.2 todavía debe ejecutarse sobre sus fuentes identificadas. H6 continúa pendiente: el ensayo de 48 horas y su seguimiento están aplazados y v0.2 no se declara estable. Consultar la auditoría para los escenarios concretos comprobados y sus límites.

| Hito | Cambio concreto | Criterios de aceptación |
|---|---|---|
| **H0 · Auditoría y referencia** | Identificar versión base y estado Git; revisar lanzadores, almacenamiento, compilación y comprobaciones existentes; registrar defectos y decidir prioridad. | Cada defecto tiene un escenario reproducible o una limitación reconocida. Estado local y evidencia histórica diferenciados. No se sobrescriben cambios del usuario. |
| **H1 · Procesos y diagnóstico** | Validar versiones/comandos, puertos y configuración; registrar instancia y salud; controlar salida y limpieza de procesos propios. | Doble arranque no crea motores adicionales; un puerto ajeno se rechaza sin matar su proceso; un arranque fallido libera sus recursos; parada repetida es segura; errores indican causa y registro. La caída de un servidor se detecta y no deja una falsa apariencia de funcionamiento. |
| **H2 · Ejecución compilada** | Instalar con dependencias fijadas, compilar la interfaz y servir el artefacto local; separar el modo de desarrollo del arranque habitual. | Sin servidor de desarrollo en el recorrido normal; página, recursos y proxy funcionan desde otra carpeta y en rutas con espacios. Artefactos ausentes/incompatibles dan instrucciones de reconstrucción. Motor e interfaz conservan las restricciones locales. |
| **H3 · Copia y restauración** | Crear copias mediante un mecanismo coherente con WAL; registrar fecha, esquema y comprobación de integridad; automatizar con frecuencia/retención explícitas; restaurar con motor detenido. | Restaurar en directorio aislado reproduce IDs, importes, experimentos y controles. Una copia inválida se rechaza sin sustituir el estado. Se conserva respaldo del destino antes de restaurar. Sin espacio o permisos, el fallo queda visible y no se presenta como copia correcta. |
| **H4 · Esquema y actualización** | Registrar versión de base, introducir migraciones ordenadas y documentar actualización desde v0.1 con copia previa. | Una base nueva y una copia de v0.1 alcanzan el esquema esperado conservando datos. Repetir inicio no repite migraciones. Una migración fallida no deja una base parcialmente actualizada. Un esquema más nuevo se rechaza con diagnóstico. Volver a una versión incompatible exige restaurar su copia y código correspondientes. |
| **H5 · Instalación y comprobaciones automáticas** | Ajustar instalación/diagnóstico y acceso directo; ejecutar pruebas Python, TypeScript y compilación en CI; documentar matriz de versiones soportadas y novedades. | Instalación desde clon limpio sin estado previo del desarrollador. CI prueba datos aislados, proveedores simulados y dependencias fijadas, sin secretos ni llamadas pagadas. No se asume que el plan de GitHub permite consumo ilimitado: revisar la ejecución y sus límites antes de activarla. |
| **H6 · Candidata y cierre** | Ejecutar recorridos de instalación, actualización, restauración y operación sostenida; registrar resultados y límites; preparar versión identificable. | Evidencia completa, defectos bloqueantes resueltos e instrucciones de uso verificadas. No etiquetar v0.2 como estable si quedan pruebas de cierre pendientes. |

Orden recomendado: H0 → H1 → H2; diseñar H3/H4 conjuntamente para que la actualización siempre tenga una salida de recuperación. H5 incorpora las pruebas conforme se entregan los cambios. H6 se ejecuta sobre una candidata concreta y vuelve a comprobar solo lo afectado si esa candidata cambia.

## Matriz de validación de la candidata

| Recorrido | Preparación y evidencia esperada |
|---|---|
| **Instalación limpia** | Clon/directorio y datos independientes, sin `.venv`, `node_modules` ni base previa. Registrar versiones, instalación, build, inicio, cartera demo, Laboratorio, experimento sin IA y parada. No confundir reconstruir dependencias con tener ya los programas del sistema instalados. |
| **Actualización desde v0.1** | Copia coherente de una base v0.1, con inventario de IDs, saldos, datos, controles y estado de experimentos. Aplicar actualización, verificar integridad y comparar invariantes; repetir el inicio. Conservar código y copia de partida para la vuelta atrás. |
| **Restauración** | Generar copia con estado identificable, restaurarla en destino aislado y comprobar integridad y contenido. Probar rechazo de copia corrupta/incompatible y restauración con instancia activa. No sustituir la única base del usuario para probar. |
| **Fallos controlados** | Doble arranque, puerto ocupado por tercero, proceso terminado, PID/registro obsoleto, dependencia o build ausente, fallo de migración y destino de copia no escribible. Verificar limpieza, mensajes y ausencia de duplicación de trabajo. |
| **Integración y E2E de rc.2** | Interfaz compilada y API real, navegador Chromium, una base nueva por ejecución en `var/validation/e2e-UUID`. Verificar los recorridos de datos, Laboratorio y experimentos sintéticos, contratos, controles y recuperación de errores. Comprobar teclado, foco tras operaciones asíncronas y anuncios sin repetición por sondeo. Registrar aparte el escalado físico de Windows al 125 % y 150 %, todavía pendiente; un viewport CSS no lo sustituye. Procedimiento en [operacion_windows.md](operacion_windows.md#validación-e2e-aislada). |
| **Prueba sostenida** | Fijar duración, muestreo y umbrales antes de empezar. La v0.1 citaba 48 h como prueba pendiente; la duración de la candidata se concretará y quedará registrada. Usar demo, `provider: none`, sin fuentes de red ni llamadas pagadas. Medir salud, recursos, errores, copias y persistencia; incluir parada/reinicio al final. Una comprobación corta no sustituye esta prueba. |

Las pruebas de fallos y escrituras usan datos aislados. No se termina un proceso ajeno ni se altera una cartera de uso para probar recuperación. Las copias, registros y resultados locales van en rutas excluidas de Git; la documentación conserva resultados resumidos y trazables sin secretos.

## Riesgos y decisiones que debe resolver la auditoría

- **Artefacto de interfaz:** comprobar cómo el framework sirve su compilación y mantiene el proxy antes de elegir el lanzador definitivo. Una compilación correcta por sí sola no prueba el recorrido en navegador.
- **Propiedad de procesos:** un PID puede quedar obsoleto o reutilizarse. El cierre debe acreditar que corresponde a la instancia de ATLAS, incluyendo sus procesos descendientes.
- **SQLite y WAL:** copiar solamente el archivo principal mientras hay escrituras puede omitir estado. Elegir copia coherente y validar restauración real; un hash por sí solo no demuestra coherencia lógica.
- **Migraciones:** versionar el esquema no autoriza pérdida silenciosa de datos. Definir punto de copia y recuperación, bloqueo por versiones incompatibles y conducta ante interrupción.
- **Almacenamiento:** decidir frecuencia y número/edad de copias, proteger la última copia válida y hacer visibles los fallos por espacio o permisos. Guardar una copia en el mismo disco permite restaurar cambios, pero no protege de perder ese disco.
- **Reinicio del motor:** no repetir llamadas de IA interrumpidas ni liberar reservas sin evidencia. Detectar caída y ofrecer recuperación clara tiene prioridad sobre reiniciar indefinidamente.
- **Alcance de soporte:** confirmar versiones realmente probadas; no declarar compatibilidad con WSL/Linux ni tiempos de funcionamiento que no se hayan medido.

## Registro de cierre

La entrega debe aportar: versión/commit probado, equipo y dependencias, comprobaciones ejecutadas con resultado, copia y restauración verificadas, duración real de la prueba sostenida, defectos pendientes y comandos finales de inicio/parada/actualización. La versión publicada y [CONTINUIDAD](CONTINUIDAD.md) deben describir el mismo comportamiento.

Hasta completar H6, el estado se comunica como avance de v0.2 y se distingue lo implementado de lo probado. Ningún hito de este plan certifica rentabilidad ni habilita operativa real.

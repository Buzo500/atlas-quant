# Frontend crema y cobre

Implementado el 8 de septiembre de 2026, tras autorización expresa del usuario. Se entrega en la aplicación local de Windows y mantiene la versión **0.2.0-rc.1**. El cierre de la candidata sigue pendiente; esta entrega no inicia un ensayo de 48 horas ni publica una versión estable.

## Diseño y alcance

- Fondo crema `#F4F1EA`, superficies marfil `#FFFCF6`, cobre `#975435`, texto oscuro `#272B2D` y curva azul pizarra `#526B80`.
- Sans serif del sistema, cifras tabulares, columnas numéricas alineadas y monoespaciada para símbolos e identificadores. Navegación compacta, nombres de conjunto visibles y estado de conexión separado del último estado recibido.
- Cartera: métricas, posiciones y curva en paralelo cuando hay espacio; tabla vacía si no hay posiciones abiertas y acceso a importación/demo cuando faltan movimientos.
- Laboratorio: parámetros junto al método cronológico; resultados con curva, candidatos y sensibilidad a costes. Los cálculos proceden del mismo motor.
- Agente IA: tabla de experimentos, selección desde el símbolo, formulario desplegable, expediente con controles al principio y datos estructurados de cada criterio desplegables. Se conservan motivos, valores y condiciones de pausa, reanudación, cancelación y autorización.
- Datos: importación, fuente diaria y metadatos distribuidos en paneles. Se conservan previsualización y confirmación de movimientos, selección de precios/movimientos, procedencia, versiones, CSV y plantillas. Mensajes claros para nombre/procedencia incompletos.
- Ajustes: límites, proveedores y auditoría tabular. Sin campos de claves en la interfaz.

La curva se ha extraído a `frontend/components/atlas/curve.tsx`: mide su contenedor mediante `ResizeObserver`, mantiene etiquetas de tamaño legible y una altura acotada, representa series de un punto y admite valores cero o negativos. El benchmark se representa solo si la serie completa lo contiene. Incluye nombre y descripción accesibles. No se añaden hover, zoom, velas ni indicadores del backlog.

No se modifican endpoints, contratos, esquema SQLite ni lógica financiera. Se conservan React, Vinext, Base UI y las dependencias fijadas; no se instala ninguna dependencia nueva. El archivo `frontend/.openai/hosting.json` se conserva. La maqueta publicada en Sites es independiente y no se vuelve a desplegar.

## Comprobaciones en este sobremesa

**Motor:** 394 pruebas y 91 subtests superados en 32,16 segundos, con los dos avisos anteriores de TestClient. Una prueba de carga simultánea de la demo tenía un reloj fijo distinto de la fecha real del generador. Se sincronizan ambos relojes dentro de esa prueba, conservando el generador y las dos cargas concurrentes; el motor no cambia.

**Fuentes:** TypeScript, contratos OpenAPI/TypeScript y lint de aplicación más el componente de curva correctos. Compilación generada y comprobada con `tools/build_frontend.py`. Se usaron las herramientas ya instaladas mediante sus rutas locales porque el `pnpm` de la sesión resolvía a un ejecutable de respaldo que no encontraba `tsc`.

**Navegador:** 35 comprobaciones de distribución sobre la compilación final, recorriendo las cinco secciones en cada tamaño:

| Viewport CSS | Uso comprobado |
| --- | --- |
| 3440 × 1440 | Ultrapanorámico; tablas y curvas en paralelo, tres paneles en Datos/Ajustes y en Agente con formulario abierto |
| 2752 × 1152 | Ancho equivalente a 3440/1,25 |
| 2560 × 1440 | Escritorio ancho |
| 2293 × 960 | Ancho aproximado equivalente a 3440/1,5 |
| 1920 × 1080 | Escritorio convencional |
| 1366 × 768 | Portátil/ventana reducida |
| 390 × 844 | Ventana estrecha, paneles apilados y tablas con desplazamiento propio |

No se observa desbordamiento horizontal de la página en esos recorridos. El viewport temporal del navegador se restaura al terminar. Los tamaños equivalentes al escalado no prueban el comportamiento físico del monitor ni del sistema operativo: **queda pendiente probar Windows al 125 % y 150 %** en el equipo del usuario.

Recorridos realizados: estado inicial sin datos, carga de demo y comparación histórica en base aislada; cartera y expediente existentes en base habitual; apertura/cierre del formulario de experimento; selección de proveedor sin clave y comprobación del botón de inicio deshabilitado; mensajes de importación incompleta; navegación por teclado con flechas y Enter. Se verificó la respuesta JSON del informe existente y la salud directa del motor y a través del proxy. El formulario abierto en 3440 mantiene Pausar/Cancelar en la primera pantalla del expediente.

La revisión automática de aprobación rechazó crear un experimento adicional de 48 horas durante la validación. No se reintentó, no se creó ese experimento y no se ejercieron pausas/cancelaciones sobre el expediente del usuario. La semántica de esos controles está cubierta por las pruebas del núcleo; esta entrega no afirma un recorrido completo de creación/control nuevo en navegador. No se consultó Yahoo ni se llamó a proveedores de IA.

## Datos y operación

ATLAS se detuvo antes de cada edición/compilación. Copia previa: `backups/atlas-20260908T124552339287Z-c00f74f9`. Las pruebas de datos usaron `var/validation/frontend-crema-cobre/data`, sin sustituir la base habitual.

Tras el arranque normal, integridad SQLite correcta, huella persistente y prefijo de auditoría idénticos a la copia; conjunto, versiones, ledger, investigación e IDs conservados. NAV **25.118,66876 EUR**, tres posiciones y un experimento original en observación. Las actualizaciones de horas transcurridas y los eventos de ciclo de vida siguen su comportamiento normal. Parada global activada, proveedores sin configurar, presupuesto/gasto/reserva de API cero.

**ATLAS queda arrancado en http://127.0.0.1:3000/** con la compilación verificada. Para abrirlo normalmente: doble clic en `Abrir-ATLAS.cmd`; para cerrar motor e interfaz: `Detener-ATLAS.cmd`. También están disponibles `Start-Atlas.ps1 -OpenBrowser` y `Stop-Atlas.ps1` desde la raíz. Cerrar la pestaña no detiene el motor.

Evidencia local, excluida de Git:

- `output/validation/frontend_crema_cobre.json`: fuentes compiladas, salud, pruebas y conservación de datos.
- `output/validation/frontend_crema_cobre_tests.xml`: suite del motor.
- `output/validation/frontend_crema_cobre_viewports.json`: dimensiones y distribución de las 35 comprobaciones.
- `output/validation/frontend_data_preservation.json`: comparación con la copia previa.
- `output/validation/frontend_crema_cobre_3440.png` y `frontend_crema_cobre_1920.png`: capturas de la cartera en la compilación final.

Los cambios son locales y no se han subido a GitHub. La CI anterior corresponde a otras fuentes. Identificar la próxima candidata y ejecutar CI y el ensayo pendiente antes de declarar v0.2 estable. Los informes LaTeX siguen en planificación en REPORT-001; tampoco se implementan aprendizaje, móvil o acceso remoto.

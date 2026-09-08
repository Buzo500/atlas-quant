# Consolidación del núcleo · 6 de septiembre de 2026

**Cierre posterior:** preparada la candidata `0.2.0-rc.1`; seguimiento y evidencia del commit en [candidata_v0_2.md](candidata_v0_2.md). Las cifras y el estado del motor citados abajo corresponden al bloque anterior. La condición estable sigue pendiente de sus comprobaciones de cierre.

Implementada y validada en el sobremesa Windows sobre el árbol local de v0.2 en desarrollo. El motor sigue en 0.1.0. Responde a la autorización de mantener el monolito modular y corregir concurrencia, controles, contratos y pruebas. La revisión inicial se conserva en [revision_core_arquitectura.md](revision_core_arquitectura.md).

## Cambios y garantías comprobadas

- **Datos y contabilidad:** `DatasetService` concentra importación, fuentes, demo y ledger. La comprobación de barras anteriores, procedencia, nueva versión y auditoría ocurre en la misma transacción. Un fallo de descarga solo actualiza los metadatos vigentes; respuestas de descargas superadas se descartan. Una descarga que ya no contiene la historia actual falla conservando la versión nueva. La importación contable concurrente conserva movimientos e idempotencia; la creación concurrente de demo no la duplica.
- **Persistencia:** `Store.atomic` y su unidad de trabajo delimitan operaciones de varios registros. Datos y auditoría confirman o revierten juntos. `Store.update` muta el registro vigente, y `get_dataset_version` encapsula el acceso a la versión congelada; Service no contiene SQL.
- **Controles:** las transiciones y los límites de riesgo salen de los endpoints y viven en `controls.py`. Pausar/cancelar ya no espera al bloqueo de investigación o de descarga. Los resultados tardíos no pueden restaurar estados ni cuentas anteriores. El cambio de parada/límite y las órdenes pendientes se guardan en una transacción.
- **Simulación:** al publicar una observación se vuelven a leer estado, datos, cuenta y límites dentro de la transacción. Los datos cambiados requieren reevaluación. Reanudar tras pausa o desbloquear por parada global/peso consume las sesiones recibidas durante el bloqueo sin ejecutarlas retrospectivamente.
- **Ejecutor único local:** un bloqueo del SO protege el lifespan antes de recuperar trabajos, y otro evita ticks simultáneos, incluso de objetos Service independientes. El trabajo se reclama sobre su estado vigente con un identificador de ejecución. Un segundo servidor sobre la misma base se rechaza; no se ha implementado reparto entre ejecutores o equipos.
- **Recuperación:** cerrar la tarea drena el cálculo cooperativo en su hilo. Restaurar también comprueba los bloqueos del motor, elimina propietarios antiguos y conserva reservas inciertas. Una observación restaurada queda en pausa; una investigación interrumpida no se repite automáticamente.
- **Contratos:** respuestas JSON validadas por modelos Pydantic; tipos TypeScript generados desde OpenAPI y consumidos en estado, cartera, investigación, datos y experimentos. Los tokens internos no salen en las respuestas normales. `tools/export_contracts.py --check` detecta divergencias. El informe JSON descargable conserva el registro de diagnóstico completo.
- **Interfaz:** permite pausar/cancelar mientras investiga, explica una parada aún en curso y bloquea reanudar hasta que termine y no haya reserva pendiente. Se protege el detalle frente a respuestas antiguas del sondeo. El cliente HTTP se extrae a `frontend/lib/api.ts`; se eliminan los `any` de los dos archivos de aplicación.

## Semántica de pausa y cancelación

`status=paused` o `cancelled` significa que la orden de control ya está guardada. Si `execution_active=true` y `control_requested` contiene la acción, todavía se está cerrando una operación. El cálculo comprueba la parada al comenzar y entre bloques de simulación; no hay una garantía de latencia máxima para cualquier tamaño de datos. Al terminar el tramo, `execution_active=false` y la solicitud pendiente se limpia.

Una petición de IA enviada no puede retirarse del proveedor. Se deja terminar o se conserva su reserva si la respuesta queda incierta. Los costes conocidos se liquidan sin cambiar el estado elegido por el usuario. No empieza otra llamada mientras el experimento esté pausado/cancelado. Al pausar, los resultados de fases ya completadas se guardan para no repetir la propuesta al reanudar; un error o una interrupción incierta impide el reintento automático.

La parada global afecta a la simulación paper, no cancela la investigación. Las posiciones existentes permanecen abiertas. No existe conexión a bróker ni envío de órdenes reales.

## Validación en este PC

**328 pruebas y 91 subtests superados**, 74 pruebas más que antes de esta consolidación. Dos avisos de deprecación de TestClient ya existentes. Sin claves ni llamadas de red de proveedores; las pruebas de concurrencia usan barreras y eventos controlados, bases temporales y proveedores simulados.

Pruebas añadidas: `test_dataset_transactions.py`, `test_concurrency_controls.py`, `test_worker_lock.py`, `test_cooperative_backtest.py`, `test_contracts.py` y ampliación de `test_backup.py`. Incluyen HTTP de pausa/cancelación durante CPU, llamada IA en curso, contabilidad de reservas, reanudación sin repetir fases, rollback de riesgo, señales posteriores al desbloqueo, dos procesos y liberación del bloqueo tras caída. Los tests financieros previos siguen pasando.

TypeScript, generación de contratos, `pip check`, lint de aplicación y compilación con manifiesto correctos. El workflow manual de Windows incorpora contratos y lint de aplicación, pero **no se ha ejecutado en GitHub**. `pnpm lint` verifica `app`, `lib`, configuración y servidor local. `pnpm lint:all` conserva la revisión amplia: quedan diagnósticos anteriores en componentes base y hooks de plantilla; no se han desactivado globalmente. La excepción local de accesibilidad del SVG está justificada junto al componente. No se rediseñó el gráfico.

La compilación principal arrancó con el motor y el proxy sanos. La cartera cargó en navegador con tres posiciones y NAV **25.118,66876 EUR**. Estado, detalle e informe respondieron mediante el proxy. La comparación con la copia coherente anterior confirma que conjunto completo, versión, ledger, investigación, resumen, IDs, estado observado y presupuesto/gasto/reserva permanecen iguales. Integridad SQLite correcta. La base principal no se restauró ni se sustituyó. En navegador se probaron la comparación de DEMO_BOND y la pausa/reanudación del experimento existente, que volvió a observación sin cambios en sus resultados. Las regresiones durante CPU/IA se automatizan por HTTP; no se añadió una suite de navegador.

Evidencia local: `output/validation/core_hardening_desktop.json`. Copia previa: `backups/atlas-20260906T163217941908Z-e705d40d`. Esos directorios están excluidos de Git. ATLAS queda arrancado con la demo original, sin proveedor configurado, presupuesto/gasto/reserva cero y parada global activada.

## Incidencia operativa durante el cierre

La primera ejecución de este bloque (`83632708999e4271a84c7ff4b1584e51`) estuvo sana en la comprobación de las 16:54:58 UTC y terminó a las 16:56:17 UTC: el supervisor detectó que uno de los servidores había salido y cerró el otro sin parada forzada. No hubo pérdida de datos. Los registros anteriores no guardaban el hijo ni su código de salida y Windows no aportó un evento de fallo en el intervalo consultado; **la causa de ese cierre no se ha determinado**.

Se amplió el diagnóstico para guardar `unexpected_child_exit` antes de la limpieza y `child_exit_codes` finales, con cuatro regresiones nuevas. También se distingue una parada solicitada concurrente de un fallo. No se atribuye retrospectivamente la salida a Node, Python o al entorno sin evidencia. La repetición del arranque se registra en `output/validation/core_runtime_short.json`; un ensayo corto correcto no sustituye resolver cualquier recurrencia durante las 48 horas pendientes.

La repetición completó **331,7 segundos** de funcionamiento, con 19 muestras adicionales de salud de ambos servidores y cero fallos del supervisor. Se probaron Laboratorio, informe, pausa y reanudación. La parada posterior fue normal: `status=stopped`, `forced_stop=false`, códigos backend/frontend **0/0**; evidencia en `output/validation/core_clean_stop.json`. ATLAS volvió a arrancar y se repitió la comparación de datos y presupuesto con resultado correcto. El cierre anterior no se reprodujo en este ensayo; su causa sigue sin confirmarse.

## Límites que siguen abiertos

Este bloque resuelve CORE-001, CORE-002 y los contratos prioritarios de CORE-003; aborda las fronteras de persistencia y casos de uso de CORE-004. CORE-004 conserva la política de señales/dimensionamiento duplicada entre backtest y paper y la división adicional de paneles. No se ha identificado una divergencia de cálculo en esta entrega. CORE-005 mejora con regresiones y lint de aplicación, pero quedan la revisión de componentes base, pruebas automatizadas de navegador y ejecución remota de CI.

SQLite y los bloqueos siguen siendo locales: no compartir la base por una carpeta de red ni aumentar workers esperando paralelismo. Antes de v0.2 estable faltan identificar la candidata en Git, ejecutar su CI y completar un ensayo operativo de 48 horas con evidencia. La escala distribuida, móvil, gráficos y aprendizaje permanecen en sus hitos futuros.

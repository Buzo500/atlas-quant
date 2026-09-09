# v0.3 · Preparación de la revisión final

9 de septiembre de 2026. **0.3.0-dev.1**, rama `codex/v0.3-graficos`. Este documento reúne la evidencia vigente y las decisiones pendientes; no declara la versión estable ni autoriza una publicación.

## Cambios preparados

Los gráficos ya incluyen fichas junto al cursor, lectura por teclado, barras de navegación, lupas, restablecimiento y vista ampliada con arrastre y rueda. Conservan observaciones originales, tablas, identidad de datos y límites de representación. [Uso](graficos_v0_3.md) y [revisión del código](revision_graficos_20260909.md).

La preparación final añade diagnóstico optativo de API, sus protecciones y pruebas, y documentación consolidada. El arranque habitual, motor, frontend, contratos y dependencias no cambian. La instrumentación se carga únicamente mediante `tools/diagnostics/run_api_diagnostic.py` sobre un entorno E2E nuevo.

## Evidencia aplicable

| Área | Resultado y alcance |
|---|---|
| CI de los gráficos | [34340199451](https://github.com/Buzo500/atlas-quant/actions/runs/34340199451), fuentes `c8f4eb615ca40993c7ad021fa195e60c62b61ed7`: 477 Python + 91 subtests, 244 frontend y 10/10 E2E. No atribuir esta CI a las herramientas añadidas posteriormente. |
| Rendimiento | 100.000 observaciones; precios 1,66 s y curva 1,98 s. Interacciones habituales p95 inferior a 100 ms en los escenarios registrados. [Métodos y límites](revision_graficos_20260909.md). |
| Escalado físico | Seis recorridos correctos a Windows 125 % y 150 % en 3440×1440. Fichas, lupas, barra por teclado, arrastre, rueda y Escape; 100 % inicial restaurado. [Evidencia](escalado_controles_20260909.md). |
| Diagnóstico consolidado | 27 pruebas Python de diagnóstico/aislamiento correctas en 1,55 s; incluyen tres pruebas Node de los clientes. Prueba real: 100 ciclos, 300 lecturas concurrentes más una comprobación previa, todas correctas; máximo observado 112,42 ms. Sintaxis Node y manifiesto del frontend verificados. |
| Conservación de datos | Entorno `e2e-a9f9e2f0e3704ea09a0067c2246a4a66` cerrado con resultado 0 y salidas 0/0, integridad `ok`, hashes habituales intactos y puertos libres. ATLAS normal detenido. |

## Incidencias y decisiones pendientes

1. **API: causa sin determinar.** La espera histórica de 10 s en `/api/state` no se reprodujo. La instrumentación y las ejecuciones correctas no son una corrección del fallo. Si reaparece en un entorno instrumentado, guardar logs y correlación antes de atribuirlo a cliente, proxy o motor. Las herramientas actuales son para bases E2E: no capturan automáticamente el uso habitual. [Diagnóstico](diagnostico_api_20260909.md).
2. **Pantalla completa: ocultación del marco de Chrome sin certificar.** Se comprobaron la vista ampliada y sus controles. El intento posterior en Chrome normal fue detenido por Computer Use al no poder determinar la URL con suficiente certeza; no es evidencia de un fallo del gráfico. Entorno `e2e-24c46f40c2584852ae85e7ff268d8aa3` cerrado con resultado 0, integridad `ok`, hashes habituales intactos y puertos libres. Queda una comprobación manual: abrir un gráfico con su botón de pantalla completa, observar si desaparecen pestañas/barra de direcciones y pulsar Escape para comprobar la restauración. F11 no sustituye la prueba del botón.
3. **Integración y publicación.** Revisar los archivos preparados, subirlos y ejecutar CI sobre el commit final antes de decidir la fusión de la PR #3 y su etiqueta de desarrollo. Este trabajo prepara la revisión; no fusiona ni publica.

G6 permanece abierto. El ensayo de **48 horas sigue aplazado**, así como su seguimiento, y continúa siendo requisito antes de declarar v0.2 estable. La aceptación de esta revisión no inicia v0.4, nuevos indicadores, aprendizaje, móvil, remoto, LaTeX ni operativa real.

## Reproducción del diagnóstico

Desde la raíz, con ATLAS detenido:

```powershell
node --test tools/diagnostics/checks.test.cjs
.\.venv\Scripts\python.exe -m pytest backend/tests/test_api_diagnostics.py backend/tests/test_e2e_isolation.py -q
.\.venv\Scripts\python.exe tools/build_frontend.py --check
.\.venv\Scripts\python.exe tools/diagnostics/run_api_diagnostic.py --manual --timeout 600
```

En otra consola, usar el identificador exacto impreso por el lanzador:

```powershell
node tools/diagnostics/api_clients.cjs e2e-IDENTIFICADOR
.\.venv\Scripts\python.exe tools/run_e2e.py --stop-run e2e-IDENTIFICADOR
```

El cliente rechaza estados HTTP distintos de 200, proveedores configurados, experimentos existentes, datos no sintéticos y descriptores incompletos/inactivos o de otra ejecución. Los wrappers rechazan una base ajena o una parada de otra carpeta antes de cargar la aplicación o instalar hooks; la protección Python sigue activa con `-O`. Estos controles complementan al lanzador, que comprueba la propiedad real de los puertos y conserva el bloqueo de mantenimiento. No son autenticación frente a un proceso local que pueda alterar los archivos de ejecución.

Informes y logs completos permanecen excluidos de Git en `var/validation/` y `output/validation/`. El informe del cliente se crea sin sobrescribir uno previo. Los comandos no cargan claves ni hacen llamadas pagadas.

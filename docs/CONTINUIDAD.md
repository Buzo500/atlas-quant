# ATLAS Quant: continuidad entre equipos

Actualizado: 6 de septiembre de 2026. Este documento resume decisiones y estado para una conversación nueva de Codex; no contiene la transcripción completa del chat original.

## Solicitud actual

El usuario ha retomado el proyecto en su sobremesa y ha pedido instalar y arrancar la v0.1 en Windows nativo desde `C:\Users\lulae\Documents\Personal\Proyectos\atlas-quant`, con base nueva, datos de demostración, sin claves de API y presupuesto cero. Las mejoras de gráficos y aprendizaje siguen fuera de esta tarea.

La instalación partió del commit `cdab38a`, con el árbol de trabajo limpio y sin `.venv`, `frontend/node_modules`, `.env` ni base local. La instalación y validación han terminado: funcionan el motor, el proxy y las interacciones principales de la interfaz; la parada cierra ambos puertos y el reinicio conserva la cartera, el conjunto y el experimento. ATLAS queda arrancado en segundo plano, con la demo y un experimento técnico sin IA en observación. Ambos proveedores siguen sin configurar, sin `.env`, con presupuesto, gasto y reserva cero.

La preparación anterior en el portátil solo añadió documentos, instrucciones y exclusiones de Git. Esta sesión del sobremesa no ha modificado el motor ni la interfaz, no ha migrado la cartera del portátil y conserva los archivos de dependencias fijadas. Se ha añadido `.pnpm-store/` a las exclusiones de Git por la caché local de instalación. Consultar Git en cada equipo antes de asumir el estado de su copia.

## Objetivo y preferencias confirmadas

- Software para analizar inversiones y gestionar una cartera personal; acciones y ETF primero.
- Diseño funcional y técnico amplio, implementado por fases; recursos gratuitos al principio y costes justificados antes de contratar.
- El usuario quiere órdenes reales y automatización configurable como objetivo futuro. La v0.1 no puede enviar órdenes a un bróker. IBKR es candidato, sin conexión ni cuenta comprobadas aquí.
- OpenAI y Anthropic seleccionables; configurar integración antes de decidir presupuesto. Presupuesto inicial cero.
- La IA debe acumular experiencia sobre estrategias y condiciones de mercado, no limitarse a responder preguntas aisladas. Sigue pendiente elegir e implementar la arquitectura de aprendizaje.
- El usuario probó v0.1 y confirmó que funciona y le gusta su aspecto.
- Comunicación en español, concreta, realista y sin dar por buena cualquier propuesta.

## Equipos

El portátil original usa Windows. Una inspección anterior identificó Intel Core Ultra 9 185H, 32 GiB de RAM instalada y NVIDIA RTX 2000 Ada Generation Laptop GPU, con 8.188 MiB de VRAM. No se ejecutó un benchmark de IA local.

En el sobremesa se han comprobado Windows 11 Home x64, versión `10.0.26200`, Intel Core i7-10700K, 31,9 GiB de RAM y NVIDIA RTX 3080 con 10.240 MiB de VRAM y controlador `616.64`. El usuario declara WSL2 instalado; no se ha utilizado ni comprobado su distribución o acceso a CUDA.

La v0.1 se ha instalado en Windows nativo. WSL2 queda para un posible piloto posterior de IA local. El software actual no usa CUDA ni un modelo local; la GPU no acelera automáticamente los backtests.

## Lo que existe

- Backend Python/FastAPI en `backend/atlas_quant/`, con SQLite WAL en `var/atlas/atlas.sqlite3`.
- Interfaz React/TypeScript, Vinext y Shadcn en `frontend/`. Servidor de desarrollo local, sin despliegue compartido.
- Cartera EUR: movimientos, comisiones, dividendos/splits contables, posiciones, P&L y TWR diario con aproximación de flujos al final del día. Sin FX, fiscalidad ni XIRR.
- Importación CSV con validación, versiones inmutables y previsualización de movimientos. Demo con tres símbolos ficticios.
- Backtests long-only: mantener, SMA y momentum en el núcleo; ejecución posterior a la señal, costes y límites de posición compartidos con el benchmark.
- Investigación con división cronológica 60/20/20, selección en validación, ganador congelado y sensibilidad a costes.
- Experimentos persistidos: propuesta, backtest, informe y observación de nuevas sesiones. Máximo ocho candidatos y dos llamadas LLM por experimento. Sin código arbitrario generado por el modelo.
- Adaptadores OpenAI y Anthropic con claves locales y reservas de presupuesto previas al envío. Sin llamadas de IA al arrancar. Catálogo determinista disponible sin proveedor.
- Simulación paper condicionada a datos, evidencia, autorización y límites; parada global activada inicialmente. Los datos sintéticos no habilitan promoción.
- Fuente opcional Yahoo/yfinance diaria en EUR. Datos parciales o problemas corporativos conocidos bloquean promoción; no hay reconciliación completa de dividendos/splits en backtesting.
- Historial y auditoría en la base local. No hay sincronización de bases, backup automático, aprendizaje acumulativo ni servicio del sistema con reinicio automático.

Los umbrales temporales y numéricos no garantizan rentabilidad. Dos días de ejecución son una prueba operativa, no validación estadística de una estrategia. Cada experimento paper tiene capital independiente; falta riesgo agregado entre ellos.

## Instalación y ejecución

Guía paso a paso: `docs/traslado_sobremesa.md`.

Versiones observadas en el portátil el 06/09/2026: Python 3.12.14, Node 24.19.0 y pnpm 11.19.0. Son referencias históricas; la recomendación de reproducirlas en la guía de traslado precede a la validación del sobremesa. El README pide Python 3.12+ y Node 22.13+; el instalador comprueba que existan comandos, pero no valida sus versiones.

En este sobremesa se usa Python 3.14.4 x64 del sistema (`C:\Python314`), con `.venv` creada localmente; Node 24.15.0 del sistema y pnpm 11.19.0 instalado en el perfil del usuario. Su directorio global se ha añadido al PATH del usuario: abrir una ventana nueva de PowerShell para recoger el cambio. Se han instalado `requirements.txt` y `frontend/pnpm-lock.yaml` sin modificarlos; `pip check` no detecta incompatibilidades.

La descarga con npm/pnpm necesitó `NODE_OPTIONS=--use-system-ca` en la sesión de instalación para usar los certificados del sistema. No se desactivó la verificación TLS ni se hizo permanente esa variable. No se han configurado claves ni presupuesto de pago para probar la aplicación.

Desde PowerShell en la raíz, después de instalar dependencias:

```powershell
.\.venv\Scripts\python.exe tools\run_atlas.py --open
```

Interfaz: `http://127.0.0.1:3000/`. Backend: puerto 8000. Ambos son exclusivamente locales. Mantener el proceso y el equipo activos para observar experimentos; no hay autoinicio ni recuperación automática si muere un servidor. Para parar: Ctrl+C en el lanzador en primer plano o `Stop-Atlas.ps1`.

`Start-Atlas.ps1 -OpenBrowser` arranca en segundo plano. Registros: `var/logs/`. Las claves opcionales se configuran en `.env`; no son necesarias para instalar ni probar la demo.

Desde una nueva ventana de PowerShell en este PC:

```powershell
cd C:\Users\lulae\Documents\Personal\Proyectos\atlas-quant
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-Atlas.ps1 -OpenBrowser
```

Para solicitar la parada desde esa carpeta:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Stop-Atlas.ps1
```

`ExecutionPolicy Bypass` se aplica únicamente al proceso que ejecuta el script. Se han comprobado el arranque en segundo plano, la parada efectiva de los puertos 3000/8000 y la persistencia tras reiniciar. Cerrar la pestaña no detiene ATLAS. No hay arranque automático al encender el PC.

## Código, datos y conversación se trasladan por vías distintas

GitHub conserva código, documentación y pruebas. `.venv` y `frontend/node_modules` se reconstruyen en cada equipo. `.env` y `var/` están excluidos. Con un clon nuevo se empieza sin los experimentos ni la cartera del portátil.

Para mover estado existente hay que detener y comprobar el fin del motor, preparar una copia coherente y guardar respaldo del destino. No copiar una base SQLite activa aislada de sus archivos WAL. No fusionar dos bases ni arrancar los mismos experimentos activos en ambos equipos. Un estado `running` interrumpido se marca `interrupted` al recuperarse; no se repite automáticamente una llamada al proveedor.

Propuesta de operación entre equipos: sobremesa como dueño de las ejecuciones prolongadas; portátil con datos de desarrollo independientes. Descargar cambios antes de trabajar, guardar/subir al terminar y actualizar la versión de ejecución entre experimentos. No editar en caliente la versión con la que se está evaluando una estrategia.

Este documento y `AGENTS.md` permiten reanudar el trabajo en un chat nuevo con contexto explícito. Clonar Git no copia la transcripción de Codex ni sus credenciales. Las funciones de conexión remota y handoff son alternativas que requieren configuración y disponibilidad; no se han configurado durante el traslado.

## Backlog pendiente

Fuente detallada: `docs/backlog_planificacion.md`.

1. Cursor sobre gráficos con fecha, hora cuando exista, apertura/máximo/mínimo/cierre y volumen. No inventar información intradía en datos diarios ni OHLC de mercado en una curva de patrimonio.
2. Velas japonesas, barras OHLC, línea/área, zoom y desplazamiento; después otros tipos si aportan utilidad. Los precios sintéticos de gráficos transformados no deben usarse para simular ejecuciones.
3. Memoria consultable de investigaciones: conservar también fallos y variantes rechazadas, datos y versiones, costes y conclusiones verificables.
4. Modelo cuantitativo pequeño que aprenda relaciones entre variables observables y resultados posteriores, con evaluación temporal y comparación con alternativas fijas.
5. Comparar un LLM por API con uno local; ajustar adaptadores solo si una tarea concreta lo justifica. La recomendación de memoria y modelos numéricos locales con LLM intercambiable es una propuesta, no una arquitectura ya aprobada o construida.

El usuario pidió expresamente mantener estas mejoras en planificación. No retomarlas automáticamente al instalar la aplicación en otro ordenador.

## Evidencia y límites de la entrega anterior

La documentación de v0.1 registra 167 pruebas y 91 subtests superados, compilación y TypeScript comprobados, prueba del proxy local y recuperación del estado tras reinicio. Hubo dos avisos de deprecación de TestClient. Son resultados de la entrega en el portátil, no pruebas nuevas realizadas en el sobremesa.

En aquella entrega no se validaron interacciones automatizadas en navegador, ejecución continua de 48 horas, llamadas de pago, conexión IBKR ni inferencia/entrenamiento local. El usuario sí verificó personalmente que la interfaz funciona. Las comprobaciones nuevas del sobremesa se detallan a continuación; las demás limitaciones siguen vigentes.

## Validación en el sobremesa · 06/09/2026

- Python: 167 pruebas y 91 subtests superados, con dos avisos de deprecación de TestClient. Se usó `ATLAS_DATA_DIR=var/test-data` para aislar la base creada al importar la app y `--basetemp var/pytest-<guid>` porque el sandbox denegaba el directorio Temp. Los proveedores de IA y Yahoo están simulados en estas pruebas.
- TypeScript: pasó `node frontend/node_modules/typescript/bin/tsc --noEmit --project frontend/tsconfig.json`, ejecutado desde la raíz. También pasó `pnpm.cmd --dir frontend exec tsc --noEmit` usando el pnpm instalado y el PATH normal del usuario fuera del sandbox. Compilación: pasó `node node_modules/vinext/dist/cli.js build`, ejecutado desde `frontend`.
- Arranque: backend `http://127.0.0.1:8000/api/health` y proxy `http://127.0.0.1:3000/api/health` respondieron `status: ok`, `mode: local` y `live_available: false`. La página principal devolvió HTTP 200.
- Navegador: carga de demostración comprobada, tres posiciones ficticias y patrimonio de 25.118,66876 EUR. En Laboratorio se ejecutó la comparación de `DEMO_BOND`, con tres candidatos y sensibilidad a costes de 0,5×, 1× y 2×.
- Motor persistente: `tools/smoke_local.py` creó el experimento técnico sin IA (`provider: none`, presupuesto 0), que llegó a `observing`, con 220 observaciones fuera de muestra, promoción rechazada y `paper_account: null`. El informe se abrió en la interfaz y mostró gasto y reserva de API en cero. La prueba dejó ese experimento de demostración en la base nueva; su resultado local está en `output/validation/runtime_v01.json`.
- Estado final: ambos proveedores sin configurar, `.env` ausente, un único conjunto sintético sin fuentes automáticas y un único experimento con presupuesto/gasto/reserva cero, `auto_paper: false` y sin cuenta paper. Parada global activada, modo paper y capacidad real deshabilitada.
- Parada y reinicio: `Stop-Atlas.ps1` cerró los puertos 3000 y 8000; `Start-Atlas.ps1` volvió a abrirlos exclusivamente en `127.0.0.1`. Se conservaron los IDs del conjunto y experimento, las tres posiciones, el patrimonio, los límites y el estado `observing`. `PRAGMA integrity_check` devolvió `ok`. Tras recargar el navegador, la interfaz volvió a mostrar «Motor conectado» y la cartera conservada.
- Evidencia local adicional: `output/validation/desktop_windows.json`, excluido de Git, registra el entorno y estas comprobaciones. El campo `browser_interactions: not_tested` del informe original de smoke solo describe lo que hace ese script; las interacciones posteriores sí se verificaron en esta sesión.

No se han realizado pruebas sostenidas de 48 horas, llamadas de pago, descarga de mercado en este equipo, conexión con IBKR ni inferencia local. Las pruebas de instalación no equivalen a validar una estrategia de inversión.

Comprobaciones para cambios de código cuando correspondan:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
pnpm --dir frontend exec tsc --noEmit
pnpm --dir frontend build
```

`tools/smoke_local.py` modifica el estado de la instalación con datos/experimentos de prueba. No ejecutarlo sobre una cartera de uso sin valorar esa modificación.

## Documentos y publicación

- `README.md`: uso y arranque.
- `docs/version_0_1.md`: alcance implementado y limitaciones.
- `docs/atlas_quant_diseno.md`: especificación objetivo completa, 20 secciones.
- `output/pdf/atlas_quant_diseno.pdf`: diseño en PDF, 22 páginas; no es la especificación del alcance ya implementado.
- `docs/backlog_planificacion.md`: gráficos y aprendizaje pendientes.
- `docs/insumos_*` y `docs/base_diseno_quant.md`: material preparatorio, no reemplaza el diseño definitivo.

El PDF móvil se publicó en un sitio privado independiente, enlazado desde README. `pdf-mobile/` es otro repositorio Git y no forma parte del clon principal. El archivo local `frontend/.openai/hosting.json` sí es necesario: contiene valores nulos de configuración y lo importa Vite. No eliminarlo por confundirlo con la publicación del PDF.

El generador `tools/render_design_pdf.py` necesita ReportLab/pypdf y fuentes de Windows que no forman parte de la instalación del motor. Leer el PDF existente no requiere regenerarlo.

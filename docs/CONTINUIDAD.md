# ATLAS Quant: continuidad entre equipos

Actualizado: 6 de septiembre de 2026. Este documento resume decisiones y estado para una conversación nueva de Codex; no contiene la transcripción completa del chat original.

## Solicitud actual

El usuario quiere llevar la aplicación que ya funciona en su portátil a su sobremesa Windows, descargarla mediante GitHub privado y seguir hablando con Codex desde allí. Ha pedido instrucciones para hacerlo. Preparar el traslado no autoriza implementar todavía las mejoras del backlog ni consumir API de pago.

En esta preparación solo se añadieron documentos, instrucciones del proyecto y exclusiones de Git. No se modificó el motor ni la interfaz, no se publicó el repositorio y no se migró la base de datos. La cuenta/nombre/URL del repositorio todavía no se han facilitado en esta conversación. Consultar Git en el equipo actual antes de asumir su estado.

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

El usuario indica que el sobremesa tiene Windows, WSL2 y una RTX 3080 de 10 GB de VRAM. CPU, RAM, versión de Windows, distribución WSL y configuración CUDA del sobremesa están por comprobar. No asumir que WSL2 ya puede usar CUDA.

Recomendación propuesta: instalar v0.1 en Windows nativo para reproducir lo probado. Reservar WSL2 para un piloto posterior de IA local. El software actual no usa CUDA ni un modelo local; la GPU no acelera automáticamente los backtests.

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

Versiones observadas en el portátil el 06/09/2026: Python 3.12.14, Node 24.19.0 y pnpm 11.19.0. El README pide Python 3.12+ y Node 22.13+; el instalador comprueba que existan comandos, pero no valida sus versiones. Reproducir preferentemente las versiones comprobadas y verificar disponibilidad en el equipo nuevo.

Desde PowerShell en la raíz, después de instalar dependencias:

```powershell
.\.venv\Scripts\python.exe tools\run_atlas.py --open
```

Interfaz: `http://127.0.0.1:3000/`. Backend: puerto 8000. Ambos son exclusivamente locales. Mantener el proceso y el equipo activos para observar experimentos; no hay autoinicio ni recuperación automática si muere un servidor. Para parar: Ctrl+C en el lanzador en primer plano o `Stop-Atlas.ps1`.

`Start-Atlas.ps1 -OpenBrowser` arranca en segundo plano. Registros: `var/logs/`. Las claves opcionales se configuran en `.env`; no son necesarias para instalar ni probar la demo.

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

No se validaron interacciones en navegador, ejecución continua de 48 horas, llamadas de pago, conexión IBKR ni inferencia/entrenamiento local. El usuario sí verificó personalmente que la interfaz funciona. No presentar estas limitaciones como resueltas por una instalación nueva.

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

# ATLAS Quant

Antes de continuar una tarea sobre este proyecto, lee `docs/CONTINUIDAD.md` y `README.md`. Para instalarlo en otro equipo, consulta `docs/traslado_sobremesa.md`.

- Responde en español, de forma directa y realista. El usuario estudia el doble grado de Ingeniería del Software y Matemática Computacional en U-TAD; quiere precisión y discrepancias argumentadas cuando correspondan.
- El alcance implementado está en `docs/version_0_1.md`. `docs/atlas_quant_diseno.md` describe el objetivo completo, no funciones ya disponibles.
- La secuencia vigente de versiones está en `docs/hoja_de_ruta.md`. Las mejoras operativas de v0.2 están en desarrollo: leer `docs/plan_v0_2.md`, `docs/auditoria_v0_2.md` y `docs/operacion_windows.md` al trabajar en ellas. La candidata actual se identifica como 0.2.0-rc.2; conservar la etiqueta histórica rc.1. No etiquetarla estable hasta completar CI y el ensayo de 48 horas, que sigue aplazado. Consultar docs/candidata_v0_2.md para el cierre.
- La consolidación del núcleo y la semántica de controles están en `docs/consolidacion_core.md`. Mantener un ejecutor por base; no añadir escrituras de snapshots antiguos tras un `await`. Al cambiar contratos API, regenerar `frontend/lib/api-types.ts` con `tools/export_contracts.py` y comprobar `--check`.
- Detener ATLAS antes de modificar su código o reconstruir la interfaz. El arranque habitual necesita el manifiesto generado por `tools/build_frontend.py`; un `pnpm build` directo no genera ese manifiesto. Usar datos aislados para pruebas destructivas y restauraciones.
- El usuario autorizó implementar v0.3: gráficos interactivos sobre precios y curvas existentes. La rama de desarrollo es `codex/v0.3-graficos`, identificada como `0.3.0-dev.1`; alcance y criterios en `docs/plan_v0_3.md`. No confundir esta entrega de desarrollo con v0.2 estable ni reactivar el ensayo aplazado. Aprendizaje, nuevos indicadores, móvil, remoto e informes LaTeX siguen en planificación en `docs/backlog_planificacion.md`.
- Presupuesto inicial de API: cero hasta que el usuario decida uno. No introducir llamadas pagadas en instalaciones, pruebas o arranque. OpenAI y Anthropic son opciones previstas y ya tienen adaptadores.
- La v0.1 solo ejecuta órdenes simuladas. No tiene integración con un bróker ni órdenes reales. La automatización real es una intención futura bajo reglas y límites configurados.
- `.env`, `var/`, instalaciones locales y copias de seguridad no van a Git. No pedir claves en el chat ni mostrarlas en salidas.
- `frontend/.openai/hosting.json` es necesario para importar la configuración local; conservarlo. `pdf-mobile/` es una publicación y repositorio independientes, excluidos del repositorio principal.
- Distinguir pruebas históricas en el portátil de validaciones realizadas en el equipo actual. No declarar una migración validada solo porque la instalación original funcionó.
- Al cambiar de equipo, actualizar la documentación de continuidad con el estado relevante del proyecto; no asumir que otra conversación tiene este historial.

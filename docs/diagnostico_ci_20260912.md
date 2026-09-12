# Diagnóstico del servidor E2E · 12/09/2026

El usuario autoriza los tres primeros pasos: diagnosticar la pérdida del servidor,
corregir la causa con regresión y repetir CI gratuita. Rama `codex/v0.6-evaluador`,
dev.4 y esquema 5 conservados. No incluye revisión manual, PR, fusión o etiqueta.

Antecedente: [CI 34610747174](https://github.com/Buzo500/atlas-quant/actions/runs/34610747174)
abortó después de 14 recorridos sin retener el código de salida ni stderr del
servidor. [Evidencia anterior](diagnostico_api_20260911.md).

Primera ampliación: la excepción de propiedad captura PID creado, propietario
del listener, pertenencia al grupo y código de salida antes de la limpieza.
Los controles y abortos se conservan. La salida final incluye códigos de ambos
servidores y parada forzada; el wrapper retiene hasta 16 KiB de cola por servidor,
omitiendo trazas JSON ya incluidas en el informe. También captura fallos previos
al arranque de Playwright. Un error al generar evidencia no sustituye el resultado.
Los logs provienen exclusivamente del entorno E2E aislado sin credenciales.

Validación dirigida: 33 pruebas de aislamiento/informe correctas, incluidas seis
regresiones nuevas. E2E completo local `e2e-4237f2b2c12d447b81722b70b3ebae90`:
23/23 en 1,7 min; códigos backend/frontend 0, integridad correcta, sin parada
forzada, puertos liberados y base habitual intacta. No reproduce el fallo remoto.
Motor y frontend habituales estaban detenidos antes de editar; no se arrancan.

Se prepara CI de diagnóstico sobre esta instrumentación, manteniendo límite de
20 minutos, dependencias fijadas y ninguna llamada pagada. Presupuesto Actions
0 USD con bloqueo verificado. La causa sigue pendiente de esa captura; un pase
correcto por sí solo no demuestra que el fallo anterior esté corregido.

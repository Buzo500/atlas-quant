# Dev.9: cinco tareas autorizadas

13/09/2026. «Vale, haz los 5» autoriza captura automática de presión TCP,
adaptador de informes D7 guardados, descarga LaTeX en interfaz, implementación
aislada por grupos y ejecución del experimento predefinido. Mantiene presupuesto
cero, aplicación habitual detenida y datos aislados. No publica PR/etiqueta ni
reactiva ensayo, portátil o movimientos personales.

## Antes del experimento

Se conserva sin modificar [el protocolo fijado](v0_6_dependencia_grupos_plan.md).
Implementación: `tools/diagnostics/dependence_groups.py`. Candidata q4, q8 solo
sensibilidad; mismos generadores, semillas, tamaños, 1.000 historias por celda,
5.000 réplicas L10 y filtros previamente definidos. Sin nuevos paquetes de arranque.
Las pruebas usan semilla de fixture 123, nunca las historias principales para ajustar.

Once pruebas independientes correctas antes del lote principal: cuadratura Simpson
de densidad t para df3/7 (error CDF <1e-10), álgebra de medias/SE, traslación/escala,
degeneración, covarianza AR(1) por suma explícita para cinco phi, JSON/semilla canónicos,
repetición y corrupción, filtro fallido sin rescate con q8, tablas pareadas e incompletitud.
Referencia de cuantiles: [NIST](https://www.itl.nist.gov/div898/handbook/eda/section3/eda3672.htm).
Supuestos y limitaciones contrastados con [Ibragimov y Müller](https://www.princeton.edu/~umueller/tstat.pdf):
no suponer independencia entre grupos por el mero hecho de dividir una serie.

Se congela un commit local del código/pruebas antes de la simulación. `plan.json`
conserva commit, hashes, versiones y filtros; `seeds.jsonl` registra las 36.000
identidades canónicas antes de calcular. Cada caso guarda sus retornos y huellas.
Se comprueban todos los casos y se repiten 0/999 en cada celda antes de decidir.

Máximo seis procesos, 60 min por lote, salida `var/validation/dependence-groups-main`.
Parada por archivo `stop-request`; reanudación valida plan, semillas y casos, sin
sustituir las historias pendientes. La semilla 20260917 solo se ejecuta si q4 pasa
todas las condiciones de 20260916. Ningún resultado modifica la robustez del producto.

## Informe de cartera

Implementar únicamente las fases 1–2 del [contrato de periodo](informes_periodo_contrato.md):
original D7 almacenado, modelo de presentación tipado, JSON/CSV/LaTeX, misma estética
y compilación local opcional con los límites dev.8. Detalles no guardados se muestran
ausentes; no leer posiciones actuales para completar un histórico. Vigencia de consulta
separada del hash económico. Descarga por IDs del servidor, no por cifras del cliente.

La captura TCP es optativa mediante el diagnóstico E2E/CLI local: recuentos por PID,
estado, familia y loopback, eventos 4227/4231, intervalos y límites explícitos. Sin
direcciones remotas ni cambios del SO. TIME_WAIT/PID 0 no acredita al consumidor previo.

Registro de pruebas, PDF, resultados y conservación final: continuidad y guía dev.9.

# v0.6 · Sensibilidad y registro de candidatas

Autorización del usuario: «Venga, a hacer todos», referida a diagnosticar la API,
subir y ejecutar CI gratuita, contrastar un CSV observado, implementar sensibilidad
y registrar candidatas. Desarrollo `0.6.0-dev.3` en `codex/v0.6-evaluador`, esquema 5.
La revisión del portátil, PR #12/fusión/etiqueta, ensayo de 48 horas, movimientos
personales, APIs pagadas y órdenes externas siguen fuera de este bloque.

## Sensibilidad inicial

- Opcional al crear un protocolo, declarada antes del cálculo. Variar una media
  o los costes cada vez, conservando el resto. No es una búsqueda de combinaciones.
- Valores absolutos de media rápida/lenta; multiplicadores de comisión fija,
  comisión proporcional y deslizamiento. La comisión fija resultante se redondea
  hacia arriba al céntimo. Capital, lotes y controles originales permanecen.
- Base y variantes sobre el desarrollo completo, con calentamiento independiente
  dentro del periodo y el mismo motor/libro. No calcular la prueba final ni
  walk-forward de cada variante en este primer alcance.
- Máximo ocho casos distintos, incluida la base. Máximo 24.000 sesiones de
  sensibilidad y 30.000 en conjunto con desarrollo y walk-forward. Dos cálculos
  simultáneos como el resto del Laboratorio; rechazar antes del cálculo si excede.
- Métricas, curvas y motivos por caso; rango y dispersión descriptivos, sin elegir
  automáticamente un ganador, cambiar la estrategia o atribuir significación.
- Guardado/auditoría atómicos y reproducción. Protocolos anteriores sin esta opción
  conservan sus identidades e informes.

## Candidatas

- Hipótesis y nombre independientes del protocolo; creación antes o después de
  investigar, sin presentar un registro retrospectivo como preregistro.
- Estados de investigación, seguimiento o descarte; motivo obligatorio en cada
  revisión. Ningún estado autoriza órdenes, supera riesgo ni activa estrategias.
- Revisiones inmutables con control optimista y auditoría en la misma transacción.
  Los vínculos a informes se añaden y nunca eliminan evidencia anterior.
- La evidencia enlazada conserva las huellas y métricas existentes al registrarla.
  Abrir después una prueba final no reescribe la evidencia de una revisión anterior.
- Historial paginado, hasta 20 protocolos por candidata y 100 revisiones; sin
  borrado de hipótesis, informes o motivos de descarte.

## Verificación y publicación

ATLAS detenido antes de editar. Copia previa:
`backups/atlas-20260911T121035724463Z-d6011740`.
Regresión local: **990 Python + 91 subcasos** (106,99 s; dos avisos previos),
**317 frontend**, ocho pruebas Node, contratos, TypeScript, lint y build canónico.
23/23 E2E en `e2e-6f00680177b748e4827a8e2b82627e70` (1,8 min), además del
recorrido dirigido `e2e-7fe1ba713a3241fda34b0dc5e5058583`.

Cobertura nueva: 29 pruebas Python de costes, límites, lectura protegida de la
reserva, reproducción, identidad antigua, rollback/auditoría, revisiones
concurrentes, evidencia y API real. Frontend: 17 casos adicionales de entradas
ambiguas, reserva, reproducción incompleta, borradores, guardado duplicado,
conflictos y lecturas tardías. E2E nuevo con sensibilidad, curvas, guardado,
descarte, reapertura e historial conservado en 960/1366/3440 px.

Un primer pase frontend obtuvo 316/317 por la apertura de un selector del test
previo de eventos corporativos. El archivo dirigido pasó 8/8 y la regresión
completa posterior 317/317 sin cambiar código, tiempos ni reintentos. No se
presenta ese primer intento como correcto. Dos pruebas backend iniciales usaban
ventanas/variantes incompatibles con sus fixtures; se corrigieron las entradas
de prueba y se conservaron los límites del producto.

Revisión visual: se corrigió el uso de fecha civil para `created_at`; ahora usa
fecha/hora Europe/Madrid, con prueba de cambio de día y microsegundos Python.
Compilación y test dirigido posteriores correctos. Capturas finales:
`output/validation/v06-sensitivity-*.png`, `v06-candidates-*.png`; entorno
`e2e-b64af26b5d5c40128d072359e8d85442`, cerrado limpiamente sin tocar la base
habitual. Esta revisión de anchos CSS no es una prueba física nueva del portátil.

Subida/CI final y arranque habitual se registran en [continuidad](CONTINUIDAD.md).
API y CSV observado tienen [diagnóstico](diagnostico_api_20260911.md) y
[auditoría](v0_6_csv_observado.md) separados; no se consideran resueltos/aptos.

## Uso

1. En **Laboratorio → Simulación SMA con protocolo temporal**, selecciona una
   versión CSV EUR acreditada, fechas, aperturas y parámetros del protocolo.
2. Activa **Añadir análisis de sensibilidad**. Escribe ventanas absolutas
   alternativas (p. ej., rápida 15/25 o lenta 40/60, separadas por comas) y
   multiplicadores de costes (`1, 2` por defecto). Deja vacío un eje que no varíes.
   La base se incluye una vez; se omiten variantes económicamente idénticas.
   Con costes cero, duplicarlos no crea un caso nuevo: declara otra variante.
3. Congela y calcula. Consulta tabla, detalle de cada caso, curvas, costes,
   limitaciones y huella. Modificar después el formulario no modifica el informe.
   La comprobación de reproducción exige coincidencia de sensibilidad cuando
   el protocolo la contiene. La reserva final no se abre por estos pasos.
4. Abre **Hipótesis y candidatas de investigación**. Registra nombre, hipótesis,
   motivo y, si existen, informes. Puede hacerse antes de calcular; vincular
   resultados después requiere una nueva revisión.
5. **Revisar candidata** crea otra revisión con motivo y estado. Los informes
   anteriores siguen vinculados. Se captura la evidencia disponible ahora;
   **Revisiones conservadas** mantiene lo conocido en cada momento. Ante conflicto,
   conserva el texto, cancela explícitamente la edición, actualiza y revisa la
   versión vigente antes de decidir qué guardar. No hay reintento automático.

API: sensibilidad opcional en `POST /api/lab/protocols`; consulta/reproducción
por los endpoints existentes. Registro en `GET/POST /api/lab/candidates`,
`GET /api/lab/candidates/{id}` y `GET/POST .../{id}/revisions`; escrituras con
control local y `expected_revision` al revisar. Las revisiones no se eliminan.

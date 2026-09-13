# Continuación autorizada de dev.7 · 13/09/2026

El usuario confirma que el panel es claro y autoriza las cinco propuestas:
aceptación funcional, publicación dev.7/CI gratuita, experimento de dependencia,
validación de maqueta/compilación LaTeX y generador `.tex` del desarrollo completo.
La aceptación comunicada no es aceptación de PR #12 ni comprobación del portátil.

- Publicación: `ab7764d` sobre `codex/v0.6-evaluador`, dev.7/esquema 5, CI manual
  gratuita. El código siguiente se identificará como dev.8 local, sin fusión/tag.
- Estadística: ejecutar el [protocolo fijado](v0_6_dependencia_revision.md), semilla
  20260914, 12 celdas × 500 historias, n504/1008, 5.000 réplicas, L10/20/40 y oráculo
  gaussiano. Ningún cambio al método del producto o selección tras ver resultados.
  Semilla de historia: mismo JSON de derivación con `length: null`; cada remuestreo
  añade su longitud entera. Claves: `seed`, `dgp`, `n`, `history`, `length`.
  Sesgo de la media y tablas pareadas se publican por celda; valores fuente y
  huellas permiten reproducir cada ensayo. Paralelización por historia, sin
  modificar consumo de PCG64 ni orden final canónico.
  Las longitudes configuradas tienen distribución degenerada (10/20/40). Como
  control adicional, registrar longitudes realizadas de bloques, incluyendo
  truncamiento final, en las primeras 100 réplicas de la historia 0 de cada celda
  y longitud; esta selección se fija antes de generar resultados.
  El contraste independiente 20260915 depende de elegir un diseño que pase los
  filtros; no se usa para rescatar candidatos que fallen.
- LaTeX: instalar una distribución gratuita y portable bajo `var/tools`, sin
  cambiar PATH global ni descargar paquetes durante el arranque de ATLAS.
  Validar maqueta y generar fuente/recursos de informes retrospectivos completos.
  Botón de descarga del paquete LaTeX; PDF por herramienta CLI local explícita,
  sin ejecutar archivos TeX aportados por datos/importaciones. Mantener ZIP
  JSON/CSV anterior compatible y diferenciar manifiesto de renderizado.
- Calidad: límites locales, escape de datos, sin red durante generación/cálculo,
  compilación acotada sin shell-escape, cifras verificadas contra JSON y revisión
  de todas las páginas de ejemplos y casos largos. Fuente editable siempre incluida.

App habitual detenida y base intacta; no reactivar ensayo, portátil, movimientos
personales o PR #12. Presupuesto cero; no usar APIs de IA ni bróker.

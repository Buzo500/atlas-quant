# REPORT-001 · Definición de la plantilla LaTeX ATLAS

Actualización dev.8: el primer generador y la compilación Windows ya están implementados en [la guía de uso](informes_latex_implementacion.md). La definición siguiente conserva el diseño previo; cartera y fechas arbitrarias siguen pendientes.

Diseño concretado el 13/09/2026 por autorización de las cinco tareas posteriores a
dev.6. Entregables de esta fase: contrato, jerarquía, fuente de maqueta y vista
HTML de referencia. **No es todavía un generador integrado ni un PDF compilado.**
No se instala TeX ni se añaden descargas al arranque.

## Identidad visual y composición

A4 vertical, márgenes de 20 mm, cuerpo sans serif de 10,5–11 pt, interlineado 1,2.
La maqueta emplea TeX Gyre Heros como equivalente portable a la sans de la interfaz;
monoespaciada solo para IDs/huellas. Cifras tabulares, importes a la derecha y
unidad en cabeceras; decimales españoles. Sin serif editorial ni estética de terminal.

Paleta exacta del producto: texto `#272B2D`, cobre `#975435`, fondo crema `#F4F1EA`,
superficies marfil `#FFFCF6`, bordes `#DCD7CF` y azul pizarra `#526B80`. El cobre
marca títulos y divisiones, no todas las cifras. Gráficas sin sombras, rellenos
pesados o gradientes. Series identificadas también por trazo, no solo por color.
Para imprimir se usa papel blanco, conservando paneles suaves y líneas; no se
requiere tinta crema en toda la página. El informe debe seguir legible en gris.

## Estructura elegida

1. Primera página funcional, sin portada vacía: ATLAS, título, instrumento/cartera,
   rango solicitado y rango efectivo, moneda, tipo de datos y estado de evidencia.
   Después, resumen numérico, evolución y lectura breve de los resultados.
2. Contexto: estrategia/parámetros/costes o cartera/flujos, convenciones, fuentes,
   comparabilidad del benchmark, supuestos y datos no disponibles.
3. Detalle: posiciones y movimientos o ejecuciones de estrategia, con tablas que
   repiten cabecera y continúan en páginas posteriores. Sin reducir letra hasta
   hacerla ilegible ni omitir filas silenciosamente.
4. Anexo reproducible: versión de ATLAS/plantilla, política, hashes completos,
   configuración, fecha de generación y ficheros de datos incluidos. Las huellas
   largas pueden partir línea; no se incrustan rutas personales o claves.

La [maqueta fuente](templates/atlas-report-v1.tex) y su
[referencia visual HTML](templates/atlas-report-v1.html) usan cifras explícitamente
**sintéticas**, no resultados de una estrategia aceptada. Muestran densidad y
jerarquía; el HTML no certifica la compilación de la fuente TeX.

## Contrato de generación propuesto

`atlas-report-template-v1`, motor elegido **LuaLaTeX** local. Paquetes previstos:
fontspec, babel/español, geometry, xcolor, booktabs, tabularx, longtable, fancyhdr,
hyperref y pgfplots. Fijar versiones y licencia de distribución al implementar;
la definición no instala ni descarga estos paquetes. El generador debe funcionar
con la red deshabilitada y sin `shell-escape`, con tiempo/memoria acotados.

Entrada tipada: `kind` (cartera/backtest), referencia inmutable, intervalo solicitado
inclusivo, moneda base, nivel de detalle y opción PDF. Salida: ZIP con `report.tex`,
recursos locales, `report.json`, CSV originales relevantes, manifiesto y README de
compilación. El PDF, cuando exista, acompaña al fuente; nunca lo sustituye.

Fases separadas: lectura coherente → cálculo de métricas del tramo → modelo de
informe validado → escape de texto → render TeX → compilación opcional aislada →
verificación de cifras y páginas. No ejecutar texto TeX procedente de nombres,
notas, CSV o informes importados. Tratar `\\`, `{}`, `%`, `$`, `#`, `_`, `&`, `~`
y `^` como datos; no permitir rutas de recursos elegidas por esos textos.

## Semántica del periodo

El primer generador se limitará al desarrollo completo de un informe retrospectivo
ya calculado y verificado. Es el alcance respaldado por el ZIP actual; no se ofrece
un selector arbitrario de fechas que reutilice métricas de toda la historia.

La ampliación por intervalo debe heredar posiciones/efectivo al inicio y recalcular
métricas y referencias del mismo intervalo sin reiniciar SMA, reoptimizar o crear
una nueva prueba. En carteras debe reconstruir posiciones anteriores y flujos,
reutilizando NAV/TWR/MWR del motor y sus estados de calidad. No calcular retornos
cuando faltan valoraciones/FX o no existe el estado inicial necesario.

Mostrar rango solicitado y efectivo si los límites caen en días sin sesión;
rechazar intervalos vacíos. Una reserva no calculada no se lee ni se exporta para
rellenar el informe. No incluir estadísticas de robustez que no pertenezcan a la
misma ejecución/política/tramo ni presentar un nivel nominal como cobertura acreditada.

## Criterios de aceptación para implementarlo

- Coincidencia de cada cifra y serie con el modelo de informe, incluyendo comisiones,
  flujos, posiciones previas y redondeo solo de presentación. Números fuente intactos.
- Compilar la maqueta y los casos de referencia con LuaLaTeX fijado; revisar todas
  las páginas renderizadas, fuentes, español, tablas largas y gráfico en gris.
- Pruebas de textos con caracteres TeX, notas largas, huecos, intervalos vacíos y
  resultados de código anterior. Nada de red, procesos o lecturas externas desde datos.
- Identificar siempre sintético/retrospectivo/acreditado; registrar política y
  limitaciones sin inferir que un informe autoriza operaciones.
- Entregar fuente compilable y recursos, verificar manifiesto y evitar sobrescribir
  informes previos. Registrar fallos de compilación sin perder el JSON/CSV original.

El siguiente paso es implementar este generador para desarrollo completo, tras
aceptar la composición y validar la compilación. Cartera y fechas arbitrarias son
ampliaciones posteriores con sus propios oráculos temporales.

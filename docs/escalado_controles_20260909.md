# Escalado físico de los controles de gráficos

9 de septiembre de 2026 · sobremesa · **0.3.0-dev.1**. Fuentes de la interfaz `c8f4eb615ca40993c7ad021fa195e60c62b61ed7`, compilación verificada con `tools/build_frontend.py --check`, huella `03d013e3a2e4ed500adc2f18e1a081e10e84658cab920e5c38a0256d999547ed`. No se modificó ni reconstruyó el programa.

## Procedimiento y resultado

El usuario abrió Configuración → Sistema → Pantalla. Se seleccionó el monitor **2, 3440 × 1440**, se observó su **100 % inicial**, y se aplicaron **125 % y 150 % reales de Windows** mediante Computer Use. Chrome instalado se abrió con perfil temporal, visible en ese monitor y maximizado; `viewport: null`, sin emular DPR ni dimensiones de página. Zoom observado mediante CDP: **1 (100 %)**.

| Escala de Windows | Pantalla en píxeles CSS | Área de página | DPR |
|---|---|---|---|
| 125 % | 2752 × 1152 | 2752 × 1018 | 1,25 |
| 150 % | 2294 × 960 | 2294 × 825 | 1,5 |
| 100 % restaurado | 3440 × 1440 | 3440 × 1305 | 1 |

**Seis recorridos correctos:** precios DEMO_BOND, curva de cartera y curva de backtest, en ambas escalas. Datos sintéticos: 1.100 barras de precios, 1.100 observaciones de cartera y 220 de prueba reservada del Laboratorio. La comparación se ejecutó contra el motor real, con DEMO_WORLD; no se simularon respuestas de API.

- Lupas de ampliar/reducir y navegación con Inicio/Fin sobre la barra: controles operables y rango actualizado.
- Ficha junto al puntero en vista normal y ampliada: fecha y valores originales contrastados con la API; OHLCV en precios, patrimonio en cartera y valor de estrategia en backtest. Fichas dentro del área visible.
- Botón de pantalla completa: activa el espacio ampliado y `document.fullscreenElement`, sin sustituir la API del navegador. Arrastrar cambia la posición sin cambiar el número de observaciones; rueda amplía el tramo.
- Escape cierra el espacio ampliado, conserva el rango y devuelve el foco al botón de apertura.
- Sin desbordamiento horizontal global en los estados comprobados ni errores JavaScript. Se inspeccionaron las doce capturas: texto y controles legibles; las vistas normales incluyen desplazamiento vertical intencional.

**Restaurado y verificado el 100 % inicial** en Configuración y mediante las dimensiones/DPR/zoom de Chrome. Se cerró exclusivamente el navegador temporal.

## Límites de la comprobación

El navegador automatizado activó `document.fullscreenElement` y el gráfico ocupó el área de página, pero mantuvo sus dimensiones de viewport; la consulta adicional de CDP al 125 % siguió indicando ventana `maximized`, no `fullscreen`. Esta evidencia acredita el gráfico ampliado y sus controles al DPI físico comprobado; **no certifica la ocultación del marco de Chrome ni la cobertura de toda la pantalla física**. No se atribuye este comportamiento al programa sin reproducirlo en una ventana de uso normal.

No es una auditoría exhaustiva de accesibilidad, ni valida otros monitores, navegadores, todas las representaciones o el ensayo sostenido. La incidencia intermitente de API sigue abierta según el [diagnóstico](diagnostico_api_20260909.md); estos recorridos correctos no demuestran resuelta su causa. No hubo CI, subida, fusión ni etiqueta en esta revisión.

## Aislamiento y evidencia

Entorno `e2e-03515a1481ab4494a2b8461ef35d4155`, creado con `tools/run_e2e.py --manual --timeout 1200`. Demo y comparación únicamente en su base nueva. Sin claves, fuentes externas ni llamadas pagadas. Parada cooperativa con `--stop-run`: resultado **0**, ambos servidores cerrados correctamente, integridad **ok**, puertos libres y hashes de la base habitual conservados. ATLAS normal estaba y queda detenido.

Registro local excluido de Git: `output/validation/v03-controls-windows-scale-20260909/results.json`, doce capturas y `check-chart-function.txt` con la función de comprobación usada en la sesión. Las imágenes nativas de Configuración, incluidos los tres porcentajes, están en las respuestas de Computer Use de esta conversación; no se exportaron sus payloads.

Se conserva una incidencia del propio comprobador al cerrar: `deepStrictEqual` rechazó arrays equivalentes de distintos contextos JavaScript. Se verificaron las dimensiones serializadas y los escalares DPR/zoom correctamente. Los seis recorridos del programa ya habían pasado y el entorno cerró correctamente. No se atribuye al producto ni se afirma una comparación posterior de la cartera aislada que no llegó a ejecutarse.

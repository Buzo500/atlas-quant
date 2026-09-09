# Comprobación del escalado de Windows

**8 de septiembre de 2026 · sobremesa · 0.2.0-rc.2**, commit `9aee4224a12556e97cde16ed283854af10845bda`. Comprobados el **125 % y 150 % reales de Windows** en el monitor 2 ultrapanorámico de **3440 × 1440**, con la aplicación compilada ya instalada. No se modificaron fuentes ni se reconstruyó la interfaz.

## Procedimiento y medidas

Se seleccionó el monitor en Configuración de Windows y se aplicó cada porcentaje. Se utilizó Chrome instalado, visible y maximizado en ese monitor, con perfil temporal, `viewport: null`, sin `deviceScaleFactor` ni emulación de DPI. El zoom del navegador observado mediante CDP fue **1 (100 %)** en ambas escalas. Las capturas de Configuración identifican el monitor, la resolución y el porcentaje; DPR y dimensiones del navegador complementan esa evidencia, no la sustituyen.

| Escala de Windows | `screen` en píxeles CSS | DPR | Área de página aproximada, descontando el marco de Chrome |
|---|---|---|---|
| 125 % | 2752 × 1152 | 1,25 | 2752 × 1018 |
| 150 % | 2294 × 960 | 1,5 | 2294 × 825 |

El ancho 2294 es el redondeo observado en Windows; no se impuso un viewport equivalente de 2293. **Restaurado y comprobado el 100 % inicial**: Configuración muestra 3440 × 1440 al 100 % y Chrome registra `screen` 3440 × 1440, DPR 1, zoom 1 y área de página aproximada 3440 × 1305. Se cerró el perfil temporal de Chrome.

## Resultado y alcance

Se revisaron **Cartera, Laboratorio, Agente IA, Datos y Ajustes** en ambas escalas, mediante capturas, medidas de distribución y navegación por teclado. No se observaron desbordamientos horizontales de la página, superposiciones ni controles ilegibles en los estados recorridos. El foco visible y el desplazamiento permiten alcanzar los controles; el calendario nativo muestra su propio anillo de foco aunque el elemento contenedor no coincida con `:focus-visible`.

- Cartera: métricas, posiciones, curva original y tabla de datos desplegada, con desplazamiento interno y paginación.
- Laboratorio: formulario de configuración y validación cronológica; no se ejecutó una comparación nueva.
- Agente IA: expediente existente y formulario abierto en ambas escalas; al 150 % se desplegaron además costes/criterios y el detalle de pruebas y comparación existente. En esa escala, el desplazamiento horizontal propio del listado permite ver completa la columna Duración: `scrollWidth` 607, `clientWidth` 530 y desplazamiento 76,67 píxeles CSS. La elipsis de la hipótesis limita intencionalmente el resumen a dos líneas.
- Datos: formularios de precios y movimientos CSV, fechas y metadatos. La huella larga se ajusta mediante salto de línea; no se previsualizó ni confirmó una importación.
- Ajustes: límites, proveedores y auditoría, sin guardar cambios ni accionar la parada.

El registro de navegador no detectó errores JavaScript ni peticiones de escritura a la API durante esta comprobación. No se crearon experimentos, conectaron fuentes ni configuraron claves. ATLAS sigue saludable en la ejecución `7fa354c2b8d5425fa4818dab68acd8a0`, con NAV 25.118,66876 EUR, tres posiciones, parada global activada, proveedores sin claves y presupuesto/gasto/reserva cero. Este recorrido no compara hashes de la base ni atribuye la actividad de otros clientes.

## Evidencia y límites

Registro local excluido de Git: `output/validation/windows-scale-20260908/results.json`, con commit, dimensiones, escalas, medidas, teclado y peticiones; capturas de la aplicación `125-*.png` y `150-*.png` en esa misma carpeta. Las capturas completas muestran la distribución; el recorrido interactivo acredita el acceso mediante desplazamiento. Los estados nativos de Configuración de Windows al 125 %, 150 % y 100 % restaurado se observaron en las imágenes devueltas por Computer Use en esta conversación.

**Límite de exportación de evidencia nativa:** el payload de imágenes accesible desde JavaScript devolvió una captura antigua de Inicio al intentar guardarlo. Los tres archivos se conservan como `invalid-payload-windows-*.png` y están excluidos de la evidencia válida; `nativeWindowsEvidence` en el registro explica la incidencia. No acreditan porcentajes ni restauración. Las observaciones nativas de las respuestas de la herramienta, las medidas CDP y las capturas de la aplicación sí corresponden a los estados revisados.

Para repetir: mantener la resolución 3440 × 1440, identificar el mismo monitor, aplicar 125 % y después 150 % en Windows, mantener Chrome al 100 %, recorrer esas secciones y estados, registrar medidas/capturas y restaurar la escala inicial. Cambiar únicamente el viewport CSS, el zoom o un DPR emulado no reproduce esta comprobación.

Es una revisión funcional y visual de estos estados en este PC y Chrome; no una auditoría exhaustiva de accesibilidad ni certificación de otros monitores, navegadores o escalas. Los E2E y resultados de Laboratorio ya registrados son evidencia separada. **El ensayo de 48 horas y su seguimiento siguen aplazados; rc.2 continúa siendo candidata, no v0.2 estable.**

# Publicación dev.8 · 13/09/2026

El usuario acepta expresamente el PDF («El pdf me parece bien») y autoriza las
cinco propuestas: diagnóstico API, aceptación visual, subida/CI gratuita y definición
del siguiente experimento y de informes por fechas/cartera. La aceptación corresponde
al PDF dev.8 presentado, no a PR #12, portátil o una declaración de versión estable.

Código inicial `823b336`, rama `codex/v0.6-evaluador`, 0.6.0-dev.8, esquema 5.
Se añade captura de fallos de recursos estáticos y cuatro regresiones durante
el [diagnóstico](diagnostico_api_20260913.md); no cambia el motor ni el formato PDF.
CI manual pendiente de resultado en este registro. Sin PR, fusión o etiqueta nueva.

Antes de ejecutar: 531,7/2.000 minutos incluidos y 0 USD facturables comprobados
en GitHub. Actions mantiene presupuesto 0 USD y `Stop usage: Yes` verificados;
no se cambian ajustes. Cierre de cuota pendiente al completar la CI.

Comprobación local posterior de diagnóstico: ocho pruebas Python de captura,
tres frontend nuevas, TypeScript/lint/build correctos; 25 E2E de 25, sin omitidos
ni reintentos, 110,31 s. Run `e2e-6ced188b297e41e3add95b36d5e84145`:
ambos servidores 0, sin parada forzada, puertos libres, integridad y base habitual
conservadas. Captura 1.887 grupos/78 incidencias cortas, ninguna lenta ≥1 s.
No se repite íntegramente la suite Python/frontend local previa: la CI ejecutará
la regresión completa de este commit. La validación previa dev.8 está en continuidad.

Los protocolos estadístico y de informes son definición, no nueva implementación.
La aplicación habitual sigue detenida y su base intacta. Trabajos aplazados conservados.

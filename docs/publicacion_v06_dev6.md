# Publicación de dev.6 · 13/09/2026

Primer punto de las cinco tareas posteriores autorizado por el usuario.
`codex/v0.6-evaluador` subida sobre `27892a2784432a3903f21c7a28be19ebbe9e6aa4`,
**0.6.0-dev.6**, esquema 5. Sin nueva PR, fusión o etiqueta.

[CI gratuita 34768335375](https://github.com/Buzo500/atlas-quant/actions/runs/34768335375),
disparada manualmente sobre esa rama, correcta. Job Windows 103753239196:

- 1.104 pruebas Python + 91 subcasos; 328 frontend y ocho de transporte Node.
- 24 E2E completos, build, TypeScript, contratos, lint y arranque/parada correctos.
- Node 24.21.0; sonda de 30 segundos, 3.685 conexiones y ningún fallo.
- Duración mostrada 13 min 19 s. Captura API: 1.864 grupos, 74 incidencias al umbral
  de 1 s, 60 con marca de fallo/cancelación, máximo observado 3.050,8183 ms.
  Incluye peticiones canceladas/incompletas; no equivale a 60 errores funcionales.
  Los recorridos pasan y la captura no identifica la causa de la incidencia
  histórica. No se han alterado transporte o timeouts para ocultarla.

Antes de lanzar: presupuesto Actions 0 USD con **Stop usage: Yes**, cuota
486,7/2.000 minutos. Después: **510/2.000 minutos**, 3,06 USD de consumo bruto
íntegramente descontados, **0 USD facturables** y 0 GB de almacenamiento usados.
Comprobación mediante la sesión autenticada de GitHub; no se modificó el presupuesto.

El desarrollo posterior del panel es **dev.7 local**. Esta CI verifica el código
dev.6 indicado, no esos cambios nuevos. Las pruebas locales posteriores se
documentan en [la entrega dev.7](v0_6_retrospectivo_interfaz.md).

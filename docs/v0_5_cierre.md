# v0.5 · Revisión de cierre funcional

11/09/2026. Dev.1 y dev.2 están publicadas; dev.3 se implementa localmente en `codex/v0.5-comparador`, esquema 5. **Candidata al cierre funcional del alcance analítico inicial**, no declaración de versión estable. La aceptación visual/funcional del usuario y la publicación de dev.3 se registran por separado.

| Criterio de la hoja de ruta | Entrega/evidencia | Límite o decisión de cierre |
| --- | --- | --- |
| Pesos, bandas, concentración y posiciones objetivo | Dev.1, objetivos por instrumento/efectivo, diagnóstico y revisión de contexto | Objetivos manuales; reglas de estrategia no ejecutadas todavía |
| Aportaciones y rebalanceo reproducibles | Dev.2, cantidades por lotes, costes, remanentes, límites tras simular | Una cotización por instrumento, coste fijo/proporcional; ventas hipotéticamente liquidadas |
| Presupuesto compartido, sin doble gasto | Dev.2, agregación de estrategias y efectivo EUR/USD separado | No convierte monedas implícitamente; derechos no gastables; no es optimizador fiscal o de rotación |
| Referencia de rentabilidad | Dev.2, TWR contra CSV total-return EUR, fechas exactas y procedencia | Benchmark propio verificado por el usuario; no descarga/transformación automática de cualquier serie nativa |
| Escenarios precio/FX | Dev.2, cartera/efectivo/derechos valorados bajo cambios explícitos | Escenario puntual, no probabilidad ni pronóstico |
| Fichas y comparación de activos | Dev.3, versiones/identidad, precio EUR, volatilidad, drawdown, base 100 común | Precios brutos sin dividendos; cobertura y falta de evidencia explícitas |
| Correlaciones comparables | Dev.3, retornos simples EUR e intervalos idénticos para toda la matriz | Mínimo 20, constante indefinida, sin interpolación; matriz histórica, no estimador de riesgo futuro |
| Contexto, transacciones, recuperación | Dev.1–3, informes inmutables, revisión optimista y auditoría atómica | Cambiar contexto invalida la vigencia; no reintentar una mutación en conflicto |
| Recursos comprometidos por órdenes | Marcados como no implementados | Dependen del OMS de v0.7. Aceptar el alcance analítico no significa implementar reservas; nunca se presentan como cero |
| Validación de entrega | Pruebas numéricas, concurrencia, restauración, transporte y navegador | CI de dev.2 no certifica dev.3; requiere su revisión/publicación independiente |

## Dictamen y dependencias

Los elementos analíticos de la hoja de ruta tienen implementación inicial al terminar dev.3. El cierre debe aceptar explícitamente los límites anteriores, en particular referencia por CSV y ausencia de reservas OMS. No corresponde afirmar que existe ejecución de estrategias, optimización completa o un gestor operativo de recursos.

El caso guiado de planificación y su resultado se entregan en [v0_5_ejemplo_guiado.md](v0_5_ejemplo_guiado.md). Revisarlo no registra movimientos personales ni órdenes. La revisión del agente se acredita con pruebas/capturas; no se atribuye aceptación manual al usuario si no responde.

Estado de comprobaciones y operación: [guía del comparador](v0_5_comparador.md) y [continuidad](CONTINUIDAD.md). Primer contrato v0.6 [definido aparte](v0_6_alcance_inicial.md), sin implementación. La publicación de dev.3 y su CI gratuita son la siguiente decisión; no se reutiliza la CI de otra entrega ni se publica una etiqueta estable. El ensayo operativo de 48 horas continúa aplazado y v0.2 sigue siendo candidata.

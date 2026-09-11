# Ejemplo guiado de planificación v0.5

Caso **ficticio**, comprobado el 11/09/2026 en una base E2E aislada. No describe la cartera del usuario y no se añade a su base habitual. Recorrido real `e2e-fb3c520ba00b4cf489147f1c2b7c799a`, con API local y navegador compilado.

## De los movimientos al patrimonio

El 05/01/2026 se aportan 1.000 USD y se compran cuatro unidades a 100 USD, con 2 USD de comisión. Quedan **598 USD de efectivo** y cuatro unidades. El día 06/01 el cierre es 110 USD y el cambio declarado es **0,95 EUR por USD**.

| Concepto al cierre del 06/01 | Cálculo | EUR |
| --- | --- | ---: |
| Posición | 4 × 110 USD × 0,95 | 418,00 |
| Efectivo | 598 USD × 0,95 | 568,10 |
| Patrimonio | 418 + 568,10 | **986,10** |

Los objetivos de este caso son **40 % en el activo y 60 % en efectivo**, con bandas que permiten desviaciones. No se confunde una banda aceptable con alcanzar exactamente el porcentaje objetivo.

## Simular una aportación

En **Cartera → Planificación y escenarios → Aportaciones y rebalanceo**, se elige el corte del 06/01 y se introduce una aportación hipotética de **250 USD**, sin permitir gastar el efectivo anterior. Lote 0,1 unidades, comisión fija 1 USD, comisión proporcional cero. Es un supuesto de fraccionamiento del ejemplo, no una propiedad acreditada de un instrumento real.

Al calcular, el simulador propone **comprar 0,6 unidades a 110 USD**: bruto 66 USD y comisión 1 USD. Las dos variantes coinciden en este caso porque no hace falta vender.

| Resultado hipotético | Cálculo | Resultado |
| --- | --- | ---: |
| Cantidad final | 4 + 0,6 | 4,6 unidades |
| Efectivo final USD | 598 + 250 − 66 − 1 | 781 USD |
| Posición final EUR | 4,6 × 110 × 0,95 | 480,70 EUR |
| Efectivo final EUR | 781 × 0,95 | 741,95 EUR |
| Comisión en EUR | 1 × 0,95 | 0,95 EUR |
| Patrimonio final EUR | 986,10 + 250 × 0,95 − 0,95 | **1.222,65 EUR** |

El activo queda en **39,316239 %**, frente al objetivo del 40 %. La desviación es **−8,36 EUR**; efectivo +8,36 EUR. Se conserva el remanente porque los lotes/costes impiden ajustar cualquier cantidad. «Dentro de límites» significa que cumple las bandas del caso, no que sea una recomendación o un objetivo exacto.

## Revisión y guardado

Revisar ambas alternativas, cantidades, costes, efectivo por moneda y las fuentes que justifican precio/FX. **Guardar análisis** conserva el informe y su evidencia; no registra el depósito de 250 USD, la compra de 0,6 unidades ni un cambio de objetivos. Si cambia el contexto antes de guardar, se exige una nueva revisión.

Los controles automáticos verificaron la igualdad de los libros antes/después, el guardado y la reapertura. Referencia, agregación de presupuestos y escenario precio/FX se recorrieron también en esa misma ejecución. Capturas locales en `var/validation/e2e-fb3c520ba00b4cf489147f1c2b7c799a/browser-artifacts/zzzzzz-market-D6-D7-v0-5-C-3c59a--y-objetivos-en-tres-anchos/`, archivos `v05-planning-390.png`, `v05-planning-1280.png` y `v05-planning-3440.png`.

Pendiente de la respuesta del usuario: si esta presentación y los límites del simulador resultan claros para aceptar el alcance analítico inicial. La aprobación no se deduce del resultado de las pruebas.

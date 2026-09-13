# Informes por fechas y cartera: contrato inicial

13/09/2026. **Definición autorizada, todavía sin implementar.** Continúa
[REPORT-001](informes_latex_diseno.md). El PDF y la estética de dev.8 están aceptados
por el usuario; se conserva la plantilla. No se renumera la hoja de ruta.

## Dos fuentes, un modelo de presentación

| Fuente | Cálculo que se reutiliza | Primera entrega propuesta |
|---|---|---|
| Cartera nativa EUR/USD | `PerformanceService`, `performance.calculate`, `Valuator` y libro compartido | Exportar un informe D7 guardado para su periodo exacto; moneda de informe EUR |
| Investigación retrospectiva | Ejecución congelada, evaluador SMA y `NativeBook` | Recortar un desarrollo verificado, heredando cuentas y posiciones |

La exportación no añade otro motor financiero ni copia fórmulas a React/LaTeX.
`legacy-eur-v1` conserva su semántica: queda fuera de la exportación de cartera
nativa inicial, con explicación, sin convertirlo o reinterpretarlo automáticamente.
No hay operaciones, rebalanceo, cambios de objetivos o datos externos al exportar.

Orden recomendado: **cartera D7 guardada → detalle patrimonial verificable →
subperiodo retrospectivo**. Los informes D7 por fechas ya existen; lo pendiente
es su documento editable y la ampliación del recorte retrospectivo.

## Periodos: reglas que no pueden mezclarse

### Cartera: conservar el contrato D7

`start_date=s` es el **cierre de referencia**, `end_date=e` el cierre final;
s<e. Se representan ambos cierres y se incluyen movimientos/flujos en **(s,e]**.
No convertir esta entrada a una fecha de apertura sin avisar. Para informar de
todo enero, seleccionar cierre de referencia 31/12 y cierre final 31/01.
En UI y documento, nombrar explícitamente esos dos campos. Para un día D, usar
D−1 como referencia y D como final. Máximo 3.660 días, igual que D7.

Son fechas civiles del contrato contable, no un filtro de sesiones bursátiles.
No desplazar fines de semana a lunes ni eliminar flujos del sábado. Los precios
arrastrados, antigüedad, calendario y FX siguen exactamente los estados de Valuator.
No permitir al exportador rellenar huecos, interpolar, inventar FX o rebajar calidad.

### Retrospectivo: sesiones inclusivas con estado heredado

Solicitud `from_date` y `to_date` inclusivas y dentro de las fechas civiles del
desarrollo congelado. No aceptar ningún extremo de la reserva, aunque no hubiera
sesión ese día. Seleccionar primera sesión ≥from_date y última ≤to_date; informar
solicitud y rango efectivo. Si no queda sesión, rechazar. No desplazar una sesión
ausente del calendario declarado como si fuera un fin de semana normal.

Estado inicial: cierre de la sesión anterior a la primera incluida. Si comienza
en la primera sesión de desarrollo, usar el capital/cuenta antes de su primera
apertura. Esa base se identifica como estado previo, no como un precio o sesión
inventada. La curva presenta también ese anclaje con etiqueta explícita.
Una solicitud que incluya todo el desarrollo debe reproducir el informe dev.8.

No reiniciar SMA ni volver a invertir el capital original al recortar. Mantener
señales pendientes, calentamiento, lotes, costes y posiciones heredadas de la
ejecución original. Una orden decidida antes del tramo pero ejecutada dentro se
incluye; una venta ejecutada después no. Comprar/mantener hereda también sus
tenencias originales: no compra otra vez el primer día del tramo.

Reproducir el desarrollo con el evaluador/NativeBook compartidos y proyectar
estados de apertura/cierre y ejecuciones; no deducir posiciones a partir de una
curva redondeada. Esa proyección de estados **aún no forma parte del ZIP dev.8**
y es una dependencia real de esta ampliación. Nunca leer ni calcular la reserva.

## Modelo propuesto y trazabilidad

`atlas-period-report-v1`, formato nuevo sin modificar `atlas-performance-v1`
ni `atlas-research-development-bundle-v1`. Modelo interno tipado, sin endpoints
o migración aprobados como si estuvieran ya implementados:

- `kind`: `portfolio_performance` o `retrospective_slice`.
- `source`: ID/hash del informe original, política, revisión/código originales,
  moneda, procedencia y estado sintético/retrospectivo/calidad contable.
- `period`: solicitud, semántica `closing_interval` o `inclusive_sessions`,
  extremos efectivos y referencia del estado inicial.
- `metrics`: valor decimal/fracción, unidad, estado y motivos por métrica.
- `initial_state`, `final_state`: efectivo por moneda, derechos no cobrados,
  posiciones por instrumento/listing y valoraciones con precio/FX/fecha/calidad.
- `curve`, `flows`, `costs`, `movements` o `executions`: todas las filas del tramo;
  `opening_positions` diferencia tenencias previas de compras en el periodo.
- `benchmark`: referencia y condiciones de comparabilidad, o ausencia motivada.
- `provenance`: fuentes/versiones, hash de contexto, hash de modelo, plantilla,
  generador, UTC y limitaciones. No incluir rutas locales o credenciales.

En la primera fase, el detalle que el informe fuente no conserve será `null`
con motivo explícito, nunca una lista vacía que parezca una cartera sin posiciones.

Separar el hash de contenido económico del manifiesto de renderizado/fecha.
Conservar `source-report.json` original junto al nuevo `period-report.json` y CSV
sin redondear. La reserva mantiene solo los metadatos ya autorizados, sin precios.
Mismo modelo/plantilla/fecha genera el mismo ZIP. El PDF conserva los límites
actuales de CLI y su recibo; ninguna descarga HTTP compila TeX.

## Coherencia, históricos y exportación

Para cartera, cargar el informe guardado desde el servidor; no aceptar un JSON
del cliente como informe contable auténtico. **Los informes D7 antiguos guardan
NAV, flujos y referencias, pero no toda la instantánea de posiciones.**

Primera fase: exportar fielmente sus métricas, curva, flujos, costes y contexto
almacenados, sin completar campos desde la cartera actual. Mostrar «detalle de
posiciones no incluido en este informe» cuando falte. Un informe histórico se
puede exportar como histórico con su vigencia; no recalcularlo contra fuentes nuevas.

Para añadir posiciones y movimientos verificables en la segunda fase:

1. Leer informe y contexto económico en una instantánea coherente; exigir que
   su huella coincida con la del informe guardado antes de ampliar su contenido.
2. Proyectar estados/detalle con el motor existente fuera de la transacción larga;
   verificar que las métricas resultantes coinciden con el informe original.
3. Formar una cápsula inmutable autocontenida de exportación. Un cambio de contexto
   durante la preparación provoca conflicto 409; no combinar versiones ni reintentar.
4. El archivo ya generado conserva esa revisión aunque la cartera cambie después.
   Volver a preparar exige una nueva lectura. Sin escrituras de libro o auditorías
   financieras ficticias por descargar; persistencia de cápsulas requiere decisión aparte.

Si no se puede reconstruir la revisión histórica, ofrecer la exportación limitada
de la primera fase y explicar la ausencia. No completar posiciones antiguas con
las actuales ni afirmar que un hash sin fuentes acredita su reproducción económica.

En retrospectivo, verificar primero el informe completo según el contrato vigente;
derivar el nuevo modelo sin sobrescribir hashes, resultados o código originales.
Identificar un recorte elegido después de ver resultados como análisis exploratorio.
Un informe de robustez de toda la muestra no se adjunta como si perteneciera al
subperiodo. No calcular robustez nueva ni abrir una prueba final al exportar.

## Métricas y casos no disponibles

- Cartera: P&L neto = NAV_e−NAV_s−flujos externos de (s,e], en EUR y al FX de
  cada fecha. TWR, tramos y MWR/XIRR se importan de D7 con su política y estados.
- Comisiones, cargos y retenciones ya están en NAV; el desglose no vuelve a restarlas.
  Compras, ventas, FX y dividendos retenidos son movimientos internos.
- Retrospectivo: retorno del tramo = NAV_final/NAV_previo−1 si la base es positiva
  y la curva completa. Drawdown recalculado con máximo acumulado dentro del tramo,
  incluyendo la base heredada. Exceso frente al benchmark usa el mismo tramo y
  sus estados heredados. No anualizar por defecto ni reutilizar métricas globales.
- Base cero, huecos/FX faltante y MWR ambiguo: `null` con motivo, nunca cero por defecto.
  No unir curvas a través de huecos. El informe puede mostrar métricas disponibles
  aunque otra no lo esté; el estado global no oculta la calidad individual.
- Carteras: sin benchmark añadido automáticamente. Un futuro benchmark requerirá
  moneda, calendario, flujos y dividendos comparables y referencia congelada.

## Oráculos de aceptación fijados antes de implementar

| Caso | Resultado esperado |
|---|---|
| Inicio con posición heredada | 2 acciones a 100 al cierre previo, sin efectivo; final a 110: NAV 200→220, retorno 10 %, sin nueva compra |
| Recorte sin máximo anterior | NAV histórico previo 200, base del tramo 100, siguientes 110 y 99: drawdown del tramo 10 %, no 50,5 % |
| Aporte en el cierre de referencia s | NAV_s incluye 1.000 aportados; NAV_e 1.100, sin flujos en (s,e]: P&L 100; no restar el aporte dos veces |
| Dos días y aporte | NAV 1.000→1.200 con aporte 100→1.320: P&L 220, TWR 21 % |
| Aporte con comisión | Base 1.000, aporte bruto 100, coste 2, final 1.098: P&L −2, TWR −0,2 %; coste no se resta dos veces |
| Exposición USD | 10 acciones a 100 USD, FX 0,90 EUR/USD; final 110 USD y FX 0,80: NAV 900→880, P&L −20 EUR, no +100 EUR |
| Dividendo con derecho previo | 10 acciones y derecho a cobrar 10 EUR ya en NAV_s; cobro mueve derecho a efectivo sin nuevo P&L |
| Split 2:1 | 10 acciones ×100→20×50, mismo efectivo: sin P&L artificial |
| Hueco intermedio | Mantener el diagnóstico D7: TWR puede faltar aunque MWR/P&L con extremos y flujos completos estén disponibles |
| Base retirada y repuesta | Sin concatenar TWR a través de NAV cero; conservar tramos separados |
| Fin de semana | Cartera conserva fechas/flujos civiles; retrospectivo informa sesiones efectivas o rechaza si no hay ninguna |
| Reserva | Cualquier extremo fuera del desarrollo se rechaza, sin leer precios reservados |
| Histórico sin posiciones | Valores guardados idénticos y detalle ausente explicado, nunca datos de la revisión actual |
| Revisión concurrente | Preparación con contexto cambiado devuelve conflicto; archivo ya capturado sigue inmutable |

Además: signo de retiradas, coste USD sin FX, raíces múltiples D7, año bisiesto,
una sola sesión retrospectiva, ambos extremos inválidos, todas las filas de tablas
largas, textos TeX no fiables, ZIP alterado, redondeo de presentación y código antiguo.
Contrastar los esperados con aritmética independiente; no generarlos con la función probada.

## Entregas y decisiones pendientes

1. Adaptador puro D7 guardado → modelo de presentación, exportación limitada y pruebas.
2. HTTP/UI para ese adaptador con las guardias actuales y descarga de fuente; sin compilador web.
3. Cápsula de posiciones/efectivo y movimientos de una revisión reproducible.
4. Proyección retrospectiva y selector de fechas con los oráculos anteriores.
5. Revisión visual y CI gratuita de cada entrega; benchmark/LaTeX de otros módulos después.

No se implementa ninguno de estos cinco bloques por el mero hecho de definirlos.
El usuario decidirá qué entrega desarrollar. Ensayo de 48 h, portátil y movimientos
personales siguen aplazados; presupuesto de API cero.

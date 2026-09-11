# v0.6: CSV, Laboratorio y validación temporal

Ampliación posterior `0.6.0-dev.2`: [walk-forward con parámetros fijos](v0_6_walk_forward.md),
opcional al crear un protocolo. Preserva el comportamiento y las huellas de los
protocolos anteriores sin walk-forward. La CI que se registra abajo valida dev.1.

El usuario autorizó el 11/09/2026 los cuatro siguientes pasos: subir la rama y
ejecutar CI gratuita, conectar CSV propio con evidencia explícita, integrar las
simulaciones en API/Laboratorio y separar desarrollo de una prueba final con
benchmarks. La revisión manual del portátil y el cierre de PR #12 siguen pendientes.

## Contrato de esta entrega

- Reutilizar las series CSV nativas EUR, su identidad y versiones. Exigir precios
  raw, calendario y disponibilidad acreditados. Añadir un CSV de aperturas y su
  disponibilidad; contrastarlo con los cierres del calendario ya importado.
  La declaración del usuario sobre ausencia de eventos corporativos no se presenta
  como certificación externa. Los eventos conocidos incompatibles bloquean.
- Congelar fuente, evidencia, ventanas SMA, costes y corte temporal antes de
  publicar resultados. Conservar informes inmutables y auditoría atómica en el
  esquema 5, sin tocar carteras, objetivos ni libros operativos.
- Dos cuentas simuladas independientes: desarrollo y prueba final. Ambas empiezan
  en efectivo y calientan la SMA dentro de su periodo. Comparar con efectivo y
  comprar/mantener bajo los mismos costes, lotes, capital y límites.
- La prueba final requiere una apertura explícita e irreversible dentro del
  protocolo. Registrar exposición por instrumento y fechas en esta base: impedir
  reutilizar periodos ya calculados como prueba no vista, incluso con otra versión
  de precios. Una base local no puede certificar que el usuario nunca vio el CSV
  ni controlar otras bases o análisis externos.
- Máximo 2.000 sesiones por protocolo; historial paginado; cálculo fuera de la
  transacción y publicación con comprobación de contexto y reservas temporales.
- Reproducir un informe usa su fuente congelada y políticas identificadas. No
  implica aprobación de una estrategia ni habilita paper externo.

## Verificación y publicación

Respaldo anterior: `backups/atlas-20260911T100806272408Z-ab4ac1f1`.
ATLAS detenido antes de editar. Rama `codex/v0.6-evaluador` subida inicialmente en
`d7ea898`. GitHub: 330/2.000 minutos, almacenamiento 0/0,5 GB, importe facturable
0 USD; presupuesto Actions 0 USD con Stop usage activado. La CI inicial del núcleo
no sustituye la CI del código final de esta ampliación.

CI inicial del núcleo **34588116355**, job **103226913519**, correcta sobre
`d7ea898`. La ampliación posterior supera **929 Python + 91 subcasos**,
**297 frontend**, **8 Node**, TypeScript, contratos y lint. Dos avisos de
deprecación Python anteriores; no fallos. Logs `output/validation/v06-lab-*`.

Los 20 E2E anteriores pasan. El nuevo recorrido detectó inicialmente un import
JSON ESM sin atributo y selectores que incluían texto de ayuda o coincidían con
el formulario anterior; corregidos con etiquetas y ámbito de formulario explícitos,
sin sustituir ni simular la API. **El nuevo E2E completo pasa** en
`e2e-e301b24c03f642de989af305882563d6`: importación, reserva, apertura, F5,
reproducción y ventanas de 960/1366/3440 px. Base habitual intacta, integridad `ok`
y puertos liberados. Son tamaños de navegador en el sobremesa, no escalado físico
ni aceptación manual en el portátil. CI final correcta, detallada más abajo. No fusionar ni etiquetar
PR #12 por esta autorización; tampoco reactivar el ensayo de 48 horas.

## Uso

1. En **Datos**, crea/elige instrumento y cotización EUR con mercado explícito.
   Importa el CSV nativo mediante previsualización y confirmación. Declara la
   base `raw`, procedencia, calendario completo (días abiertos y cerrados) y
   disponibilidad de los cierres. No marcar datos como acreditados sin evidencia.
2. En **Laboratorio → Simulación SMA con protocolo temporal**, actualiza las
   series y elige una versión. Indica fechas, ventanas, capital, costes y límites.
   El formulario no depende del conjunto heredado seleccionado en la barra global.
3. Pega el CSV de sesiones `date,open_at,close_at,open_available_at`, en orden y
   con zona horaria. Debe cubrir exactamente las sesiones abiertas del periodo.
   Dejar `open_available_at` vacío indica apertura no acreditada; no se sustituye
   por el cierre. En esta integración, un cierre tardío hasta la siguiente apertura
   bloquea el protocolo. El evaluador puro soporta más situaciones, pero no se
   infiere una hora de publicación al importar.
4. Declara las fuentes de evidencia de apertura y ausencia de eventos; revisa y
   pulsa **Congelar y simular desarrollo**. El protocolo y su informe se guardan
   juntos; se conserva una copia exacta de los datos, no una referencia mutable.
5. Reabre desde **Protocolos guardados**. **Comprobar reproducción** recalcula
   únicamente periodos ya publicados. La prueba final no se calcula por esta vía.
   Para verla, acepta el efecto de apertura y pulsa **Abrir prueba final**.

El informe muestra NAV al cierre disponible, retorno neto, caída máxima entre
esas observaciones, costes y ejecuciones. Incluye curva interactiva, tabla de
valores originales y trazabilidad. Si falta valoración no la reemplaza por cero
ni dibuja una continuidad inventada. No hay liquidación artificial al final.
La política temporal no busca parámetros, ni prueba significación estadística,
ni afirma independencia frente al comparador antiguo u otras aplicaciones.

### Referencia reproducible, solo ficticia

`fixtures/v0_6_lab_reference.json` reúne entradas y resultado esperado. Sus CSV
separados `v0_6_lab_prices.csv`, `v0_6_lab_calendar.csv` y
`v0_6_lab_sessions.csv` facilitan pegarlos en los formularios. Mercado `TEST`,
zona `UTC`, todos los días abiertos ficticiamente: no son cotizaciones reales.

Capital 1.000 EUR por periodo, SMA 2/3, comisión fija 1 EUR, comisión proporcional
y deslizamiento cero, peso/límite 1 y lote 1. Desarrollo 01–07/01/2025; prueba final
08–14/01/2025. En cada periodo: SMA compra 99 a 10 EUR, vende 99 a 8 EUR y acaba
en **800 EUR**; comprar/mantener acaba en **801 EUR** (99 títulos y 9 EUR de
efectivo); efectivo en **1.000 EUR**. No sustituye la SMA 20/50 por defecto.

No importar esta referencia en una cartera personal. La CI/E2E la ejecuta en una
base exclusiva y comprueba que la base habitual no cambia.


## Comprobación operativa del sobremesa

Código publicado en `e797ca34cfbfcd177c7873b605f21d484f0f643d`. CI final
[34590252591](https://github.com/Buzo500/atlas-quant/actions/runs/34590252591),
job 103233664678, **correcta sobre ese commit** (10 min 51 s). Antes de lanzarla:
348,3/2.000 minutos gratuitos, 0/0,5 GB, facturable 0 USD y presupuesto Actions
0 USD con Stop usage activado. No se modificó la configuración de facturación.

ATLAS reiniciado con run `41ea181bbe744aabbd6a34d20a0acdf2`. Salud directa y por
proxy `ok`, versión `0.6.0-dev.1`, HTML 200, parada global activa y ningún proveedor
configurado. Las tres carteras y todas las filas de todas las tablas coinciden
con la copia previa, esquema 5, integridad `ok`; el Laboratorio habitual está vacío.
Evidencia: `v06-lab-health.json` y `v06-lab-data-online.json` en `output/validation`.
No se insertaron las referencias sintéticas en la base habitual.

Comprobación del límite de entrada en memoria, con 2.000 sesiones sintéticas,
dos periodos de 1.000 y 16 ejecuciones SMA por periodo: 0,747 s en este sobremesa,
177.782 bytes de informes. Es una medición local de este escenario, no una garantía
de latencia ni una prueba prolongada. Evidencia `v06-lab-bound.json`.


## Cierre verificado

CI gratuita **34590252591** correcta sobre **e797ca3**: **929 Python + 91 subcasos,
297 frontend, 8 Node y 21 E2E**, además de instalación, compilación, TypeScript,
contratos, lint y arranque/parada. Evidencia local `output/validation/v06-lab-ci.json`.
La CI completa confirmó los 21 recorridos juntos, incluyendo los selectores corregidos.
Facturación tras terminar: **366,7/2.000 minutos**, 0/0,5 GB, coste bruto 2,20 USD
cubierto por 2,20 USD de uso incluido, **facturable 0 USD**. Presupuesto Actions
0 USD con bloqueo de uso de pago verificado antes de ambas ejecuciones.

Los cuatro pasos quedan implementados y subidos a `codex/v0.6-evaluador`.
La documentación de cierre posterior no cambia el código probado por CI.
No se ha creado una nueva etiqueta ni fusionado PR #12. La validación de una
fuente observada concreta sigue pendiente: las pruebas usan datos ficticios
identificados y no convierten NVD.DE u otra serie existente en datos acreditados.

La exposición es un registro de esta base: restaurar una copia antigua, crear
identidades duplicadas o usar otra base no demuestra que un periodo sea desconocido.
Mantener esa distinción al investigar. El usuario conserva la decisión de cuándo
retomar la revisión del portátil; el ensayo de 48 horas no se ha reactivado.

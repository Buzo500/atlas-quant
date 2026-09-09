# Descarga de Yahoo y certificados de Windows

## Incidencia y solución del 09/09/2026

Al intentar conectar `NVD.DE`, el motor respondió 422 y no creó ningún conjunto. El log mostró `CertificateVerifyError`, curl 60, `unable to get local issuer certificate`. La cadena presentada por `query1.finance.yahoo.com` estaba firmada por `Avast Web/Mail Shield Root`, ya instalado como raíz de confianza en Windows. Se comprobó su emisor con OpenSSL rechazando la conexión no verificable; no se aceptaron certificados obtenidos de la red.

El paquete de CA de certifi usado por curl/yfinance no incluía esa raíz local. También falló en este entorno la prueba con `CURLSSLOPT_NATIVE_CA`. La misma consulta HTTPS respondió 200 al usar un archivo PEM formado por certifi y las CA del contexto de confianza de Windows. La descarga completa mediante el adaptador de ATLAS confirmó EUR y 427 sesiones de `NVD.DE`, del 02/01/2025 al 08/09/2026.

Configuración local aplicada:

- `var/certificates/requests-ca.pem`: certificados públicos de certifi y del contexto de confianza de Windows; sin claves privadas.
- `.env`: `REQUESTS_CA_BUNDLE` con la ruta absoluta a ese archivo. El lanzador admite ahora esta variable en su lista explícita de configuración y respeta un valor ya heredado del entorno.
- Se mantienen la verificación de cadena y de nombre HTTPS. No se desactivó Avast ni se modificó el almacén de certificados del sistema. Las variables para desactivar verificaciones siguen excluidas de la lectura de `.env`.

Ambos archivos locales están excluidos de Git y no se trasladan automáticamente a otro PC. Es una instantánea del almacén de confianza de este equipo: si el antivirus renueva su certificado o cambia la confianza de Windows, debe regenerarse. No añadir certificados recibidos por correo o descargados de una conexión fallida como raíces confiables.

Para regenerar el archivo en este mismo Windows, con ATLAS detenido, desde la raíz del proyecto:

```powershell
@'
from pathlib import Path
import ssl, certifi
bundle = Path('var/certificates/requests-ca.pem')
bundle.parent.mkdir(parents=True, exist_ok=True)
roots = ssl.create_default_context().get_ca_certs(binary_form=True)
bundle.write_text(
    Path(certifi.where()).read_text(encoding='ascii') + '\n'
    + ''.join(ssl.DER_cert_to_PEM_cert(root) for root in roots),
    encoding='ascii',
)
'@ | .\.venv\Scripts\python.exe -
```

La ruta guardada en `.env` debe seguir apuntando a ese archivo. Reiniciar mediante `Abrir-ATLAS.cmd`. No hace falta reconstruir la interfaz para este ajuste del lanzador. Referencias del mecanismo: [certificados CA en curl](https://curl.se/docs/sslcerts.html) y [sesiones de curl_cffi](https://curl-cffi.readthedocs.io/en/stable/api.html).

## Validación y estado final

Copia manual previa: `backups/atlas-20260909T142248305429Z-eaa0545f`. ATLAS se detuvo antes de editar el lanzador y reinició como `f059c045db5448a1a71af06737978cf3`. El arranque normal lee la configuración y la API real descarga `NVD.DE` correctamente; fuente `4fc6914f5b944719a4901d8613d9968b`, versión 1, histórico desde 2025. El catálogo incorpora su identidad local. Las dos carteras anteriores conservan registros, movimientos y valoración exactos; no se añadió ninguna compra ni se modificaron sus vínculos de precios.

- **48 pruebas de runtime/feed y 28 subtests**, incluidas aceptación de una ruta CA con espacios, precedencia del entorno y exclusión de variables que deshabilitan HTTPS. Log `output/validation/nvidia-tests.log`. El primer intento no pudo acceder al directorio temporal general de pytest; se ejecutó correctamente con un directorio nuevo y aislado dentro de `var/validation`.
- Build existente verificado y `git diff --check` correcto. Sin cambios en frontend, contratos API ni dependencias.
- Gráfico real visible con `NVD.DE`, última sesión 08/09/2026, OHLCV y sin errores JavaScript; comprobación de navegador a 1720×1000 CSS. Evidencia `output/validation/nvidia-chart.json` y `nvidia-chart.png`. No es una repetición de la suite E2E completa ni del escalado físico.
- Comparación de carteras: `output/validation/nvidia-before.json` y `nvidia-portfolios-unchanged.json`. Datos de descarga: `nvidia-dataset.json`. Diagnósticos y certificados excluidos de Git.

Yahoo comunica seis eventos corporativos en el periodo; permanecen registrados y sin conciliar, con sus restricciones vigentes de promoción automática. La reparación de HTTPS no implementa conciliación, ajustes nuevos ni USD. Presupuesto de IA cero, sin nuevas claves, órdenes, CI, subida, etiqueta o ensayo de 48 horas.

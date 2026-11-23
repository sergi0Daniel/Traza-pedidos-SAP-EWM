# TRAZA+ | Seguimiento de pedidos de grifería

Prototipo web para consultar el recorrido de pedidos, productos y unidades de manipulación dentro del centro de distribución. La aplicación está construida con Python y Flask en el backend y HTML, CSS y JavaScript en la interfaz.

## Qué incluye

- Inicio con resumen de pedidos y distribución por etapa.
- Búsqueda por pedido, entrega, referencia de producto o HU.
- Detalle de pedido con productos, unidades de manipulación, ubicación registrada y eventos.
- Alertas de permanencia superiores a umbrales configurados.
- Módulo de informes y consultas con IA (requiere autorización y configuración).
- Panel de conexión de SAP EWM con comprobación y consulta de solo lectura.
- Modo de demostración claramente identificado.

## Estado de la integración

La aplicación **no queda conectada automáticamente a SAP EWM**. La conexión se habilita solo cuando TI facilite y autorice el endpoint, la autenticación, el esquema de respuesta y las condiciones de red.

El conector no presupone una URL OData específica. La versión y configuración de EWM deben confirmarse con TI. El código espera una respuesta JSON normalizada descrita en la sección **Contrato de datos esperado**. Si la API corporativa devuelve otra estructura, debe ajustarse el mapeo antes de utilizarla.

Los datos de demostración son inventados y están identificados como tales. No representan registros ni tiempos reales de Corona.

## Requisitos

- Python 3.10 o superior.
- Visual Studio Code (recomendado).
- Acceso a una terminal (PowerShell o CMD en Windows).

## Instalación en Windows

1. Descomprime el proyecto y abre la carpeta `traza_pedidos_sap_ewm` en Visual Studio Code.
2. Abre la terminal integrada.
3. Crea un entorno virtual:

```powershell
py -m venv .venv
```

4. Actívalo en PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si utilizas CMD:

```bat
.venv\Scripts\activate.bat
```

5. Instala las dependencias:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

6. Ejecuta la aplicación:

```powershell
python app.py
```

7. Abre esta dirección en tu navegador:

```text
http://127.0.0.1:5000
```

La aplicación abrirá en modo demostración. No necesita credenciales para mostrar las pantallas de ejemplo.

## Cómo utilizar la aplicación

1. En **Inicio**, revisa el resumen de pedidos y su distribución por etapa.
2. En **Seguimiento de pedidos**, busca por número de pedido, entrega, referencia o identificador HU.
3. Selecciona **Ver detalle** para revisar productos, unidades de manipulación, ubicación registrada e historial de eventos.
4. En **Alertas y demoras**, revisa los pedidos que exceden los límites configurados. Los valores del modo demostración son solo ilustrativos.
5. En **Informes con IA**, usa generación de informes, preguntas o análisis de demoras una vez que la empresa autorice y configure el servicio.
6. En **Conexión SAP EWM**, revisa el estado de la integración y ejecuta las pruebas cuando TI entregue la configuración.

## Configuración de SAP EWM

1. Copia `.env.example` y crea un archivo local llamado `.env` en la raíz del proyecto.
2. Solicita a TI los endpoints de consulta, el método de autenticación, los permisos de solo lectura, los certificados y el contrato de datos.
3. Completa solo las variables que TI haya confirmado. No inventes las rutas del servicio.
4. Cuando exista autorización y configuración completa, cambia `EWM_ENABLED=false` a `EWM_ENABLED=true`.
5. Reinicia Flask y utiliza **Verificar conexión**.
6. Luego utiliza **Consultar pedidos de SAP EWM** y contrasta los resultados con un pedido autorizado en SAP GUI.

Variables disponibles:

```env
EWM_ENABLED=false
EWM_ORDERS_URL=
EWM_HEALTH_URL=
EWM_AUTH_TYPE=none
EWM_API_TOKEN=
EWM_USERNAME=
EWM_PASSWORD=
EWM_CA_BUNDLE=
EWM_TIMEOUT_SECONDS=15
```

`EWM_AUTH_TYPE` admite `none`, `bearer` o `basic` en esta versión. Si la empresa utiliza OAuth con flujo de obtención de token, SSO, certificados de cliente u otro mecanismo, TI debe definir el ajuste del conector. La validación TLS permanece activada.

### Contrato JSON esperado

El conector acepta una lista JSON directa o un objeto que incluya `orders` (también admite algunos envoltorios OData comunes). Cada pedido debe entregarse con campos equivalentes a este ejemplo:

```json
{
  "orders": [
    {
      "order_id": "ID_PEDIDO",
      "delivery_id": "ID_ENTREGA",
      "created_at": "2026-11-23T08:00:00Z",
      "status": "En proceso",
      "stage": "Picking",
      "stage_started_at": "2026-11-23T08:20:00Z",
      "location": "UBICACION_REGISTRADA",
      "items": [
        {
          "reference": "REFERENCIA_PRODUCTO",
          "description": "Descripción",
          "quantity": 2,
          "unit": "UN"
        }
      ],
      "handling_units": [
        {
          "hu_id": "ID_HU",
          "location": "UBICACION_HU",
          "status": "Estado HU",
          "contents": "Contenido"
        }
      ],
      "events": [
        {
          "event_time": "2026-11-23T08:20:00Z",
          "event": "Tarea de picking iniciada",
          "stage": "Picking",
          "location": "UBICACION_REGISTRADA",
          "status": "En proceso"
        }
      ]
    }
  ]
}
```

Este JSON es un **contrato de adaptación para el prototipo**, no una muestra de la respuesta real de SAP EWM. Los nombres de campos y relaciones deben mapearse a partir de la documentación y respuesta de la API corporativa. La etapa `stage` no debe inferirse si SAP no entrega un dato suficiente para establecerla.

## Tiempos y alertas

En el modo de demostración se utilizan límites ilustrativos para mostrar cómo funciona el panel. En modo SAP EWM las alertas permanecen sin configurar hasta que Operaciones confirme los límites y se definan estas variables:

```env
SLA_PICKING_MINUTES=
SLA_EMPAQUE_MINUTES=
SLA_STAGING_MINUTES=
SLA_LOADING_MINUTES=
```

El tiempo se calcula desde `stage_started_at`. Si SAP EWM no registra la hora de inicio o las marcas de tiempo necesarias, no será posible calcular la permanencia con fiabilidad.

## Configuración de inteligencia artificial

El módulo utiliza la Responses API y permanece desactivado por defecto. Antes de enviar información a un proveedor externo, la empresa debe aprobar expresamente el tratamiento de datos y definir el proveedor, modelo, credenciales y reglas de seguridad.

Solo después de esa aprobación se configuran las siguientes variables en el entorno seguro del servidor:

```env
AI_ENABLED=true
AI_DATA_APPROVED=true
OPENAI_API_KEY=CLAVE_ENTREGADA_POR_EL_ADMINISTRADOR
OPENAI_MODEL=MODELO_APROBADO_POR_TI
```

No incluyas claves en archivos compartidos, capturas o repositorios. No subas `.env` a GitHub. El servicio recibe campos logísticos resumidos y excluye el nombre del cliente; aun así, los identificadores y demás datos operativos solo deben enviarse con autorización corporativa.

Si la empresa selecciona otro proveedor o una plataforma interna, debe sustituirse el adaptador `services/ai_service.py` por el conector aprobado.

## Endpoints internos de la aplicación

| Método | Ruta | Función |
|---|---|---|
| GET | `/` | Interfaz principal |
| GET | `/api/health` | Estado básico de la aplicación |
| GET | `/api/summary` | Indicadores del conjunto actual |
| GET | `/api/orders` | Búsqueda y listado de pedidos |
| GET | `/api/orders/<order_id>` | Detalle de pedido |
| GET | `/api/alerts` | Alertas calculadas |
| GET | `/api/integration/status` | Estado de configuración EWM |
| POST | `/api/integration/check` | Verificación del endpoint configurado |
| POST | `/api/integration/refresh` | Consulta y actualización de pedidos |
| GET | `/api/ai/status` | Estado de configuración IA |
| POST | `/api/ai/report` | Generar informe |
| POST | `/api/ai/ask` | Preguntar sobre datos disponibles |
| POST | `/api/ai/delays` | Analizar alertas y demoras |

Las rutas `/api/...` son endpoints internos de esta aplicación, no URLs de SAP.

## Estructura del proyecto

```text
traza_pedidos_sap_ewm/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── services/
│   ├── __init__.py
│   ├── ewm_connector.py
│   └── ai_service.py
├── templates/
│   └── index.html
└── static/
    ├── css/styles.css
    └── js/app.js
```

## Seguridad y limitaciones

- La conexión EWM realiza solicitudes GET; no ejecuta cambios en SAP.
- No se deben utilizar endpoints o credenciales sin autorización de TI.
- No se deben poner contraseñas ni tokens en HTML, JavaScript o GitHub.
- La conexión puede requerir red interna, VPN, API Gateway o infraestructura aprobada por TI.
- La integración se valida en un ambiente no productivo siempre que la empresa lo disponga.
- La última ubicación mostrada es la última informada por la fuente, no una confirmación física en tiempo real.
- El prototipo mantiene los pedidos consultados en memoria; el almacenamiento persistente y la gestión de usuarios deben definirse antes de cualquier uso operativo.
- No se debe publicar la aplicación con información interna sin autenticación, autorización y revisión de seguridad.
- Una respuesta HTTP exitosa no prueba por sí sola que los campos, estados o relaciones estén correctamente interpretados.

## Despliegue

Para un servicio Linux compatible con Gunicorn:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`

No se debe desplegar con datos internos hasta que TI apruebe el entorno de alojamiento y su conectividad con SAP EWM.

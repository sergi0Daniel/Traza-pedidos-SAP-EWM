# TRAZA+ | Seguimiento y trazabilidad de pedidos de grifería

**Solución web para el seguimiento de pedidos dentro del centro de distribución** 
**Área:** Operaciones y Logística 
**Empresa:** Corona 
**Sistema de gestión de almacén de referencia:** SAP Extended Warehouse Management (SAP EWM) 


---

## 1. Presentación de la solución

TRAZA+ es una aplicación web diseñada para facilitar el seguimiento de los pedidos de productos de grifería durante su recorrido dentro del centro de distribución. Su propósito es ofrecer al personal de operación y supervisión una vista clara del estado de cada pedido, los productos que lo componen, las unidades de manipulación relacionadas y la última ubicación registrada en cada etapa del proceso.

La solución está centrada en **SAP EWM como fuente principal de información logística**. El seguimiento contempla las actividades de picking, empaque, traslado a la zona de despacho, asignación de puerta, cargue y salida del centro de distribución, de acuerdo con los eventos y estados disponibles en la fuente.

La aplicación reúne la información en una interfaz de consulta sencilla, de modo que el usuario pueda localizar un pedido y revisar su avance sin navegar por diferentes pantallas del sistema de origen. TRAZA+ tiene un enfoque informativo: facilita la consulta y el análisis del recorrido, sin ejecutar movimientos ni modificar documentos operativos en SAP EWM.

## 2. Propósito y beneficios operativos

La solución busca mejorar la visibilidad del proceso de despacho dentro del centro de distribución. Su utilización permite:

- Consultar en qué etapa se encuentra un pedido.
- Revisar los productos y cantidades asociados a cada pedido.
- Consultar las unidades de manipulación, cuando estén relacionadas con el pedido.
- Identificar la última ubicación registrada y revisar el historial de eventos.
- Visualizar los tiempos de permanencia y reconocer pedidos que requieren revisión.
- Contar con una vista resumida de la operación para facilitar el seguimiento por parte de los responsables.

## 3. Módulos de la aplicación

| Módulo | Funcionalidad |
|---|---|
| **Inicio** | Presenta indicadores generales de pedidos, pedidos despachados, pedidos en proceso y pedidos con tiempos que requieren revisión. Incluye una distribución por etapa para facilitar la lectura del estado de la operación. |
| **Seguimiento de pedidos** | Permite buscar pedidos mediante su identificador y otros datos relacionados disponibles, como documento de entrega o referencia de producto. Presenta los resultados y su etapa actual. |
| **Detalle del pedido** | Muestra la información general del pedido, sus productos, cantidades, unidades de manipulación, ubicación reportada y recorrido cronológico. |
| **Recorrido y trazabilidad** | Organiza los eventos registrados para mostrar el avance del pedido por las etapas logísticas y la última ubicación informada. |
| **Alertas y demoras** | Identifica pedidos cuyo tiempo de permanencia supera los límites configurados para una etapa. Las alertas orientan la revisión operativa y no sustituyen la verificación del responsable. |
| **Conexión SAP EWM** | Incluye el estado de la configuración de conexión y las acciones de verificación y consulta disponibles en el conector. |
| **Informes con IA** | Se contempla como ampliación futura para generar informes, responder preguntas sobre la operación y resumir patrones de demora. |

## 4. Alcance de la trazabilidad

TRAZA+ contempla dos niveles de consulta complementarios:

### 4.1 Seguimiento del pedido

Permite consultar el estado general del documento de salida y visualizar su avance dentro del centro de distribución. El recorrido de presentación contempla las siguientes etapas, sujetas a la disponibilidad y correspondencia de eventos en SAP EWM:

1. Registro del pedido.
2. Picking.
3. Empaque.
4. Zona de despacho o *staging*.
5. Puerta de embarque.
6. Cargue.
7. Salida del centro de distribución.

### 4.2 Seguimiento de productos y unidades de manipulación

Dentro del detalle del pedido se pueden consultar las referencias, descripciones y cantidades de los productos. Cuando la fuente proporciona la relación correspondiente, también se presentan las unidades de manipulación, su estado, contenido y ubicación registrada.

Un pedido puede incluir varios productos y unidades de manipulación. Estos elementos no necesariamente avanzan al mismo tiempo; por eso, el estado general del pedido debe interpretarse junto con el detalle disponible de sus productos y unidades de manipulación.

### 4.3 Ubicaciones y eventos

La ubicación que presenta la aplicación corresponde al último registro recibido de la fuente. El historial muestra los eventos con la fecha y hora disponibles, la actividad o etapa y la ubicación reportada. La visualización no representa geolocalización física en tiempo real: depende de los registros y de la frecuencia de actualización del origen de datos.

## 5. Experiencia de usuario y navegación

La interfaz mantiene una identidad visual basada en los tonos corporativos azul oscuro y azul claro. La navegación se organiza mediante un menú lateral con acceso directo a los módulos principales.

El flujo de uso previsto es sencillo:

1. El usuario ingresa al resumen general para revisar la actividad de los pedidos.
2. Accede a **Seguimiento de pedidos** y busca el pedido que necesita consultar.
3. Abre el detalle para revisar productos, cantidades y estado general.
4. Consulta el recorrido para identificar los eventos y la última ubicación registrada.
5. Revisa **Alertas y demoras** para priorizar los pedidos que requieren atención.

## 6. Arquitectura tecnológica

La aplicación utiliza una arquitectura web en la que la interfaz presenta la información y el backend gestiona las consultas, el procesamiento y la comunicación con los servicios externos.

```text
Usuario
 │
 ▼
Interfaz web
HTML · CSS · JavaScript
 │
 ▼
Backend de aplicación
Python · Flask
 │
 ├── Gestión de pedidos y productos
 ├── Organización de eventos y ubicaciones
 ├── Cálculo de tiempos y alertas
 │
 ▼
Conector de consulta
SAP EWM
```

### 6.1 Tecnologías

| Tecnología | Uso dentro de TRAZA+ |
|---|---|
| **Python** | Procesamiento de la información de pedidos, productos, unidades de manipulación, eventos y tiempos. |
| **Flask** | Gestión de las rutas de la aplicación y comunicación entre la interfaz y la lógica del sistema. |
| **HTML** | Estructura de las pantallas y organización de los elementos de consulta. |
| **CSS** | Presentación visual, identidad de color, distribución de componentes y adaptación de la interfaz. |
| **JavaScript** | Navegación, búsquedas, filtros, solicitudes al backend y actualización de los resultados en pantalla. |
| **Requests** | Comunicación HTTP desde el backend con el servicio de consulta configurado para SAP EWM. |
| **python-dotenv** | Lectura de parámetros de configuración definidos para el entorno de ejecución. |
| **Gunicorn** | Servidor WSGI para entornos Linux compatibles. |

## 7. Fuente de información: SAP EWM

SAP EWM es la fuente principal considerada para la trazabilidad logística. La aplicación dispone de un conector de consulta HTTP de solo lectura, preparado para recibir los datos de pedidos y organizarlos en la estructura que utiliza la interfaz.

El entorno de referencia identificado durante la revisión en SAP GUI es **PS4, mandante 100**, con el monitor de almacén `/SCWM/MON` y número de almacén **MD01**. Esta identificación corresponde al contexto de acceso observado en SAP GUI.

La aplicación diferencia los registros recibidos desde SAP EWM de los datos de demostración que se utilizan para revisar la interfaz. La consulta de información corporativa requiere que el conector tenga configurado el servicio autorizado por la compañía. Cuando se utiliza el modo de demostración, los registros que aparecen en pantalla se identifican como información ilustrativa y no como datos reales de SAP EWM.

El conector realiza solicitudes de consulta y no confirma tareas, modifica pedidos ni ejecuta movimientos en el sistema de origen.

## 8. Gestión de tiempos y alertas

La aplicación calcula el tiempo transcurrido en una etapa a partir de la marca de tiempo de inicio disponible. Cuando se configuran límites por etapa, el sistema compara el tiempo calculado con el valor establecido y presenta los pedidos que superan ese umbral.

Los límites de permanencia deben corresponder a los criterios operativos definidos para cada actividad. Una alerta indica que un pedido requiere revisión; no determina por sí sola la causa de la demora ni confirma que la mercancía se encuentre físicamente detenida.

Si no se dispone de una fecha de inicio válida o del umbral correspondiente, la aplicación no debe presentar un tiempo de permanencia como si estuviera confirmado.

## 9. Ampliación futura: inteligencia artificial

Como evolución de TRAZA+, se proyecta incorporar un módulo de inteligencia artificial para apoyar la elaboración y consulta de información operativa. Esta ampliación permitirá:

- **Generar informes:** preparar resúmenes diarios, semanales o por pedido a partir de los registros disponibles.
- **Responder preguntas:** facilitar consultas en lenguaje natural, por ejemplo, qué pedidos llevan más tiempo en empaque o cuáles están pendientes de cargue.
- **Analizar demoras:** resumir las etapas con mayor concentración de alertas y presentar observaciones para revisión.

La inteligencia artificial tendrá una función de apoyo: los estados, cantidades y tiempos serán obtenidos y calculados por la aplicación. La IA se utilizará para redactar y explicar los resultados, sin modificar pedidos ni ejecutar operaciones en SAP EWM. Su incorporación se realizará como una ampliación futura, de acuerdo con las políticas corporativas para el uso de servicios de IA y datos empresariales.

## 10. Estructura del proyecto

```text
traza_pedidos_sap_ewm/
├── app.py # Aplicación Flask y rutas del sistema
├── requirements.txt # Dependencias del proyecto
├──.env.example # Plantilla de configuración
├──.gitignore # Exclusión de archivos locales y secretos
├── README.md # Documentación de la solución
├── INICIAR_EN_WINDOWS.bat # Inicio local en Windows
├── services/
│ ├── __init__.py
│ ├── ewm_connector.py # Conector de consulta SAP EWM
│ └── ai_service.py # Servicio preparado para la ampliación de IA
├── templates/
│ └── index.html # Interfaz web principal
└── static/
 ├── css/
 │ └── styles.css # Estilos y diseño visual
 └── js/
 └── app.js # Navegación e interacción de la interfaz
```

## 11. Seguridad y uso de la información

- Las credenciales y los tokens de conexión se administran mediante variables de entorno y no deben incorporarse al código fuente ni al repositorio.
- El archivo `.env` se mantiene fuera del control de versiones; se comparte únicamente la plantilla `.env.example` sin secretos.
- La conexión con SAP EWM se limita a operaciones de consulta desde el backend.
- Los datos empresariales deben utilizarse únicamente en entornos y servicios aprobados por la compañía.
- La ubicación presentada corresponde al último registro recibido y debe interpretarse de acuerdo con la fecha de actualización.
- Antes de habilitar el acceso compartido o productivo, la publicación debe respetar los controles corporativos de autenticación, autorización y protección de información.

## 12. Puesta en marcha y soporte

La aplicación se ejecuta como un servicio web desarrollado con Flask. Las dependencias se encuentran declaradas en `requirements.txt` y la configuración del entorno se documenta en `.env.example`.

Para la operación local, el servicio se inicia desde el entorno Python del proyecto y la interfaz se consulta desde el navegador en la dirección local configurada. En un entorno corporativo, la publicación y el acceso deben ajustarse a la infraestructura y a los controles de la compañía.

La estructura del proyecto permite mantener por separado la interfaz, la lógica de procesamiento y el conector de SAP EWM, facilitando el mantenimiento y la evolución de la solución.

---

## Control del documento

| Campo | Descripción |
|---|---|
| **Nombre de la solución** | TRAZA+ – Seguimiento y trazabilidad de pedidos de grifería |
| **Área** | Operaciones y Logística |
| **Proceso** | Seguimiento interno de pedidos en el centro de distribución |
| **Fuente principal** | SAP EWM |
| **Tecnología principal** | Python y Flask |
| **Interfaz** | HTML, CSS y JavaScript |
| **Ampliación futura** | Inteligencia artificial para informes y análisis operativo |

**TRAZA+ – Visibilidad del recorrido de los pedidos dentro del centro de distribución.**

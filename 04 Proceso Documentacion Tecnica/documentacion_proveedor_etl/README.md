# Documentación de Procesos ETL

Este repositorio contiene documentación técnica relacionada con los procesos ETL desarrollados en Python y R para la extracción, transformación y carga de datos hacia estructuras de análisis. La información incluida está destinada a facilitar la comprensión, mantenimiento y evolución de los flujos de datos en el proyecto.

## 📄 Archivos incluidos

1. **`procesos_etl_original.docx`**  
   Documento que detalla los flujos ETL construidos hasta la fecha. Contiene:
   - Descripción general del proceso ETL.
   - Detalles sobre fuentes de datos, transformaciones aplicadas y destinos finales.
   - Librerías utilizadas clasificadas por función (ETL, automatización, bases de datos, APIs, nube, etc.).
   - Documentación técnica de un proceso específico de scraping (Transmilenio).
   - Buenas prácticas y organización del código.

2. **`relacion_tablas_original.xlsx`**  
   Archivo Excel que relaciona:
   - Nombre de cada proceso ETL implementado.
   - Tablas y esquemas en PostgreSQL a los que apunta cada proceso.
   - Columnas de cada tabla, incluyendo su nombre y tipo de dato.

---

## 🗓 Fecha y origen de la documentación original

- **Fecha de creación inicial:** marzo de 2025.
- **Origen:** Documentación generada por el equipo técnico de datos encargado de los procesos ETL del proyecto, basada en el desarrollo en Python y R.

---

## 🔁 Actualizaciones realizadas

Por favor, registrar a continuación cualquier actualización sobre los documentos:

- `21/07/2025` — Se actualizan procesos inactivos, se agrega proceso EMIC por operador, Planificación de buses, Historico ausentismos, Procesos disciplinarios y Pasivo vacacional. **Documentos:** procesos_etl_original y relacion_tablas_original. **Responsable:** Smith Garcia.
- `09/09/2025` — Se agrega procesos Ruteros telemetria, Paradas pasajeros y Scrapy detalle ICO, se actualiza proceso FactLubricantes y FactDescargaPaxSae, **Documentos:** procesos_etl_original y relacion_tablas_original. **Responsable:** Smith Garcia.

---

## ⚠️ Observaciones sobre su uso y vigencia

- Esta documentación **refleja el estado actual de los procesos ETL hasta septiembre de 2025**.  
- Se recomienda revisar y actualizar este repositorio en caso de:
  - Cambios en las fuentes de datos.
  - Nuevos procesos ETL o modificación de los existentes.
  - Alteraciones en los esquemas o bases de datos de destino.
- El uso de esta documentación debe complementarse con revisiones del código fuente real para confirmar la implementación actual.

---

## ✅ Recomendaciones

- Centralizar funciones comunes en módulos para facilitar mantenimiento.
- Validar rutas y credenciales mediante variables de entorno seguras.
- Documentar cada nuevo ETL en formato similar al descrito para asegurar trazabilidad.

---

> Para cualquier duda técnica relacionada con los procesos descritos, contactar al equipo de ingeniería de datos.

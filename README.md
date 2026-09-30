<div align="center">

# 🚀 Framework ETL Experimental  
### Prototipo de Pipelines para Data Warehouse

<br>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![R](https://img.shields.io/badge/R-4.x-276DC3?style=for-the-badge&logo=r&logoColor=white)](https://www.r-project.org/)
[![Delta Lake](https://img.shields.io/badge/Delta%20Lake-0.18-00ADD8?style=for-the-badge&logo=databricks&logoColor=white)](https://delta.io/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.0-FFF000?style=for-the-badge&logo=duckdb&logoColor=black)](https://duckdb.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Compatible-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Estado](https://img.shields.io/badge/Estado-Experimental-FF6B6B?style=for-the-badge)](#)

<br>

**Procesos ETL de prueba diseñados para validar arquitectura, patrones de modelado de datos y el comportamiento de los pipelines bajo condiciones operativas reales.**

</div>

---

## ✨ Propósito de este repositorio

Este repositorio contiene una colección de **pipelines ETL experimentales** construidos para explorar y poner a prueba una arquitectura modular de Data Warehouse.

El objetivo **no** fue entregar un sistema productivo definitivo, sino:

- Validar cómo se comporta un modelo dimensional con fuentes heterogéneas del mundo real  
- Probar diferentes estrategias de extracción (APIs, bases de datos, archivos, SOAP, web scraping)  
- Observar el rendimiento, problemas de calidad de datos y la complejidad de las transformaciones  
- Prototipar patrones de control de procesos, logging y notificaciones  
- Evaluar flujos de trabajo híbridos Python + R dentro del mismo ecosistema analítico  

Estos scripts funcionaron como un **laboratorio** para entender la estructura, descubrir casos límite y refinar el diseño de una solución más robusta a futuro.

---

## 🧠 Filosofía de diseño y lógica

El framework sigue un patrón claro y repetible:

```text
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐
│   Fuentes       │     │  Transformación  │     │   Data Warehouse   │
│ Heterogéneas    │ ──► │  + Reglas de     │ ──► │   Dimensional      │
│ (APIs, BDs,     │     │    Negocio       │     │   (Star Schema)    │
│  Archivos, SOAP)│     │                  │     │                    │
└─────────────────┘     └──────────────────┘     └────────────────────┘
         │                        │                         │
         │                        ▼                         │
         │              ┌──────────────────┐                │
         └─────────────►│ Control de       │◄───────────────┘
                        │ Procesos +       │
                        │ Notificaciones   │
                        └──────────────────┘


├── 00 Querys/                     # DDLs y scripts SQL para dimensiones y hechos
├── 01 Inputs/                     # Archivos de entrada estáticos (CSV, Excel, catálogos)
├── 02 Documentacion/              # Scripts de soporte y particionamiento en R
├── 03 DataWarehouse/              # Funciones SQL, roles, vistas y utilidades de la BD
├── 04 Proceso Documentacion Tecnica/# Diagnósticos del DW, validaciones PK/FK y diccionarios
├── DeltaLocal/                    # Almacenamiento local en formato Delta Lake
├── Funciones/                     # Módulos reutilizables en Python y R
├── ETL-*.py / ETL-*.R             # Pipelines ETL de extracción y transformación
├── README.md                      # Documentación principal
├── requirements.txt               # Dependencias del proyecto
└── .env                           # Configuración de variables de entorno (no versionado)
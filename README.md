# 📊 DataDash: Data Dashboard interactivo

> **v0.2.0** — Soporte Excel, filtrado interactivo, exportación de gráficos, modo oscuro y tests unitarios.

Un dashboard web ligero y potente que permite a los usuarios subir archivos CSV/Excel y visualizar sus datos al instante. La aplicación procesa la información en el backend y genera automáticamente estadísticas descriptivas, tablas de datos y gráficos interactivos (barras, líneas, pastel, dispersión) sin necesidad de configuraciones complejas.

El flujo de datos es: **subida → parseo → clasificación → derivación → caché → renderizado**. Cada etapa es un módulo independiente, diseñado para poder testearse o sustituirse sin tocar los demás.

## ✨ Características Principales

- **Subida de Archivos:** Interfaz con drag & drop para cargar archivos `.csv` y `.xlsx` (máx. 50 MB).
- **Detección Automática:** Sniffing de codificación (utf-8, latin-1, cp1252) y delimitador (`, ; | \t`) para CSV; lectura directa con openpyxl para Excel.
- **Limpieza de Datos:** Normalización de tokens nulos, eliminación de filas/columnas vacías, strip de espacios.
- **Clasificación de Columnas:** Identificación automática de variables numéricas, categóricas, temporales y de alta cardinalidad.
- **Filtrado Interactivo:** Panel de filtros en el dashboard con multi-select para categóricas, sliders de rango para numéricas y selector de fechas para temporales. Filtrado vectorizado en backend, sin mutar el dataset original.
- **Estadísticas Automáticas:** Cálculo instantáneo de media, mediana, desviación estándar, mínimos, máximos y conteo de nulos.
- **Visualización Interactiva:** Hasta 12 gráficos generados automáticamente (barras, líneas, pastel, dispersión) con Chart.js.
- **Exportación de Gráficos:** Descarga individual de gráficos en formato PNG o exportación masiva a PDF (vía jsPDF).
- **Tabla Paginada:** Vista previa de los datos con paginación del lado del servidor.
- **Modo Oscuro:** Tema claro/oscuro con persistencia en localStorage y transiciones suaves.
- **Caché en Memoria:** Dataset almacenado en memoria con TTL de 1 hora, thread-safe. Sin base de datos.
- **Almacenamiento Efímero:** El archivo subido se elimina del disco inmediatamente tras procesarse.
- **Tests Unitarios:** Suite de tests con pytest que cubre todo el pipeline de datos (carga, limpieza, clasificación, estadísticas, filtrado).

## 🛠️ Tecnologías Utilizadas

- **Backend:** Python 3, Flask (factory pattern + blueprints)
- **Análisis de Datos:** pandas, NumPy
- **Excel:** openpyxl (motor de lectura .xlsx)
- **Frontend:** HTML5, CSS3, JavaScript (vanilla)
- **UI Framework:** Bootstrap 5 (CDN)
- **Visualización:** Chart.js v4 (CDN)
- **Exportación PDF:** jsPDF (CDN)
- **Testing:** pytest

## 🚀 Instalación y Uso

### 1. Clona el repositorio

```bash
git clone https://github.com/amr299-ua/DataDash.git
cd DataDash
```

### 2. Crea y activa un entorno virtual

```bash
python -m venv venv

# En Windows:
venv\Scripts\activate

# En macOS/Linux:
source venv/bin/activate
```

### 3. Instala las dependencias

```bash
pip install -r requirements.txt
```

### 4. Ejecuta la aplicación

```bash
python app.py
```

### 5. Abre en el navegador

Visita [http://localhost:5000](http://localhost:5000), sube un CSV o Excel y explora el dashboard.

### Ejecutar tests

```bash
pytest tests/ -v
```

## 📁 Estructura del Proyecto

```plaintext
DataDash/
│
├── app.py                      # Factory pattern Flask, blueprints, error handlers
├── config.py                   # Configuración centralizada (TTL, límites, rutas)
├── requirements.txt            # Dependencias de Python
├── CLAUDE.md                   # Guía para Claude Code
│
├── core/                       # Pipeline de procesamiento de datos
│   ├── data_loader.py          # Carga CSV/Excel con sniffing de encoding y delimitador
│   ├── data_cleaner.py         # Limpieza: nulos, espacios, filas/columnas vacías
│   ├── column_classifier.py    # Clasifica columnas (numérica, categórica, temporal, otra)
│   ├── filter_engine.py        # Filtrado vectorizado sobre el DataFrame cacheado
│   ├── stats.py                # Estadísticas descriptivas vectorizadas
│   ├── chart_builder.py        # Genera configs Chart.js automáticamente
│   ├── table_builder.py        # Payloads paginados para la tabla
│   └── cache.py                # Caché en memoria, thread-safe, con TTL
│
├── routes/                     # Blueprints Flask
│   ├── main.py                 # Rutas de usuario: upload, dashboard, reset
│   └── api.py                  # API JSON: /api/charts, /api/stats, /api/table, /api/filter
│
├── templates/                  # Plantillas Jinja2
│   ├── base.html               # Layout base (navbar, toggle oscuro, flash messages, footer)
│   ├── index.html              # Página de subida con drag & drop
│   ├── dashboard.html          # Dashboard: KPIs, stats, filtros, gráficos, tabla
│   └── error.html              # Página de error genérica
│
├── static/
│   ├── css/styles.css          # Estilos personalizados con sistema de temas CSS variables
│   └── js/
│       ├── upload.js           # Validación y drag & drop del formulario
│       ├── dashboard.js        # Renderizado de gráficos Chart.js + exportación PNG/PDF
│       ├── filters.js          # Controlador de UI para el panel de filtros
│       ├── table.js            # Tabla paginada con fetch a la API
│       ├── theme.js            # Adaptador de tema para Chart.js
│       └── theme-toggle.js     # Toggle de modo oscuro con persistencia localStorage
│
├── tests/                      # Suite de tests con pytest
│   ├── conftest.py             # Configuración de pytest (sys.path)
│   └── test_pipeline.py        # Tests del pipeline: carga, limpieza, clasificación, stats, filtros
│
└── uploads/                    # Carpeta temporal (ignorada en git)
```

## 📡 Superficie de Rutas

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Formulario de subida |
| `POST` | `/upload` | Procesa CSV/Excel y redirige al dashboard |
| `GET` | `/dashboard` | Vista principal del dashboard |
| `POST` | `/reset` | Descarta el dataset actual |
| `GET` | `/api/charts` | JSON con configs de gráficos |
| `GET` | `/api/stats` | JSON con overview y stats numéricas |
| `GET` | `/api/classification` | JSON con clasificación de columnas |
| `GET` | `/api/table?page=&page_size=` | JSON con filas paginadas |
| `GET` | `/api/filter_options` | JSON con metadata de filtros disponibles |
| `POST` | `/api/filter` | Aplica filtros y devuelve datos recalculados |

Las rutas API devuelven `404` si no hay dataset en sesión, `410` si el dataset expiró (TTL = 1h).

## ✅ Roadmap Completado (v0.2.0)

- [x] Soporte para archivos Excel (`.xlsx`)
- [x] Opciones de filtrado interactivo en el frontend
- [x] Exportación de los gráficos generados a formato PNG/PDF
- [x] Modo oscuro para la interfaz web
- [x] Tests unitarios para el pipeline de datos

## 👨‍💻 Autor

Desarrollado por **amr299-ua**.

Siéntete libre de abrir *issues* o enviar *pull requests* si quieres contribuir a mejorar este proyecto.

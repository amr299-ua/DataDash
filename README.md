# 📊 DataDash: Data Dashboard interactivo

Un dashboard web ligero y potente que permite a los usuarios subir archivos CSV y visualizar sus datos al instante. La aplicación procesa la información en el backend y genera automáticamente estadísticas descriptivas, tablas de datos y gráficos interactivos (barras, líneas, pastel) sin necesidad de configuraciones complejas.

Este proyecto fue desarrollado para demostrar la integración fluida entre un backend en Python y una interfaz web dinámica orientada a la manipulación y visualización de datos.

## ✨ Características Principales

- **Subida de Archivos:** Interfaz sencilla para cargar archivos `.csv`.
- **Procesamiento de Datos:** Uso de `pandas` para limpiar, analizar y extraer estadísticas clave de los conjuntos de datos.
- **Visualización Interactiva:** Gráficos dinámicos y responsivos renderizados con `Chart.js`.
- **Generación de Tablas:** Vista previa paginada de los datos subidos en formato HTML.
- **Estadísticas Automáticas:** Cálculo instantáneo de medias, medianas, máximos, mínimos y conteo de valores nulos.

## 🛠️ Tecnologías Utilizadas

- **Backend:** Python 3, Flask
- **Análisis de Datos:** pandas
- **Frontend:** HTML5, CSS3, JavaScript
- **Librerías de Visualización:** Chart.js

## 🚀 Instalación y Uso

Sigue estos pasos para ejecutar el proyecto en tu entorno local:

### 1. Clona el repositorio

```bash
git clone https://github.com/amr299-ua/DataDash.git
cd DataDash
```

### 2. Crea y activa un entorno virtual (recomendado)

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

### 5. Abre la aplicación en tu navegador

Visita:

```txt
http://localhost:5000
```

## 📁 Estructura del Proyecto

```plaintext
csviz-dashboard/
│
├── app.py                 # Lógica principal de Flask y rutas
├── requirements.txt       # Dependencias de Python
├── uploads/               # Carpeta temporal para los CSV subidos (ignorada en git)
├── templates/
│   ├── index.html         # Página de inicio / subida de archivos
│   └── dashboard.html     # Vista principal de gráficos y tablas
└── static/
    ├── css/               # Hojas de estilo
    └── js/                # Scripts para inicializar Chart.js
```

## 📈 Próximas Mejoras (Roadmap)

- [ ] Soporte para archivos Excel (`.xlsx`)
- [ ] Opciones de filtrado interactivo en el frontend
- [ ] Exportación de los gráficos generados a formato PNG/PDF
- [ ] Modo oscuro para la interfaz web

## 👨‍💻 Autor

Desarrollado por **amr299-ua**.

Siéntete libre de abrir *issues* o enviar *pull requests* si quieres contribuir a mejorar este proyecto.

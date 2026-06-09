# Gym Tracker

Aplicación Streamlit para tracking de plan de entrenamiento personal.

## Requisitos

- Python 3.11+
- Conda (recomendado) o virtualenv

## Instalación

```bash
# Crear entorno conda
conda create -n gym_tracker python=3.11 -y
conda activate gym_tracker

# Instalar dependencias
pip install -r requirements.txt
```

## Ejecutar

```bash
cd gym_tracker
streamlit run app.py
```

La app abre en http://localhost:8501

## Datos

Los datos se guardan en `gym_tracker.db` (SQLite local). Este archivo está en `.gitignore` y **nunca se borra al actualizar el código**.

## Vistas

| Tab | Descripción |
|-----|-------------|
| 📅 Hoy | Registro diario de ejercicios y postura |
| 📊 Semana | Resumen semanal con métricas |
| 📆 Mes | Heatmap mensual y adherencia por día |
| 📋 Rutinas | Historial de rutinas y registro de nuevas |

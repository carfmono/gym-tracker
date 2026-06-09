# Gym Tracker

Aplicación Streamlit para tracking de plan de entrenamiento personal.
Base de datos: **Supabase (PostgreSQL)** — los datos persisten en la nube.

## Requisitos

- Python 3.11+
- Conda (recomendado) o virtualenv
- Cuenta en [supabase.com](https://supabase.com)

## Instalación local

```bash
# Crear entorno conda
conda create -n gym_tracker python=3.11 -y
conda activate gym_tracker

# Instalar dependencias
pip install -r requirements.txt
```

## Configurar base de datos

1. Crea un proyecto en [supabase.com](https://supabase.com)
2. Ve a **Settings → Database → Connection string → URI**
3. Copia el string (empieza con `postgresql://postgres:...`)
4. Crea el archivo `.streamlit/secrets.toml`:

```toml
DATABASE_URL = "postgresql://postgres:[PASSWORD]@[HOST].supabase.co:5432/postgres"
```

## Ejecutar localmente

```bash
streamlit run app.py
```

La app abre en http://localhost:8501

## Deploy en Streamlit Cloud

1. Push a GitHub (ya hecho)
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta el repo `gym-tracker` → rama `main` → archivo `app.py`
4. En **Advanced settings → Secrets**, pega:
   ```toml
   DATABASE_URL = "postgresql://postgres:..."
   ```
5. Deploy

## Estructura

| Archivo | Descripción |
|---------|-------------|
| `app.py` | Entrada principal, 4 tabs |
| `db.py` | Funciones de base de datos (PostgreSQL) |
| `data.py` | Plan de 7 días + rutina de postura |
| `components/` | Vistas: día, semana, mes, rutinas |

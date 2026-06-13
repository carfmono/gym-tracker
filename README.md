# Iron Age — Gym Tracker

Aplicación Streamlit de tracking de entrenamiento personal con gamificación, rutinas dinámicas y estética analog Iron Age.

**Stack:** Streamlit · Supabase (PostgreSQL + Auth) · Plotly · Python 3.11

---

## Deploy en Streamlit Cloud (producción)

### 1. Supabase — crear tablas

En el **SQL Editor** de tu proyecto Supabase, ejecuta el siguiente script:

```sql
-- Perfiles de usuario
create table if not exists profiles (
  id            bigserial primary key,
  auth_user_id  uuid unique,
  name          text not null default 'Entrenador',
  created_at    timestamptz default now()
);

-- Sesiones diarias
create table if not exists sessions (
  id         bigserial primary key,
  profile_id bigint references profiles(id) on delete cascade,
  date       date not null,
  completed  boolean default false,
  unique(profile_id, date)
);

-- Ejercicios por día
create table if not exists exercises (
  id          text primary key,
  profile_id  bigint references profiles(id) on delete cascade,
  date        date not null,
  exercise_id text not null,
  completed   boolean default false
);

-- Postura diaria
create table if not exists posture (
  id          text primary key,
  profile_id  bigint references profiles(id) on delete cascade,
  date        date not null,
  exercise_id text not null,
  completed   boolean default false
);

-- XP y nivel del usuario
create table if not exists user_xp (
  id                        bigserial primary key,
  profile_id                bigint unique references profiles(id) on delete cascade,
  total_xp                  int default 0,
  current_level             int default 1,
  current_streak            int default 0,
  longest_streak            int default 0,
  last_session_date         date,
  total_sessions            int default 0,
  total_exercises_completed int default 0
);

-- Log de eventos XP
create table if not exists xp_log (
  id          bigserial primary key,
  profile_id  bigint references profiles(id) on delete cascade,
  event_type  text not null,
  xp_gained   int default 0,
  description text default '',
  created_at  timestamptz default now()
);

-- Catálogo de logros
create table if not exists achievements (
  id              bigserial primary key,
  code            text unique not null,
  name            text not null,
  description     text,
  icon            text,
  xp_reward       int default 0,
  category        text,
  condition_type  text,
  condition_value int
);

-- Logros desbloqueados por usuario
create table if not exists user_achievements (
  id             bigserial primary key,
  profile_id     bigint references profiles(id) on delete cascade,
  achievement_id bigint references achievements(id) on delete cascade,
  unlocked_at    timestamptz default now(),
  unique(profile_id, achievement_id)
);

-- Plantillas de rutinas
create table if not exists routine_templates (
  id             bigserial primary key,
  name           text not null,
  description    text,
  goal           text,
  level          text,
  days_per_week  int,
  duration_weeks int
);

-- Ejercicios de cada plantilla
create table if not exists template_exercises (
  id            bigserial primary key,
  template_id   bigint references routine_templates(id) on delete cascade,
  day_name      text not null,
  order_index   int default 0,
  exercise_name text not null,
  sets          text,
  reps          text,
  category      text,
  is_posture    boolean default false,
  is_ankle      boolean default false
);

-- Rutinas activas del usuario
create table if not exists routines (
  id         bigserial primary key,
  profile_id bigint references profiles(id) on delete cascade,
  version    text,
  name       text not null,
  start_date date,
  end_date   date,
  notes      text
);

-- Días de una rutina activa
create table if not exists routine_days (
  id           bigserial primary key,
  routine_id   bigint references routines(id) on delete cascade,
  day_name     text not null,
  session_type text,
  order_index  int default 0
);

-- Metas semanales
create table if not exists weekly_goals (
  id                bigserial primary key,
  profile_id        bigint references profiles(id) on delete cascade,
  week_start        date not null,
  sessions_goal     int default 4,
  exercises_goal    int default 30,
  posture_days_goal int default 5,
  sessions_done     int default 0,
  exercises_done    int default 0,
  posture_days_done int default 0,
  completed         boolean default false,
  unique(profile_id, week_start)
);

-- Récords personales (incluye peso corporal con exercise_name='Peso corporal')
create table if not exists personal_records (
  id            bigserial primary key,
  profile_id    bigint references profiles(id) on delete cascade,
  exercise_name text not null,
  record_type   text not null,
  value         float not null,
  date          date,
  notes         text,
  unique(profile_id, exercise_name, record_type)
);
```

> **Supabase Auth:** habilita Email Auth en **Authentication → Providers → Email**.

### 2. Streamlit Cloud — secrets

En la app → ⚙ Settings → Secrets, pega:

```toml
SUPABASE_URL = "https://[TU_PROJECT_ID].supabase.co"
SUPABASE_KEY = "[TU_ANON_KEY]"
```

Las claves en **Supabase → Settings → API**.

### 3. Push y deploy

```bash
git add -A
git commit -m "feat: full implementation"
git push origin main
```

Streamlit Cloud redeploya automáticamente al detectar el push.

---

## Desarrollo local

```bash
conda create -n gym_tracker python=3.11 -y
conda activate gym_tracker
pip install -r requirements.txt
```

Crea `.streamlit/secrets.toml` (ignorado por git):

```toml
SUPABASE_URL = "https://[TU_PROJECT_ID].supabase.co"
SUPABASE_KEY = "[TU_ANON_KEY]"
```

```bash
streamlit run app.py
```

---

## Estructura

| Archivo / carpeta | Descripción |
|---|---|
| `app.py` | Entrada principal, routing de 4 tabs |
| `db.py` | Capa de datos (Supabase Python client) + seed |
| `gamification.py` | XP, niveles, rachas, achievements |
| `styles.py` | CSS Iron Age (paletas, tokens, componentes) |
| `ui.py` | Helpers HTML (ticket_row, dial_svg, member_card…) |
| `data.py` | Rutina de postura diaria |
| `components/auth.py` | Login / registro con Supabase Auth |
| `components/day_view.py` | Vista HOY — ejercicios, sesión, XP, log de PRs |
| `components/week_view.py` | Vista SEMANA |
| `components/month_view.py` | Vista MES — heatmap, charts |
| `components/routine_library.py` | Biblioteca de 25 rutinas con ejercicios |
| `components/routine_log.py` | Historial de rutinas |
| `components/gamification_dashboard.py` | Récords, logros, XP |
| `components/profile.py` | Perfil, peso corporal, paleta de colores |

# FlexIA — Plataforma SaaS de Rehabilitacion Biomecanica

## Estructura del proyecto

```
flexia/
├── app/          # Casos de uso (orquestacion)
├── domain/       # Modelos, interfaces y value objects
├── frontend/     # Streamlit (solo presentacion)
├── infrastructure/ # Supabase + MediaPipe (implementaciones)
├── shared/       # Config, logger, excepciones, container DI
└── tests/        # Unit + integration
```

## Setup

```bash
cp .env.example .env
# Completar .env con credenciales de Supabase

python -m venv .venv
source .venv/bin/activate   # Mac/Linux
.venv\Scripts\activate    # Windows

pip install -r requirements-dev.txt
```

## Correr la app

```bash
streamlit run frontend/main.py
```

## Correr los tests

```bash
pytest tests/
```

## Desarrolladoras

- **Desarrolladora A**: domain/, infrastructure/, app/use_cases/biomechanics/, app/use_cases/sessions/
- **Desarrolladora B**: frontend/, app/use_cases/patients/, app/use_cases/routines/, app/dto/

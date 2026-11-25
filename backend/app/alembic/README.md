# Database migrations

Run from the `backend` directory after installing the backend development dependencies:

```powershell
$env:CLOUDLOG_DATABASE_URL = "sqlite:///./cloudlog_lens.db"
python -m alembic -c alembic.ini upgrade head
```

Set `CLOUDLOG_DATABASE_URL` to a PostgreSQL URL for a PostgreSQL deployment. Migrations are the schema source of truth; application startup must not call `metadata.create_all()`.

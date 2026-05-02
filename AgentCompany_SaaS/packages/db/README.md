# Database Package

This package owns the PostgreSQL schema and database client helpers.

## Local Commands

Start PostgreSQL:

```bash
docker compose up postgres
```

Push the current schema:

```bash
npm run db:push
```

Open Drizzle Studio:

```bash
npm run db:studio
```

The default local database URL is defined in `.env.example`.

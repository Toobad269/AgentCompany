import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "./schema";

let pooledUrl: string | undefined;
let pooledClient: postgres.Sql | undefined;
let pooledDb: ReturnType<typeof drizzle<typeof schema>> | undefined;

function poolSize() {
  const configured = Number(process.env.DATABASE_POOL_MAX);
  if (Number.isFinite(configured) && configured > 0) {
    return configured;
  }

  return process.env.NODE_ENV === "production" ? 10 : 3;
}

export function createDb(databaseUrl = process.env.DATABASE_URL) {
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is required to create the database client.");
  }

  if (!pooledClient || !pooledDb || pooledUrl !== databaseUrl) {
    pooledUrl = databaseUrl;
    pooledClient = postgres(databaseUrl, {
      max: poolSize()
    });
    pooledDb = drizzle(pooledClient, { schema });
  }

  return pooledDb;
}

export function createDbConnection(databaseUrl = process.env.DATABASE_URL) {
  if (!databaseUrl) {
    throw new Error("DATABASE_URL is required to create the database client.");
  }

  const client = postgres(databaseUrl, {
    max: 1
  });
  return {
    client,
    db: drizzle(client, { schema })
  };
}

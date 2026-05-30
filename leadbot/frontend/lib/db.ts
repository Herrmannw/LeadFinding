import postgres from "postgres";

let client: postgres.Sql | null = null;

export function hasDatabaseConfig() {
  return Boolean(process.env.DATABASE_URL);
}

export function db() {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL is required for server database access");
  }

  client ??= postgres(process.env.DATABASE_URL, {
    max: 5,
    ssl: process.env.DATABASE_SSL === "disable" ? false : "require",
  });

  return client;
}

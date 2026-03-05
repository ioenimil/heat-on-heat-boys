DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_database
        WHERE datname = 'airflow_metadata'
    ) THEN
        RAISE NOTICE 'Database "airflow_metadata" already exists. Skipping create.';
    ELSE
        RAISE NOTICE 'Database "airflow_metadata" does not exist. Creating.';
    END IF;
END
$$;

SELECT 'CREATE DATABASE airflow_metadata'
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_database
    WHERE datname = 'airflow_metadata'
)
\gexec

GRANT ALL PRIVILEGES ON DATABASE airflow_metadata TO servicehub;

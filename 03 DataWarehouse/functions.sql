-- ********************************************************************************************
-- @Nombre: Query Crear usuarios y garantizar permisos en el DW
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

-- Limpieza de base de datos vacum y reindexado
-- Para windows
-- "C:\Program Files\PostgreSQL\14\bin\vacuumdb.exe" -a -U postgres -h 10.0.22.11
-- "C:\Program Files\PostgreSQL\14\bin\reindexdb.exe" -a -U postgres -h 10.0.22.11

-- Funciones **********************************************************************************
-- Obtener los schemas de la base datos
SELECT schema_name 
FROM information_schema.schemata;

-- Obtener el listado de las tablas
SELECT schemaname, tablename 
FROM pg_tables;

-- Obtener el tamaño de la base de datos
SELECT
pg_database.datname,
pg_size_pretty(pg_database_size(pg_database.datname)) AS size
FROM pg_database;

-- Obtener el tamaño de todas las tablas
-- Para obtener los valores en megas, se debe dividir los bytes entre 1048576
SELECT 
nspname AS SchemaName,
relname AS TableName,
reltuples::integer as RowsNumber,
relpages*8*1024 as SizeBytes,
pg_size_pretty(relpages::bigint*8*1024) AS SizePretty,
(relpages::bigint*8*1024) / 1048576 AS Mbsize
FROM pg_class C 
LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace) 
WHERE nspname NOT IN ('pg_catalog', 'information_schema') 
AND relkind = 'r' 
ORDER BY reltuples DESC;


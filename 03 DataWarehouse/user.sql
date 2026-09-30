-- ********************************************************************************************
-- @Nombre: Query Crear usuarios y garantizar permisos en el DW
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

-- Documentacion ******************************************************************************

-- ********************************************************************************************
-- Creacion de roles 
-- ********************************************************************************************

-- Creacion ROLE de Lectura -------------------------------------------------------------------
-- CREATE ROLE role_nombre
-- GRANT CONNECT ON DATABASE nombre_database TO role_nombre
-- GRANT USAGE ON SCHEMA nombre_schema TO role_nombre
-- GRANT SELECT ON TABLE nombre_tabla_1, nombre_tabla_2 TO role_nombre
-- GRANT SELECT ON ALL TABLES IN SCHEMA nombre_schema TO role_nombre
-- ALTER DEFAULT PRIVILEGES IN SCHEMA nombre_schema GRANT SELECT ON TABLES TO role_nombre

-- Creacion ROLE de Lectura / Escritura -------------------------------------------------------
-- CREATE ROLE role_nombre
-- GRANT CONNECT ON DATABASE nombre_database TO role_nombre
-- GRANT USAGE, CREATE ON SCHEMA nombre_schema TO role_nombre
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA nombre_schema TO role_nombre
-- ALTER DEFAULT PRIVILEGES IN SCHEMA nombre_schema GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO role_nombre
-- GRANT USAGE ON ALL SEQUENCES IN SCHEMA nombre_schema TO role_nombre
-- ALTER DEFAULT PRIVILEGES IN SCHEMA nombre_schema GRANT USAGE ON SEQUENCES TO role_nombre

-- Creacion de usuarios se debe usar la siguiente clausula ------------------------------------
-- CREATE USER nombre.apellido WITH LOGIN PASSWORD 'some_password'

-- Grantizar privilegios a los usuarios -------------------------------------------------------
-- GRANT role_nombre TO nombre.apellido


CREATE ROLE dw_operaciones_read_all
GRANT CONNECT ON DATABASE "GRMDW" TO dw_operaciones_read_all
GRANT USAGE ON SCHEMA operaciones TO dw_operaciones_read_all
GRANT SELECT ON ALL TABLES IN SCHEMA operaciones TO dw_operaciones_read_all
ALTER DEFAULT PRIVILEGES IN SCHEMA operaciones GRANT SELECT ON TABLES TO dw_operaciones_read_all

GRANT dw_contable_read_all TO "maria.marin"
GRANT dw_public_read_all TO "andres.castro", "carlos.ramirez", "daniel.cardenas", 
"david.deantonio", "diego.romero", "jhonnathan.ramirez", "jonnathan.garcia", "laura.parga", 
"luis.durango", "richard.guevara"

-- ********************************************************************************************
-- @Nombre: Query para obtener el maestro de empresas de siesa
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
f010_id as IdCompania, 
f010_razon_social as RazonSocial, 
f010_nit as Nit,
CASE 
    WHEN f010_id = 1 THEN 'ZMOIII'
    WHEN f010_id = 2 THEN 'ZMPIII'
END as Empresa
from BI_GRMUNOEREALUF06.dbo.t010_mm_companias

UNION

SELECT 
CASE 
    WHEN f010_id = 1 THEN 3
    WHEN f010_id = 2 THEN 4
END as IdCompania,
f010_razon_social as RazonSocial, 
f010_nit as Nit,
CASE 
    WHEN f010_id = 1 THEN 'ZMOV'
    WHEN f010_id = 2 THEN 'ZMPV'
END as Empresa
from BI_GRMUNOEREALUF17.dbo.t010_mm_companias

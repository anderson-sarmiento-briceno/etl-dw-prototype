-- ********************************************************************************************
-- @Nombre: Query para obtener el maestro de terceros de siesa
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
f200_id_cia as IdCompania,
f200_rowid as RowId,
f200_id as IdTercero,
f200_razon_social as RazonSocial 
from BI_GRMUNOEREALUF06.dbo.t200_mm_terceros

UNION

SELECT 
CASE 
    WHEN f200_id_cia = 1 THEN 3
    WHEN f200_id_cia = 2 THEN 4
END as IdCompania,
f200_rowid as RowId,
f200_id as IdTercero,
f200_razon_social as RazonSocial 
from BI_GRMUNOEREALUF17.dbo.t200_mm_terceros

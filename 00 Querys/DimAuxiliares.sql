-- ********************************************************************************************
-- @Nombre: Query para obtener el maestro de auxiliares flujo efectivo de siesa
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
f253_id_cia as IdCompania,
f253_rowid as RowId,
f253_id as IdAuxiliar,
f253_descripcion as Descripcion
from BI_GRMUNOEREALUF06.dbo.t253_co_auxiliares

UNION

SELECT 
CASE 
    WHEN f253_id_cia = 1 THEN 3
    WHEN f253_id_cia = 2 THEN 4
END as IdCompania,
f253_rowid as RowId,
f253_id as IdAuxiliar,
f253_descripcion as Descripcion
from BI_GRMUNOEREALUF17.dbo.t253_co_auxiliares

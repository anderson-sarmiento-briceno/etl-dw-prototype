-- ********************************************************************************************
-- @Nombre: Query para obtener el maestro de conceptos flujo efectivo de siesa
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
f274_id_cia as IdCompania,
f274_rowid as RowIdFlujoEfectivo, 
f274_id as IdFlujoEfectivo, 
f274_descripcion as Descripcion
from BI_GRMUNOEREALUF06.dbo.t274_co_fe_conceptos
WHERE f274_id <> 'Generico'

UNION

SELECT 
CASE 
    WHEN f274_id_cia = 1 THEN 3
    WHEN f274_id_cia = 2 THEN 4
END as IdCompania,
f274_rowid as RowIdFlujoEfectivo, 
f274_id as IdFlujoEfectivo, 
f274_descripcion as Descripcion
from BI_GRMUNOEREALUF17.dbo.t274_co_fe_conceptos
WHERE f274_id <> 'Generico'

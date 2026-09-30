-- ********************************************************************************************
-- @Nombre: Query para obtener el maestro de centro de costos de siesa
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT
f284_id_cia as IdCompania,
f284_rowid as RowId,
f284_id as IdCentroCosto,
f284_descripcion as Descripcion,
f284_ind_estado as IndEstado,
f284_id_ccosto_mayor as IdCentroCostoMayor,
f284_id_grupo_ccosto as IdGrupoCentroCosto
FROM BI_GRMUNOEREALUF06.dbo.t284_co_ccosto

UNION

SELECT
CASE 
    WHEN f284_id_cia = 1 THEN 3
    WHEN f284_id_cia = 2 THEN 4
END as IdCompania,
f284_rowid as RowId,
f284_id as IdCentroCosto,
f284_descripcion as Descripcion,
f284_ind_estado as IndEstado,
f284_id_ccosto_mayor as IdCentroCostoMayor,
f284_id_grupo_ccosto as IdGrupoCentroCosto
FROM BI_GRMUNOEREALUF17.dbo.t284_co_ccosto

-- ********************************************************************************************
-- @Nombre: Query para obtener el presupuesto de siesa
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT
f295_id_cia as IdCompania,
f295_rowid_auxiliar as RowIdAuxiliar,
aux.f253_id as IdAuxiliar,
f295_id_plan_presupuesto as PlanPresupuesto,
f295_rowid_ccosto as RowIdCentroCosto,
cco.f284_id as CentroDeCosto,
f295_periodo as Periodo,
f295_valor as Valor
from BI_GRMUNOEREALUF06.dbo.t295_co_presupuesto_detalle ppto
LEFT JOIN BI_GRMUNOEREALUF06.dbo.t253_co_auxiliares aux
        on ppto.f295_id_cia = aux.f253_id_cia and ppto.f295_rowid_auxiliar = aux.f253_rowid
LEFT JOIN BI_GRMUNOEREALUF06.dbo.t284_co_ccosto cco
        on ppto.f295_id_cia = cco.f284_id_cia and ppto.f295_rowid_ccosto = cco.f284_rowid

UNION

SELECT
CASE 
    WHEN f295_id_cia = 1 THEN 3
    WHEN f295_id_cia = 2 THEN 4
END as IdCompania,
f295_rowid_auxiliar as RowIdAuxiliar,
aux.f253_id as IdAuxiliar,
f295_id_plan_presupuesto as PlanPresupuesto,
f295_rowid_ccosto as RowIdCentroCosto,
cco.f284_id as CentroDeCosto,
f295_periodo as Periodo,
f295_valor as Valor
from BI_GRMUNOEREALUF17.dbo.t295_co_presupuesto_detalle ppto
LEFT JOIN BI_GRMUNOEREALUF17.dbo.t253_co_auxiliares aux
        on ppto.f295_id_cia = aux.f253_id_cia and ppto.f295_rowid_auxiliar = aux.f253_rowid
LEFT JOIN BI_GRMUNOEREALUF17.dbo.t284_co_ccosto cco
        on ppto.f295_id_cia = cco.f284_id_cia and ppto.f295_rowid_ccosto = cco.f284_rowid

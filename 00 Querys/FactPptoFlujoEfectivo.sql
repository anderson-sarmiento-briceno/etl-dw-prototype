-- ********************************************************************************************
-- @Nombre: Query para obtener el presupuesto de conceptos flujo efectivo de siesa
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
Compania,
Flujo_efectivo as FlujoEfectivo,
Plan_presupuestal as PlanPresupuestal,
Periodo,
Valor
FROM BI_GRMUNOEREALUF06.dbo.GRM_FLUJ_CIAS

UNION

SELECT 
Compania,
Flujo_efectivo as FlujoEfectivo,
Plan_presupuestal as PlanPresupuestal,
Periodo,
Valor
FROM BI_GRMUNOEREALUF17.dbo.GRM_FLUJ_CIAS

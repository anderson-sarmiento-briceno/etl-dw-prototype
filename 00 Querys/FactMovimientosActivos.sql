-- ********************************************************************************************
-- @Nombre: Query para obtener movimientos de activos fijos
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
Empresa,
Activo,
Referencia,
Descripcion,
Cargo,
Fecha,
Estado,
Tipo_de_Inventario_descripcion as TipoInventarioDescripcion,
Periodo_a_Depreciar as PeriodoDepreciar,
Periodos_Depreciados as PeriodosDepreciados,
Periodos_pendientes_por_Depreciar as PeriodosPendientesDepreciar,
Depreciacion,
Costo_Movimiento as CostoMovimiento,
Periodos_Depreciados_Movimiento as PeriodosDepreciadosMovimiento,
Centro_de_Costo_Codigo as CentroCostoCodigo,
Centro_de_Costo_Descripcion as CentroCostoDescripcion,
Identificacion,
Responsable
from BI_GRMUNOEREALUF06.dbo.GRM_ASSE_MOVE

UNION

SELECT 
Empresa,
Activo,
Referencia,
Descripcion,
Cargo,
Fecha,
Estado,
Tipo_de_Inventario_descripcion as TipoInventarioDescripcion,
Periodo_a_Depreciar as PeriodoDepreciar,
Periodos_Depreciados as PeriodosDepreciados,
Periodos_pendientes_por_Depreciar as PeriodosPendientesDepreciar,
Depreciacion,
Costo_Movimiento as CostoMovimiento,
Periodos_Depreciados_Movimiento as PeriodosDepreciadosMovimiento,
Centro_de_Costo_Codigo as CentroCostoCodigo,
Centro_de_Costo_Descripcion as CentroCostoDescripcion,
Identificacion,
Responsable
from BI_GRMUNOEREALUF17.dbo.GRM_ASSE_MOVE

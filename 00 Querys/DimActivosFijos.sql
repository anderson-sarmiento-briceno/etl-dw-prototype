-- ********************************************************************************************
-- @Nombre: Query para obtener el maestro de activos fijos
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
Nit,
Razon_Social as RazonSocial,
Activo,
Referencia,
Descripcion,
Descripcion_Abreviada as DescripcionAbreviada,
Tipo_de_Inventario_Codigo as TipoInventarioCodigo,
Tipo_de_Inventario_descripcion as TipoInventarioDescripcion,
Centro_de_Costo_Codigo as CentroCostoCodigo,
Centro_de_Costo_Descripcion as CentroCostoDescripcion,
Identificacion,
Responsable,
Fecha_adq as FechaAdq
from BI_GRMUNOEREALUF06.dbo.GRM_ASSE_RESU

UNION

SELECT 
Nit,
Razon_Social as RazonSocial,
Activo,
Referencia,
Descripcion,
Descripcion_Abreviada as DescripcionAbreviada,
Tipo_de_Inventario_Codigo as TipoInventarioCodigo,
Tipo_de_Inventario_descripcion as TipoInventarioDescripcion,
Centro_de_Costo_Codigo as CentroCostoCodigo,
Centro_de_Costo_Descripcion as CentroCostoDescripcion,
Identificacion,
Responsable,
Fecha_adq as FechaAdq
from BI_GRMUNOEREALUF17.dbo.GRM_ASSE_RESU

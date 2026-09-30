-- ********************************************************************************************
-- @Nombre: Query para obtener el especificaciones de vehiculos
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT assetnum as AssetNum
      ,assetattrid as AssetAttrId
      ,numvalue as NumValue
      ,alnvalue as AlnValue
  FROM [GRMAXPR].[dbo].[assetspec]
  WHERE classstructureid = 1002

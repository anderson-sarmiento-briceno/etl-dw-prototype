-- ********************************************************************************************
-- @Nombre: Query para obtener las especificaciones de los articulos
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT [itemnum] as ItemNum
      ,[assetattrid] as AssetAttrId
      ,[classstructureid] as ClassStructureId
      ,[numvalue] as NumValue
      ,[alnvalue] as AlnValue
      ,[changedate] as ChangeDate
      ,[changeby] as ChangeBy
  FROM [GRMAXPR].[dbo].[itemspec]

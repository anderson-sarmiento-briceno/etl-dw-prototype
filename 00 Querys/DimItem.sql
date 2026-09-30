-- ********************************************************************************************
-- @Nombre: Query para obtener el maestro de articulos
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT itemnum as ItemNum
      ,description as Description
      ,capitalized as Capitalized
      ,classstructureid as ClasSstructureId
      ,inspectionrequired as InspectionRequired
      ,itemsetid as ItemSetId
      ,orderunit as OrderUnit
      ,issueunit as IssueUnit
      ,commoditygroup as CommodityGroup
      ,itemtype as ItemType
      ,maxissue as MaxIssue
      ,status as Status
      ,grn_universalcode as GrnUniversalCode
      ,grnrepreposicion as GrnRepreposicion
      ,parte_nueva as ParteNueva
      ,grupoimpositivo as GrupoImpositivo
      ,grpimpositivo as GrpImpositivo
      ,grntax as GrnTax
      ,itemid as ItemId
      ,statusdate as StatusDate
FROM [GRMAXPR].[dbo].[item]

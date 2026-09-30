-- ********************************************************************************************
-- @Nombre: Query para obtener el fact de despachos de almacen
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT  
	    invu.grncreateddate as CreateDate
	    ,invl.invusenum as InvuseNum
	    ,invu.status as Status
      ,actualdate as ActualDate
      ,financialperiod as FinancialPeriod
      ,invl.usetype as UseType
      ,invl.assetnum as AssetNum
	    ,wor.parent as Parent
      ,refwo as Refwo
      ,linetype as LineType
      ,invuselinenum as InvuselineNum
      ,itemnum as ItemNum
      ,invl.description as Description
      ,invl.commoditygroup as CommodityGroup
      ,quantity as Quantity
      ,returnedqty as ReturnedQty
      ,unitcost as UnitCost
      ,linecost as LineCost
      ,tositeid as ToSiteid
	    ,invu.issueto as IssueTo
      ,requestnum as RequestNum
      ,invl.fromstoreloc as FromStoreloc
      ,enterby as EnterBy
      ,invl.siteid as SiteId
      ,conversion as Conversion
      ,returnagainstissue as ReturnAgainstIssue
      ,receiptscomplete as ReceiptsComplete
      ,receivedqty as ReceivedQty
      ,inspectionrequired as InspectionRequired
      ,invuselineid as InvuseLineid
  FROM [GRMAXPR].[dbo].[invuseline] invl
  LEFT JOIN [GRMAXPR].[dbo].[workorder] wor on invl.refwo = wor.wonum
  LEFT JOIN [GRMAXPR].[dbo].[invuse] invu on invl.invusenum = invu.invusenum

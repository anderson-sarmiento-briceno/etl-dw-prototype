-- ********************************************************************************************
-- @Nombre: Query para obtener el fact recepcion de materiales
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT  
	   mt.ponum as Ponum
	  ,mt.porevisionnum as PoRevisionNum
	  ,mt.siteid as SiteId
	  ,mt.itemnum as ItemNum
    ,mt.actualdate as ActualDate
	  ,pol.requireddate as RequiredDate
	  ,pol.orderdate as OrderDate
	  ,mt.quantity as Quantity 
	  ,mt.rejectqty as RejectQty
	  ,mt.linecost as LineCost
	  ,mt.financialperiod as FinancialPeriod
  FROM [GRMAXPR].[dbo].[matrectrans] mt
  LEFT JOIN [GRMAXPR].[dbo].[po] pol on mt.siteid = pol.siteid and mt.ponum = pol.ponum and mt.porevisionnum = pol.revisionnum 
  where mt.issuetype = 'RECIBO'

-- ********************************************************************************************
-- @Nombre: Query para obtener el fact de materiales
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT  
  actualdate as ActualDate
	,financialperiod as FinancialPeriod
  ,assetnum as AssetNum
	,refwo as RefWo
	,enteredastask as EnteredAsTask
	,itemnum as ItemNum
	,linetype as LineType
	,commoditygroup as CommodityGroup
	,description as Description
  ,storeloc as StoreLoc
  ,curbal as CurBal
  ,physcnt as PhysCnt
  ,actualcost as ActualCost
	,issueunit as IssueUnit
	,issuetype as IssueType
	,qtyrequested as QtyRequested
  ,quantity as Quantity
  ,unitcost as UnitCost
	,qtyreturned as QtyReturned
  ,linecost as LineCost
  ,enterby as EnterBy
  ,orgid as OrgId
  ,siteid as SiteId
  ,transdate as TransDate 
FROM [GRMAXPR].[dbo].[matusetrans]

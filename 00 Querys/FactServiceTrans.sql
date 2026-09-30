-- ********************************************************************************************
-- @Nombre: Query para obtener el fact de los servicios
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
	   financialperiod AS FinancialPeriod 
	  ,status AS Status 
	  ,ponum AS PoNum 
	  ,porevisionnum AS PoRevisionNum 
	  ,polinenum AS PoLineNum 
	  ,itemnum AS ItemNum 
	  ,commoditygroup AS CommodityGroup
	  ,issuetype AS IssueType
	  ,description AS Description
	  ,quantity AS Quantity
	  ,unitcost AS UnitCost
	  ,tax1code AS Tax1Code 
	  ,tax1 AS Tax1
	  ,linecost AS LineCost 
	  ,loadedcost AS LoadedCost 
	  ,rejectqty AS RejectQty 
	  ,rejectcost AS RejectCost 
	  ,assetnum AS AssetNum 
	  ,refwo AS RefWo 
	  ,enteredastask AS EnteredAsTask 
	  ,gldebitacct AS GlDebitAcCt 
	  ,transdate AS TransDate
	  ,enterdate AS EnterDate 
	  ,enterby AS EnterBy 
	  ,orgid AS OrgId 
	  ,siteid AS SiteId
FROM [GRMAXPR].[dbo].[servrectrans]
WHERE issuetype <> 'FACTURA'

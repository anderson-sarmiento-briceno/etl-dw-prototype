-- ********************************************************************************************
-- @Nombre: Query para obtener el maestro de Activos
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT  
       assetnum as AssetNum
      ,serialnum as SerialNum
      ,description as Description
      ,'GREEN MOVIL' as Vendor
      ,'GREEN MOVIL' Manufacturer
      ,purchaseprice as PurchasePrice
      ,installdate as InstallDate
      ,dateadd(yy, 5, installdate) as WarrantyExpDate
      ,totalcost as TotalCost
      ,ytdcost as YtdCost
      ,budgetcost as BudgetCost
      ,isrunning as IsRunning
      ,statusdate as Statusdate
      ,changedate as Changedate
      ,changeby as ChangeBy
      ,classstructureid as ClassStructureId
      ,siteid as SiteId
      ,orgid as OrgId
      ,assettype as AssetType
      ,status as Status
      ,assetid as AssetId
      ,sendersysid as SenderSysId
      ,expectedlife as ExpectedLife
      ,estendoflife as EstEndOfLife
      ,expectedlifedate as ExpectedLifeDate
FROM [GRMAXPR].[dbo].[asset]
WHERE assettype = 'CARGA'

-- ********************************************************************************************
-- @Nombre: Query para obtener las ordenes de compra
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT ponum as Ponum 
      ,description as Description 
      ,purchaseagent as PurchaseAgent 
      ,orderdate as OrderDate 
      ,requireddate as RequiredDate 
      ,potype as Potype 
      ,originalponum as OriginalPonum 
      ,status as Status 
      ,statusdate as StatusDate 
      ,vendor as Vendor 
      ,totalcost as TotalCost 
      ,priority as Priority 
      ,historyflag as HistoryFlag 
      ,po2 as PurchaseArea 
      ,vendeliverydate as VendeliveryDate 
      ,receipts as Receipts 
      ,currencycode as CurrencyCode 
      ,exchangerate as ExchangeRate 
      ,exchangedate as ExchangeDate 
      ,totaltax1 as TotalTax1 
      ,siteid as SiteId 
      ,contractrefnum as ContractRefNum 
      ,revisionnum as RevisionNum 
      ,revcomments as RevComments 
  FROM [GRMAXPR].[dbo].[po]

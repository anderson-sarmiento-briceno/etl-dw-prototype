-- ********************************************************************************************
-- @Nombre: Query para obtener el fact de la mano de obra
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
	 lab.paymenttransdate as PaymentTransDate
	,lab.transdate as TransDate
  ,lab.financialperiod as FinancialPeriod
  ,lab.laborcode as LaborCode
	,lbo.personid as PersonId
  ,lab.craft as Craft
  ,lab.refwo as RefWo
	,wor.parent as Parent
  ,lab.assetnum as AssetNum
  ,lab.transtype as TransType
	,lab.startdatetime as StartDateTime
  ,lab.finishdatetime as FinishDateTime
	,lab.payrate as PayRate
  ,lab.linecost as LineCost
  ,lab.regularhrs as RegularHrs
  ,lab.startdate as StartDate
  ,lab.starttime as StartTime
  ,lab.finishdate as FinishDate
  ,lab.finishtime as FinishTime
  ,lab.genapprservreceipt as GenApprServReceipt
  ,lab.enteredastask as EnteredAsTask
	,lab.enterby as EnterBy
  ,lab.enterdate as EnterDate
  ,lab.siteid as SiteId
  ,lab.labtransid as LabTransId
FROM [GRMAXPR].[dbo].[labtrans] lab
LEFT JOIN [GRMAXPR].[dbo].[labor] lbo ON lab.laborcode = lbo.laborcode
LEFT JOIN [GRMAXPR].[dbo].[workorder] wor ON lab.refwo = wor.wonum

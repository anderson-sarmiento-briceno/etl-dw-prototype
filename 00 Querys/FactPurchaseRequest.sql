-- ********************************************************************************************
-- @Nombre: Query para obtener la solicitud de servicios
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT  
	   prn.issuedate as IssueDate
	  ,prl.prnum as PrNum
	  ,prn.description as Description
	  ,prn.status as Status
	  ,prn.pr1 as AreaCompra
	  ,prn.requireddate as RequiredDate
	  ,prl.storeloc as StoreLoc
    ,prl.ponum as Ponum
    ,prl.polinenum as Polinenum
	  ,prl.porevisionnum as PoRevisionNum
	  ,poc.receiptscomplete as ReceiptsComplete
	  ,prl.prlinenum as PrLineNum
	  ,prl.linetype as LineType
    ,prl.itemnum as ItemNum
    ,prl.description as DescriptionItem
	  ,prl.commoditygroup as CommodityGroup
    ,prl.orderqty as OrderQty
    ,prl.orderunit as OrderUnit
    ,poc.orderqty as OrderQtyPurchase
    ,poc.receivedqty as ReceivedQty 
    ,prl.tax1code as Tax1Code
    ,prl.unitcost as UnitCost
    ,prl.linecost as LineCost
    ,prl.tax1 as Tax1
    ,prl.loadedcost as LoadedCost
	  ,prl.refwo as RefWo
    ,prl.enteredastask as EnteredasTask
    ,prl.assetnum as AssetNum
    ,prl.reqdeliverydate as ReqDeliveryDate
    ,prl.vendeliverydate as VenDeliveryDate
    ,prl.enterdate as EnterDate
    ,prl.enterby as EnterBy
    ,prl.requestedby as RequestedBy
    ,prl.receiptreqd as ReceiptReqd
    ,prl.inspectionrequired as InspectionRequired
    ,prl.siteid as SiteId
    ,prl.orgid as OrgId
    ,prl.positeid as PositeId
  FROM [GRMAXPR].[dbo].[prline] prl
  LEFT JOIN [GRMAXPR].[dbo].[pr] prn ON prl.prnum = prn.prnum and prl.siteid = prn.siteid
  LEFT JOIN [GRMAXPR].[dbo].[poline] poc ON prl.polineid = poc.polineid

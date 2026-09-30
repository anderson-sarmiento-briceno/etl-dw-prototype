-- ********************************************************************************************
-- @Nombre: Query para obtener las lienas de las ordenes de compra
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT ponum as PoNum
      ,itemnum as ItemNum
      ,storeloc as StoreLoc
      ,modelnum as ModelNum
      ,catalogcode as CatalogCode
      ,orderqty as OrderQty
      ,orderunit as OrderUnit
      ,unitcost as UnitCost
      ,receivedqty as ReceivedQty
      ,receivedunitcost as ReceivedUnitCost
      ,receivedtotalcost as ReceivedTotalCost
      ,rejectedqty as RejectedQty
      ,vendeliverydate as VenDeliveryDate
      ,enterdate as EnterDate
      ,description as Description
      ,requestedby as RequestedBy
      ,reqdeliverydate as ReqDeliveryDate
      ,issue as Issue
      ,polinenum as PolineNum
      ,taxed as Taxed
      ,assetnum as AssetNum
      ,linecost as LineCost
      ,tax1code as Tax1Code
      ,tax1 as Tax1
      ,receiptreqd as ReceiptReqd
      ,manufacturer as Manufacturer
      ,category as Category
      ,loadedcost as LoadedCost
      ,receiptscomplete as ReceiptsComplete
      ,inspectionrequired as InspectionRequired
      ,proratecost as ProrateCost
      ,polineid as PolineId
      ,linecost2 as LineCost2
      ,siteid as SiteId
      ,refwo as RefWo
      ,enteredastask as EnteredAsTask
      ,linetype as LineType
      ,contractrefnum as ContractRefNum
      ,commoditygroup as CommodityGroup
      ,tositeid as ToSiteId
      ,conversion as Conversion
      ,mktplcitem as MktplcItem
      ,revisionnum as RevisionNum
      ,revstatus as RevStatus
      ,taxexempt as TaxExempt
      ,restype as ResType
      ,linecost1 as LineCost1
      ,loadedcost1 as LoadedCost1
      ,obsequio as Obsequio
      ,descuento as Descuento
  FROM [GRMAXPR].[dbo].[poline]

-- ********************************************************************************************
-- @Nombre: Query para obtener el fact de los servicios asociados a las OT
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
    ser.wonum as WoNum
    ,wor.parent as Parent
    ,wor.assetnum as AssetNum
    ,wor.status as Status
    ,wor.worktype as WorkType
    ,wor.woclass as WoClass
    ,itemnum as ItemNum
    ,ser.description as Description
    ,itemqty as ItemQty
    ,unitcost as UnitCost
    ,linecost as LineCost
    ,orderunit as OrderUnit
    ,pr as Pr
    ,prlinenum as PrlineNum
    ,requestby as RequestBy
    ,requestnum as RequestNum
    ,requiredate as RequireDate
    ,ser.siteid as SiteId
    ,ser.vendor as Vendor
    ,vendorpackcode as VendorPackCode
    ,vendorpackquantity as VendorPackQuantity
    ,vendorunitcost as VendorUnitCost
    ,vendorwarehouse as VendorWareHouse
    ,wpitemid as WpItemId
FROM [GRMAXPR].[dbo].[wpservice] ser
LEFT JOIN [dbo].[workorder] wor on ser.wonum = wor.wonum

-- ********************************************************************************************
-- @Nombre: Query para obtener el fact de materiales pendientes
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
    w2.itemnum as ItemNum,
    w.parent as Parent,
    w2.wonum as WoNum,
    w.status as Status,
    w.woclass as WoClass,    
    w2.itemqty as ItemQty,
    w2.requiredate as RequireDate,
    w2.siteid as SiteId
FROM 
    [GRMAXPR].[dbo].[wpmaterial] w2
LEFT JOIN 
    [GRMAXPR].[dbo].[workorder] w ON w2.wonum = w.wonum
WHERE 
    w.status = 'EMAT'
ORDER BY 
    w2.requiredate DESC
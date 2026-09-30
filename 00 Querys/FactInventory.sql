-- ********************************************************************************************
-- @Nombre: Query para obtener el Inventario
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
       invy.itemnum as ItemNum
      ,item.status as Status 
      ,invy.location as Location
      ,invy.siteid as SiteId
      ,invy.manufacturer as Manufacturer
      ,invy.orderunit as OrderUnit
      ,invy.sstock as Sstock
      ,invy.vendor as Vendor
      ,invy.abctype as AbcType
      --,invy.controlacc as ControlAcc
      --,invy.invcostadjacc as InvCostAdjacc
      ,invy.issueunit as IssueUnit
      ,invy.lastissuedate as LastIssueDate
      ,invy.deliverytime as DeliveryTime
      ,invy.issue1yrago as Issue1yrAgo
      ,invy.issue2yrago as Issue2yrAgo
      ,invy.issue3yrago as Issue3yrAgo
      ,invy.issueytd as IssueYtd
      ,invy.maxlevel as MaxLevel
      ,invy.minlevel as MinLevel
      ,invy.orderqty as OrderQty
      ,invy.statusdate as StatusDate
	    ,invb.curbal as CurBal
	    ,invb.physcnt as PhysCnt
	    ,invb.physcntdate as PhysCntDate
	    ,invb.reconciled as Reconciled
	    ,invc.stdcost as StdCost
      ,invc.avgcost as AvgCost
      ,invc.lastcost as LastCost
      --,invc.invcostadjacc as InvCostAdjAcc
	    ,invr.actualqty as ActualQty
	    ,invr.reservedqty as ReservedQty
	    ,invr.pendingqty as PendingQty
	    ,invb.curbal * invc.avgcost as TotalCostInventory
	    ,ISNULL(invb.curbal, 0) - ISNULL(invr.reservedqty, 0) as CurBalAvailable
	    ,trsy.QtyTransit
FROM [GRMAXPR].[dbo].[inventory] invy
--Join con Item
LEFT JOIN [GRMAXPR].dbo.item item 
		on invy.itemnum = item.itemnum
--Join con la tabla de balances
LEFT JOIN (SELECT itemnum
			,location
			,siteid
			,curbal
			,physcnt
			,physcntdate
			,reconciled
		FROM [GRMAXPR].[dbo].[invbalances]) invb 
		on invy.itemnum = invb.itemnum
		and invy.location = invb.location
		and invy.siteid = invb.siteid
--Join con la tabla de costo
LEFT JOIN (SELECT itemnum
			,location
			,siteid
			,stdcost
			,avgcost
			,lastcost
			,invcostadjacc
		FROM [GRMAXPR].[dbo].[invcost]) invc
		on invy.itemnum = invc.itemnum
		and invy.location = invc.location
		and invy.siteid = invc.siteid
--Join con la tabla de reservas
LEFT JOIN (SELECT itemnum
			,location
			,siteid
			,sum(actualqty) as actualqty
			,sum(reservedqty) as reservedqty
			,sum(pendingqty) as pendingqty
		FROM [GRMAXPR].[dbo].[invreserve]
		group by itemnum, location, siteid) invr
		on invy.itemnum = invr.itemnum
		and invy.location = invr.location
		and invy.siteid = invr.siteid
--Join con compras para saber el transito
LEFT JOIN (SELECT itemnum
			  ,storeloc
			  ,siteid
			  ,sum(orderqty - ISNULL(receivedqty, 0)) as QtyTransit
		FROM [GRMAXPR].[dbo].[poline] pol
		INNER JOIN (select [ponum], [revisionnum]
					from (select v.*,
							  row_number() over (partition by ponum order by revisionnum desc) as seqnum_desc
						  from [GRMAXPR].[dbo].[po] v
						 ) v
					where seqnum_desc = 1 and status in ('APROB', 'ENVPROV')) poc 
					on pol.ponum = poc.ponum and pol.revisionnum = poc.revisionnum
		where storeloc is not null and receiptscomplete = 0 
		group by itemnum, storeloc, siteid) trsy 
		on invy.itemnum = trsy.itemnum
		and invy.location = trsy.storeloc
		and invy.siteid = trsy.siteid 

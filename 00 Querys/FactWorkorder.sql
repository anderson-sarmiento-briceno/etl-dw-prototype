-- ********************************************************************************************
-- @Nombre: Query para obtener el fact de las ordenes de trabajo
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT wonum as WoNum
      ,wor.description as DescriptionOt
      ,wor.siteid as SiteId
	    ,woclass as WoClass
      ,status as Status
      ,assetnum as AssetNum
      ,worktype as WorkType
      ,statusdate as StatusDate
	    ,cla.description as DescriptionClass
	    ,wor.parent as Parent
	    ,lectodom as LectOdom
      ,fechalectodom as FechaLectodom
      ,jpnum as JpNum
	    ,pluscjprevnum as PluscJpRevnum
      ,pmnum as PmNum
	    ,wopriority as WoPriority
      ,schedstart as SchedStart
      ,schedfinish as SchedFinish
	    ,actstart as ActStart
      ,actfinish as ActFinish
      ,estdur as EstDur
	    ,reportdate as ReportDate
      ,taskid as TaskId
      ,istask as IsTask
      ,route as Route
      ,estmatcost as EstMatCost
      ,actmatcost as ActMatCost
	    ,actservcost as ActServCost
	    ,estservcost as EstServCost
	    ,workorderid as WorkOrderId
  FROM [GRMAXPR].[dbo].[workorder] wor
  LEFT JOIN [dbo].[classstructure] cla on wor.classstructureid = cla.classstructureid

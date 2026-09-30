-- ********************************************************************************************
-- @Nombre: Query para obtener el fact de las lecturas de medidor
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
       assetnum as AssetNum
      ,metername as MeterName
      ,readingsource as ReadingSource
      ,readingtype as ReadingType
      ,delta as Delta
      ,reading as Reading
      ,rollover as RollOver
      ,measureunitid as MeasureUnitId
      ,readingdate as ReadingDate
      ,inspector as Inspector
      ,rolldownsource as RollDownSource
      ,enterby as EnterBy
      ,enterdate as EnterDate
      ,siteid as SiteId
      ,modified as Modified
      ,reason as Reason
      ,meterreadingid as MeterReadingId
FROM [GRMAXPR].[dbo].[meterreading]

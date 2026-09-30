-- ********************************************************************************************
-- @Nombre: Query para obtener el fact de los kilometros
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT assetnum as AssetNum
      ,metername as MeterName 
      ,active as Active 
      ,avgcalcmethod as AvgCalcMethod 
      ,slidingwindowsize as SlidingWindowSize 
      ,lifetodate as LifeToDate 
      ,changeby as ChangeBy 
      ,changedate as ChangeDate 
      ,remarks as Remarks 
      ,lastreadingdate as LastReadingDate 
      ,lastreading as LastReading 
      ,average as Average 
      ,readingtype as ReadingType 
      ,assetmeterid as AssetMeterid 
  FROM [GRMAXPR].[dbo].[assetmeter]

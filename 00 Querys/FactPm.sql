-- ********************************************************************************************
-- @Nombre: Query para obtener el fact de los Mantenimientos Preventivos
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT
       pmm.assetnum as AssetNum
	    ,pmm.pmnum as PmNum
      ,pmm.description as Description
      ,pmm.jpnum as JpNum
      ,pmm.worktype as WorkType
      ,pmm.lastcompdate as LastCompDate
      ,pmm.laststartdate as LastStartDate
      ,pmm.firstdate as FirstDate
      ,pmm.frequency as FrequencyPm
      ,pmm.pmcounter as PmCounter
      ,pmm.jpseqinuse as JpEeqinUse
      ,pmm.nextdate as NextDate
      ,pmm.storeloc as StoreLoc
      ,pmm.frequnit as FreqUnit
      ,pmm.wostatus as WoStatus
      ,pmm.siteid as SiteId
      ,pmm.status as Status
      ,pmm.grn_startpmfreq as GrnStartPmFreq
	    ,pmt.metername as MeterNamePm
      ,pmt.frequency as Frequency
      ,pmt.tolerance as Tolerance
      ,pmt.lastpmwogenread as LastPmWoGenRead
      ,pmt.lastpmwogenreaddt as LastPmWoDenReadDt
      ,pmt.readingatnextwo as ReadingAtNextWo
      ,pmt.ltdreadatnextwo as LtdReadAtNextWo
      ,pmt.ltdlastpmworead as LtdLastPmWoRead
	    ,ass.metername as MeterName
	    ,ass.lifetodate as LifetoDate
	    ,ass.lastreadingdate as LastReadingDate
	    ,ass.lastreading as LastReading
	    ,ass.average as Average
      ,pmm.changedate as ChangeDate
      ,pmm.changeby as ChangeBy
FROM [GRMAXPR].[dbo].[pm] pmm
LEFT JOIN [GRMAXPR].[dbo].[pmmeter] pmt on pmm.pmnum = pmt.pmnum and pmm.siteid = pmt.siteid
LEFT JOIN (SELECT 
			[assetnum]
			,[metername]
			,[lifetodate]
			,[lastreadingdate]
			,[lastreading]
			,[average]
			FROM [GRMAXPR].[dbo].[assetmeter]
			WHERE [measureunitid] = 'KMS') ass on pmm.assetnum = ass.assetnum

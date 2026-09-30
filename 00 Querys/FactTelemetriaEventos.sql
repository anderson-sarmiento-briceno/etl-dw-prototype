-- ********************************************************************************************
-- @Nombre: Query para los eventos de la telemtria en la base de datos de duckdb
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

-- ********************************************************************************************
-- Query para los eventos
-- ********************************************************************************************

-- EV10: Accidentes ---------------------------------------------------------------------------
(
    WITH tabla_anterior AS (
    SELECT
        idVehiculo as IdVehiculo
        ,fecha as Fecha
        ,fechaHoraLecturaDato AS FechaHoraLecturaDato
        ,idRuta as IdRuta
        ,Latitud
        ,Longitud
        ,HOUR(fechaHoraLecturaDato) AS Hora
        ,'' AS Variable
        ,'' AS Unidad
        ,'' AS NivelAlarma
        ,codigoEvento AS Tabla
        ,'' AS FechaEventoId
    FROM EV10
    ORDER BY idVehiculo, fechaHoraLecturaDato
    ) 

SELECT e.*, v.FechaHora, v.Conductor, v.NombreConductor, v.LINEA
FROM tabla_anterior e
ASOF LEFT JOIN FactTablaVehiculo v
ON e.IdVehiculo = v.CodigoBus
AND e.Fecha = v.Fecha
AND e.FechaHoraLecturaDato >= v.FechaHora
ORDER BY e.IdVehiculo, e.FechaHoraLecturaDato
)

UNION ALL

-- EV19: Comportamiento Anomalo del operador --------------------------------------------------
(
    WITH tabla_anterior AS (
    SELECT
        idVehiculo as IdVehiculo
        ,fecha as Fecha
        ,fechaHoraLecturaDato AS FechaHoraLecturaDato
        ,idRuta as IdRuta
        ,Latitud
        ,Longitud
        ,HOUR(fechaHoraLecturaDato) AS Hora
        ,codigoComportamientoAnomalo AS Variable
        ,'' AS Unidad
        ,'' AS NivelAlarma
        ,codigoEvento AS Tabla
        ,'' AS FechaEventoId
    FROM EV19
    WHERE codigoComportamientoAnomalo <> 4
    ORDER BY idVehiculo, fechaHoraLecturaDato
    ) 

SELECT e.*, v.FechaHora, v.Conductor, v.NombreConductor, v.LINEA
FROM tabla_anterior e
ASOF LEFT JOIN FactTablaVehiculo v
ON e.IdVehiculo = v.CodigoBus
AND e.Fecha = v.Fecha
AND e.FechaHoraLecturaDato >= v.FechaHora
ORDER BY e.IdVehiculo, e.FechaHoraLecturaDato
)

UNION ALL

-- ********************************************************************************************
-- Query para las alarmas
-- ********************************************************************************************

-- ALA1: Aceleracion Brusca -------------------------------------------------------------------
(
    WITH tabla_anterior AS (
    SELECT 
        idVehiculo as IdVehiculo
        ,fecha as Fecha
        ,fechaHoraLecturaDato AS FechaHoraLecturaDato
        ,idRuta as IdRuta
        ,Latitud
        ,Longitud
        ,HOUR(fechaHoraLecturaDato) AS Hora
        ,aceleracionVehiculo as Variable
        ,'ms2' AS Unidad
        ,nivelAlarma as NivelAlarma
        ,codigoAlarma AS Tabla
        ,'' AS FechaEventoId
    FROM ALA1
    ORDER BY idVehiculo, fechaHoraLecturaDato
    )

SELECT e.*, v.FechaHora, v.Conductor, v.NombreConductor, v.LINEA
FROM tabla_anterior e
ASOF LEFT JOIN FactTablaVehiculo v
ON e.IdVehiculo = v.CodigoBus
AND e.Fecha = v.Fecha
AND e.FechaHoraLecturaDato >= v.FechaHora
ORDER BY e.IdVehiculo, e.FechaHoraLecturaDato
)

UNION ALL

-- ALA2: Frenada Brusca -----------------------------------------------------------------------
(
    WITH tabla_anterior AS (
    SELECT 
        t.idVehiculo as IdVehiculo,
        t.fecha as Fecha,
        t.fechaHoraLecturaDato AS FechaHoraLecturaDato,
        t.idRuta as IdRuta,
        t.Latitud,
        t.Longitud,
        t.Hora,
        ROUND(t.Variable, 0) AS Variable,
        'ms2' AS Unidad,
        t.NivelAlarma,
        t.codigoAlarma AS Tabla,
        CONCAT(t.idVehiculo, '-', CAST(t.Fecha AS VARCHAR), '-', CAST(SUM(CASE WHEN t.DiffSeg >= 10 OR t.DiffSeg IS NULL THEN 1 ELSE 0 END) OVER (PARTITION BY t.IdVehiculo, t.Fecha ORDER BY t.fechaHoraLecturaDato) AS VARCHAR)) AS FechaEventoId
    FROM (
        SELECT
            idVehiculo,
            fecha,
            fechaHoraLecturaDato,
            ABS(DATEDIFF('second', fechaHoraLecturaDato, LAG(fechaHoraLecturaDato, 1) OVER (PARTITION BY idVehiculo, fecha ORDER BY fechaHoraLecturaDato))) AS DiffSeg,
            idRuta,
            Latitud,
            Longitud,
            HOUR(fechaHoraLecturaDato) AS Hora,
            aceleracionVehiculo as Variable,
            nivelAlarma,
            codigoAlarma
        FROM ALA2) t
    ) 

SELECT e.*, v.FechaHora, v.Conductor, v.NombreConductor, v.LINEA
FROM tabla_anterior e
ASOF LEFT JOIN FactTablaVehiculo v
ON e.IdVehiculo = v.CodigoBus
AND e.Fecha = v.Fecha
AND e.FechaHoraLecturaDato >= v.FechaHora
ORDER BY e.IdVehiculo, e.FechaHoraLecturaDato
)

UNION ALL

-- ALA3: Exceso Velocidad ---------------------------------------------------------------------
(
    WITH tabla_anterior AS (
    SELECT 
        t.idVehiculo as IdVehiculo,
        t.fecha as Fecha,
        t.fechaHoraLecturaDato AS FechaHoraLecturaDato,
        t.idRuta as IdRuta,
        t.Latitud,
        t.Longitud,
        t.Hora,
        ROUND(t.Variable, 0) AS Variable,
        'kmh' AS Unidad,
        t.NivelAlarma,
        t.codigoAlarma AS Tabla,
        CONCAT(t.idVehiculo, '-', CAST(t.Fecha AS VARCHAR), '-', CAST(SUM(CASE WHEN t.DiffSeg >= 5 OR t.DiffSeg IS NULL THEN 1 ELSE 0 END) OVER (PARTITION BY t.IdVehiculo, t.Fecha ORDER BY t.fechaHoraLecturaDato) AS VARCHAR)) AS FechaEventoId
    FROM (
        SELECT
            idVehiculo,
            fecha,
            fechaHoraLecturaDato,
            ABS(DATEDIFF('second', fechaHoraLecturaDato, LAG(fechaHoraLecturaDato, 1) OVER (PARTITION BY idVehiculo, fecha ORDER BY fechaHoraLecturaDato))) AS DiffSeg,
            idRuta,
            Latitud,
            Longitud,
            HOUR(fechaHoraLecturaDato) AS Hora,
            velocidadVehiculo as Variable,
            nivelAlarma,
            codigoAlarma
        FROM ALA3) t
    )

SELECT e.*, v.FechaHora, v.Conductor, v.NombreConductor, v.LINEA
FROM tabla_anterior e
ASOF LEFT JOIN FactTablaVehiculo v
ON e.IdVehiculo = v.CodigoBus
AND e.Fecha = v.Fecha
AND e.FechaHoraLecturaDato >= v.FechaHora
ORDER BY e.IdVehiculo, e.FechaHoraLecturaDato
)

UNION ALL

-- ALA10: Desgaste de Pastillas ---------------------------------------------------------------
(
    WITH tabla_anterior AS (
    SELECT 
        idVehiculo AS IdVehiculo,
        fecha AS Fecha,
        fechaHoraLecturaDato AS FechaHoraLecturaDato,
        idRuta AS IdRuta,
        Latitud,
        Longitud,
        HOUR(fechaHoraLecturaDato) AS Hora,
        estadoDesgasteFrenos AS Variable,
        'pct' AS Unidad,
        'NIV5' AS NivelAlarma,
        'ALA10' AS Tabla,
        '' AS FechaEventoId,
        ROW_NUMBER() OVER (PARTITION BY idVehiculo, fecha ORDER BY fechaHoraLecturaDato DESC) AS RowNum
    FROM 
        P60
    WHERE 
        estadoDesgasteFrenos <= 15
)
SELECT 
    e.IdVehiculo, e.Fecha, e.FechaHoraLecturaDato, e.IdRuta, e.Latitud, e.Longitud, e.Hora, 
    e.Variable, e.Unidad, e.NivelAlarma, e.Tabla, e.FechaEventoId, v.FechaHora, v.Conductor, 
    v.NombreConductor, v.LINEA
FROM 
    tabla_anterior e
ASOF LEFT JOIN FactTablaVehiculo v
ON e.IdVehiculo = v.CodigoBus
AND e.Fecha = v.Fecha
AND e.FechaHoraLecturaDato >= v.FechaHora
WHERE 
    e.RowNum = 1
ORDER BY 
    e.IdVehiculo, e.FechaHoraLecturaDato
)

-- ********************************************************************************************
-- @Nombre: Query para eventos 1 de la telemtria en la base de datos de duckdb
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

-- EV1: Pasajeros -----------------------------------------------------------------------------
WITH Pasajeros AS (
    SELECT
        idVehiculo As IdVehiculo
        ,strftime(fecha, '%Y-%m-%d') AS Fecha
        ,fechaHoraLecturaDato AS FechaHoraLecturaDato
        ,idRuta AS IdRuta
        ,Latitud
        ,Longitud
        ,HOUR(fechaHoraLecturaDato) AS Hora
        ,estimacionOcupacionAbordo AS Abordo
        ,estimacionOcupacionBajan AS Bajan
        ,estimacionOcupacionSuben AS Suben
    FROM EV1
    ORDER BY idVehiculo, fechaHoraLecturaDato
    ) 

SELECT e.Fecha, e.Hora, v.Linea, v.SentidoRuta, v.Descripcion, e.Abordo, e.Bajan, e.Suben
FROM Pasajeros e
ASOF LEFT JOIN FactTablaVehiculo v
ON e.IdVehiculo = v.CodigoBus
AND e.Fecha = v.Fecha
AND e.FechaHoraLecturaDato >= v.FechaHora
ORDER BY e.IdVehiculo, e.FechaHoraLecturaDato

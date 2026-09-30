-- ********************************************************************************************
-- @Nombre: Query para obtener las sombras del p20
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT *, FLOOR(DiffSeg / 10) * 10 AS bin 
FROM (
    SELECT 	idVehiculo
            ,fecha
            ,idRuta
            ,Latitud
            ,Longitud
            ,HOUR(fechaHoraLecturaDato) AS hora
            ,DATEDIFF('second', fechaHoraLecturaDato, fechaHoraEnvioDato) AS DiffSeg
            ,CASE 
                WHEN DATEDIFF('second', fechaHoraLecturaDato, fechaHoraEnvioDato) > 5
                THEN TRUE 
                ELSE FALSE 
        END AS sombra
    from p20 
    ORDER by idVehiculo, fechaHoraEnvioDato
)
WHERE sombra = TRUE AND Latitud > 0

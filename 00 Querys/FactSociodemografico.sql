--*********************************************************************************************
-- @Nombre: Query para extraer informacion sociodemografica de los empleados
-- @Autor: Anderson Sarmiento
--*********************************************************************************************

SELECT DISTINCT
    gn_empre.nom_empr AS [Empresa],
    bi_emple.cod_inte AS [Codigo operador],
    nm_contr.nro_cont AS [No Contrato],
    nm_contr.cod_empl AS [Cedula Empleado],
    bi_emple.nom_empl AS [Nombres],
    bi_emple.ape_empl AS [Apellidos],
    bi_cargo.nom_carg AS [Cargo],
    nm_contr.tip_cont AS [Tipo Contrato],
    nm_contr.fec_ingr AS [Fecha Ingreso],
    nm_contr.fec_venc AS [Fecha Retiro],
    nm_contr.ind_acti AS [Indicador Actividad],
    nm_contr.fec_deja AS [Fecha Novedad],
    gn_ccost.nom_ccos AS [Centro Costo],
    nm_mdeja.nom_mdej AS [Motivo Retiro],
    nm_escar.nom_esca AS [Detalle Retiro],
    bi_emple.sex_empl AS [Genero Empleado],
    bi_emple.box_mail AS [Correo Corporativo],
    bi_emple.eee_mail AS [Correo Personal],
    bi_emple.fec_naci AS [Fecha de nacimiento],
    DATEDIFF(YEAR, bi_emple.fec_naci, GETDATE()) AS [Edad Empl],
    bi_emple.dir_resi AS [Direccion],
    bi_emple.tel_movi AS [Telefono],
    bi_emple.est_civi AS [Estado civil],
    bi_emple.cab_fami as [Cabeza Hogar],
    CASE 
        WHEN DATEPART(YEAR, CAST(bi_emple.fec_naci AS DATE)) BETWEEN 1946 AND 1964 THEN 'BabyBoomer'
        WHEN DATEPART(YEAR, CAST(bi_emple.fec_naci AS DATE)) BETWEEN 1965 AND 1979 THEN 'Generacion X'
        WHEN DATEPART(YEAR, CAST(bi_emple.fec_naci AS DATE)) BETWEEN 1980 AND 2000 THEN 'Generacion Y'
        WHEN DATEPART(YEAR, CAST(bi_emple.fec_naci AS DATE)) BETWEEN 2001 AND 2010 THEN 'Generacion Z'
        ELSE 'Alfa'
    END AS [Generacion],
    CASE
        WHEN DATEPART(YEAR, CAST(bi_emple.fec_naci AS DATE)) BETWEEN 1946 AND 1964 THEN 
            ' ' + CAST(DATEPART(YEAR, GETDATE()) - 1964 AS VARCHAR) + '-' + CAST(DATEPART(YEAR, GETDATE()) - 1946 AS VARCHAR)
        WHEN DATEPART(YEAR, CAST(bi_emple.fec_naci AS DATE)) BETWEEN 1965 AND 1979 THEN 
            ' ' + CAST(DATEPART(YEAR, GETDATE()) - 1979 AS VARCHAR) + '-' + CAST(DATEPART(YEAR, GETDATE()) - 1965 AS VARCHAR)
        WHEN DATEPART(YEAR, CAST(bi_emple.fec_naci AS DATE)) BETWEEN 1980 AND 2000 THEN 
            ' ' + CAST(DATEPART(YEAR, GETDATE()) - 2000 AS VARCHAR) + '-' + CAST(DATEPART(YEAR, GETDATE()) - 1980 AS VARCHAR)
        WHEN DATEPART(YEAR, CAST(bi_emple.fec_naci AS DATE)) BETWEEN 2001 AND 2010 THEN 
            ' ' + CAST(DATEPART(YEAR, GETDATE()) - 2010 AS VARCHAR) + '-' + CAST(DATEPART(YEAR, GETDATE()) - 2001 AS VARCHAR)
        ELSE 
            'Mayor de ' + CAST(DATEPART(YEAR, GETDATE()) - 2010 AS VARCHAR)
    END AS [RangoEdades],
    bi_edfor.mod_acad AS [Modalidad Academica],
    BI_DMODA.COD_PROF AS [Profesion],
    bi_DMODA.NOM_PROF AS [Nombre Profesion],
    (DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()) * 12) + 
    DATEDIFF(MONTH, DATEADD(YEAR, DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()), nm_contr.fec_ingr), GETDATE()) + 
    CASE 
        WHEN DAY(GETDATE()) < DAY(nm_contr.fec_ingr) THEN 
            (DAY(GETDATE()) + DAY(EOMONTH(GETDATE())) - DAY(nm_contr.fec_ingr)) / 30 
        ELSE 
            (DAY(GETDATE()) - DAY(nm_contr.fec_ingr)) / 30 
    END AS [Antiguedad],
    CASE 
        WHEN bi_emple.sex_empl = 'M' AND DATEDIFF(YEAR, bi_emple.fec_naci, GETDATE()) >= 61 THEN 'Proximo a pensionar'
        WHEN bi_emple.sex_empl = 'F' AND DATEDIFF(YEAR, bi_emple.fec_naci, GETDATE()) >= 56 THEN 'Proximo a pensionar'
        ELSE 'No aplica'
    END AS [Estado Pension],
    -- Calcular el rango semestral
    CASE
        WHEN 
            (DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()) * 12) + 
            DATEDIFF(MONTH, DATEADD(YEAR, DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()), nm_contr.fec_ingr), GETDATE()) +
            CASE 
                WHEN DAY(GETDATE()) < DAY(nm_contr.fec_ingr) THEN 
                    (DAY(GETDATE()) + DAY(EOMONTH(GETDATE())) - DAY(nm_contr.fec_ingr)) / 30 
                ELSE 
                    (DAY(GETDATE()) - DAY(nm_contr.fec_ingr)) / 30 
            END < 6 
            THEN '0-6'
        WHEN 
            (DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()) * 12) + 
            DATEDIFF(MONTH, DATEADD(YEAR, DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()), nm_contr.fec_ingr), GETDATE()) +
            CASE 
                WHEN DAY(GETDATE()) < DAY(nm_contr.fec_ingr) THEN 
                    (DAY(GETDATE()) + DAY(EOMONTH(GETDATE())) - DAY(nm_contr.fec_ingr)) / 30 
                ELSE 
                    (DAY(GETDATE()) - DAY(nm_contr.fec_ingr)) / 30 
            END >= 6 AND
            (DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()) * 12) + 
            DATEDIFF(MONTH, DATEADD(YEAR, DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()), nm_contr.fec_ingr), GETDATE()) +
            CASE 
                WHEN DAY(GETDATE()) < DAY(nm_contr.fec_ingr) THEN 
                    (DAY(GETDATE()) + DAY(EOMONTH(GETDATE())) - DAY(nm_contr.fec_ingr)) / 30 
                ELSE 
                    (DAY(GETDATE()) - DAY(nm_contr.fec_ingr)) / 30 
            END < 12
            THEN '06-12'
        WHEN 
            (DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()) * 12) + 
            DATEDIFF(MONTH, DATEADD(YEAR, DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()), nm_contr.fec_ingr), GETDATE()) +
            CASE 
                WHEN DAY(GETDATE()) < DAY(nm_contr.fec_ingr) THEN 
                    (DAY(GETDATE()) + DAY(EOMONTH(GETDATE())) - DAY(nm_contr.fec_ingr)) / 30 
                ELSE 
                    (DAY(GETDATE()) - DAY(nm_contr.fec_ingr)) / 30 
            END >= 12 AND
            (DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()) * 12) + 
            DATEDIFF(MONTH, DATEADD(YEAR, DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()), nm_contr.fec_ingr), GETDATE()) +
            CASE 
                WHEN DAY(GETDATE()) < DAY(nm_contr.fec_ingr) THEN 
                    (DAY(GETDATE()) + DAY(EOMONTH(GETDATE())) - DAY(nm_contr.fec_ingr)) / 30 
                ELSE 
                    (DAY(GETDATE()) - DAY(nm_contr.fec_ingr)) / 30 
            END < 18
            THEN '12-18'
        WHEN 
            (DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()) * 12) + 
            DATEDIFF(MONTH, DATEADD(YEAR, DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()), nm_contr.fec_ingr), GETDATE()) +
            CASE 
                WHEN DAY(GETDATE()) < DAY(nm_contr.fec_ingr) THEN 
                    (DAY(GETDATE()) + DAY(EOMONTH(GETDATE())) - DAY(nm_contr.fec_ingr)) / 30 
                ELSE 
                    (DAY(GETDATE()) - DAY(nm_contr.fec_ingr)) / 30 
            END >= 18 AND
            (DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()) * 12) + 
            DATEDIFF(MONTH, DATEADD(YEAR, DATEDIFF(YEAR, nm_contr.fec_ingr, GETDATE()), nm_contr.fec_ingr), GETDATE()) +
            CASE 
                WHEN DAY(GETDATE()) < DAY(nm_contr.fec_ingr) THEN 
                    (DAY(GETDATE()) + DAY(EOMONTH(GETDATE())) - DAY(nm_contr.fec_ingr)) / 30 
                ELSE 
                    (DAY(GETDATE()) - DAY(nm_contr.fec_ingr)) / 30 
            END < 24
            THEN '18-24'
        ELSE 'Mas de 24'
    END AS [Rango Antiguedad]
FROM 
    nm_contr
INNER JOIN gn_empre ON nm_contr.cod_empr = gn_empre.cod_empr 
INNER JOIN bi_emple ON nm_contr.cod_empl = bi_emple.cod_empl AND nm_contr.cod_empr = bi_emple.cod_empr
LEFT JOIN bi_cargo ON nm_contr.cod_carg = bi_cargo.cod_carg AND nm_contr.cod_empr = bi_cargo.cod_empr
LEFT JOIN gn_ccost ON nm_contr.cod_ccos = gn_ccost.cod_ccos AND nm_contr.cod_empr = gn_ccost.cod_empr
LEFT JOIN nm_centp ON nm_contr.cod_cenp = nm_centp.cod_cenp AND nm_contr.cod_empr = nm_centp.cod_empr
LEFT JOIN nm_gprot ON nm_contr.cod_gpro = nm_gprot.cod_gpro AND nm_contr.cod_empr = nm_gprot.cod_empr
LEFT JOIN nm_tnomi ON nm_contr.cod_tnom = nm_contr.cod_tnom AND nm_contr.cod_empr = nm_tnomi.cod_empr
LEFT JOIN nm_mdeja ON nm_contr.cod_mdej = nm_mdeja.cod_mdej AND nm_contr.cod_empr = nm_mdeja.cod_empr
LEFT JOIN nm_escar ON nm_contr.cod_esca = nm_escar.cod_esca AND nm_contr.cod_empr = nm_escar.cod_empr
LEFT JOIN bi_edfor ON nm_contr.cod_empl = bi_edfor.cod_empl AND nm_contr.cod_empr = bi_edfor.cod_empr
LEFT JOIN BI_DMODA ON bi_edfor.COD_PROF = BI_DMODA.COD_PROF AND bi_edfor.cod_empr = BI_DMODA.COD_EMPR AND BI_DMODA.COD_MODI IN ('TN','PG','BI','ES','TT','MA','PI')
WHERE nm_contr.cod_empl NOT IN (SELECT cod_empl
								FROM Empleados_Rigel
								WHERE cod_ccos IN (2011, 2012))
                                
-- ********************************************************************************************
-- @Nombre: Query para obtener pasivo vacacional
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

DECLARE @FechaProyectada DATE = GETDATE();

WITH DiasNoLaborados AS (
    SELECT 
        d.cod_empl, 
        d.cod_empr, 
        SUM(CASE WHEN d.cod_conc IN ('519', '492', '522') THEN d.num_dias ELSE 0 END) AS TotalDiasNoLaborados
    FROM [KactusGrM].[dbo].[NM_DIASN] d
    WHERE d.fec_desd >= (
        SELECT MIN(c.fec_cont) 
        FROM [KactusGrM].[dbo].[nm_contr] c 
        WHERE c.cod_empl = d.cod_empl 
            AND c.cod_empr = d.cod_empr)
    GROUP BY d.cod_empl, d.cod_empr),

VacacionesTomadas AS (
    SELECT 
        v.cod_empl, 
        v.cod_empr, 
        SUM(v.dia_tomt + v.dia_tomd) AS TotalVacacionesTomadas
    FROM [KactusGrM].[dbo].[NM_VACAC] v
    WHERE v.TIP_LIQU = 'N'
        AND EXISTS (
            SELECT 1 
            FROM [KactusGrM].[dbo].[nm_contr] c2
            WHERE c2.cod_empl = v.cod_empl 
                AND c2.cod_empr = v.cod_empr 
                AND c2.IND_ACTI = 'A'  
                AND v.fec_cau1 >= c2.fec_cont)
    GROUP BY v.cod_empl, v.cod_empr)

SELECT 
    e.NOM_EMPR AS 'Empresa',
    c.cod_empl AS 'CodEmpleado',
    bi.nom_empl AS 'Nombre', 
    bi.ape_empl AS 'Apellido', 
    bc.nom_carg AS 'Cargo',  
    cc.nom_ccos AS 'CentroCostos',
    c.fec_cont AS 'FechaContratacion',

    -- Calculo de Dias Pendientes
    ROUND(((DATEDIFF(DAY, c.fec_cont, @FechaProyectada) - ISNULL(dnl.TotalDiasNoLaborados, 0)) * 360.0 / 365.0) / 24
        - ISNULL(vt.TotalVacacionesTomadas, 0), 2) AS 'DiasPendientes'

FROM [KactusGrM].[dbo].[nm_contr] c
JOIN [KactusGrM].[dbo].[GN_EMPRE] e ON c.cod_empr = e.cod_empr  
JOIN [KactusGrM].[dbo].[gn_ccost] cc ON c.cod_ccos = cc.cod_ccos  
JOIN [KactusGrM].[dbo].[bi_emple] bi ON c.cod_empl = bi.cod_empl  
LEFT JOIN DiasNoLaborados dnl ON c.cod_empl = dnl.cod_empl AND c.cod_empr = dnl.cod_empr
LEFT JOIN VacacionesTomadas vt ON c.cod_empl = vt.cod_empl AND c.cod_empr = vt.cod_empr
LEFT JOIN [KactusGrM].[dbo].[bi_cargo] bc ON c.cod_carg = bc.cod_carg  

WHERE 
    c.IND_ACTI = 'A'  
    AND bc.nom_carg NOT IN ('APRENDIZ SENA ETAPA LECTIVA', 'APRENDIZ SENA ETAPA PRODUCTIVA')
    AND cc.nom_ccos NOT IN ('MO PROYECTO Y SEGUIMIENTO FANALCA', 'MO PROYECTO Y SEGUIMIENTO TD')

GROUP BY 
    c.cod_empr, e.NOM_EMPR, c.cod_empl, bi.nom_empl, bi.ape_empl, bc.nom_carg, cc.nom_ccos, c.fec_cont, 
    dnl.TotalDiasNoLaborados, vt.TotalVacacionesTomadas;

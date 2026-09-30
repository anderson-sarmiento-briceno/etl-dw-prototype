--*********************************************************************************************
-- @Nombre: Query para extraer la informacion de los familiares de los empleados
-- @Autor: Anderson Sarmiento
--*********************************************************************************************

SELECT
gn_empre.nom_empr AS 'CodEmpresa',
nm_contr.cod_empl AS 'CodEmpleado',
nm_contr.fec_ingr AS 'FechaIngreso',
bi_emple.nom_empl AS 'Nombres',
bi_emple.ape_empl AS 'Apellidos',
bi_cargo.nom_carg  AS 'Cargo',
bi_emple.sex_empl AS 'GeneroEmpleado',
nm_contr.ind_acti AS 'EstadoEmpleado',
bi_famil.cod_fami AS 'CodFamiliar',
bi_famil.nom_fami AS 'NombreFamiliar',
bi_famil.ape_fami AS 'ApellidoFamiliar',
bi_famil.sex_fami AS 'GeneroFamiliar',
bi_famil.fec_naci AS 'FechaNacimientoFamiliar',
bi_famil.tip_rela AS 'RelacionFamiliar',
datediff(year,bi_famil.fec_naci, getdate()) AS 'EdadFamiliar',
bi_famil.act_hora AS 'Registro'
FROM nm_contr
INNER JOIN gn_empre
    ON nm_contr.cod_empr = gn_empre.cod_empr
LEFT JOIN bi_famil
    ON nm_contr.cod_empr = bi_famil.cod_empr
    AND nm_contr.cod_empl = bi_famil.cod_empl
INNER JOIN bi_emple
    ON nm_contr.cod_empl = bi_emple.cod_empl
    AND nm_contr.cod_empr = bi_emple.cod_empr
INNER JOIN bi_cargo
    ON nm_contr.cod_carg = bi_cargo.cod_carg
    AND nm_contr.cod_empr = bi_cargo.cod_empr
WHERE nm_contr.cod_empl NOT IN (SELECT cod_empl
								FROM Empleados_Rigel
								WHERE cod_ccos IN (2011, 2012))

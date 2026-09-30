-- ********************************************************************************************
-- @Nombre: Query para obtener el maestro de empleados EPS y barrio
-- @Autor: Jorge Saavedra - Carlos Preciado
-- @Fecha: 20211218
-- ********************************************************************************************

SELECT 
	 emp.cod_empl as CodEmpleado
	,emp.bar_resi as BarrioResidencia
	,emp.est_civi as EstadoCivil
	,eps.AFP
	,eps.ARP
	,eps.CCF
	,eps.EPS
FROM [KactusGrM].[dbo].[bi_emple] emp
LEFT JOIN (select * from
			(SELECT a.cod_empl, a.tip_enti, b.nom_enti
			FROM [KactusGrM].[dbo].[nm_cuent] a
			LEFT JOIN (SELECT cod_empr, tip_enti, cod_enti, nom_enti
						FROM [KactusGrM].[dbo].[nm_entid]
						where tip_enti in ('AFP', 'EPS', 'ARP', 'CCF') AND cod_sucu = 0) b on a.cod_empr = b.cod_empr and a.tip_enti = b.tip_enti and a.cod_enti = b.cod_enti
			where a.tip_enti in ('AFP', 'EPS', 'ARP', 'CCF')) as tabla
			pivot(max(nom_enti)
			for tip_enti in ([AFP], [EPS], [ARP], [CCF])) as pvt) eps on emp.cod_empl = eps.cod_empl

-- ********************************************************************************************
-- @Nombre: Query para obtener el maestro de empleados
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
   [cod_empl] as "CodEmpleado"
  ,[tip_docu]	as "TipoDocumento"
  ,[cod_inte]	as "NoSAE"
  ,[nom_empl]	+ ' ' + [ape_empl] as "NombreEmpleado"
  ,cast([fec_naci] as date) as FechaNacimiento
  ,cast(DATEADD(YEAR, YEAR(GETDATE()) - YEAR(fec_naci), fec_naci) as date) as "ProximaFechaCumpleanios"
  ,datediff(year, fec_naci, getdate() ) as "Edad"
  ,[dir_resi]	as "DireccionResidencia"
  ,[aEmple]	as "ActualizacionEmpleado"
  ,[tel_resi]	as "TelefonoResidencia"
  ,[tel_movi]	as "TelefonoMovil"
  ,[sex_empl]	as "Genero"
  ,[box_mail]	as "EmailEmpresa"
  ,[eee_mail]	as "EmailPersonal"
  ,[gru_sang]	as "GrupoSanguineo"
  ,[fac_sang]	as "FactorRH"
  ,[cod_carg]	as "CodCargo"
  ,[nom_carg]	as "Cargo"
  ,[cod_ccos]	as "CodCentroCostos"
  ,[nom_ccos]	as "CentroCostos"
  ,[ind_acti]	as "EstadoEmpleado"
  ,cast([fec_cont] as date) as "FechaContratacion"
  ,cast([fec_venc] as date) as "FechaRetiro"
  ,[tip_cont]	as "TipoContrato"
  ,[nro_cont]	as "CantidadContratos"
  ,[fec_deja]	as "FechaDeja"
  ,[temporal]	as "EsTemporal"
  ,[aContr]	as "ActualizacionContrato"
  ,[nom_empr]	as "Empresa"
  ,[act_hora]	as "HoraActualizacion"
FROM [KactusGrM].[dbo].[Empleados_Rigel]

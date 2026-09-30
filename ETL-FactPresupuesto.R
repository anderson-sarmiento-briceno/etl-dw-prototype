#**********************************************************************************************
#  @Nombre: Proceso para el cargue del presupuesto de kms y Costo de flota
#  @Autor: Anderson Sarmiento
#**********************************************************************************************

# Se carga archivo .env -----------------------------------------------------------------------
readRenviron(".env")
source("Funciones/funciones.R")

# Presupuesto de Kms --------------------------------------------------------------------------
kmsflota <- fread("01 Inputs/PresupuestoKm.csv") %>% 
  mutate(Mes = dmy(Mes),
         InsertDate = format(Sys.time(), tz = "")) %>% 
  select("Fecha" = "Mes", everything())

odbc::dbWriteTable(con(), DBI::SQL('ma."FactPptoKmsFlota"'), kmsflota, overwrite = TRUE,
                   field.types = c(Fecha = "date",
                                   Empresa = "text",
                                   Tipologia = "text",
                                   CtdadBus = "integer",
                                   Kilometros = "integer",
                                   InsertDate = "timestamp"))

# Presupuesto de costo de Flota ---------------------------------------------------------------
costoflota <- fread("01 Inputs/PresupuestoCosto.csv") %>% 
  mutate(Mes = dmy(Mes),
         InsertDate = format(Sys.time(), tz = "")) %>% 
  select("Fecha" = "Mes", everything())

odbc::dbWriteTable(con(), DBI::SQL('ma."FactPptoCostoFlota"'), costoflota, overwrite = TRUE,
                   field.types = c(Fecha = "date",
                                   Empresa = "text",
                                   Tipologia = "text",
                                   Rubro = "text",
                                   Presupuesto = "integer",
                                   InsertDate = "timestamp"))

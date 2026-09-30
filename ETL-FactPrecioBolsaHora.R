#**********************************************************************************************
#  @Nombre: Fact Precios Bolsa de Energía por Hora
#  @Autor: Anderson Sarmiento
#**********************************************************************************************

# Cargue de Librerias -------------------------------------------------------------------------
library(readxl)       # Leer archivos de excel

# Se carga archivo .env -----------------------------------------------------------------------
readRenviron(".env")
source("Funciones/funciones.R")

# Definimos el path de downloads --------------------------------------------------------------
userpc <- "E:\\Drive"
path <- "\\greenmovil.com.co\\Gestion Mantenimiento - General\\Documentos\\10 Datos\\13 PreciosBolsa\\"
pathfiles <- str_c(userpc, path)

# Cargue de precios ponderados ----------------------------------------------------------------
ponderadoBolsa <- list.files(pathfiles, pattern = "Ponderado",full.names = T)

ponderadobolsa <- read_excel(ponderadoBolsa, skip = 1) %>% 
  janitor::clean_names(., case = c("upper_camel"), replace = c("Suma de " = "")) %>% 
  mutate(InsertDate = format(Sys.time(), tz = ""))

# Insertar los datos en el DW
odbc::dbWriteTable(cona(), DBI::SQL('ma."FactPrecioBolsaPonderado"'), ponderadobolsa, overwrite = TRUE,
                   field.types = c(Fecha = "date",
                                   PppBolsaMesNuevo = "double precision",
                                   PppDeEscasez = "double precision",
                                   PrecioMinBolsaDiario = "double precision",
                                   PrecioMaxBolsaDiario = "double precision",
                                   PppBolsaDiario = "double precision",
                                   PrecioEscasezActivacion = "double precision",
                                   InsertDate = "timestamp"))

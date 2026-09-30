#**********************************************************************************************
#  @Nombre: Script para soportar la documentacion de las tablas del DW
#  @Autor: Anderson Sarmiento
#**********************************************************************************************

# Cargue de Librerias -------------------------------------------------------------------------
library(tidyverse)    # Transformaciones de datos
library(data.table)   # Transformaciones de datos
library(lubridate)    # Tratamiento de fechas
library(httr)         # Publicacion de notificaciones
options(scipen = 999)

# Proceso de particiones de tablas ------------------------------------------------------------
# Al crear una partición de rango, el límite inferior especificado con FROM es un inclusivo , 
# mientras que el límite superior especificado con TO es exclusivo atado 

# Crear vector con las fechas que debe tener la particion
fechas <- seq.Date(as.Date("2019-01-01"), as.Date("2023-01-01"), by = "2 month")

# Crear los parametros que deben incluirse en la query
Nombretabla1 <- "FactParada"
Nombretabla2 <- format(fechas, "%Y%m%d")
tabla <- "FactDemandaParadaZonalTM"
fecha <- fechas
final <- dplyr::lead(fechas)

# Funcion glue para crear las sentencias que deben aplicarse en la base de datos
glue::glue('create table {Nombretabla1}', '{Nombretabla2} ', 'partition of "{tabla}" ', 
           "for values from ('{fecha}') to ", "('{final}');")

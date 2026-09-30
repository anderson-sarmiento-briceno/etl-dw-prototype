#**********************************************************************************************
#  @Nombre: Proceso de Extraccion historico Disponibilidad
#  @Autor: Anderson Sarmiento
#**********************************************************************************************

# Cargue de Librerias -------------------------------------------------------------------------
options(scipen = 999)
suppressWarnings(suppressPackageStartupMessages({
  library(jsonlite)     # Manejo de documentos json
}))

# Se carga archivo .env -----------------------------------------------------------------------
readRenviron(".env")
source("Funciones/funciones.R")

# Nombre del proceso para correr en el script -------------------------------------------------
# Titulo que se desplega en el mensaje de slack
pretext <- "*Estado %SOC*"
# Función del proceso
ini_proceso(IdProceso = 1330, pretext = pretext)

# Crear una función para generar el texto para cada columna
generar_texto_columna <- function(registro) {
  texto <- paste(paste0("*", registro[ ,1], ":*", collapse = "', '"), toString(registro[, 2:num_columnas]), collapse = "\n")
  return(texto)
}

# Cargue de Documentos de referencia ----------------------------------------------------------
# Servicio para obtener el estado de la bateria de los buses
geturl <- "http://myservice.grupomovil.com.co:9999/WS-MOVIL/service/polygon/findDataBattery?user=consultant&pass=cm,9dr%23$%25wte9%23%25%26/daf"

# Obtener la hora actual
hora_actual <- as.POSIXlt(Sys.time())

busesproblema <- c("Z674001", "Z674017", "Z634042")

get_soc <- function(ubicacion = c("En Patio", "En Via")) {
  
  jsonlite::fromJSON(geturl) %>% 
    select(fechaHoraLecturaDato, idVehiculo, nivelRestanteEnergia, patio) %>% 
    mutate(fechaHoraLecturaDato = as.character(dmy_hms(fechaHoraLecturaDato)),
           nivelRestanteEnergia = parse_number(nivelRestanteEnergia),
           patio = ifelse(patio == "true", "En Patio", "En Via")) %>% 
    filter(!is.na(nivelRestanteEnergia), nivelRestanteEnergia > 0, nivelRestanteEnergia <= 30) %>% 
    rename(Fecha = fechaHoraLecturaDato, Vehiculo = idVehiculo, Energia = nivelRestanteEnergia,
           EstaEnPatio = patio) %>% 
    select(Vehiculo, Energia, everything()) %>% 
    mutate(Energia = sprintf("%.0f%%", Energia)) %>% 
    filter(!Vehiculo %in% busesproblema) %>% 
    filter(EstaEnPatio %in% ubicacion)
  
}

# Verificar si es después de las 04:00 AM y antes de las 21:00
if (hora_actual$hour >= 4 && hora_actual$hour <= 21) {
  
  df <- get_soc()

} else {  
  
  # Si es entre las 21:00 y las 04:00 AM, reporta solo si el bus está en vía
  df <- get_soc(ubicacion = "En Via")
  
}

# Obtener la cantidad de filas y columnas de la tabla
num_filas <- nrow(df)
num_columnas <- ncol(df)

# Crear una lista para almacenar los textos de cada columna
textos_columnas <- vector("list", length = num_filas)

# Publicacion de resultados -------------------------------------------------------------------
if (length(textos_columnas) == 0) {
  
  # Publicacion de resultados
  request <- POST(keyring::key_get("hook", "battery"),
                  body = paste(
                    '{"attachments": [{',
                    
                    '"pretext": "', pretext,
                    '",',
                    
                    '"footer": "',
                    "Fecha Ejecucion: ", str_c(format(Sys.time(), "%Y-%m-%d %H:%M:%S"), " - ", parametros$Fuente[1]),
                    '",',
                    
                    '"text": "',
                    "*Estado: * ", str_c("Toda la flota con > 30%"),
                    '", "color": "#f2f2f2"',
                    
                    '}]}',
                    
                    sep = ''
                  )
  )
  
} else {
  
  # Generar el texto para cada columna
  for (i in 1:num_filas) {
    textos_columnas[[i]] <- generar_texto_columna(df[i, ])
  }
  
  # Publicacion de resultados
  request <- POST(Sys.getenv("TOK_SLACK"),
                  body = paste(
                    '{"attachments": [{',
                    
                    '"pretext": "', pretext,
                    '",',
                    
                    '"footer": "',
                    "Fecha Ejecucion: ", str_c(format(Sys.time(), "%Y-%m-%d %H:%M:%S"), " - ", parametros$Fuente[1]),
                    '",',
                    
                    '"text": "',
                    " ", paste(textos_columnas, collapse = "\n\n"),
                    '", "color": "#f2f2f2"',
                    
                    '}]}',
                    
                    sep = ''
                  )
  )

  }

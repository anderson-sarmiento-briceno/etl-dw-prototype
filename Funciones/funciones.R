#**********************************************************************************************
#  @Nombre: Funciones para hacer cargadas en cada ejecucion del script
#  @Autor:Anderson Sarmiento
#**********************************************************************************************

# Cargue de Librerias -------------------------------------------------------------------------
options(scipen = 999)
suppressWarnings(suppressPackageStartupMessages({
  library(tidyverse)    # Transformaciones de datos
  library(data.table)   # Transformaciones de datos
  library(lubridate)    # Tratamiento de fechas
  library(httr)         # Publicacion de notificaciones
  library(RPostgres)    # Funcion para tabajar con postgres
  library(glue)         # Manejo de cadenas
  library(slackr)       # Notificacion en slack
}))

# Se carga archivo .env -----------------------------------------------------------------------
readRenviron(".env")

# Nombre del proceso para correr en el script -------------------------------------------------
# Colocar el Id del proceso que esta en el DW
ini_proceso <- function(IdProceso, pretext) {
  
  IdProceso <- IdProceso
  # Titulo que se desplega en el mensaje de slack
  pretext <- pretext
  
  # Mensaje Inicio del Proceso ------------------------------------------------------------------
  start_time <- Sys.time()
  
  message(paste0(strrep("*", 95)), 
          "\nProceso: ", pretext,
          "\nHora Inicio: ", format(start_time, tz = ""),
          "\n",
          paste0(strrep("*", 95)))
  
  # Parametros del proceso ----------------------------------------------------------------------
  # Se obtiene los datos de los procesos
  totalprocesos <- odbc::dbGetQuery(cona(), glue::glue_sql("SELECT count(*) as \"Total\"
                                                FROM bi.process WHERE frecuencia = 1"))
  
  parametros <- odbc::dbGetQuery(cona(), glue::glue_sql("SELECT * 
                                              FROM bi.process
                                              WHERE id_proceso = {IdProceso}",
                                                       .con = cona()))
  
  numprocess <- str_c("*", str_pad(parametros$Secuencia, 2, "left", 0), "/", totalprocesos$Total)
  
  assign("start_time", start_time, envir = .GlobalEnv)
  assign("totalprocesos", totalprocesos, envir = .GlobalEnv)
  assign("parametros", parametros, envir = .GlobalEnv)
  assign("numprocess", numprocess, envir = .GlobalEnv)
  
}

# Mensaje Fin del Proceso ---------------------------------------------------------------------
fin_proceso <- function(start_time, numprocess, pretext, parametros, dataset, token) {
  
  # Imprimir mensaje en consola
  message(
    paste0(strrep("*", 95)),
    "\nHora Fin: ", format(Sys.time(), tz = ""),
    "\nDuracion: ", Sys.time() - start_time,
    "\n",
    paste0(strrep("*", 95))
  )
  
  # Construcción del cuerpo JSON para Slack
  body_msg <- paste(
    '{"attachments": [{',
    
    '"pretext": "', stringr::str_c(numprocess, " - ", pretext), '",',
    
    '"footer": "',
      "Fecha Ejecucion: ",
      stringr::str_c(format(Sys.time(), "%Y-%m-%d %H:%M:%S"), " - ", parametros$Fuente[1]),
    '",',
    
    '"text": "',
      "*Registros: * ", stringr::str_c(nrow(dataset), " Rows"),
    '",',
    
    '"color": "#f2f2f2"',
    
    '}]}',
    sep = ""
  )
  
  # Enviar mensaje a Slack
  request <- httr::POST(token, body = body_msg)
  
  return(request)
}


#**********************************************************************************************
#* Funciones de conexion a las bases de datos
#**********************************************************************************************

# Funcion Conexion al DWA __--------------------------------------------------------------------
cona <- function() {
  DBI::dbConnect(RPostgres::Postgres(),
                 host = '10.0.22.78',
                 port = '5432',
                 dbname = 'GRMDW',
                 user = Sys.getenv("DBB_USER_DWGRMA"),
                 password = Sys.getenv("DBB_PASS_DWGRMA"))
}

# Funcion Conexion al DW __--------------------------------------------------------------------
conlt <- function() {
  DBI::dbConnect(RPostgres::Postgres(),
                 host = '10.0.22.11',
                 port = '5432',
                 dbname = 'LEGDW',
                 user = Sys.getenv("DBB_USER_DWGRM"),
                 password = Sys.getenv("DBB_PASS_DWGRM"))
}

## Conexion a maximo 
conmx <- function() {
  DBI::dbConnect(odbc::odbc(),
                 Driver = "SQL Server",
                 Server = "10.0.3.58\\MANTENIMIENTOSQL",
                 Database = "GRMAXPR",
                 uid = Sys.getenv("DBB_USER_MAXIM"),
                 pwd = Sys.getenv("DBB_PASS_MAXIM"),
                 encoding = "latin1",
                 Port = 1433)
}

# Conexion a la base de datos Kactus 
conexionkt <- function() {
  conkt <- odbc::dbConnect(odbc::odbc(),
                           Driver = "SQL Server",
                           Server = "10.0.3.63\\RRHHMSSQL",
                           Database = "KactusGrM",
                           uid = Sys.getenv("DBB_USER_KACTUS"),
                           pwd = Sys.getenv("DBB_PASS_KACTUS"),
                           encoding = "latin1",
                           Port = 1433)
}

consi <- function() {
  odbc::dbConnect(odbc::odbc(),
                  Driver = "SQL Server",
                  Server = "BUSAN\\CONTABLEMMSQL",
                  Database = "BI_GRMUNOEREALUF06",
                  uid = Sys.getenv("DBB_USER_SIESA"),
                  pwd = Sys.getenv("DBB_PASS_SIESA"),
                  encoding = "latin1",
                  Port = 1433)
}

#**********************************************************************************************
#* Funciones de Transformacion
#**********************************************************************************************

# Funcion para mensaje en slack ---------------------------------------------------------------
frows <- function(x) {
  
  str_c(format(dim(x)[1], big.mark = ","), " Rows")
  
}

# Funcion cargar actualizacion de tablas ------------------------------------------------------
registrar_actualizacion <- function(conn, id_tabla, id_proceso, max_fecha_tabla = NA,
                                    cantidad_registros = NA, observacion = NA) {
  
  today <- Sys.Date()
  dia_hoy <- as.integer(format(today, "%d"))
  
  # 1. Saber si hoy es dia habil
  day_habil <- DBI::dbGetQuery(conn, sprintf('SELECT ("IsWeekday" = 1 AND "IsHoliday" = 0) AS habil
                                              FROM "DimDate"
                                              WHERE "Date" = \'%s\'', today))$habil[1]
  
  # 2. Traer parametros del proceso
  df_proc <- DBI::dbGetQuery(conn, sprintf('SELECT frecuencia, frecuencia_fija
                                            FROM bi.process
                                            WHERE id_proceso = %s', id_proceso))
  frec <- df_proc$frecuencia[1]
  dias_mes_raw <- df_proc$frecuencia_fija[1]
  indicador <- NA
  
  # 2.5 Regla especial: error → fuerza comportamiento
  if (!is.null(observacion) && !is.na(observacion) && trimws(observacion) != "") {
    if (isTRUE(day_habil)) indicador <- 0 else indicador <- NA
  } else {
    # 4. Caso: dias fijos del mes
    if (!is.na(dias_mes_raw)) {dias_mes <- as.integer(unlist(strsplit(dias_mes_raw, ",")))
                               indicador <- ifelse(dia_hoy %in% dias_mes, 1, 0)
    } else {
      # 3. Si no es dia habil
      if (!isTRUE(day_habil)) {indicador <- NA
      } else {
        # 5. Frecuencia en días
        if (frec == 1) {indicador <- 1
        } else {
          df_last <- DBI::dbGetQuery(conn, sprintf('SELECT fecha_actualizacion
                                                    FROM bi.table_updates
                                                    WHERE id_proceso = %s
                                                      AND id_tabla = %s
                                                    ORDER BY fecha_actualizacion DESC
                                                    LIMIT 1', id_proceso, id_tabla))
          if (nrow(df_last) == 0) {indicador <- 1
          } else {fecha_last <- as.Date(df_last$fecha_actualizacion[1])
                  diff_days <- as.integer(today - fecha_last)
                  indicador <- ifelse(diff_days <= frec, 1, 0)}}}}}
  
  # 6. Registrar fila
  df_insert <- data.frame(id_tabla = id_tabla, id_proceso = id_proceso, max_fecha_tabla = max_fecha_tabla,
                          cantidad_registros = cantidad_registros, indicador = indicador, observacion = observacion,
                          stringsAsFactors = FALSE)
  
  # 7. Insertar en la tabla
  DBI::dbWriteTable(conn, name = DBI::Id(schema = "bi", table = "table_updates"), value = df_insert,
                    append = TRUE, row.names = FALSE)}

# Funcion para actualizar la fecha de proceso -------------------------------------------------
actualizar_fecha_proceso <- function(conn, id_proceso) {
DBI::dbExecute(conn, " UPDATE bi.process
                       SET fecha_ultima_ejecucion = $1
                       WHERE id_proceso = $2",
    params = list(Sys.time(), id_proceso))}

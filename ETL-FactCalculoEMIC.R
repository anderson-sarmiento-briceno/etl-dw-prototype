#**********************************************************************************************
#  @Nombre: Proceso para el calculo de la EMIC
#  @Autor: Anderson Sarmiento
#**********************************************************************************************

# Cargue de Librerias -------------------------------------------------------------------------
suppressWarnings(suppressPackageStartupMessages({
  library(here)         # Ubicacion de los archivos 
}))

# Recive argumentos del script de python ------------------------------------------------------
args <- commandArgs(trailingOnly = TRUE)
if (length(args) > 0) {
  setwd(args[1])
}

# Se carga archivo .env -----------------------------------------------------------------------
readRenviron(".env")
source("Funciones/funciones.R")

# Nombre del proceso para correr en el script -------------------------------------------------
# Titulo que se desplega en el mensaje de slack
IdProceso = 1142
pretext <- paste0(IdProceso, " - Proceso Calculo EMIC*")
# Función del proceso
ini_proceso(IdProceso = IdProceso, pretext = pretext)

# Proceso de cargar de archivos ---------------------------------------------------------------
tryCatch({
# Se cargan los valores de referencia establecidos en el manual de operaciones de acuerdo con
# sus respectivas vigencias Ver Capitulo 9 del manual
a_valores_referencia <- data.table::fread(here("01 Inputs/valor_referencia.csv")) %>% 
  mutate_at(vars("FechaInicio", "FechaFin"), .funs = dmy)

# Valores de nivel de servicio de acuerdo con los resultados de los indicadores
a_nivel_servicio <- data.table::fread(here("01 Inputs/nivel_servicio.csv"))

# Niveles de referencia para los puntajes establecidos en el manual de niveles de servicio 
a_puntajes <- data.table::fread(here("01 Inputs/puntajes.csv")) %>% 
  tibble::column_to_rownames('Puntajes')

# Ponderaciones
a_ponderaciones <- data.table::fread(here("01 Inputs/ponderaciones.csv")) %>% 
  mutate_at(vars("FechaIni", "FechaFin"), .funs = dmy)
 
# Carga de las funciones y puntajes de calculo
source(here("Funciones/indices.R"))
source(here("Funciones/puntajes.R"))

# Funciones -----------------------------------------------------------------------------------
# Conexion Slack
slackr_setup(username = "",
             incoming_webhook_url =  Sys.getenv("TOK_SLACK"), 
             token = Sys.getenv("TOK_SLACK_MESG"))

# Carga Tabla calendario ----------------------------------------------------------------------
# se carga la tabla calendario para quitar los dias atipicos por fallo en el SAE
dimfechas <- odbc::dbGetQuery(cona(), 'SELECT "Date" as "Fecha" 
                                      FROM "DimDate" 
                                      WHERE "Date" BETWEEN \'2022-04-02\' AND CURRENT_DATE
                                      AND "IsFailSae" is NULL
                                      ORDER BY 1')

# Carga de datos reales -----------------------------------------------------------------------
## ISV ---------------------------------------------------------------------------------------- 
# Simples (1), Lesionados (3), Fatalidades (18)
dataisv <- odbc::dbGetQuery(cona(), 'SELECT "FechaReporte"::DATE as "Fecha", "Estado", "Operador", "GravedadEvento", 
                                  "ObsTmsa"
                                  FROM "op"."FactEmicISV4"
                            
                                  UNION ALL
                            
                                  SELECT "FechaReporte"::DATE as "Fecha", "Estado", "Operador", "GravedadEvento", 
                                  "ObsTmsa"
                                  FROM "op"."FactEmicISV1"') %>% 
  filter(Estado != 'Contestado Contundente') %>% 
  # Se filtran dias atipicos
  filter(Fecha %in% dimfechas$Fecha) %>% 
  mutate(Fecha = floor_date(as_date(Fecha), unit = "month"),
         GravedadEvento = str_to_lower(GravedadEvento),
         GravedadEvento = ifelse(str_detect(GravedadEvento, "con lesionado"), 
                                 "Con lesionado", str_to_sentence(GravedadEvento))) %>%
  group_by(Fecha, Operador, GravedadEvento) %>% 
  summarise(Total = n()) %>% 
  ungroup() %>% 
  mutate(Eventos = case_when(
    GravedadEvento == "Simple" ~ Total,
    GravedadEvento == "Con lesionado" ~ Total * 3L,
    GravedadEvento == "Con victima mortal" ~ Total * 18L)) %>% 
  group_by(Fecha, Operador) %>% 
  summarise(SeguridadVial = sum(Eventos, na.rm = T))

## ICK  --------------------------------------------------------------------------------------- 
# # Kmse, Kmsa
datakms <- odbc::dbGetQuery(cona(), 'select "FechaViaje" as "Fecha", "OperadorProgramado" as "Operador", 
                                  "KmProgramado", "KmDefinitivo", "Cumplimiento"
                                  from "op"."FactEmicICS4"

                                  UNION ALL

                                  select "FechaViaje" as "Fecha", "OperadorProgramado" as "Operador", 
                                  "KmProgramado", "KmDefinitivo", "Cumplimiento"
                                  from "op"."FactEmicICS1"') %>% 
  # Se filtran dias atipicos
  filter(Fecha %in% dimfechas$Fecha,
         Operador %in% c("ZMOV", "ZMOIII"))

kmprog <- datakms %>% 
  filter(!Cumplimiento %in% c('DESCARTADO', "NO APLICA")) %>% 
  mutate(Fecha = floor_date(as_date(Fecha), unit = "month")) %>% 
  group_by(Fecha, Operador) %>% 
  summarise(KmProgramado = sum(KmProgramado, na.rm = T))

kmeje <-  datakms %>% 
  mutate(Fecha = floor_date(as_date(Fecha), unit = "month")) %>% 
  group_by(Fecha, Operador) %>% 
  summarise(KmDefinitivo = sum(KmDefinitivo, na.rm = T))

dataick <- kmprog %>% 
  left_join(kmeje, by = c("Fecha", "Operador"))

## ICD ----------------------------------------------------------------------------------------
# NDep, NDea, NDep, NDea 
datandpr <- datakms %>% 
  filter(!Cumplimiento %in% c('DESCARTADO', "NO APLICA")) %>% 
  mutate(Fecha = floor_date(as_date(Fecha), unit = "month")) %>% 
  group_by(Fecha, Operador) %>% 
  summarise(DespachoProgramado = n())

datandej <- datakms %>% 
  filter(str_detect(Cumplimiento, "^CUMPLIDO")) %>% 
  mutate(Fecha = floor_date(as_date(Fecha), unit = "month")) %>% 
  group_by(Fecha, Operador) %>% 
  summarise(DespachoEjecutado = n())

dataicd <- datandpr %>% 
  left_join(datandej, by = c("Fecha", "Operador"))

## IDP ----------------------------------------------------------------------------------------
dataidp <- odbc::dbGetQuery(cona(), 'select "FechaViaje" as "Fecha", "OperadorProgramado" as "Operador", 
                                    "EvalPuntualidad"
                                    from "op"."FactEmicICS4" 
                                    where "DespachoInicial" = 1
                            
                                  UNION ALL
                            
                                  select "FechaViaje" as "Fecha", "OperadorProgramado" as "Operador", 
                                    "EvalPuntualidad"
                                    from "op"."FactEmicICS1" 
                                    where "DespachoInicial" = 1') %>%
  filter(EvalPuntualidad %in% c("Puntual", "No puntual")) %>% 
  # Se filtran dias atipicos
  filter(Fecha %in% dimfechas$Fecha) %>% 
  mutate(Fecha = floor_date(as_date(Fecha), unit = "month")) %>% 
  group_by(Fecha, Operador, EvalPuntualidad) %>%
  summarise(TotalDespachos = n()) %>% 
  ungroup() %>% 
  pivot_wider(names_from = EvalPuntualidad, values_from = TotalDespachos) %>% 
  janitor::clean_names(., case = c("upper_camel")) %>% 
  mutate(DespachoPatio = Puntual + NoPuntual) %>% 
  select(Fecha, Operador, "DespachoPuntual" = "Puntual", DespachoPatio)

# DPV *****************************************************************************************
datadpv <- odbc::dbGetQuery(cona(), 'select "FInmovilizacion"::DATE as "Fecha", "Empresa" as "Operador",
                                  "Estado"
                                  from "op"."FactEmicDPV4"
                            
                                  UNION ALL
                                  
                                  select "FInmovilizacion"::DATE as "Fecha", "Empresa" as "Operador",
                                  "Estado"
                                  from "op"."FactEmicDPV1"') %>% 
  filter(Estado != "Contestado Contundente") %>% 
  # Se filtran dias atipicos
  filter(Fecha %in% dimfechas$Fecha) %>% 
  mutate(Fecha = floor_date(as_date(Fecha), unit = "month")) %>% 
  group_by(Fecha, Operador) %>% 
  summarise(Varados = n())
  
## ICO ----------------------------------------------------------------------------------------
dataico <- odbc::dbGetQuery(cona(), 'select "FechaNovedad"::DATE as "Fecha", "Empresa" as "Operador",
                                  "Estado", "Puntos"
                                  from "op"."FactEmicICO4"
                            
                                  UNION ALL
                                  
                                  select "FechaNovedad"::DATE as "Fecha", "Empresa" as "Operador",
                                  "Estado", "Puntos"
                                  from "op"."FactEmicICO1"') %>% 
  filter(Estado != "Contestado Contundente") %>% 
  # Se filtran dias atipicos
  filter(Fecha %in% dimfechas$Fecha) %>% 
  mutate(Fecha = floor_date(as_date(Fecha), unit = "month")) %>% 
  group_by(Fecha, Operador) %>%
  summarise(PuntosIco = sum(Puntos, na.rm = T)) %>% 
  ungroup()

## ITS ----------------------------------------------------------------------------------------
dataits <- odbc::dbGetQuery(cona(), 'select "FRegistro"::DATE as "Fecha", "IdOperador" as "Operador",
                                  "Estado", "Trv" as "Tram20Gene", "Trs" as "Tram60Gene",
                                  "Tev" as "Tram20Espe", "Tes" as "Tram60Espe", 
                                  "Ecp" as "ConteoPaxReci", "Ep" as "EventoPtaReci", 
                                  "Vr" as "VideoRecibido", "Pe" as "EvntBotoPanico", 
                                  "Cc" as "CantCamaraBus", "Me" as "MttoItsEjec", 
                                  "Te" as "TckSolucion", "Ttr" as "TckRegistrado", 
                                  "Falgie" as "Efectividad", "Falgcpas" as "Pasajeros", 
                                  "Falgbpan" as "Camaras", "Falgim" as "Mtto"
                                  from "op"."FactEmicITS4"
                            
                                  UNION ALL
                                  
                                  select "FRegistro"::DATE as "Fecha", "IdOperador" as "Operador",
                                  "Estado", "Trv" as "Trama20Gene", "Trs" as "Tram60Gene",
                                  "Tev" as "Tram20Espe", "Tes" as "Tram60Espe", 
                                  "Ecp" as "ConteoPaxReci", "Ep" as "EventoPtaReci", 
                                  "Vr" as "VideoRecibido", "Pe" as "EvntBotoPanico", 
                                  "Cc" as "CantCamaraBus", "Me" as "MttoItsEjec", 
                                  "Te" as "TckSolucion", "Ttr" as "TckRegistrado",
                                  "Falgie" as "Efectividad", "Falgcpas" as "Pasajeros", 
                                  "Falgbpan" as "Camaras", "Falgim" as "Mtto"
                                  from "op"."FactEmicITS1"') %>% 
  filter(Estado != "Contestado Contundente") %>% 
  mutate(Categoria = case_when(Efectividad == 1 ~ "Efectividad",
                               Pasajeros == 1 ~ "Pasajeros",
                               Camaras == 1 ~ "Camaras",
                               Mtto == 1 ~ "Mtto")) %>%
  select(-Efectividad, -Pasajeros, -Camaras, -Mtto) %>%
  mutate(
    # Realiza las divisiones por separado
    Division1 = Tram20Gene / Tram20Espe,
    Division2 = Tram60Gene / Tram60Espe) %>%
  mutate(
    Resultado = case_when(
      Categoria == "Pasajeros" ~ ConteoPaxReci / EventoPtaReci,
      Categoria == "Camaras" ~ VideoRecibido / (2 * CantCamaraBus * EvntBotoPanico),
      Categoria == "Mtto" & TckSolucion == 0 & TckRegistrado == 0 ~ MttoItsEjec / 1,
      Categoria == "Mtto" ~ ((MttoItsEjec / 1) + (TckSolucion / TckRegistrado)) / 2)) %>%
  # Eliminar los Inf antes de filtrar
  filter(!is.infinite(Resultado)) %>%
  # Reinicia los numeradores que superan el indicador
  mutate(
    Tram20Gene = ifelse(Categoria == "Efectividad" & Division1 > 1, 0, Tram20Gene),
    Tram60Gene = ifelse(Categoria == "Efectividad" & Division2 > 1, 0, Tram60Gene),
    ConteoPaxReci = ifelse(Categoria == "Pasajeros" & Resultado > 1, 0, ConteoPaxReci),
    VideoRecibido = ifelse(Categoria == "Camaras" & Resultado > 1, 0, VideoRecibido),
    MttoItsEjec = ifelse(Categoria == "Mtto" & Resultado > 1, 0, MttoItsEjec),
    TckSolucion = ifelse(Categoria == "Mtto" & Resultado > 1, 0, TckSolucion)) %>%
  select(-Resultado, -Categoria, -Division1, -Division2) %>%

  # Se filtran dias atipicos
  filter(Fecha %in% dimfechas$Fecha) %>%
  mutate(Fecha = floor_date(as_date(Fecha), unit = "month"),
         Operador = case_when(Operador == 233 ~ "ZMOV",
                              Operador == 231 ~ "ZMOIII",
                              TRUE ~ as.character(Operador))) %>%
  group_by(Fecha, Operador) %>% 
  summarise(
    across(.cols = where(is.numeric) & !all_of(c("EvntBotoPanico", "CantCamaraBus")), .fns = sum, na.rm = TRUE),
    EventoCamaras = sum(2 * CantCamaraBus * EvntBotoPanico, na.rm = TRUE)) %>%
  ungroup() %>%
  mutate(MttoItsProg = case_when(Operador == "ZMOIII" ~ 193, Operador == "ZMOV" ~ 213, TRUE ~ NA_real_))

## ECS ----------------------------------------------------------------------------------------
# Simulacion de los datos de encuensta de satisfacion
resultado_encuesta <- tibble(
  Fecha = c("2022-06-01", "2022-06-01", "2022-12-01", "2022-12-01", "2023-05-01", "2023-05-01", 
            "2024-05-01", "2024-05-01", "2024-11-01", "2024-11-01", "2024-12-01", "2024-12-01"),
  Operador = c("ZMOV", "ZMOIII", "ZMOV", "ZMOIII", "ZMOV", "ZMOIII", "ZMOV", "ZMOIII", "ZMOV", "ZMOIII",
               "ZMOV", "ZMOIII"),
  Encuesta = c(0.776, 0.802, 0.860, 0.802, 0.946, 0.862, 0.914, 0.805, 0.765, 0.794, 0.799, 0.891)) %>% 
  mutate(Fecha = ymd(Fecha))

dataecs <- dataico %>% 
  select(Fecha, Operador) %>% 
  left_join(resultado_encuesta, by = c("Fecha", "Operador")) %>% 
  replace_na(list(Encuesta = 0))

# Se elimian los objetos que no sirven
rm(list = c("kmeje", "kmprog", "datandej", "datandpr", "datakms"))

# Se unen los indices
datos_emic <- purrr::reduce(list(dataick, dataicd, dataidp,  dataico, dataits, 
                                 dataecs, datadpv, dataisv),
                            dplyr::left_join, by = c("Fecha", "Operador")) %>% 
  ungroup() %>% 
  mutate_if(is.numeric, .funs = replace_na, 0) %>% 
  na.omit()

# Cargue de datos de prueba para validar las funciones de indicadores y puntajes --------------
#a_datos_test <- data.table::fread("01 Inputs/datos_test.csv") %>% 
#  mutate(Fecha = dmy(Fecha))
resultado <- datos_emic %>% 
  rowwise() %>% 
  mutate(IndIsv      = indice_isv(evt = SeguridadVial, kmse = KmDefinitivo),
         Icd         = indice_icd(nde = DespachoEjecutado, ndp = DespachoProgramado),
         Ick         = indice_ick(kmse = KmDefinitivo, kmsp = KmProgramado),
         IndIcs      = indice_ics(icd = Icd, ick = Ick),
         IndDpv      = indice_dpv(kmse = KmDefinitivo, nev = Varados),
         IndIdp      = indice_idp(dpt = DespachoPuntual, dpp = DespachoPatio),
         IndIco      = indice_ico(npi = PuntosIco, kmse = KmDefinitivo),
         Ief         = indice_ie(trv = Tram20Gene, tev = Tram20Espe, trs = Tram60Gene, tes = Tram60Espe),
         Icp         = indice_cp(ecp = ConteoPaxReci, ept = EventoPtaReci),
         Imt         = indice_mt(mpe = MttoItsEjec, mpp = MttoItsProg, tcs = TckSolucion, ttr = TckRegistrado),
         Ibp         = indice_bp(cvr = VideoRecibido, evca = EventoCamaras),
         IndIts      = indice_its(ief = Ief, icp = Icp, imt = Imt, ibp = Ibp)) %>% 
  mutate(PuntIsv     = puntaje_isv(IndIsv = IndIsv, Fecha = Fecha),
         PuntIcs     = puntaje_ics(IndIcs = IndIcs, Fecha = Fecha),
         PuntDpv     = puntaje_dpv(IndDpv = IndDpv, Fecha = Fecha),
         PuntIdp     = puntaje_idp(IndIdp = IndIdp, Fecha = Fecha),
         PuntIco     = puntaje_ico(IndIco = IndIco, Fecha = Fecha),
         PuntIts     = puntaje_its(IndIts = IndIts, Fecha = Fecha),
         PuntEct     = puntaje_ect(IndEct = Encuesta, Fecha = Fecha))

resultado <- resultado %>% 
  cbind(purrr::pmap_df(list(Fecha = resultado$Fecha,
                            PtSv = resultado$PuntIsv, 
                            PtCs = resultado$PuntIcs, 
                            PtDp = resultado$PuntIdp,
                            PtDpv = resultado$PuntDpv,
                            PtIco = resultado$PuntIco,
                            PtIts = resultado$PuntIts,
                            PtEct = resultado$PuntEct), WtPuntaje))

# Cargue de datos al DW -----------------------------------------------------------------------
odbc::dbWriteTable(cona(), DBI::SQL('op."FactEmicResult"'), resultado, overwrite = TRUE)
registrar_actualizacion(cona(), 105, IdProceso, 
                        max_fecha_tabla = max(resultado$Fecha, na.rm = TRUE),
                        cantidad_registros = nrow(resultado))
odbc::dbWriteTable(cona(), DBI::SQL('op."FactEmicVlrRef"'), a_valores_referencia, overwrite = TRUE)
registrar_actualizacion(cona(), 106, IdProceso, 
                        max_fecha_tabla = max(a_valores_referencia$FechaFin, na.rm = TRUE),
                        cantidad_registros = nrow(a_valores_referencia))
}, error = function(e){registrar_actualizacion(cona(), 105, IdProceso, observacion = e$message)
                       registrar_actualizacion(cona(), 106, IdProceso, observacion = e$message)})
actualizar_fecha_proceso(cona(), IdProceso)
# Notificacion de operaciones -----------------------------------------------------------------
mensaje <- list(
  channel = Sys.getenv("SLK_EMIC_OPE"),
  text = paste0(
    "\u2705 El proceso de la *EMIC* se ejecuto correctamente.\n",
    "\U0001F4E6 La informacion ya esta disponible en el *Data Warehouse*.\n",
    "\U0001F552 Fecha de ejecucion: ", format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  ),
  mrkdwn = TRUE
)
mensaje$text <- enc2utf8(mensaje$text)

# Enviar el mensaje
res <- POST(
  url = "https://slack.com/api/chat.postMessage",
  add_headers(Authorization = paste("Bearer", Sys.getenv("TOK_SLACK_MESG"))),
  content_type_json(),
  body = mensaje,
  encode = "json"
)

# Actualizacion del dataset de PowerBI --------------------------------------------------------
path <- Sys.getenv("PAT_PBI_REFRESH")

# Dataset del Emic 
system(paste('python', shQuote(path), Sys.getenv("PBI_EMIC"), sep = ' '))

Sys.sleep(60)

# Dataset Novedades Operacionales
system(paste('python', shQuote(path), Sys.getenv("PBI_NOVOPERACIONAL"), sep = ' '))

# Envio de resultados del dPV al canal de varados ---------------------------------------------
mensage <- glue::glue("Los resultados del *DPV* para el mes de *{format(as_date(tail(resultado$Fecha, 1)), '%B')}* son:

 - *ZMOV: * *{round(tail(resultado$IndDpv[resultado$Operador == 'ZMOV'], 1), 0)}* kms/Varado

 - *ZMOIII: * *{round(tail(resultado$IndDpv[resultado$Operador == 'ZMOIII'], 1), 0)}* kms/Varado 
 
:muscle: *Nuestra meta es de 30.000 kms/varado*")

## Envio mensaje Slack ma-ej-varados 
slackr_msg(mensage, channel = Sys.getenv("SLK_VARADOS"))

# Ejecucion del proceso de informes por correo ------------------------------------------------
source("C:/Users/dev/Documents/01 Modelos/20220714-analisis-provision/Render-Informes.R", chdir = T)

#**********************************************************************************************
#  @Nombre: Funciones para el cálculo de los Indices EIC
#  @Autor: Anderson Sarmiento
#**********************************************************************************************

#**********************************************************************************************
# 10.1. Puntaje por Gestión de Seguridad Vial -------------------------------------------------
#**********************************************************************************************
puntaje_isv <- function(IndIsv, Fecha, Servicio = "uce") {
  
  # Se obtiene los puntajes
  PtgIsvEst <- a_puntajes["PuntIsv", "PuntajeEst"]
  PtgIsvCrt <- a_puntajes["PuntIsv", "PuntajeCrit"]

  # Se obtiene los valores de referencia
  VlrRefIsvEst <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefIsv", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorEstandar) %>%
    unlist() %>% 
    unname()
    
  VlrRefIsvCrt <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefIsv", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorCritico) %>%
    unlist() %>% 
    unname()
  
  # Definicion de parametros
  b <- (PtgIsvEst - PtgIsvCrt) / (VlrRefIsvEst - VlrRefIsvCrt)
  a <- PtgIsvEst - (b *  VlrRefIsvEst)
  
  # Bucle para obtener el puntaje de acuerdo con los condicionales de la formula
  if (IndIsv < VlrRefIsvEst) {
    
    return(PtgIsvEst)
    
  } else if ((VlrRefIsvEst <= IndIsv) && (IndIsv < VlrRefIsvCrt)) {
    
    return(a + (b * IndIsv))
    
  } else {
    
    return(0)
    
  }
  
}

#**********************************************************************************************
# 10.2. Puntaje por Gestión de Cumplimiento de Servicios --------------------------------------
#**********************************************************************************************
puntaje_ics <- function(IndIcs, Fecha, Servicio = "uce") {
  
  # Se obtiene los puntajes
  PtgIcsEst <- a_puntajes["PuntIcs", "PuntajeEst"]
  PtgIcsCrt <- a_puntajes["PuntIcs", "PuntajeCrit"]
  
  # Se obtiene los valores de referencia
  VlrRefIcsEst <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefIcs", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorEstandar) %>%
    unlist() %>% 
    unname()
  
  VlrRefIcsCrt <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefIcs", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorCritico) %>%
    unlist() %>% 
    unname()
  
  # Definicion de parametros
  b <- (PtgIcsEst - PtgIcsCrt) / (VlrRefIcsEst - VlrRefIcsCrt)
  a <- PtgIcsEst - (b *  VlrRefIcsEst)
  
  # Bucle para obtener el puntaje de acuerdo con los condicionales de la formula
  if (IndIcs >= VlrRefIcsEst) {
    
    return(PtgIcsEst)
    
  } else if ((VlrRefIcsCrt <= IndIcs) && (IndIcs < VlrRefIcsEst)) {
    
    return(a + (b * IndIcs))
    
  } else {
    
    return(0)
    
  }

}

#**********************************************************************************************
# 10.3. Puntaje por Gestión de Mantenimiento --------------------------------------------------
#**********************************************************************************************
puntaje_dpv <- function(IndDpv, Fecha, Servicio = "uce") {
  
  # Se obtiene los puntajes
  PtgDpvEst <- a_puntajes["PuntDpv", "PuntajeEst"]
  PtgDpvCrt <- a_puntajes["PuntDpv", "PuntajeCrit"]
  
  # Se obtiene los valores de referencia
  VlrRefDpvEst <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefDpv", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorEstandar) %>%
    unlist() %>% 
    unname()
  
  VlrRefDpvCrt <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefDpv", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorCritico) %>%
    unlist() %>% 
    unname()
  
  # Definicion de parametros
  b <- (PtgDpvEst - PtgDpvCrt) / (VlrRefDpvEst - VlrRefDpvCrt)
  a <- PtgDpvEst - (b *  VlrRefDpvEst)
  
  # Bucle para obtener el puntaje de acuerdo con los condicionales de la formula
  if (IndDpv >= VlrRefDpvEst) {
    
    return(PtgDpvEst)
    
  } else if ((VlrRefDpvCrt <= IndDpv) && (IndDpv < VlrRefDpvEst)) {
    
    return(a + (b * IndDpv))
    
  } else {
    
    return(0)
    
  }
  
}

#**********************************************************************************************
# 10.4. Puntaje por Gestión de Despachos Puntuales --------------------------------------------
#**********************************************************************************************
puntaje_idp <- function(IndIdp, Fecha, Servicio = "uce") {
  
  # Se obtiene los puntajes
  PtgIdpEst <- a_puntajes["PuntIdp", "PuntajeEst"]
  PtgIdpCrt <- a_puntajes["PuntIdp", "PuntajeCrit"]
  
  # Se obtiene los valores de referencia
  VlrRefIdpEst <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefIdp", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorEstandar) %>%
    unlist() %>% 
    unname()
  
  VlrRefIdpCrt <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefIdp", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorCritico) %>%
    unlist() %>% 
    unname()

  # Definicion de parametros
  b <- (PtgIdpEst - PtgIdpCrt) / (VlrRefIdpEst - VlrRefIdpCrt)
  a <- PtgIdpEst - (b *  VlrRefIdpEst)
  
  # Bucle para obtener el puntaje de acuerdo con los condicionales de la formula
  if (IndIdp >= VlrRefIdpEst) {
    
    return(PtgIdpEst)
    
  } else if ((VlrRefIdpCrt <= IndIdp) && (IndIdp < VlrRefIdpEst)) {
    
    return(a + (b * IndIdp))

  } else {
    
    return(0)
    
  }
  
}

#**********************************************************************************************
# 10.5. Puntaje por Gestión de Conducta Operacional -------------------------------------------
#**********************************************************************************************
puntaje_ico <- function(IndIco, Fecha, Servicio = "uce") {
  
  # Se obtiene los puntajes
  PtgIcoEst <- a_puntajes["PuntIco", "PuntajeEst"]
  PtgIcoCrt <- a_puntajes["PuntIco", "PuntajeCrit"]
  
  # Se obtiene los valores de referencia
  VlrRefIcoEst <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefIco", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorEstandar) %>%
    unlist() %>% 
    unname()
  
  VlrRefIcoCrt <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefIco", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorCritico) %>%
    unlist() %>% 
    unname()
  
  # Definicion de parametros
  b <- (PtgIcoEst - PtgIcoCrt) / (VlrRefIcoEst - VlrRefIcoCrt)
  a <- PtgIcoEst - (b *  VlrRefIcoEst)
  
  # Bucle para obtener el puntaje de acuerdo con los condicionales de la formula
  if (IndIco <= VlrRefIcoEst) {
    
    return(PtgIcoEst)
    
  } else if ((VlrRefIcoEst < IndIco) && (IndIco <= VlrRefIcoCrt)) {
    
    return(a + (b * IndIco))
    
  } else {
    
    return(0)
    
  }
  
}

#**********************************************************************************************
# 10.6. Puntaje por Gestión de ITS ------------------------------------------------------------
#**********************************************************************************************
puntaje_its <- function(IndIts, Fecha, Servicio = "uce") {
  
  # Se obtiene los puntajes
  PtgItsEst <- a_puntajes["PuntIts", "PuntajeEst"]
  PtgItsCrt <- a_puntajes["PuntIts", "PuntajeCrit"]
  
  # Se obtiene los valores de referencia
  VlrRefItsEst <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefIts", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorEstandar) %>%
    unlist() %>% 
    unname()
  
  VlrRefItsCrt <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefIts", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorCritico) %>%
    unlist() %>% 
    unname()
  
  # Definicion de parametros
  b <- (PtgItsEst - PtgItsCrt) / (VlrRefItsEst - VlrRefItsCrt)
  a <- PtgItsEst - (b *  VlrRefItsEst)
  
  # Bucle para obtener el puntaje de acuerdo con los condicionales de la formula
  if (IndIts >= VlrRefItsEst) {
    
    return(PtgItsEst)
    
  } else if ((VlrRefItsEst > IndIts) && (IndIts >= VlrRefItsCrt)) {
    
    return(a + (b * IndIts))
    
  } else {
    
    return(0)
    
  }
  
}

#**********************************************************************************************
# 10.7. Puntaje por Incentivo -----------------------------------------------------------------
#**********************************************************************************************
puntaje_ect <- function(IndEct, Fecha, Servicio = "uce") {
  
  # Se obtiene los puntajes
  PtgEctEst <- a_puntajes["PuntEct", "PuntajeEst"]
  PtgEctCrt <- a_puntajes["PuntEct", "PuntajeCrit"]
  
  # Se obtiene los valores de referencia
  VlrRefEctEst <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefEct", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorEstandar) %>%
    unlist() %>% 
    unname()
  
  VlrRefEctCrt <- a_valores_referencia %>% 
    filter(Indicador == "VlrRefEct", TipoServicio == Servicio) %>% 
    filter(FechaInicio <= Fecha, Fecha <= FechaFin) %>% 
    select(ValorCritico) %>%
    unlist() %>% 
    unname()
  
  # Definicion de parametros
  b <- (PtgEctEst - PtgEctCrt) / (VlrRefEctEst - VlrRefEctCrt)
  a <- PtgEctEst - (b *  VlrRefEctEst)
  
  # Bucle para obtener el puntaje de acuerdo con los condicionales de la formula
  if (IndEct >= VlrRefEctEst) {
    
    return(PtgEctEst)
    
  } else if ((VlrRefEctCrt <= IndEct) && (IndEct < VlrRefEctEst)) {
    
    return(a + (b * IndEct))
    
  } else {
    
    return(0)
    
  }
  
}

# Puntajes Ponderados -------------------------------------------------------------------------
WtPuntaje <- function(Fecha, PtSv, PtCs, PtDp, PtDpv, PtIco, PtIts, PtEct) {
  Fecha <- as.Date(Fecha)
  
  get_ponderacion <- function(variable, Fecha) {
    ponderacion <- a_ponderaciones %>%
      filter(Variable == variable, Fecha >= FechaIni, Fecha <= FechaFin) %>%
      select(Ponderacion) %>%
      slice(1) %>%
      pull()
    return(ponderacion)
  }
  
  WtSv <- PtSv * get_ponderacion("WtSv", Fecha)
  WtCs <- PtCs * get_ponderacion("WtCs", Fecha)
  WtDp <- PtDp * get_ponderacion("WtDp", Fecha)
  WtDpv <- PtDpv * get_ponderacion("WtDpv", Fecha)
  WtIco <- PtIco * get_ponderacion("WtIco", Fecha)
  WtIts <- PtIts * get_ponderacion("WtIts", Fecha)
  WtEct <- PtEct * get_ponderacion("WtEct", Fecha)
  
  puntaje <- (WtSv + WtCs + WtDp + WtDpv + WtIco + WtIts + WtEct)
  
  Nivel <- case_when(
    puntaje < 60 ~ "E",
    puntaje < 70 ~ "D",
    puntaje < 80 ~ "C",
    puntaje < 90 ~ "B",
    puntaje <= 120 ~ "A"
  )
  
  Calificacion <- case_when(
    Nivel == "A" ~ a_nivel_servicio$Calificacion[1],
    Nivel == "B" ~ a_nivel_servicio$Calificacion[2],
    Nivel == "C" ~ a_nivel_servicio$Calificacion[3],
    Nivel == "D" ~ a_nivel_servicio$Calificacion[4],
    Nivel == "E" ~ a_nivel_servicio$Calificacion[5]
  )
  
  list(
    "WtSv"          = WtSv,
    "WtCs"          = WtCs,
    "WtDp"          = WtDp,
    "WtDpv"         = WtDpv,
    "WtIco"         = WtIco,
    "WtIts"         = WtIts,
    "WtEct"         = WtEct,
    "Puntaje"       = puntaje,
    "Nivel"         = Nivel,
    "Calificacion"  = Calificacion
  )
}

#**********************************************************************************************
#  @Nombre: Funciones para el cálculo de los Indices EIC
#  @Autor: Anderson Sarmiento
#**********************************************************************************************

# Definicion de variables estandar para los indicadores ---------------------------------------
# @kmse   = Número total de kilómetros en servicio ejecutados por el concesionario
# @kmsea  = Número total de kilómetros en servicio ejecutados por el concesionario adicionales

#**********************************************************************************************
# 8.1. Gestión de Seguridad Vial --------------------------------------------------------------
#**********************************************************************************************
# @evt = Se introduce el valor del resultado de los eventos de acuerdo con los factores
# ponderadores
indice_isv <- function(evt, kmse, kmsea = 0) {
  
  isv <- (evt) * 10000 / (kmse + kmsea) 
  
  return(isv)
  
}

#**********************************************************************************************
# 8.2. Gestión de Cumplimiento de Servicios ---------------------------------------------------
#**********************************************************************************************
# Indice de cumplimiento de Servicio  ---------------------------------------------------------
indice_ics <- function(icd, ick) {
  
  ics <- mean(c(icd, ick), na.rm = T)
  
  return(ics)
  
}

## 8.2.1. Índice de Cumplimiento de Despachos (ICD) -------------------------------------------
# @nde  = Número total de despachos ejecutados por el concesionario.
# @ndea = Número total de despachos adicionales ejecutados por el concesionario
# @ndp  = Número total de despachos programados
# @ndpa = Número total de despachos programados adicionales
indice_icd <- function(nde, ndea = 0, ndp, ndpa = 0) {
  
  icd <- ((nde + ndea) / (ndp + ndpa))
  
  return(icd)
  
}

## 8.2.2. Índice de Cumplimiento de Kilómetros (ICK) ------------------------------------------
# @kmsp   = Número total de kilómetros en servicio programados
# @kmspa  = Número total de kilómetros en servicio adicionales autorizados
indice_ick <- function(kmse, kmsea = 0, kmsp, kmspa = 0) {
  
  ick <- ((kmse + kmsea) / (kmsp + kmspa))
  
  return(ick)
  
}

#**********************************************************************************************
# 8.3. Gestión del Mantenimiento --------------------------------------------------------------
#**********************************************************************************************
# @nev = Número total de varados en el periodo evaluado
indice_dpv <- function(kmse, kmsea = 0, nev) {
  
  dpv <- ((kmse + kmsea) / nev)
  
  return(dpv)
  
}

#**********************************************************************************************
# 8.4. Gestión de Despachos Puntuales ---------------------------------------------------------
#**********************************************************************************************
# @dpt  = Número de despachos iniciales con precedente de salida de patio, ejecutados puntualmente
# @dpp   = Número de despachos totales programados con precedente de salida
indice_idp <- function(dpt, dpp) {
  
  idp <- ifelse(dpp == 0, 1, (dpt / dpp))
  
  return(idp)
  
}

#**********************************************************************************************
# 8.5. Gestión de Conducta Operacional --------------------------------------------------------
#**********************************************************************************************
# @npi = Número total de puntos obtenidos por infracciones
indice_ico <- function(npi, kmse, kmsea = 0) {
  
  ico <- (npi / (kmse + kmsea)) * 10000
  
  return(ico)
  
}

#**********************************************************************************************
# 8.6. Gestión de Elementos ITS ---------------------------------------------------------------
#**********************************************************************************************
# Indice de Funcionamiento ITS ----------------------------------------------------------------
indice_its <- function(ief, icp, imt, ibp) {
  
  if (ief == 0L && icp == 0L && imt == 0L && ibp == 0L) {
    
    return(0L)
    
  } else {
    
    its <- ief + icp + imt + ibp
    
    return(its)
    
  }
  
}

## 8.6.1. Indicador de Efectividad ------------------------------------------------------------
# @trv  = Cantidad de tramas de 20 segundos efectivamente generadas y recibidas.
# @tev  = Cantidad de tramas de 20 segundos esperadas
# @trs  = Cantidad de tramas de 60 segundos efectivamente generadas y recibidas
# @tes  = Cantidad de tramas de 60 segundos esperadas
indice_ie <- function(trv, tev, trs, tes) {
  
  if (trv == 0L || tev == 0L || trs == 0L || tes == 0L) {
    
    return(0L)
  
  } else {
  
  ief <- (((trv / tev) * 0.2) + ((trs / tes) * 0.3))
  
  return(ief)
  
  }
  
}

## 8.6.2. Indicador de actividad de conteo de pasajeros ---------------------------------------
# @ecp  = Cantidad de eventos de conteo de pasajeros recibidos
# @ept  = Cantidad de eventos de cierre de puertas recibidos
indice_cp <- function(ecp, ept) {
  
  if (ecp == 0L || ept == 0L) {
    
    return(0L)
  
  } else {
    
  icp <- ((ecp / ept) * 0.2)
  
  return(icp)
  
  }
  
}

## 8.6.3. Relación de los mantenimientos de los ITS -------------------------------------------
# @mpe  = Cantidad de mantenimientos preventivos ejecutados sobre los ITS
# @mpp  = Cantidad de mantenimientos preventivos programados sobre los ITS
# @tcs  = Cantidad de tickets con solución en el tiempo de solución conforme al nivel de falla establecido
# @ttr  = Número total de tickets registrados en la mesa de ayuda
indice_mt <- function(mpe, mpp, tcs, ttr) {
  
  if (mpe == 0L || mpp == 0L || tcs == 0L || ttr == 0L) {
    
    return(0L)

  } else {
  
  imt <- (((mpe / mpp) * 0.03) + ((tcs / ttr) * 0.07))
  
  return(imt)
  
  }
  
}

## 8.6.4. Relación de videos recibidos sobre eventos de botón de pánico -----------------------
# @cvr  = Cantidad de videos recibidos por TMSA
# @ccb  = Cantidad de cámaras por bus
# @cpe  = Cantidad de eventos de pisón de emergencia recibidos
indice_bp <- function(cvr, evca) {
  
  if (cvr == 0L || evca == 0L) {
    
    return(0L)
  
  } else { 
  
  ibp <- ((cvr / evca) * 0.2)
  
  return(ibp)
  
  }
  
}







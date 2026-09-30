-- ********************************************************************************************
-- @Nombre: Query para obtener el fact de movimientos
-- @Autor: Anderson Sarmiento
-- ********************************************************************************************

SELECT 
f351_id_cia as IdCompania,
--f351_rowid_docto as RowIdDocumento,
dct.f350_consec_docto as ConsecutivoDocumento,
dct.f350_id_tipo_docto as TipoDocumento,
--f351_rowid_auxiliar as RowIdAuxiliar,
aux.f253_id as IdAuxiliar,
f351_rowid_tercero as RowIdTercero,
f351_rowid_ccosto as RowIdCentroCosto,
cco.f284_id as CentroDeCosto,
f351_rowid_fe as RowIdFlujoEfectivo,
f351_fecha as Fecha,
CASE 
    WHEN f351_ind_estado = 0 THEN 'Elaboracion'
    WHEN f351_ind_estado = 1 THEN 'Aprobado'
    WHEN f351_ind_estado = 2 THEN 'Anulado'
END as IndEstado,
f351_notas as Notas,
f351_valor_db2 as ValorDebito2,
f351_valor_cr2 as ValorCredito2
from BI_GRMUNOEREALUF06.dbo.t351_co_mov_docto doc
-- traemos el consecutivo del documento
LEFT JOIN BI_GRMUNOEREALUF06.dbo.t350_co_docto_contable dct
        on doc.f351_id_cia = dct.f350_id_cia and doc.f351_rowid_docto = dct.f350_rowid
LEFT JOIN BI_GRMUNOEREALUF06.dbo.t253_co_auxiliares aux
        on doc.f351_id_cia = aux.f253_id_cia and doc.f351_rowid_auxiliar = aux.f253_rowid
LEFT JOIN BI_GRMUNOEREALUF06.dbo.t284_co_ccosto cco
        on doc.f351_id_cia = cco.f284_id_cia and doc.f351_rowid_ccosto = cco.f284_rowid

UNION ALL

SELECT 
CASE 
    WHEN f351_id_cia = 1 THEN 3
    WHEN f351_id_cia = 2 THEN 4
END as IdCompania,
--f351_rowid_docto as RowIdDocumento,
dct.f350_consec_docto as ConsecutivoDocumento,
dct.f350_id_tipo_docto as TipoDocumento,
--f351_rowid_auxiliar as RowIdAuxiliar,
aux.f253_id as IdAuxiliar,
f351_rowid_tercero as RowIdTercero,
f351_rowid_ccosto as RowIdCentroCosto,
cco.f284_id as CentroDeCosto,
f351_rowid_fe as RowIdFlujoEfectivo,
f351_fecha as Fecha,
CASE 
    WHEN f351_ind_estado = 0 THEN 'Elaboracion'
    WHEN f351_ind_estado = 1 THEN 'Aprobado'
    WHEN f351_ind_estado = 2 THEN 'Anulado'
END as IndEstado,
f351_notas as Notas,
f351_valor_db2 as ValorDebito2,
f351_valor_cr2 as ValorCredito2
from BI_GRMUNOEREALUF17.dbo.t351_co_mov_docto doc
-- traemos el consecutivo del documento
LEFT JOIN BI_GRMUNOEREALUF17.dbo.t350_co_docto_contable dct
        on doc.f351_id_cia = dct.f350_id_cia and doc.f351_rowid_docto = dct.f350_rowid
LEFT JOIN BI_GRMUNOEREALUF17.dbo.t253_co_auxiliares aux
        on doc.f351_id_cia = aux.f253_id_cia and doc.f351_rowid_auxiliar = aux.f253_rowid
LEFT JOIN BI_GRMUNOEREALUF17.dbo.t284_co_ccosto cco
        on doc.f351_id_cia = cco.f284_id_cia and doc.f351_rowid_ccosto = cco.f284_rowid

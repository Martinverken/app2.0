from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from uuid import UUID
import uuid
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel

from database import get_supabase

router = APIRouter()

# Modelos para pagos
class InvoicePaymentCreate(BaseModel):
    invoice_id: UUID
    monto_pagado: Decimal
    fecha: date
    metodo_pago: Optional[str] = None
    referencia: Optional[str] = None
    due_id: Optional[UUID] = None  # Para aplicar a vencimiento específico
    notas: Optional[str] = None

class InvoicePaymentUpdate(BaseModel):
    monto_pagado: Optional[Decimal] = None
    fecha: Optional[date] = None
    metodo_pago: Optional[str] = None
    referencia: Optional[str] = None
    notas: Optional[str] = None

@router.get("/", response_model=dict)
async def get_payments(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    invoice_id: Optional[UUID] = None,
    supplier_id: Optional[UUID] = None,
    metodo_pago: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None
):
    """Obtener lista de pagos con paginación y filtros"""
    try:
        supabase = get_supabase()
        
        # Query con JOIN para incluir información de factura y proveedor
        query = supabase.table('invoice_payment').select('''
            *,
            invoices!invoice_payment_invoice_id_fkey(
                numero_factura, monto_total,
                suppliers!invoices_supplier_id_fkey(nombre)
            )
        ''')
        
        # Aplicar filtros
        if invoice_id:
            query = query.eq('invoice_id', str(invoice_id))
        
        if metodo_pago:
            query = query.eq('metodo_pago', metodo_pago)
        
        if fecha_desde:
            query = query.gte('fecha', fecha_desde.isoformat())
        
        if fecha_hasta:
            query = query.lte('fecha', fecha_hasta.isoformat())
        
        # Filtro por proveedor (más complejo, requiere subconsulta)
        if supplier_id:
            # Primero obtener facturas del proveedor
            invoices_supplier = supabase.table('invoices').select('id').eq('supplier_id', str(supplier_id)).execute()
            invoice_ids = [inv['id'] for inv in invoices_supplier.data]
            if invoice_ids:
                query = query.in_('invoice_id', invoice_ids)
            else:
                # No hay facturas para este proveedor
                return {
                    "success": True,
                    "data": [],
                    "total": 0,
                    "page": page,
                    "per_page": per_page,
                    "pages": 0
                }
        
        # Contar total (simplificado sin joins complejos)
        count_query = supabase.table('invoice_payment').select('*', count='exact')
        if invoice_id:
            count_query = count_query.eq('invoice_id', str(invoice_id))
        if metodo_pago:
            count_query = count_query.eq('metodo_pago', metodo_pago)
        if fecha_desde:
            count_query = count_query.gte('fecha', fecha_desde.isoformat())
        if fecha_hasta:
            count_query = count_query.lte('fecha', fecha_hasta.isoformat())
        
        total_result = count_query.execute()
        total = total_result.count
        
        # Aplicar paginación
        offset = (page - 1) * per_page
        query = query.range(offset, offset + per_page - 1).order('fecha', desc=True)
        
        result = query.execute()
        
        return {
            "success": True,
            "data": result.data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo pagos: {str(e)}")

@router.get("/{payment_id}", response_model=dict)
async def get_payment(payment_id: UUID):
    """Obtener un pago específico"""
    try:
        supabase = get_supabase()
        
        result = supabase.table('invoice_payment').select('''
            *,
            invoices!invoice_payment_invoice_id_fkey(
                numero_factura, monto_total, saldo_pendiente,
                suppliers!invoices_supplier_id_fkey(nombre, contacto)
            )
        ''').eq('id', str(payment_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Pago no encontrado")
        
        payment = result.data[0]
        
        # Obtener aplicaciones a vencimientos específicos
        due_payments = supabase.table('invoice_due_payment').select('''
            *,
            invoice_due!invoice_due_payment_due_id_fkey(fecha_vencimiento, monto_vencimiento)
        ''').eq('source', 'pago').eq('source_id', str(payment_id)).execute()
        
        payment['aplicaciones_vencimientos'] = due_payments.data
        
        return {
            "success": True,
            "data": payment
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo pago: {str(e)}")

@router.post("/", response_model=dict)
async def create_payment(payment_data: InvoicePaymentCreate):
    """Crear nuevo pago de factura"""
    try:
        supabase = get_supabase()
        
        # Verificar que la factura existe
        invoice_result = supabase.table('invoices').select('*').eq('id', str(payment_data.invoice_id)).execute()
        if not invoice_result.data:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        invoice = invoice_result.data[0]
        
        # Verificar saldo pendiente
        saldo_pendiente = float(invoice.get('saldo_pendiente', 0))
        if float(payment_data.monto_pagado) > saldo_pendiente:
            raise HTTPException(status_code=400, detail=f"Monto a pagar ({payment_data.monto_pagado}) excede el saldo pendiente ({saldo_pendiente})")
        
        # Si se especifica vencimiento, verificarlo
        if payment_data.due_id:
            due_result = supabase.table('invoice_due').select('*').eq('id', str(payment_data.due_id)).eq('invoice_id', str(payment_data.invoice_id)).execute()
            if not due_result.data:
                raise HTTPException(status_code=404, detail="Vencimiento no encontrado")
        
        # Preparar datos del pago
        payment_dict = payment_data.model_dump()
        payment_dict['id'] = str(uuid.uuid4())
        payment_dict['invoice_id'] = str(payment_data.invoice_id)
        payment_dict['monto_pagado'] = float(payment_data.monto_pagado)
        payment_dict['fecha'] = payment_dict['fecha'].isoformat()
        payment_dict['created_at'] = datetime.utcnow().isoformat()
        
        # Remover campos que no van en la tabla principal
        due_id = payment_dict.pop('due_id', None)
        
        # Insertar pago
        result = supabase.table('invoice_payment').insert(payment_dict).execute()
        payment = result.data[0]
        
        # Si hay vencimiento específico, crear registro en invoice_due_payment
        if due_id:
            due_payment_data = {
                'id': str(uuid.uuid4()),
                'due_id': str(due_id),
                'source': 'pago',
                'source_id': payment['id'],
                'monto_aplicado': float(payment_data.monto_pagado),
                'fecha': datetime.utcnow().isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }
            supabase.table('invoice_due_payment').insert(due_payment_data).execute()
        
        # Actualizar saldo pendiente de la factura
        nuevo_saldo = saldo_pendiente - float(payment_data.monto_pagado)
        nuevo_estado = 'pagada_completa' if nuevo_saldo <= 0 else 'pagada_parcial'
        
        supabase.table('invoices').update({
            'saldo_pendiente': max(0, nuevo_saldo),
            'estado': nuevo_estado,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', str(payment_data.invoice_id)).execute()
        
        return {
            "success": True,
            "message": f"Pago registrado exitosamente. Nuevo saldo: ${nuevo_saldo:.2f}",
            "data": {
                **payment,
                "nuevo_saldo_factura": max(0, nuevo_saldo),
                "nuevo_estado_factura": nuevo_estado
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando pago: {str(e)}")

@router.put("/{payment_id}", response_model=dict)
async def update_payment(payment_id: UUID, payment_data: InvoicePaymentUpdate):
    """Actualizar pago existente"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        existing = supabase.table('invoice_payment').select('*').eq('id', str(payment_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Pago no encontrado")
        
        current_payment = existing.data[0]
        
        # Preparar datos (solo campos no nulos)
        update_data = {k: v for k, v in payment_data.model_dump().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No hay datos para actualizar")
        
        # Si se actualiza el monto, recalcular saldo de factura
        if 'monto_pagado' in update_data:
            # Obtener factura actual
            invoice_result = supabase.table('invoices').select('*').eq('id', current_payment['invoice_id']).execute()
            invoice = invoice_result.data[0]
            
            # Calcular diferencia
            monto_anterior = float(current_payment['monto_pagado'])
            monto_nuevo = float(update_data['monto_pagado'])
            diferencia = monto_nuevo - monto_anterior
            
            # Verificar que no exceda el saldo disponible
            saldo_actual = float(invoice.get('saldo_pendiente', 0))
            saldo_con_ajuste = saldo_actual - diferencia
            
            if saldo_con_ajuste < 0:
                raise HTTPException(status_code=400, detail="El nuevo monto excedería el total de la factura")
            
            # Actualizar saldo de factura
            nuevo_estado = 'pagada_completa' if saldo_con_ajuste <= 0 else 'pagada_parcial'
            supabase.table('invoices').update({
                'saldo_pendiente': max(0, saldo_con_ajuste),
                'estado': nuevo_estado,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', current_payment['invoice_id']).execute()
            
            update_data['monto_pagado'] = monto_nuevo
        
        # Convertir fecha si está presente
        if 'fecha' in update_data:
            update_data['fecha'] = update_data['fecha'].isoformat()
        
        # Actualizar pago
        result = supabase.table('invoice_payment').update(update_data).eq('id', str(payment_id)).execute()
        
        return {
            "success": True,
            "message": "Pago actualizado exitosamente",
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando pago: {str(e)}")

@router.delete("/{payment_id}", response_model=dict)
async def delete_payment(payment_id: UUID):
    """Eliminar pago"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        existing = supabase.table('invoice_payment').select('*').eq('id', str(payment_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Pago no encontrado")
        
        payment = existing.data[0]
        
        # Obtener factura para recalcular saldo
        invoice_result = supabase.table('invoices').select('*').eq('id', payment['invoice_id']).execute()
        invoice = invoice_result.data[0]
        
        # Eliminar aplicaciones a vencimientos
        supabase.table('invoice_due_payment').delete().eq('source', 'pago').eq('source_id', str(payment_id)).execute()
        
        # Eliminar pago
        supabase.table('invoice_payment').delete().eq('id', str(payment_id)).execute()
        
        # Recalcular saldo de factura
        saldo_actual = float(invoice.get('saldo_pendiente', 0))
        nuevo_saldo = saldo_actual + float(payment['monto_pagado'])
        nuevo_estado = 'pendiente' if nuevo_saldo >= float(invoice['monto_total']) else 'pagada_parcial'
        
        supabase.table('invoices').update({
            'saldo_pendiente': nuevo_saldo,
            'estado': nuevo_estado,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', payment['invoice_id']).execute()
        
        return {
            "success": True,
            "message": f"Pago eliminado. Saldo de factura actualizado a ${nuevo_saldo:.2f}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando pago: {str(e)}")

@router.get("/por-factura/{invoice_id}", response_model=dict)
async def get_payments_by_invoice(invoice_id: UUID):
    """Obtener todos los pagos de una factura específica"""
    try:
        supabase = get_supabase()
        
        # Verificar que la factura existe
        invoice_result = supabase.table('invoices').select('*').eq('id', str(invoice_id)).execute()
        if not invoice_result.data:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        invoice = invoice_result.data[0]
        
        # Obtener pagos
        payments_result = supabase.table('invoice_payment').select('*').eq('invoice_id', str(invoice_id)).order('fecha', desc=True).execute()
        
        # Para cada pago, obtener aplicaciones a vencimientos
        for payment in payments_result.data:
            due_payments = supabase.table('invoice_due_payment').select('''
                *,
                invoice_due!invoice_due_payment_due_id_fkey(fecha_vencimiento, monto_vencimiento)
            ''').eq('source', 'pago').eq('source_id', payment['id']).execute()
            
            payment['aplicaciones_vencimientos'] = due_payments.data
        
        # Calcular totales
        total_pagos = sum(float(pay['monto_pagado']) for pay in payments_result.data)
        
        return {
            "success": True,
            "data": {
                "factura": invoice,
                "pagos": payments_result.data,
                "resumen": {
                    "total_pagos": round(total_pagos, 2),
                    "cantidad_pagos": len(payments_result.data),
                    "saldo_pendiente": round(float(invoice.get('saldo_pendiente', 0)), 2)
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo pagos de la factura: {str(e)}")

@router.get("/stats/resumen", response_model=dict)
async def get_payments_stats():
    """Estadísticas generales de pagos"""
    try:
        supabase = get_supabase()
        
        # Obtener todos los pagos
        payments_result = supabase.table('invoice_payment').select('monto_pagado, fecha, metodo_pago').execute()
        
        # Estadísticas básicas
        total_pagos = len(payments_result.data)
        monto_total_pagado = sum(float(pay['monto_pagado']) for pay in payments_result.data)
        
        # Por método de pago
        por_metodo = {}
        for payment in payments_result.data:
            metodo = payment.get('metodo_pago', 'No especificado')
            if metodo not in por_metodo:
                por_metodo[metodo] = {'cantidad': 0, 'monto': 0}
            por_metodo[metodo]['cantidad'] += 1
            por_metodo[metodo]['monto'] += float(payment['monto_pagado'])
        
        # Pagos por mes (últimos 6 meses)
        from collections import defaultdict
        pagos_por_mes = defaultdict(lambda: {'cantidad': 0, 'monto': 0})
        
        for payment in payments_result.data:
            if payment.get('fecha'):
                fecha = datetime.fromisoformat(payment['fecha'])
                mes_key = fecha.strftime('%Y-%m')
                pagos_por_mes[mes_key]['cantidad'] += 1
                pagos_por_mes[mes_key]['monto'] += float(payment['monto_pagado'])
        
        return {
            "success": True,
            "data": {
                "totales": {
                    "cantidad_pagos": total_pagos,
                    "monto_total": round(monto_total_pagado, 2)
                },
                "por_metodo": {k: {**v, 'monto': round(v['monto'], 2)} for k, v in por_metodo.items()},
                "por_mes": {k: {**v, 'monto': round(v['monto'], 2)} for k, v in dict(pagos_por_mes).items()}
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas de pagos: {str(e)}")
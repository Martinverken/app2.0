from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from uuid import UUID
import uuid
from datetime import datetime, date
from decimal import Decimal

from database import get_supabase
from models.invoice import Invoice, InvoiceCreate, InvoiceUpdate

router = APIRouter()

@router.get("/", response_model=dict)
async def get_invoices(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    supplier_id: Optional[UUID] = None,
    estado: Optional[str] = None,
    moneda: Optional[str] = None,
    search: Optional[str] = None
):
    """Obtener lista de facturas con paginación y filtros"""
    try:
        supabase = get_supabase()
        
        # Query con JOIN para incluir nombre del proveedor
        query = supabase.table('invoices').select('''
            *,
            suppliers!invoices_supplier_id_fkey(nombre)
        ''')
        
        # Aplicar filtros
        if supplier_id:
            query = query.eq('supplier_id', str(supplier_id))
        
        if estado:
            query = query.eq('estado', estado)
            
        if moneda:
            query = query.eq('moneda', moneda)
        
        if search:
            query = query.ilike('numero_factura', f'%{search}%')
        
        # Contar total
        count_query = supabase.table('invoices').select('*', count='exact')
        if supplier_id:
            count_query = count_query.eq('supplier_id', str(supplier_id))
        if estado:
            count_query = count_query.eq('estado', estado)
        if moneda:
            count_query = count_query.eq('moneda', moneda)
        if search:
            count_query = count_query.ilike('numero_factura', f'%{search}%')
        
        total_result = count_query.execute()
        total = total_result.count
        
        # Aplicar paginación
        offset = (page - 1) * per_page
        query = query.range(offset, offset + per_page - 1).order('created_at', desc=True)
        
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
        raise HTTPException(status_code=500, detail=f"Error obteniendo facturas: {str(e)}")

@router.get("/{invoice_id}", response_model=dict)
async def get_invoice(invoice_id: UUID):
    """Obtener una factura específica"""
    try:
        supabase = get_supabase()
        
        result = supabase.table('invoices').select('''
            *,
            suppliers!invoices_supplier_id_fkey(nombre, contacto)
        ''').eq('id', str(invoice_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        return {
            "success": True,
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo factura: {str(e)}")

@router.post("/", response_model=dict)
async def create_invoice(invoice_data: InvoiceCreate):
    """Crear nueva factura (nueva lógica: solo requiere proveedor)"""
    try:
        supabase = get_supabase()
        
        # Verificar que el proveedor existe
        supplier_result = supabase.table('suppliers').select('id, nombre, activo').eq('id', str(invoice_data.supplier_id)).execute()
        if not supplier_result.data:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        supplier = supplier_result.data[0]
        if not supplier['activo']:
            raise HTTPException(status_code=400, detail="No se pueden crear facturas para proveedores inactivos")
        
        # Verificar que no existe otra factura con el mismo número para el mismo proveedor
        existing = supabase.table('invoices').select('id').eq('numero_factura', invoice_data.numero_factura).eq('supplier_id', str(invoice_data.supplier_id)).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Ya existe una factura con ese número para este proveedor")
        
        # Preparar datos
        invoice_dict = invoice_data.model_dump()
        invoice_dict['id'] = str(uuid.uuid4())
        invoice_dict['supplier_id'] = str(invoice_data.supplier_id)
        invoice_dict['monto_total'] = float(invoice_data.monto_total)
        
        # Convertir fecha a string si está presente
        if invoice_dict.get('fecha_emision'):
            invoice_dict['fecha_emision'] = invoice_dict['fecha_emision'].isoformat()
        else:
            invoice_dict['fecha_emision'] = date.today().isoformat()
        
        # Inicializar saldo pendiente igual al monto total
        invoice_dict['saldo_pendiente'] = invoice_dict['monto_total']
        
        invoice_dict['created_at'] = datetime.utcnow().isoformat()
        invoice_dict['updated_at'] = datetime.utcnow().isoformat()
        
        # Insertar factura
        result = supabase.table('invoices').insert(invoice_dict).execute()
        invoice = result.data[0]
        
        # Crear vencimiento por defecto (factura completa a 30 días)
        due_id = str(uuid.uuid4())
        due_data = {
            'id': due_id,
            'invoice_id': invoice['id'],
            'monto_vencimiento': invoice_dict['monto_total'],
            'fecha_vencimiento': (date.today().replace(day=min(date.today().day + 30, 28))).isoformat(),
            'estado': 'pendiente',
            'created_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('invoice_due').insert(due_data).execute()
        
        return {
            "success": True,
            "message": f"Factura creada exitosamente para {supplier['nombre']}",
            "data": invoice
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando factura: {str(e)}")

@router.put("/{invoice_id}", response_model=dict)
async def update_invoice(invoice_id: UUID, invoice_data: InvoiceUpdate):
    """Actualizar factura existente"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        existing = supabase.table('invoices').select('*').eq('id', str(invoice_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        current_invoice = existing.data[0]
        
        # Preparar datos (solo campos no nulos)
        update_data = {k: v for k, v in invoice_data.model_dump().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No hay datos para actualizar")
        
        # Verificar número de factura duplicado si se está actualizando
        if 'numero_factura' in update_data:
            existing_number = supabase.table('invoices').select('id').eq('numero_factura', update_data['numero_factura']).eq('supplier_id', current_invoice['supplier_id']).neq('id', str(invoice_id)).execute()
            if existing_number.data:
                raise HTTPException(status_code=400, detail="Ya existe otra factura con ese número para este proveedor")
        
        # Convertir tipos especiales
        if 'supplier_id' in update_data:
            update_data['supplier_id'] = str(update_data['supplier_id'])
        
        if 'monto_total' in update_data:
            nuevo_monto = float(update_data['monto_total'])
            monto_actual = float(current_invoice['monto_total'])
            saldo_actual = float(current_invoice.get('saldo_pendiente', 0))
            
            # Recalcular saldo pendiente
            diferencia = nuevo_monto - monto_actual
            nuevo_saldo = saldo_actual + diferencia
            update_data['saldo_pendiente'] = max(0, nuevo_saldo)
            update_data['monto_total'] = nuevo_monto
        
        if 'fecha_emision' in update_data and update_data['fecha_emision']:
            update_data['fecha_emision'] = update_data['fecha_emision'].isoformat()
        
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Actualizar
        result = supabase.table('invoices').update(update_data).eq('id', str(invoice_id)).execute()
        
        return {
            "success": True,
            "message": "Factura actualizada exitosamente",
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando factura: {str(e)}")

@router.delete("/{invoice_id}", response_model=dict)
async def delete_invoice(invoice_id: UUID):
    """Eliminar factura"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        existing = supabase.table('invoices').select('id, numero_factura').eq('id', str(invoice_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        # Verificar si tiene pagos o anticipos aplicados
        payments_count = supabase.table('invoice_payment').select('id', count='exact').eq('invoice_id', str(invoice_id)).execute().count
        advances_count = supabase.table('advance_allocation').select('id', count='exact').eq('invoice_id', str(invoice_id)).execute().count
        
        if payments_count > 0 or advances_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"No se puede eliminar: tiene {payments_count} pagos y {advances_count} anticipos aplicados"
            )
        
        # Eliminar vencimientos relacionados
        supabase.table('invoice_due').delete().eq('invoice_id', str(invoice_id)).execute()
        
        # Eliminar relaciones con órdenes
        supabase.table('invoice_po').delete().eq('invoice_id', str(invoice_id)).execute()
        
        # Eliminar relaciones con embarques
        supabase.table('shipment_invoice').delete().eq('invoice_id', str(invoice_id)).execute()
        
        # Eliminar factura
        supabase.table('invoices').delete().eq('id', str(invoice_id)).execute()
        
        return {
            "success": True,
            "message": f"Factura {existing.data[0]['numero_factura']} eliminada exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando factura: {str(e)}")

@router.post("/{invoice_id}/link-oc", response_model=dict)
async def link_invoice_to_po(invoice_id: UUID, po_id: UUID):
    """Vincular factura a una orden de compra"""
    try:
        supabase = get_supabase()
        
        # Verificar que la factura existe
        invoice_result = supabase.table('invoices').select('id, supplier_id, numero_factura').eq('id', str(invoice_id)).execute()
        if not invoice_result.data:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        invoice = invoice_result.data[0]
        
        # Verificar que la orden existe y pertenece al mismo proveedor
        po_result = supabase.table('purchase_orders').select('id, supplier_id, numero_orden').eq('id', str(po_id)).execute()
        if not po_result.data:
            raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
        
        po = po_result.data[0]
        
        if invoice['supplier_id'] != po['supplier_id']:
            raise HTTPException(status_code=400, detail="La factura y la orden deben pertenecer al mismo proveedor")
        
        # Verificar que no esté ya vinculada
        existing_link = supabase.table('invoice_po').select('id').eq('invoice_id', str(invoice_id)).eq('po_id', str(po_id)).execute()
        if existing_link.data:
            raise HTTPException(status_code=400, detail="La factura ya está vinculada a esta orden")
        
        # Crear vinculación
        link_data = {
            'id': str(uuid.uuid4()),
            'invoice_id': str(invoice_id),
            'po_id': str(po_id),
            'created_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('invoice_po').insert(link_data).execute()
        
        return {
            "success": True,
            "message": f"Factura {invoice['numero_factura']} vinculada exitosamente a orden {po['numero_orden']}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error vinculando factura a orden: {str(e)}")

@router.post("/{invoice_id}/aplicar-anticipo", response_model=dict)
async def apply_advance_to_invoice(
    invoice_id: UUID, 
    anticipo_id: UUID,
    monto_aplicar: Decimal,
    due_id: Optional[UUID] = None
):
    """Aplicar anticipo a una factura (opcionalmente a un vencimiento específico)"""
    try:
        supabase = get_supabase()
        
        # Verificar que la factura existe
        invoice_result = supabase.table('invoices').select('*').eq('id', str(invoice_id)).execute()
        if not invoice_result.data:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        invoice = invoice_result.data[0]
        
        # Verificar que el anticipo existe y está disponible
        advance_result = supabase.table('advance_payments').select('*').eq('id', str(anticipo_id)).execute()
        if not advance_result.data:
            raise HTTPException(status_code=404, detail="Anticipo no encontrado")
        
        advance = advance_result.data[0]
        
        if advance['estado'] != 'disponible':
            raise HTTPException(status_code=400, detail="El anticipo no está disponible")
        
        # Verificar monto disponible del anticipo
        applied_amount = supabase.table('advance_allocation').select('monto_aplicado').eq('anticipo_id', str(anticipo_id)).execute()
        total_applied = sum(float(item['monto_aplicado']) for item in applied_amount.data)
        available_amount = float(advance['monto']) - total_applied
        
        if float(monto_aplicar) > available_amount:
            raise HTTPException(status_code=400, detail=f"Monto a aplicar ({monto_aplicar}) excede el disponible ({available_amount})")
        
        # Verificar saldo pendiente de la factura
        saldo_pendiente = float(invoice.get('saldo_pendiente', 0))
        if float(monto_aplicar) > saldo_pendiente:
            raise HTTPException(status_code=400, detail=f"Monto a aplicar ({monto_aplicar}) excede el saldo pendiente ({saldo_pendiente})")
        
        # Si se especifica vencimiento, verificarlo
        if due_id:
            due_result = supabase.table('invoice_due').select('*').eq('id', str(due_id)).eq('invoice_id', str(invoice_id)).execute()
            if not due_result.data:
                raise HTTPException(status_code=404, detail="Vencimiento no encontrado")
        
        # Crear la aplicación del anticipo
        allocation_data = {
            'id': str(uuid.uuid4()),
            'anticipo_id': str(anticipo_id),
            'invoice_id': str(invoice_id),
            'monto_aplicado': float(monto_aplicar),
            'fecha': datetime.utcnow().isoformat(),
            'created_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('advance_allocation').insert(allocation_data).execute()
        
        # Si hay vencimiento específico, crear registro en invoice_due_payment
        if due_id:
            due_payment_data = {
                'id': str(uuid.uuid4()),
                'due_id': str(due_id),
                'source': 'anticipo',
                'source_id': str(anticipo_id),
                'monto_aplicado': float(monto_aplicar),
                'fecha': datetime.utcnow().isoformat(),
                'created_at': datetime.utcnow().isoformat()
            }
            supabase.table('invoice_due_payment').insert(due_payment_data).execute()
        
        # Actualizar saldo pendiente de la factura
        nuevo_saldo = saldo_pendiente - float(monto_aplicar)
        nuevo_estado = 'pagada_completa' if nuevo_saldo <= 0 else 'pagada_parcial'
        
        supabase.table('invoices').update({
            'saldo_pendiente': max(0, nuevo_saldo),
            'estado': nuevo_estado,
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', str(invoice_id)).execute()
        
        # Verificar si el anticipo se agotó
        new_total_applied = total_applied + float(monto_aplicar)
        if new_total_applied >= float(advance['monto']):
            supabase.table('advance_payments').update({
                'estado': 'aplicado'
            }).eq('id', str(anticipo_id)).execute()
        
        return {
            "success": True,
            "message": f"Anticipo aplicado exitosamente. Nuevo saldo: ${nuevo_saldo:.2f}",
            "data": {
                "monto_aplicado": float(monto_aplicar),
                "nuevo_saldo_factura": max(0, nuevo_saldo),
                "nuevo_estado_factura": nuevo_estado
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error aplicando anticipo: {str(e)}")

@router.get("/{invoice_id}/vencimientos", response_model=dict)
async def get_invoice_dues(invoice_id: UUID):
    """Obtener vencimientos de una factura"""
    try:
        supabase = get_supabase()
        
        # Verificar que la factura existe
        invoice_result = supabase.table('invoices').select('*').eq('id', str(invoice_id)).execute()
        if not invoice_result.data:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        # Obtener vencimientos
        dues_result = supabase.table('invoice_due').select('*').eq('invoice_id', str(invoice_id)).order('fecha_vencimiento').execute()
        
        # Para cada vencimiento, obtener los pagos aplicados
        for due in dues_result.data:
            payments_result = supabase.table('invoice_due_payment').select('*').eq('due_id', due['id']).execute()
            due['pagos_aplicados'] = payments_result.data
            due['monto_pagado'] = sum(float(p['monto_aplicado']) for p in payments_result.data)
            due['saldo_pendiente'] = float(due['monto_vencimiento']) - due['monto_pagado']
        
        return {
            "success": True,
            "data": dues_result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo vencimientos: {str(e)}")

@router.get("/stats/resumen", response_model=dict)
async def get_invoices_stats():
    """Estadísticas generales de facturas"""
    try:
        supabase = get_supabase()
        
        # Obtener todas las facturas
        invoices_result = supabase.table('invoices').select('monto_total, saldo_pendiente, estado, moneda').execute()
        
        # Calcular estadísticas
        total_facturas = len(invoices_result.data)
        
        # Por estado
        stats_por_estado = {}
        for invoice in invoices_result.data:
            estado = invoice.get('estado', 'pendiente')
            stats_por_estado[estado] = stats_por_estado.get(estado, 0) + 1
        
        # Por moneda
        totales_por_moneda = {}
        saldos_por_moneda = {}
        for invoice in invoices_result.data:
            moneda = invoice.get('moneda', 'USD')
            monto_total = float(invoice.get('monto_total', 0))
            saldo_pendiente = float(invoice.get('saldo_pendiente', 0))
            
            totales_por_moneda[moneda] = totales_por_moneda.get(moneda, 0) + monto_total
            saldos_por_moneda[moneda] = saldos_por_moneda.get(moneda, 0) + saldo_pendiente
        
        return {
            "success": True,
            "data": {
                "total_facturas": total_facturas,
                "por_estado": stats_por_estado,
                "totales_por_moneda": {k: round(v, 2) for k, v in totales_por_moneda.items()},
                "saldos_pendientes_por_moneda": {k: round(v, 2) for k, v in saldos_por_moneda.items()}
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")
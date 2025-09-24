from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from uuid import UUID
import uuid
from datetime import datetime, date
from decimal import Decimal

from database import get_supabase
from models.advance import AdvancePayment, AdvancePaymentCreate

router = APIRouter()

@router.get("/", response_model=dict)
async def get_advances(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    po_id: Optional[UUID] = None,
    estado: Optional[str] = None,
    moneda: Optional[str] = None
):
    """Obtener lista de anticipos con paginación y filtros"""
    try:
        supabase = get_supabase()
        
        # Query con JOIN para incluir información de la orden y proveedor
        query = supabase.table('advance_payments').select('''
            *,
            purchase_orders!advance_payments_po_id_fkey(
                numero_orden,
                suppliers!purchase_orders_supplier_id_fkey(nombre)
            )
        ''')
        
        # Aplicar filtros
        if po_id:
            query = query.eq('po_id', str(po_id))
        
        if estado:
            query = query.eq('estado', estado)
            
        if moneda:
            query = query.eq('moneda', moneda)
        
        # Contar total
        count_query = supabase.table('advance_payments').select('*', count='exact')
        if po_id:
            count_query = count_query.eq('po_id', str(po_id))
        if estado:
            count_query = count_query.eq('estado', estado)
        if moneda:
            count_query = count_query.eq('moneda', moneda)
        
        total_result = count_query.execute()
        total = total_result.count
        
        # Aplicar paginación
        offset = (page - 1) * per_page
        query = query.range(offset, offset + per_page - 1).order('fecha_pago', desc=True)
        
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
        raise HTTPException(status_code=500, detail=f"Error obteniendo anticipos: {str(e)}")

@router.get("/{advance_id}", response_model=dict)
async def get_advance(advance_id: UUID):
    """Obtener un anticipo específico"""
    try:
        supabase = get_supabase()
        
        result = supabase.table('advance_payments').select('''
            *,
            purchase_orders!advance_payments_po_id_fkey(
                numero_orden,
                total_oc,
                suppliers!purchase_orders_supplier_id_fkey(nombre, contacto)
            )
        ''').eq('id', str(advance_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Anticipo no encontrado")
        
        advance = result.data[0]
        
        # Obtener aplicaciones del anticipo
        allocations_result = supabase.table('advance_allocation').select('''
            *,
            invoices!advance_allocation_invoice_id_fkey(numero_factura, monto_total)
        ''').eq('anticipo_id', str(advance_id)).execute()
        
        advance['aplicaciones'] = allocations_result.data
        advance['monto_aplicado'] = sum(float(app['monto_aplicado']) for app in allocations_result.data)
        advance['saldo_disponible'] = float(advance['monto']) - advance['monto_aplicado']
        
        return {
            "success": True,
            "data": advance
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo anticipo: {str(e)}")

@router.post("/", response_model=dict)
async def create_advance(advance_data: AdvancePaymentCreate):
    """Crear nuevo anticipo"""
    try:
        supabase = get_supabase()
        
        # Verificar que la orden de compra existe
        po_result = supabase.table('purchase_orders').select('''
            id, numero_orden, supplier_id, total_oc,
            suppliers!purchase_orders_supplier_id_fkey(nombre, activo)
        ''').eq('id', str(advance_data.po_id)).execute()
        
        if not po_result.data:
            raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
        
        po = po_result.data[0]
        supplier = po['suppliers']
        
        if not supplier['activo']:
            raise HTTPException(status_code=400, detail="No se pueden crear anticipos para proveedores inactivos")
        
        # Verificar que el monto del anticipo no exceda el total de la orden
        existing_advances = supabase.table('advance_payments').select('monto').eq('po_id', str(advance_data.po_id)).execute()
        total_advances = sum(float(adv['monto']) for adv in existing_advances.data)
        nuevo_total = total_advances + float(advance_data.monto)
        
        if nuevo_total > float(po['total_oc']):
            raise HTTPException(
                status_code=400, 
                detail=f"Total de anticipos ({nuevo_total}) excedería el total de la orden ({po['total_oc']})"
            )
        
        # Preparar datos
        advance_dict = advance_data.model_dump()
        advance_dict['id'] = str(uuid.uuid4())
        advance_dict['po_id'] = str(advance_data.po_id)
        advance_dict['monto'] = float(advance_data.monto)
        advance_dict['fecha_pago'] = advance_dict['fecha_pago'].isoformat()
        advance_dict['created_at'] = datetime.utcnow().isoformat()
        
        # Insertar
        result = supabase.table('advance_payments').insert(advance_dict).execute()
        
        return {
            "success": True,
            "message": f"Anticipo creado exitosamente para orden {po['numero_orden']} ({supplier['nombre']})",
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando anticipo: {str(e)}")

@router.put("/{advance_id}", response_model=dict)
async def update_advance(advance_id: UUID, monto: Optional[Decimal] = None, fecha_pago: Optional[date] = None, 
                        metodo_pago: Optional[str] = None, usuario_pago: Optional[str] = None, notas: Optional[str] = None):
    """Actualizar anticipo existente"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        existing = supabase.table('advance_payments').select('*').eq('id', str(advance_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Anticipo no encontrado")
        
        advance = existing.data[0]
        
        # Verificar que no esté aplicado
        if advance['estado'] == 'aplicado':
            raise HTTPException(status_code=400, detail="No se puede modificar un anticipo que ya fue aplicado")
        
        # Preparar datos de actualización
        update_data = {}
        
        if monto is not None:
            # Verificar que el nuevo monto no exceda límites
            po_result = supabase.table('purchase_orders').select('total_oc').eq('id', advance['po_id']).execute()
            if po_result.data:
                other_advances = supabase.table('advance_payments').select('monto').eq('po_id', advance['po_id']).neq('id', str(advance_id)).execute()
                total_other_advances = sum(float(adv['monto']) for adv in other_advances.data)
                
                if total_other_advances + float(monto) > float(po_result.data[0]['total_oc']):
                    raise HTTPException(status_code=400, detail="El nuevo monto excedería el total de la orden")
            
            update_data['monto'] = float(monto)
        
        if fecha_pago is not None:
            update_data['fecha_pago'] = fecha_pago.isoformat()
        
        if metodo_pago is not None:
            update_data['metodo_pago'] = metodo_pago
        
        if usuario_pago is not None:
            update_data['usuario_pago'] = usuario_pago
        
        if notas is not None:
            update_data['notas'] = notas
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No hay datos para actualizar")
        
        # Actualizar
        result = supabase.table('advance_payments').update(update_data).eq('id', str(advance_id)).execute()
        
        return {
            "success": True,
            "message": "Anticipo actualizado exitosamente",
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando anticipo: {str(e)}")

@router.delete("/{advance_id}", response_model=dict)
async def delete_advance(advance_id: UUID):
    """Eliminar anticipo"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        existing = supabase.table('advance_payments').select('*').eq('id', str(advance_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Anticipo no encontrado")
        
        advance = existing.data[0]
        
        # Verificar si tiene aplicaciones
        allocations = supabase.table('advance_allocation').select('id').eq('anticipo_id', str(advance_id)).execute()
        
        if allocations.data:
            raise HTTPException(
                status_code=400, 
                detail=f"No se puede eliminar: el anticipo tiene {len(allocations.data)} aplicaciones a facturas"
            )
        
        # Eliminar
        supabase.table('advance_payments').delete().eq('id', str(advance_id)).execute()
        
        return {
            "success": True,
            "message": "Anticipo eliminado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando anticipo: {str(e)}")

@router.post("/{advance_id}/devolver", response_model=dict)
async def return_advance(advance_id: UUID, motivo: Optional[str] = None):
    """Marcar anticipo como devuelto"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        existing = supabase.table('advance_payments').select('*').eq('id', str(advance_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Anticipo no encontrado")
        
        advance = existing.data[0]
        
        # Verificar que esté disponible
        if advance['estado'] != 'disponible':
            raise HTTPException(status_code=400, detail="Solo se pueden devolver anticipos disponibles")
        
        # Verificar que no tenga aplicaciones
        allocations = supabase.table('advance_allocation').select('id').eq('anticipo_id', str(advance_id)).execute()
        if allocations.data:
            raise HTTPException(status_code=400, detail="No se puede devolver un anticipo que tiene aplicaciones")
        
        # Actualizar estado
        update_data = {
            'estado': 'devuelto'
        }
        
        if motivo:
            current_notes = advance.get('notas', '') or ''
            update_data['notas'] = f"{current_notes}\n[DEVUELTO] {motivo}".strip()
        
        result = supabase.table('advance_payments').update(update_data).eq('id', str(advance_id)).execute()
        
        return {
            "success": True,
            "message": "Anticipo marcado como devuelto",
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error devolviendo anticipo: {str(e)}")

@router.get("/por-orden/{po_id}", response_model=dict)
async def get_advances_by_po(po_id: UUID):
    """Obtener todos los anticipos de una orden específica"""
    try:
        supabase = get_supabase()
        
        # Verificar que la orden existe
        po_result = supabase.table('purchase_orders').select('*').eq('id', str(po_id)).execute()
        if not po_result.data:
            raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
        
        # Obtener anticipos
        advances_result = supabase.table('advance_payments').select('*').eq('po_id', str(po_id)).order('fecha_pago', desc=True).execute()
        
        # Para cada anticipo, calcular monto aplicado y disponible
        for advance in advances_result.data:
            allocations = supabase.table('advance_allocation').select('monto_aplicado').eq('anticipo_id', advance['id']).execute()
            advance['monto_aplicado'] = sum(float(app['monto_aplicado']) for app in allocations.data)
            advance['saldo_disponible'] = float(advance['monto']) - advance['monto_aplicado']
        
        # Calcular totales
        total_anticipos = sum(float(adv['monto']) for adv in advances_result.data)
        total_aplicado = sum(adv['monto_aplicado'] for adv in advances_result.data)
        total_disponible = sum(adv['saldo_disponible'] for adv in advances_result.data)
        
        return {
            "success": True,
            "data": {
                "orden": po_result.data[0],
                "anticipos": advances_result.data,
                "resumen": {
                    "total_anticipos": round(total_anticipos, 2),
                    "total_aplicado": round(total_aplicado, 2),
                    "total_disponible": round(total_disponible, 2)
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo anticipos de la orden: {str(e)}")

@router.get("/disponibles/{po_id}", response_model=dict)
async def get_available_advances(po_id: UUID):
    """Obtener anticipos disponibles para aplicar de una orden específica"""
    try:
        supabase = get_supabase()
        
        # Obtener anticipos disponibles
        advances_result = supabase.table('advance_payments').select('*').eq('po_id', str(po_id)).eq('estado', 'disponible').execute()
        
        # Filtrar solo los que tienen saldo disponible
        available_advances = []
        for advance in advances_result.data:
            allocations = supabase.table('advance_allocation').select('monto_aplicado').eq('anticipo_id', advance['id']).execute()
            monto_aplicado = sum(float(app['monto_aplicado']) for app in allocations.data)
            saldo_disponible = float(advance['monto']) - monto_aplicado
            
            if saldo_disponible > 0:
                advance['monto_aplicado'] = monto_aplicado
                advance['saldo_disponible'] = round(saldo_disponible, 2)
                available_advances.append(advance)
        
        return {
            "success": True,
            "data": available_advances,
            "total_disponible": round(sum(adv['saldo_disponible'] for adv in available_advances), 2)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo anticipos disponibles: {str(e)}")

@router.get("/stats/resumen", response_model=dict)
async def get_advances_stats():
    """Estadísticas generales de anticipos"""
    try:
        supabase = get_supabase()
        
        # Obtener todos los anticipos
        advances_result = supabase.table('advance_payments').select('monto, estado, moneda').execute()
        
        # Calcular estadísticas
        total_anticipos = len(advances_result.data)
        
        # Por estado
        stats_por_estado = {}
        for advance in advances_result.data:
            estado = advance.get('estado', 'disponible')
            stats_por_estado[estado] = stats_por_estado.get(estado, 0) + 1
        
        # Por moneda
        totales_por_moneda = {}
        for advance in advances_result.data:
            moneda = advance.get('moneda', 'USD')
            monto = float(advance.get('monto', 0))
            totales_por_moneda[moneda] = totales_por_moneda.get(moneda, 0) + monto
        
        # Calcular montos aplicados
        allocations_result = supabase.table('advance_allocation').select('monto_aplicado').execute()
        total_aplicado = sum(float(app['monto_aplicado']) for app in allocations_result.data)
        
        total_pagado = sum(float(adv['monto']) for adv in advances_result.data)
        total_disponible = total_pagado - total_aplicado
        
        return {
            "success": True,
            "data": {
                "total_anticipos": total_anticipos,
                "por_estado": stats_por_estado,
                "totales_por_moneda": {k: round(v, 2) for k, v in totales_por_moneda.items()},
                "resumen_financiero": {
                    "total_pagado": round(total_pagado, 2),
                    "total_aplicado": round(total_aplicado, 2),
                    "total_disponible": round(total_disponible, 2)
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")
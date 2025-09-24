from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from uuid import UUID
import uuid
from datetime import datetime, date
from decimal import Decimal

from database import get_supabase
from models.purchase_order import PurchaseOrder, PurchaseOrderCreate, PurchaseOrderUpdate

router = APIRouter()

@router.get("/", response_model=dict)
async def get_purchase_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    supplier_id: Optional[UUID] = None,
    estado: Optional[str] = None,
    moneda: Optional[str] = None,
    search: Optional[str] = None
):
    """Obtener lista de órdenes de compra con paginación y filtros"""
    try:
        supabase = get_supabase()
        
        # Query con JOIN para incluir nombre del proveedor
        query = supabase.table('purchase_orders').select('''
            *,
            suppliers!purchase_orders_supplier_id_fkey(nombre)
        ''')
        
        # Aplicar filtros
        if supplier_id:
            query = query.eq('supplier_id', str(supplier_id))
        
        if estado:
            query = query.eq('estado', estado)
            
        if moneda:
            query = query.eq('moneda', moneda)
        
        if search:
            query = query.ilike('numero_orden', f'%{search}%')
        
        # Contar total
        count_query = supabase.table('purchase_orders').select('*', count='exact')
        if supplier_id:
            count_query = count_query.eq('supplier_id', str(supplier_id))
        if estado:
            count_query = count_query.eq('estado', estado)
        if moneda:
            count_query = count_query.eq('moneda', moneda)
        if search:
            count_query = count_query.ilike('numero_orden', f'%{search}%')
        
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
        raise HTTPException(status_code=500, detail=f"Error obteniendo órdenes: {str(e)}")

@router.get("/{po_id}", response_model=dict)
async def get_purchase_order(po_id: UUID):
    """Obtener una orden de compra específica"""
    try:
        supabase = get_supabase()
        
        result = supabase.table('purchase_orders').select('''
            *,
            suppliers!purchase_orders_supplier_id_fkey(nombre, contacto)
        ''').eq('id', str(po_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
        
        return {
            "success": True,
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo orden: {str(e)}")

@router.post("/", response_model=dict)
async def create_purchase_order(po_data: PurchaseOrderCreate):
    """Crear nueva orden de compra"""
    try:
        supabase = get_supabase()
        
        # Verificar que el proveedor existe
        supplier_result = supabase.table('suppliers').select('id, nombre, activo').eq('id', str(po_data.supplier_id)).execute()
        if not supplier_result.data:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        supplier = supplier_result.data[0]
        if not supplier['activo']:
            raise HTTPException(status_code=400, detail="No se pueden crear órdenes para proveedores inactivos")
        
        # Verificar que no existe otra orden con el mismo número
        existing = supabase.table('purchase_orders').select('id').eq('numero_orden', po_data.numero_orden).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Ya existe una orden con ese número")
        
        # Preparar datos
        po_dict = po_data.model_dump()
        po_dict['id'] = str(uuid.uuid4())
        po_dict['supplier_id'] = str(po_data.supplier_id)
        po_dict['total_oc'] = float(po_data.total_oc)
        
        # Convertir fecha a string si está presente
        if po_dict.get('fecha'):
            po_dict['fecha'] = po_dict['fecha'].isoformat()
        else:
            po_dict['fecha'] = date.today().isoformat()
        
        po_dict['created_at'] = datetime.utcnow().isoformat()
        po_dict['updated_at'] = datetime.utcnow().isoformat()
        
        # Insertar
        result = supabase.table('purchase_orders').insert(po_dict).execute()
        
        return {
            "success": True,
            "message": f"Orden de compra creada exitosamente para {supplier['nombre']}",
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando orden: {str(e)}")

@router.put("/{po_id}", response_model=dict)
async def update_purchase_order(po_id: UUID, po_data: PurchaseOrderUpdate):
    """Actualizar orden de compra existente"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        existing = supabase.table('purchase_orders').select('*').eq('id', str(po_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
        
        # Preparar datos (solo campos no nulos)
        update_data = {k: v for k, v in po_data.model_dump().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No hay datos para actualizar")
        
        # Verificar número de orden duplicado si se está actualizando
        if 'numero_orden' in update_data:
            existing_number = supabase.table('purchase_orders').select('id').eq('numero_orden', update_data['numero_orden']).neq('id', str(po_id)).execute()
            if existing_number.data:
                raise HTTPException(status_code=400, detail="Ya existe otra orden con ese número")
        
        # Convertir tipos especiales
        if 'supplier_id' in update_data:
            update_data['supplier_id'] = str(update_data['supplier_id'])
        
        if 'total_oc' in update_data:
            update_data['total_oc'] = float(update_data['total_oc'])
        
        if 'fecha' in update_data and update_data['fecha']:
            update_data['fecha'] = update_data['fecha'].isoformat()
        
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Actualizar
        result = supabase.table('purchase_orders').update(update_data).eq('id', str(po_id)).execute()
        
        return {
            "success": True,
            "message": "Orden de compra actualizada exitosamente",
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando orden: {str(e)}")

@router.delete("/{po_id}", response_model=dict)
async def delete_purchase_order(po_id: UUID):
    """Eliminar orden de compra"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        existing = supabase.table('purchase_orders').select('id, numero_orden').eq('id', str(po_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
        
        # Verificar si tiene anticipos o facturas asociadas
        advances_count = supabase.table('advance_payments').select('id', count='exact').eq('po_id', str(po_id)).execute().count
        
        # Verificar facturas vinculadas via invoice_po
        invoice_po_count = supabase.table('invoice_po').select('id', count='exact').eq('po_id', str(po_id)).execute().count
        
        if advances_count > 0 or invoice_po_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"No se puede eliminar: tiene {advances_count} anticipos y {invoice_po_count} facturas asociadas"
            )
        
        # Eliminar
        supabase.table('purchase_orders').delete().eq('id', str(po_id)).execute()
        
        return {
            "success": True,
            "message": f"Orden {existing.data[0]['numero_orden']} eliminada exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando orden: {str(e)}")

@router.get("/{po_id}/anticipos-dashboard", response_model=dict)
async def get_anticipos_dashboard(po_id: UUID):
    """Dashboard de anticipos para una orden de compra"""
    try:
        supabase = get_supabase()
        
        # Verificar que la orden existe
        po_result = supabase.table('purchase_orders').select('*').eq('id', str(po_id)).execute()
        if not po_result.data:
            raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
        
        po = po_result.data[0]
        
        # Obtener anticipos
        advances_result = supabase.table('advance_payments').select('*').eq('po_id', str(po_id)).order('fecha_pago', desc=True).execute()
        
        # Calcular estadísticas
        total_anticipos = sum(float(adv.get('monto', 0)) for adv in advances_result.data)
        anticipos_disponibles = sum(float(adv.get('monto', 0)) for adv in advances_result.data if adv.get('estado') == 'disponible')
        anticipos_aplicados = sum(float(adv.get('monto', 0)) for adv in advances_result.data if adv.get('estado') == 'aplicado')
        
        # Obtener facturas vinculadas
        invoice_po_result = supabase.table('invoice_po').select('''
            invoices!invoice_po_invoice_id_fkey(numero_factura, monto_total, saldo_pendiente, estado)
        ''').eq('po_id', str(po_id)).execute()
        
        facturas_vinculadas = [item['invoices'] for item in invoice_po_result.data]
        total_facturas = sum(float(inv.get('monto_total', 0)) for inv in facturas_vinculadas)
        saldo_pendiente_facturas = sum(float(inv.get('saldo_pendiente', 0)) for inv in facturas_vinculadas)
        
        # Calcular balance
        balance = float(po['total_oc']) - total_facturas
        cobertura_anticipos = (anticipos_disponibles / saldo_pendiente_facturas * 100) if saldo_pendiente_facturas > 0 else 0
        
        return {
            "success": True,
            "data": {
                "orden": po,
                "anticipos": {
                    "lista": advances_result.data,
                    "total": round(total_anticipos, 2),
                    "disponibles": round(anticipos_disponibles, 2),
                    "aplicados": round(anticipos_aplicados, 2)
                },
                "facturas": {
                    "lista": facturas_vinculadas,
                    "total": round(total_facturas, 2),
                    "saldo_pendiente": round(saldo_pendiente_facturas, 2)
                },
                "balance": {
                    "oc_vs_facturas": round(balance, 2),
                    "cobertura_anticipos": round(cobertura_anticipos, 2)
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo dashboard de anticipos: {str(e)}")

@router.get("/stats/resumen", response_model=dict)
async def get_purchase_orders_stats():
    """Estadísticas generales de órdenes de compra"""
    try:
        supabase = get_supabase()
        
        # Obtener todas las órdenes
        pos_result = supabase.table('purchase_orders').select('total_oc, estado, moneda').execute()
        
        # Calcular estadísticas
        total_ordenes = len(pos_result.data)
        
        # Por estado
        stats_por_estado = {}
        for po in pos_result.data:
            estado = po.get('estado', 'pendiente')
            stats_por_estado[estado] = stats_por_estado.get(estado, 0) + 1
        
        # Por moneda
        totales_por_moneda = {}
        for po in pos_result.data:
            moneda = po.get('moneda', 'USD')
            total_oc = float(po.get('total_oc', 0))
            totales_por_moneda[moneda] = totales_por_moneda.get(moneda, 0) + total_oc
        
        return {
            "success": True,
            "data": {
                "total_ordenes": total_ordenes,
                "por_estado": stats_por_estado,
                "totales_por_moneda": {k: round(v, 2) for k, v in totales_por_moneda.items()}
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from uuid import UUID
import uuid
from datetime import datetime

from database import get_supabase
from models.supplier import Supplier, SupplierCreate, SupplierUpdate

router = APIRouter()

@router.get("/", response_model=dict)
async def get_suppliers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    activo: Optional[bool] = None,
    search: Optional[str] = None
):
    """Obtener lista de proveedores con paginación y filtros"""
    try:
        supabase = get_supabase()
        
        # Construir query base
        query = supabase.table('suppliers').select('*')
        
        # Aplicar filtros
        if activo is not None:
            query = query.eq('activo', activo)
        
        if search:
            query = query.ilike('nombre', f'%{search}%')
        
        # Contar total
        count_query = supabase.table('suppliers').select('*', count='exact')
        if activo is not None:
            count_query = count_query.eq('activo', activo)
        if search:
            count_query = count_query.ilike('nombre', f'%{search}%')
        
        total_result = count_query.execute()
        total = total_result.count
        
        # Aplicar paginación
        offset = (page - 1) * per_page
        query = query.range(offset, offset + per_page - 1).order('nombre')
        
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
        raise HTTPException(status_code=500, detail=f"Error obteniendo proveedores: {str(e)}")

@router.get("/{supplier_id}", response_model=dict)
async def get_supplier(supplier_id: UUID):
    """Obtener un proveedor específico"""
    try:
        supabase = get_supabase()
        
        result = supabase.table('suppliers').select('*').eq('id', str(supplier_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        return {
            "success": True,
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo proveedor: {str(e)}")

@router.post("/", response_model=dict)
async def create_supplier(supplier_data: SupplierCreate):
    """Crear nuevo proveedor"""
    try:
        supabase = get_supabase()
        
        # Verificar si ya existe un proveedor con el mismo nombre
        existing = supabase.table('suppliers').select('id').eq('nombre', supplier_data.nombre).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Ya existe un proveedor con ese nombre")
        
        # Preparar datos
        supplier_dict = supplier_data.model_dump()
        supplier_dict['id'] = str(uuid.uuid4())
        supplier_dict['created_at'] = datetime.utcnow().isoformat()
        supplier_dict['updated_at'] = datetime.utcnow().isoformat()
        
        # Insertar
        result = supabase.table('suppliers').insert(supplier_dict).execute()
        
        return {
            "success": True,
            "message": "Proveedor creado exitosamente",
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando proveedor: {str(e)}")

@router.put("/{supplier_id}", response_model=dict)
async def update_supplier(supplier_id: UUID, supplier_data: SupplierUpdate):
    """Actualizar proveedor existente"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        existing = supabase.table('suppliers').select('id').eq('id', str(supplier_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        # Preparar datos (solo campos no nulos)
        update_data = {k: v for k, v in supplier_data.model_dump().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No hay datos para actualizar")
        
        # Verificar nombre duplicado si se está actualizando
        if 'nombre' in update_data:
            existing_name = supabase.table('suppliers').select('id').eq('nombre', update_data['nombre']).neq('id', str(supplier_id)).execute()
            if existing_name.data:
                raise HTTPException(status_code=400, detail="Ya existe otro proveedor con ese nombre")
        
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Actualizar
        result = supabase.table('suppliers').update(update_data).eq('id', str(supplier_id)).execute()
        
        return {
            "success": True,
            "message": "Proveedor actualizado exitosamente",
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando proveedor: {str(e)}")

@router.delete("/{supplier_id}", response_model=dict)
async def delete_supplier(supplier_id: UUID):
    """Eliminar proveedor (soft delete - marcar como inactivo)"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        existing = supabase.table('suppliers').select('id, activo').eq('id', str(supplier_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        # Verificar si tiene órdenes o facturas asociadas
        pos_count = supabase.table('purchase_orders').select('id', count='exact').eq('supplier_id', str(supplier_id)).execute().count
        invoices_count = supabase.table('invoices').select('id', count='exact').eq('supplier_id', str(supplier_id)).execute().count
        
        if pos_count > 0 or invoices_count > 0:
            # Soft delete - marcar como inactivo
            result = supabase.table('suppliers').update({
                'activo': False,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', str(supplier_id)).execute()
            
            return {
                "success": True,
                "message": f"Proveedor marcado como inactivo (tiene {pos_count} órdenes y {invoices_count} facturas asociadas)",
                "data": result.data[0]
            }
        else:
            # Hard delete si no tiene relaciones
            supabase.table('suppliers').delete().eq('id', str(supplier_id)).execute()
            
            return {
                "success": True,
                "message": "Proveedor eliminado exitosamente"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando proveedor: {str(e)}")

@router.get("/{supplier_id}/dashboard", response_model=dict)
async def get_supplier_dashboard(supplier_id: UUID):
    """Dashboard de estadísticas del proveedor"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        supplier_result = supabase.table('suppliers').select('*').eq('id', str(supplier_id)).execute()
        if not supplier_result.data:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        supplier = supplier_result.data[0]
        
        # Estadísticas de órdenes
        pos_result = supabase.table('purchase_orders').select('total_oc, estado').eq('supplier_id', str(supplier_id)).execute()
        total_pos = len(pos_result.data)
        total_monto_pos = sum(float(po.get('total_oc', 0)) for po in pos_result.data)
        
        pos_por_estado = {}
        for po in pos_result.data:
            estado = po.get('estado', 'pendiente')
            pos_por_estado[estado] = pos_por_estado.get(estado, 0) + 1
        
        # Estadísticas de facturas
        invoices_result = supabase.table('invoices').select('monto_total, saldo_pendiente, estado').eq('supplier_id', str(supplier_id)).execute()
        total_facturas = len(invoices_result.data)
        total_monto_facturas = sum(float(inv.get('monto_total', 0)) for inv in invoices_result.data)
        total_saldo_pendiente = sum(float(inv.get('saldo_pendiente', 0)) for inv in invoices_result.data)
        
        facturas_por_estado = {}
        for inv in invoices_result.data:
            estado = inv.get('estado', 'pendiente')
            facturas_por_estado[estado] = facturas_por_estado.get(estado, 0) + 1
        
        # Estadísticas de anticipos
        advances_result = supabase.table('advance_payments').select('monto, estado').in_('po_id', 
            [po['id'] for po in pos_result.data] if pos_result.data else []).execute()
        total_anticipos = sum(float(adv.get('monto', 0)) for adv in advances_result.data)
        
        return {
            "success": True,
            "data": {
                "supplier": supplier,
                "purchase_orders": {
                    "total": total_pos,
                    "monto_total": round(total_monto_pos, 2),
                    "por_estado": pos_por_estado
                },
                "invoices": {
                    "total": total_facturas,
                    "monto_total": round(total_monto_facturas, 2),
                    "saldo_pendiente": round(total_saldo_pendiente, 2),
                    "por_estado": facturas_por_estado
                },
                "anticipos": {
                    "monto_total": round(total_anticipos, 2)
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo dashboard: {str(e)}")
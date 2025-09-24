from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from uuid import UUID
import uuid
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel

from database import get_supabase

router = APIRouter()

# Modelos específicos para embarques
class ShipmentCreate(BaseModel):
    codigo: str
    puerto_origen: Optional[str] = None
    puerto_destino: Optional[str] = None
    fecha_embarque: Optional[date] = None
    fecha_llegada_estimada: Optional[date] = None
    fecha_llegada_real: Optional[date] = None
    estado: str = "en_transito"  # en_transito, arribado, despachado
    naviera: Optional[str] = None
    numero_contenedor: Optional[str] = None
    notas: Optional[str] = None

class ShipmentUpdate(BaseModel):
    codigo: Optional[str] = None
    puerto_origen: Optional[str] = None
    puerto_destino: Optional[str] = None
    fecha_embarque: Optional[date] = None
    fecha_llegada_estimada: Optional[date] = None
    fecha_llegada_real: Optional[date] = None
    estado: Optional[str] = None
    naviera: Optional[str] = None
    numero_contenedor: Optional[str] = None
    notas: Optional[str] = None

class ShipmentSupplierLink(BaseModel):
    supplier_ids: List[UUID]

class ShipmentInvoiceLink(BaseModel):
    invoice_id: UUID
    monto_asignado: Optional[Decimal] = None

@router.get("/", response_model=dict)
async def get_shipments(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    estado: Optional[str] = None,
    search: Optional[str] = None
):
    """Obtener lista de embarques con paginación y filtros"""
    try:
        supabase = get_supabase()
        
        # Query base
        query = supabase.table('shipments').select('*')
        
        # Aplicar filtros
        if estado:
            query = query.eq('estado', estado)
        
        if search:
            query = query.or_(f'codigo.ilike.%{search}%,numero_contenedor.ilike.%{search}%')
        
        # Contar total
        count_query = supabase.table('shipments').select('*', count='exact')
        if estado:
            count_query = count_query.eq('estado', estado)
        if search:
            count_query = count_query.or_(f'codigo.ilike.%{search}%,numero_contenedor.ilike.%{search}%')
        
        total_result = count_query.execute()
        total = total_result.count
        
        # Aplicar paginación
        offset = (page - 1) * per_page
        query = query.range(offset, offset + per_page - 1).order('created_at', desc=True)
        
        result = query.execute()
        
        # Para cada embarque, obtener proveedores asociados
        for shipment in result.data:
            suppliers_result = supabase.table('shipment_supplier').select('''
                suppliers!shipment_supplier_supplier_id_fkey(id, nombre)
            ''').eq('shipment_id', shipment['id']).execute()
            
            shipment['suppliers'] = [item['suppliers'] for item in suppliers_result.data]
        
        return {
            "success": True,
            "data": result.data,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo embarques: {str(e)}")

@router.get("/{shipment_id}", response_model=dict)
async def get_shipment(shipment_id: UUID):
    """Obtener un embarque específico"""
    try:
        supabase = get_supabase()
        
        result = supabase.table('shipments').select('*').eq('id', str(shipment_id)).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Embarque no encontrado")
        
        shipment = result.data[0]
        
        # Obtener proveedores asociados
        suppliers_result = supabase.table('shipment_supplier').select('''
            suppliers!shipment_supplier_supplier_id_fkey(id, nombre, contacto)
        ''').eq('shipment_id', str(shipment_id)).execute()
        
        shipment['suppliers'] = [item['suppliers'] for item in suppliers_result.data]
        
        # Obtener facturas asociadas
        invoices_result = supabase.table('shipment_invoice').select('''
            monto_asignado,
            invoices!shipment_invoice_invoice_id_fkey(id, numero_factura, monto_total, estado)
        ''').eq('shipment_id', str(shipment_id)).execute()
        
        shipment['invoices'] = invoices_result.data
        
        return {
            "success": True,
            "data": shipment
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo embarque: {str(e)}")

@router.post("/", response_model=dict)
async def create_shipment(shipment_data: ShipmentCreate):
    """Crear nuevo embarque"""
    try:
        supabase = get_supabase()
        
        # Verificar que no existe otro embarque con el mismo código
        existing = supabase.table('shipments').select('id').eq('codigo', shipment_data.codigo).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Ya existe un embarque con ese código")
        
        # Preparar datos
        shipment_dict = shipment_data.model_dump()
        shipment_dict['id'] = str(uuid.uuid4())
        
        # Convertir fechas a string
        for date_field in ['fecha_embarque', 'fecha_llegada_estimada', 'fecha_llegada_real']:
            if shipment_dict.get(date_field):
                shipment_dict[date_field] = shipment_dict[date_field].isoformat()
        
        shipment_dict['created_at'] = datetime.utcnow().isoformat()
        shipment_dict['updated_at'] = datetime.utcnow().isoformat()
        
        # Insertar
        result = supabase.table('shipments').insert(shipment_dict).execute()
        
        return {
            "success": True,
            "message": f"Embarque {shipment_data.codigo} creado exitosamente",
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando embarque: {str(e)}")

@router.put("/{shipment_id}", response_model=dict)
async def update_shipment(shipment_id: UUID, shipment_data: ShipmentUpdate):
    """Actualizar embarque existente"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        existing = supabase.table('shipments').select('*').eq('id', str(shipment_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Embarque no encontrado")
        
        # Preparar datos (solo campos no nulos)
        update_data = {k: v for k, v in shipment_data.model_dump().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No hay datos para actualizar")
        
        # Verificar código duplicado si se está actualizando
        if 'codigo' in update_data:
            existing_code = supabase.table('shipments').select('id').eq('codigo', update_data['codigo']).neq('id', str(shipment_id)).execute()
            if existing_code.data:
                raise HTTPException(status_code=400, detail="Ya existe otro embarque con ese código")
        
        # Convertir fechas a string
        for date_field in ['fecha_embarque', 'fecha_llegada_estimada', 'fecha_llegada_real']:
            if update_data.get(date_field):
                update_data[date_field] = update_data[date_field].isoformat()
        
        update_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Actualizar
        result = supabase.table('shipments').update(update_data).eq('id', str(shipment_id)).execute()
        
        return {
            "success": True,
            "message": "Embarque actualizado exitosamente",
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando embarque: {str(e)}")

@router.delete("/{shipment_id}", response_model=dict)
async def delete_shipment(shipment_id: UUID):
    """Eliminar embarque"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe
        existing = supabase.table('shipments').select('id, codigo').eq('id', str(shipment_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Embarque no encontrado")
        
        # Verificar si tiene facturas asociadas
        invoices_count = supabase.table('shipment_invoice').select('id', count='exact').eq('shipment_id', str(shipment_id)).execute().count
        
        if invoices_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"No se puede eliminar: tiene {invoices_count} facturas asociadas"
            )
        
        # Eliminar relaciones con proveedores
        supabase.table('shipment_supplier').delete().eq('shipment_id', str(shipment_id)).execute()
        
        # Eliminar embarque
        supabase.table('shipments').delete().eq('id', str(shipment_id)).execute()
        
        return {
            "success": True,
            "message": f"Embarque {existing.data[0]['codigo']} eliminado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando embarque: {str(e)}")

@router.post("/{shipment_id}/proveedores", response_model=dict)
async def link_suppliers_to_shipment(shipment_id: UUID, link_data: ShipmentSupplierLink):
    """Vincular proveedores a un embarque"""
    try:
        supabase = get_supabase()
        
        # Verificar que el embarque existe
        shipment_result = supabase.table('shipments').select('id, codigo').eq('id', str(shipment_id)).execute()
        if not shipment_result.data:
            raise HTTPException(status_code=404, detail="Embarque no encontrado")
        
        # Verificar que todos los proveedores existen
        for supplier_id in link_data.supplier_ids:
            supplier_result = supabase.table('suppliers').select('id, nombre, activo').eq('id', str(supplier_id)).execute()
            if not supplier_result.data:
                raise HTTPException(status_code=404, detail=f"Proveedor {supplier_id} no encontrado")
            
            if not supplier_result.data[0]['activo']:
                raise HTTPException(status_code=400, detail=f"Proveedor {supplier_result.data[0]['nombre']} está inactivo")
        
        # Eliminar vínculos existentes
        supabase.table('shipment_supplier').delete().eq('shipment_id', str(shipment_id)).execute()
        
        # Crear nuevos vínculos
        links_to_create = []
        for supplier_id in link_data.supplier_ids:
            links_to_create.append({
                'id': str(uuid.uuid4()),
                'shipment_id': str(shipment_id),
                'supplier_id': str(supplier_id),
                'created_at': datetime.utcnow().isoformat()
            })
        
        if links_to_create:
            supabase.table('shipment_supplier').insert(links_to_create).execute()
        
        return {
            "success": True,
            "message": f"Vinculados {len(link_data.supplier_ids)} proveedores al embarque {shipment_result.data[0]['codigo']}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error vinculando proveedores: {str(e)}")

@router.post("/{shipment_id}/facturas", response_model=dict)
async def link_invoice_to_shipment(shipment_id: UUID, link_data: ShipmentInvoiceLink):
    """Vincular factura a un embarque"""
    try:
        supabase = get_supabase()
        
        # Verificar que el embarque existe
        shipment_result = supabase.table('shipments').select('id, codigo').eq('id', str(shipment_id)).execute()
        if not shipment_result.data:
            raise HTTPException(status_code=404, detail="Embarque no encontrado")
        
        # Verificar que la factura existe
        invoice_result = supabase.table('invoices').select('id, numero_factura, supplier_id, monto_total').eq('id', str(link_data.invoice_id)).execute()
        if not invoice_result.data:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        invoice = invoice_result.data[0]
        
        # Verificar que el proveedor de la factura está vinculado al embarque
        supplier_link = supabase.table('shipment_supplier').select('id').eq('shipment_id', str(shipment_id)).eq('supplier_id', invoice['supplier_id']).execute()
        if not supplier_link.data:
            raise HTTPException(status_code=400, detail="El proveedor de la factura no está vinculado a este embarque")
        
        # Verificar que no esté ya vinculada
        existing_link = supabase.table('shipment_invoice').select('id').eq('shipment_id', str(shipment_id)).eq('invoice_id', str(link_data.invoice_id)).execute()
        if existing_link.data:
            raise HTTPException(status_code=400, detail="La factura ya está vinculada a este embarque")
        
        # Validar monto asignado si se especifica
        monto_asignado = link_data.monto_asignado
        if monto_asignado is not None:
            if float(monto_asignado) > float(invoice['monto_total']):
                raise HTTPException(status_code=400, detail="El monto asignado no puede exceder el total de la factura")
        
        # Crear vinculación
        link_record = {
            'id': str(uuid.uuid4()),
            'shipment_id': str(shipment_id),
            'invoice_id': str(link_data.invoice_id),
            'created_at': datetime.utcnow().isoformat()
        }
        
        if monto_asignado is not None:
            link_record['monto_asignado'] = float(monto_asignado)
        
        supabase.table('shipment_invoice').insert(link_record).execute()
        
        return {
            "success": True,
            "message": f"Factura {invoice['numero_factura']} vinculada exitosamente al embarque {shipment_result.data[0]['codigo']}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error vinculando factura: {str(e)}")

@router.get("/{shipment_id}/cuadre", response_model=dict)
async def get_shipment_balance(shipment_id: UUID):
    """Obtener cuadre financiero del embarque"""
    try:
        supabase = get_supabase()
        
        # Verificar que el embarque existe
        shipment_result = supabase.table('shipments').select('*').eq('id', str(shipment_id)).execute()
        if not shipment_result.data:
            raise HTTPException(status_code=404, detail="Embarque no encontrado")
        
        shipment = shipment_result.data[0]
        
        # Obtener facturas vinculadas con sus detalles
        invoices_result = supabase.table('shipment_invoice').select('''
            monto_asignado,
            invoices!shipment_invoice_invoice_id_fkey(
                id, numero_factura, monto_total, saldo_pendiente, estado,
                suppliers!invoices_supplier_id_fkey(nombre)
            )
        ''').eq('shipment_id', str(shipment_id)).execute()
        
        # Calcular totales por proveedor
        totales_por_proveedor = {}
        total_facturas = 0
        total_asignado = 0
        total_saldo_pendiente = 0
        
        for item in invoices_result.data:
            invoice = item['invoices']
            supplier_name = invoice['suppliers']['nombre']
            monto_factura = float(invoice['monto_total'])
            monto_asignado = float(item.get('monto_asignado', 0)) if item.get('monto_asignado') else monto_factura
            saldo_pendiente = float(invoice.get('saldo_pendiente', 0))
            
            if supplier_name not in totales_por_proveedor:
                totales_por_proveedor[supplier_name] = {
                    'total_facturas': 0,
                    'total_asignado': 0,
                    'total_saldo_pendiente': 0,
                    'cantidad_facturas': 0
                }
            
            totales_por_proveedor[supplier_name]['total_facturas'] += monto_factura
            totales_por_proveedor[supplier_name]['total_asignado'] += monto_asignado
            totales_por_proveedor[supplier_name]['total_saldo_pendiente'] += saldo_pendiente
            totales_por_proveedor[supplier_name]['cantidad_facturas'] += 1
            
            total_facturas += monto_factura
            total_asignado += monto_asignado
            total_saldo_pendiente += saldo_pendiente
        
        # Obtener anticipos disponibles de las órdenes relacionadas
        invoice_ids = [item['invoices']['id'] for item in invoices_result.data]
        
        anticipos_disponibles = 0
        if invoice_ids:
            # Obtener órdenes vinculadas a estas facturas
            po_links = supabase.table('invoice_po').select('po_id').in_('invoice_id', invoice_ids).execute()
            po_ids = list(set(link['po_id'] for link in po_links.data))
            
            if po_ids:
                # Obtener anticipos disponibles de estas órdenes
                advances = supabase.table('advance_payments').select('monto').in_('po_id', po_ids).eq('estado', 'disponible').execute()
                anticipos_disponibles = sum(float(adv['monto']) for adv in advances.data)
        
        return {
            "success": True,
            "data": {
                "embarque": shipment,
                "facturas": invoices_result.data,
                "resumen_financiero": {
                    "total_facturas": round(total_facturas, 2),
                    "total_asignado": round(total_asignado, 2),
                    "total_saldo_pendiente": round(total_saldo_pendiente, 2),
                    "anticipos_disponibles": round(anticipos_disponibles, 2),
                    "cobertura_anticipos": round((anticipos_disponibles / total_saldo_pendiente * 100) if total_saldo_pendiente > 0 else 0, 2)
                },
                "por_proveedor": {k: {**v, 'total_facturas': round(v['total_facturas'], 2), 'total_asignado': round(v['total_asignado'], 2), 'total_saldo_pendiente': round(v['total_saldo_pendiente'], 2)} for k, v in totales_por_proveedor.items()}
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo cuadre: {str(e)}")

@router.delete("/{shipment_id}/facturas/{invoice_id}", response_model=dict)
async def unlink_invoice_from_shipment(shipment_id: UUID, invoice_id: UUID):
    """Desvincular factura de un embarque"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe la vinculación
        existing_link = supabase.table('shipment_invoice').select('id').eq('shipment_id', str(shipment_id)).eq('invoice_id', str(invoice_id)).execute()
        if not existing_link.data:
            raise HTTPException(status_code=404, detail="La vinculación no existe")
        
        # Eliminar vinculación
        supabase.table('shipment_invoice').delete().eq('shipment_id', str(shipment_id)).eq('invoice_id', str(invoice_id)).execute()
        
        return {
            "success": True,
            "message": "Factura desvinculada exitosamente del embarque"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error desvinculando factura: {str(e)}")

@router.put("/{shipment_id}/facturas/{invoice_id}", response_model=dict)
async def update_invoice_shipment_assignment(shipment_id: UUID, invoice_id: UUID, monto_asignado: Decimal):
    """Actualizar monto asignado de una factura en un embarque"""
    try:
        supabase = get_supabase()
        
        # Verificar que existe la vinculación
        existing_link = supabase.table('shipment_invoice').select('id').eq('shipment_id', str(shipment_id)).eq('invoice_id', str(invoice_id)).execute()
        if not existing_link.data:
            raise HTTPException(status_code=404, detail="La vinculación no existe")
        
        # Verificar que la factura existe y validar monto
        invoice_result = supabase.table('invoices').select('monto_total').eq('id', str(invoice_id)).execute()
        if not invoice_result.data:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        if float(monto_asignado) > float(invoice_result.data[0]['monto_total']):
            raise HTTPException(status_code=400, detail="El monto asignado no puede exceder el total de la factura")
        
        # Actualizar monto asignado
        supabase.table('shipment_invoice').update({
            'monto_asignado': float(monto_asignado)
        }).eq('shipment_id', str(shipment_id)).eq('invoice_id', str(invoice_id)).execute()
        
        return {
            "success": True,
            "message": f"Monto asignado actualizado a ${monto_asignado}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando monto asignado: {str(e)}")

@router.get("/por-proveedor/{supplier_id}", response_model=dict)
async def get_shipments_by_supplier(supplier_id: UUID):
    """Obtener embarques de un proveedor específico"""
    try:
        supabase = get_supabase()
        
        # Verificar que el proveedor existe
        supplier_result = supabase.table('suppliers').select('id, nombre').eq('id', str(supplier_id)).execute()
        if not supplier_result.data:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        # Obtener embarques del proveedor
        shipments_result = supabase.table('shipment_supplier').select('''
            shipments!shipment_supplier_shipment_id_fkey(*)
        ''').eq('supplier_id', str(supplier_id)).execute()
        
        shipments = [item['shipments'] for item in shipments_result.data]
        
        # Para cada embarque, obtener facturas asociadas
        for shipment in shipments:
            invoices_result = supabase.table('shipment_invoice').select('''
                monto_asignado,
                invoices!shipment_invoice_invoice_id_fkey(numero_factura, monto_total, estado)
            ''').eq('shipment_id', shipment['id']).execute()
            
            shipment['facturas'] = invoices_result.data
        
        return {
            "success": True,
            "data": {
                "proveedor": supplier_result.data[0],
                "embarques": shipments,
                "total_embarques": len(shipments)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo embarques del proveedor: {str(e)}")

@router.get("/en-transito", response_model=dict)
async def get_shipments_in_transit():
    """Obtener embarques en tránsito con información detallada"""
    try:
        supabase = get_supabase()
        
        # Obtener embarques en tránsito
        shipments_result = supabase.table('shipments').select('*').eq('estado', 'en_transito').order('fecha_embarque').execute()
        
        shipments_with_details = []
        
        for shipment in shipments_result.data:
            # Obtener proveedores
            suppliers_result = supabase.table('shipment_supplier').select('''
                suppliers!shipment_supplier_supplier_id_fkey(nombre)
            ''').eq('shipment_id', shipment['id']).execute()
            
            # Obtener facturas
            invoices_result = supabase.table('shipment_invoice').select('''
                monto_asignado,
                invoices!shipment_invoice_invoice_id_fkey(numero_factura, monto_total, saldo_pendiente)
            ''').eq('shipment_id', shipment['id']).execute()
            
            # Calcular días en tránsito
            if shipment.get('fecha_embarque'):
                fecha_embarque = datetime.fromisoformat(shipment['fecha_embarque']).date()
                dias_transito = (date.today() - fecha_embarque).days
            else:
                dias_transito = None
            
            # Calcular días hasta llegada estimada
            dias_hasta_llegada = None
            if shipment.get('fecha_llegada_estimada'):
                fecha_llegada_est = datetime.fromisoformat(shipment['fecha_llegada_estimada']).date()
                dias_hasta_llegada = (fecha_llegada_est - date.today()).days
            
            shipment_detail = {
                **shipment,
                'proveedores': [item['suppliers']['nombre'] for item in suppliers_result.data],
                'facturas': invoices_result.data,
                'total_facturas': sum(float(item['invoices']['monto_total']) for item in invoices_result.data),
                'saldo_pendiente': sum(float(item['invoices']['saldo_pendiente']) for item in invoices_result.data),
                'dias_en_transito': dias_transito,
                'dias_hasta_llegada': dias_hasta_llegada,
                'estado_llegada': 'retrasado' if dias_hasta_llegada and dias_hasta_llegada < 0 else 'a_tiempo'
            }
            
            shipments_with_details.append(shipment_detail)
        
        # Estadísticas
        total_valor = sum(ship['total_facturas'] for ship in shipments_with_details)
        total_saldo = sum(ship['saldo_pendiente'] for ship in shipments_with_details)
        retrasados = len([ship for ship in shipments_with_details if ship['estado_llegada'] == 'retrasado'])
        
        return {
            "success": True,
            "data": {
                "embarques": shipments_with_details,
                "estadisticas": {
                    "total_embarques": len(shipments_with_details),
                    "valor_total": round(total_valor, 2),
                    "saldo_pendiente": round(total_saldo, 2),
                    "retrasados": retrasados
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo embarques en tránsito: {str(e)}")

@router.get("/stats/resumen", response_model=dict)
async def get_shipments_stats():
    """Estadísticas generales de embarques"""
    try:
        supabase = get_supabase()
        
        # Obtener todos los embarques
        shipments_result = supabase.table('shipments').select('estado').execute()
        
        # Calcular estadísticas
        total_embarques = len(shipments_result.data)
        
        # Por estado
        stats_por_estado = {}
        for shipment in shipments_result.data:
            estado = shipment.get('estado', 'en_transito')
            stats_por_estado[estado] = stats_por_estado.get(estado, 0) + 1
        
        # Obtener estadísticas financieras de facturas vinculadas
        invoices_shipment = supabase.table('shipment_invoice').select('''
            invoices!shipment_invoice_invoice_id_fkey(monto_total, saldo_pendiente)
        ''').execute()
        
        total_valor_embarques = sum(float(item['invoices']['monto_total']) for item in invoices_shipment.data)
        total_saldo_pendiente = sum(float(item['invoices']['saldo_pendiente']) for item in invoices_shipment.data)
        
        return {
            "success": True,
            "data": {
                "total_embarques": total_embarques,
                "por_estado": stats_por_estado,
                "valor_total_embarques": round(total_valor_embarques, 2),
                "saldo_pendiente_total": round(total_saldo_pendiente, 2)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")

@router.post("/{shipment_id}/marcar-arribado", response_model=dict)
async def mark_shipment_arrived(shipment_id: UUID, fecha_llegada_real: Optional[date] = None):
    """Marcar embarque como arribado"""
    try:
        supabase = get_supabase()
        
        # Verificar que el embarque existe
        existing = supabase.table('shipments').select('id, codigo, estado').eq('id', str(shipment_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Embarque no encontrado")
        
        shipment = existing.data[0]
        
        if shipment['estado'] == 'arribado':
            raise HTTPException(status_code=400, detail="El embarque ya está marcado como arribado")
        
        # Preparar datos de actualización
        update_data = {
            'estado': 'arribado',
            'updated_at': datetime.utcnow().isoformat()
        }
        
        if fecha_llegada_real:
            update_data['fecha_llegada_real'] = fecha_llegada_real.isoformat()
        else:
            update_data['fecha_llegada_real'] = date.today().isoformat()
        
        # Actualizar
        result = supabase.table('shipments').update(update_data).eq('id', str(shipment_id)).execute()
        
        return {
            "success": True,
            "message": f"Embarque {shipment['codigo']} marcado como arribado",
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marcando embarque como arribado: {str(e)}")

@router.post("/{shipment_id}/marcar-despachado", response_model=dict)
async def mark_shipment_dispatched(shipment_id: UUID):
    """Marcar embarque como despachado"""
    try:
        supabase = get_supabase()
        
        # Verificar que el embarque existe
        existing = supabase.table('shipments').select('id, codigo, estado').eq('id', str(shipment_id)).execute()
        if not existing.data:
            raise HTTPException(status_code=404, detail="Embarque no encontrado")
        
        shipment = existing.data[0]
        
        if shipment['estado'] == 'despachado':
            raise HTTPException(status_code=400, detail="El embarque ya está marcado como despachado")
        
        if shipment['estado'] != 'arribado':
            raise HTTPException(status_code=400, detail="El embarque debe estar arribado antes de ser despachado")
        
        # Actualizar estado
        result = supabase.table('shipments').update({
            'estado': 'despachado',
            'updated_at': datetime.utcnow().isoformat()
        }).eq('id', str(shipment_id)).execute()
        
        return {
            "success": True,
            "message": f"Embarque {shipment['codigo']} marcado como despachado",
            "data": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marcando embarque como despachado: {str(e)}")

@router.get("/proximos-arribar", response_model=dict)
async def get_upcoming_arrivals(dias: int = Query(30, ge=1, le=365)):
    """Obtener embarques que van a arribar en los próximos días"""
    try:
        supabase = get_supabase()
        
        # Calcular fecha límite
        fecha_limite = (date.today() + timedelta(days=dias)).isoformat()
        
        # Obtener embarques próximos a arribar
        shipments_result = supabase.table('shipments').select('*').eq('estado', 'en_transito').lte('fecha_llegada_estimada', fecha_limite).order('fecha_llegada_estimada').execute()
        
        shipments_with_details = []
        hoy = date.today()
        
        for shipment in shipments_result.data:
            # Obtener proveedores
            suppliers_result = supabase.table('shipment_supplier').select('''
                suppliers!shipment_supplier_supplier_id_fkey(nombre)
            ''').eq('shipment_id', shipment['id']).execute()
            
            # Obtener facturas
            invoices_result = supabase.table('shipment_invoice').select('''
                monto_asignado,
                invoices!shipment_invoice_invoice_id_fkey(numero_factura, monto_total, saldo_pendiente)
            ''').eq('shipment_id', shipment['id']).execute()
            
            # Calcular días hasta llegada
            dias_hasta_llegada = None
            urgencia = 'normal'
            
            if shipment.get('fecha_llegada_estimada'):
                fecha_llegada_est = datetime.fromisoformat(shipment['fecha_llegada_estimada']).date()
                dias_hasta_llegada = (fecha_llegada_est - hoy).days
                
                if dias_hasta_llegada < 0:
                    urgencia = 'retrasado'
                elif dias_hasta_llegada <= 3:
                    urgencia = 'critico'
                elif dias_hasta_llegada <= 7:
                    urgencia = 'alto'
            
            shipment_detail = {
                **shipment,
                'proveedores': [item['suppliers']['nombre'] for item in suppliers_result.data],
                'facturas': invoices_result.data,
                'total_facturas': sum(float(item['invoices']['monto_total']) for item in invoices_result.data),
                'saldo_pendiente': sum(float(item['invoices']['saldo_pendiente']) for item in invoices_result.data),
                'dias_hasta_llegada': dias_hasta_llegada,
                'urgencia': urgencia
            }
            
            shipments_with_details.append(shipment_detail)
        
        # Agrupar por urgencia
        retrasados = [s for s in shipments_with_details if s['urgencia'] == 'retrasado']
        criticos = [s for s in shipments_with_details if s['urgencia'] == 'critico']
        altos = [s for s in shipments_with_details if s['urgencia'] == 'alto']
        normales = [s for s in shipments_with_details if s['urgencia'] == 'normal']
        
        return {
            "success": True,
            "data": {
                "resumen": {
                    "total": len(shipments_with_details),
                    "retrasados": len(retrasados),
                    "criticos": len(criticos),
                    "altos": len(altos),
                    "normales": len(normales)
                },
                "embarques": {
                    "retrasados": retrasados,
                    "criticos": criticos,
                    "altos": altos,
                    "normales": normales
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo próximos arribos: {str(e)}")
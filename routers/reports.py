from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from uuid import UUID
from datetime import datetime, date, timedelta
from decimal import Decimal

from database import get_supabase

router = APIRouter()

@router.get("/dashboard-ejecutivo", response_model=dict)
async def get_executive_dashboard():
    """Dashboard ejecutivo con métricas clave"""
    try:
        supabase = get_supabase()
        
        # 1. Conteos generales
        suppliers_count = supabase.table('suppliers').select("count", count="exact").eq('activo', True).execute().count
        pos_count = supabase.table('purchase_orders').select("count", count="exact").execute().count
        invoices_count = supabase.table('invoices').select("count", count="exact").execute().count
        shipments_count = supabase.table('shipments').select("count", count="exact").execute().count
        
        # 2. Estadísticas financieras
        # Órdenes de compra
        pos_result = supabase.table('purchase_orders').select('total_oc, moneda, estado').execute()
        total_pos_usd = sum(float(po.get('total_oc', 0)) for po in pos_result.data if po.get('moneda') == 'USD')
        total_pos_clp = sum(float(po.get('total_oc', 0)) for po in pos_result.data if po.get('moneda') == 'CLP')
        
        pos_por_estado = {}
        for po in pos_result.data:
            estado = po.get('estado', 'pendiente')
            pos_por_estado[estado] = pos_por_estado.get(estado, 0) + 1
        
        # Facturas
        invoices_result = supabase.table('invoices').select('monto_total, saldo_pendiente, moneda, estado').execute()
        total_facturas_usd = sum(float(inv.get('monto_total', 0)) for inv in invoices_result.data if inv.get('moneda') == 'USD')
        total_facturas_clp = sum(float(inv.get('monto_total', 0)) for inv in invoices_result.data if inv.get('moneda') == 'CLP')
        total_saldo_pendiente_usd = sum(float(inv.get('saldo_pendiente', 0)) for inv in invoices_result.data if inv.get('moneda') == 'USD')
        total_saldo_pendiente_clp = sum(float(inv.get('saldo_pendiente', 0)) for inv in invoices_result.data if inv.get('moneda') == 'CLP')
        
        facturas_por_estado = {}
        for inv in invoices_result.data:
            estado = inv.get('estado', 'pendiente')
            facturas_por_estado[estado] = facturas_por_estado.get(estado, 0) + 1
        
        # Anticipos
        advances_result = supabase.table('advance_payments').select('monto, moneda, estado').execute()
        total_anticipos_usd = sum(float(adv.get('monto', 0)) for adv in advances_result.data if adv.get('moneda') == 'USD')
        total_anticipos_clp = sum(float(adv.get('monto', 0)) for adv in advances_result.data if adv.get('moneda') == 'CLP')
        
        anticipos_disponibles_usd = sum(float(adv.get('monto', 0)) for adv in advances_result.data 
                                      if adv.get('moneda') == 'USD' and adv.get('estado') == 'disponible')
        anticipos_disponibles_clp = sum(float(adv.get('monto', 0)) for adv in advances_result.data 
                                      if adv.get('moneda') == 'CLP' and adv.get('estado') == 'disponible')
        
        # 3. Embarques
        shipments_result = supabase.table('shipments').select('estado').execute()
        embarques_por_estado = {}
        for ship in shipments_result.data:
            estado = ship.get('estado', 'en_transito')
            embarques_por_estado[estado] = embarques_por_estado.get(estado, 0) + 1
        
        # 4. Top 5 proveedores por volumen
        top_suppliers_result = supabase.table('suppliers').select('''
            id, nombre,
            purchase_orders!purchase_orders_supplier_id_fkey(total_oc)
        ''').eq('activo', True).execute()
        
        suppliers_volume = []
        for supplier in top_suppliers_result.data:
            total_volume = sum(float(po.get('total_oc', 0)) for po in supplier.get('purchase_orders', []))
            if total_volume > 0:
                suppliers_volume.append({
                    'nombre': supplier['nombre'],
                    'total_ordenes': total_volume
                })
        
        top_suppliers = sorted(suppliers_volume, key=lambda x: x['total_ordenes'], reverse=True)[:5]
        
        # 5. Alertas y métricas de riesgo
        alertas = []
        
        # Facturas vencidas (más de 30 días)
        fecha_limite = (date.today() - timedelta(days=30)).isoformat()
        facturas_vencidas = supabase.table('invoice_due').select('''
            count,
            invoices!invoice_due_invoice_id_fkey(numero_factura, suppliers!invoices_supplier_id_fkey(nombre))
        ''', count='exact').lt('fecha_vencimiento', fecha_limite).eq('estado', 'pendiente').execute()
        
        if facturas_vencidas.count > 0:
            alertas.append({
                'tipo': 'facturas_vencidas',
                'cantidad': facturas_vencidas.count,
                'mensaje': f"{facturas_vencidas.count} vencimientos pendientes hace más de 30 días"
            })
        
        # Órdenes sin anticipos
        pos_sin_anticipos = 0
        for po in pos_result.data:
            if po.get('estado') == 'pendiente':
                advances_for_po = supabase.table('advance_payments').select('id').eq('po_id', po['id']).execute()
                if not advances_for_po.data:
                    pos_sin_anticipos += 1
        
        if pos_sin_anticipos > 0:
            alertas.append({
                'tipo': 'ordenes_sin_anticipos',
                'cantidad': pos_sin_anticipos,
                'mensaje': f"{pos_sin_anticipos} órdenes pendientes sin anticipos"
            })
        
        return {
            "success": True,
            "data": {
                "conteos": {
                    "suppliers": suppliers_count,
                    "purchase_orders": pos_count,
                    "invoices": invoices_count,
                    "shipments": shipments_count
                },
                "financiero": {
                    "ordenes_compra": {
                        "total_usd": round(total_pos_usd, 2),
                        "total_clp": round(total_pos_clp, 2),
                        "por_estado": pos_por_estado
                    },
                    "facturas": {
                        "total_usd": round(total_facturas_usd, 2),
                        "total_clp": round(total_facturas_clp, 2),
                        "saldo_pendiente_usd": round(total_saldo_pendiente_usd, 2),
                        "saldo_pendiente_clp": round(total_saldo_pendiente_clp, 2),
                        "por_estado": facturas_por_estado
                    },
                    "anticipos": {
                        "total_usd": round(total_anticipos_usd, 2),
                        "total_clp": round(total_anticipos_clp, 2),
                        "disponibles_usd": round(anticipos_disponibles_usd, 2),
                        "disponibles_clp": round(anticipos_disponibles_clp, 2)
                    }
                },
                "embarques": {
                    "por_estado": embarques_por_estado
                },
                "top_suppliers": top_suppliers,
                "alertas": alertas,
                "ultima_actualizacion": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando dashboard ejecutivo: {str(e)}")

@router.get("/conciliacion-ordenes", response_model=dict)
async def get_orders_reconciliation():
    """Reporte de conciliación de órdenes vs facturas vs anticipos"""
    try:
        supabase = get_supabase()
        
        # Obtener todas las órdenes con sus relaciones
        pos_result = supabase.table('purchase_orders').select('''
            *,
            suppliers!purchase_orders_supplier_id_fkey(nombre)
        ''').order('created_at', desc=True).execute()
        
        reconciliation_data = []
        
        for po in pos_result.data:
            po_id = po['id']
            
            # Facturas vinculadas a esta orden
            invoice_po_links = supabase.table('invoice_po').select('''
                invoices!invoice_po_invoice_id_fkey(monto_total, saldo_pendiente, estado)
            ''').eq('po_id', po_id).execute()
            
            total_facturas = sum(float(link['invoices']['monto_total']) for link in invoice_po_links.data)
            total_saldo_pendiente = sum(float(link['invoices']['saldo_pendiente']) for link in invoice_po_links.data)
            
            # Anticipos de esta orden
            advances_result = supabase.table('advance_payments').select('monto, estado').eq('po_id', po_id).execute()
            total_anticipos = sum(float(adv['monto']) for adv in advances_result.data)
            anticipos_disponibles = sum(float(adv['monto']) for adv in advances_result.data if adv['estado'] == 'disponible')
            
            # Aplicaciones de anticipos
            advance_allocations = supabase.table('advance_allocation').select('monto_aplicado').in_('anticipo_id', 
                [adv['id'] for adv in advances_result.data] if advances_result.data else []).execute()
            anticipos_aplicados = sum(float(alloc['monto_aplicado']) for alloc in advance_allocations.data)
            
            # Calcular balances
            balance_oc_facturas = float(po['total_oc']) - total_facturas
            cobertura_anticipos = (anticipos_disponibles / total_saldo_pendiente * 100) if total_saldo_pendiente > 0 else 0
            
            # Estado de conciliación
            estado_conciliacion = "completa"
            if abs(balance_oc_facturas) > 0.01:
                estado_conciliacion = "pendiente_facturacion"
            elif total_saldo_pendiente > 0 and anticipos_disponibles == 0:
                estado_conciliacion = "pendiente_pago"
            elif total_saldo_pendiente > 0:
                estado_conciliacion = "parcial"
            
            reconciliation_data.append({
                "orden": {
                    "id": po['id'],
                    "numero": po['numero_orden'],
                    "proveedor": po['suppliers']['nombre'],
                    "total": float(po['total_oc']),
                    "moneda": po['moneda'],
                    "estado": po['estado']
                },
                "facturas": {
                    "total": round(total_facturas, 2),
                    "saldo_pendiente": round(total_saldo_pendiente, 2),
                    "cantidad": len(invoice_po_links.data)
                },
                "anticipos": {
                    "total_pagado": round(total_anticipos, 2),
                    "aplicados": round(anticipos_aplicados, 2),
                    "disponibles": round(anticipos_disponibles, 2)
                },
                "balance": {
                    "oc_vs_facturas": round(balance_oc_facturas, 2),
                    "cobertura_anticipos": round(cobertura_anticipos, 2)
                },
                "estado_conciliacion": estado_conciliacion
            })
        
        # Estadísticas generales
        total_ordenes = len(reconciliation_data)
        ordenes_completas = len([r for r in reconciliation_data if r['estado_conciliacion'] == 'completa'])
        ordenes_pendientes = total_ordenes - ordenes_completas
        
        return {
            "success": True,
            "data": {
                "resumen": {
                    "total_ordenes": total_ordenes,
                    "completas": ordenes_completas,
                    "pendientes": ordenes_pendientes,
                    "porcentaje_completitud": round((ordenes_completas / total_ordenes * 100) if total_ordenes > 0 else 0, 2)
                },
                "ordenes": reconciliation_data
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando reporte de conciliación: {str(e)}")

@router.get("/flujo-caja-proyectado", response_model=dict)
async def get_cash_flow_projection(semanas: int = Query(4, ge=1, le=52)):
    """Proyección de flujo de caja básica basada en vencimientos"""
    try:
        supabase = get_supabase()
        
        # Calcular fechas
        fecha_inicio = date.today()
        fecha_fin = fecha_inicio + timedelta(weeks=semanas)
        
        # Obtener vencimientos pendientes en el período
        vencimientos_result = supabase.table('invoice_due').select('''
            fecha_vencimiento, monto_vencimiento, estado,
            invoices!invoice_due_invoice_id_fkey(
                numero_factura, moneda,
                suppliers!invoices_supplier_id_fkey(nombre)
            )
        ''').gte('fecha_vencimiento', fecha_inicio.isoformat()).lte('fecha_vencimiento', fecha_fin.isoformat()).eq('estado', 'pendiente').order('fecha_vencimiento').execute()
        
        # Agrupar por semana
        proyeccion_semanal = {}
        
        for venc in vencimientos_result.data:
            fecha_venc = datetime.fromisoformat(venc['fecha_vencimiento']).date()
            semana = (fecha_venc - fecha_inicio).days // 7 + 1
            
            if semana not in proyeccion_semanal:
                proyeccion_semanal[semana] = {
                    'fecha_inicio': (fecha_inicio + timedelta(weeks=semana-1)).isoformat(),
                    'fecha_fin': (fecha_inicio + timedelta(weeks=semana) - timedelta(days=1)).isoformat(),
                    'salidas_usd': 0,
                    'salidas_clp': 0,
                    'vencimientos': []
                }
            
            moneda = venc['invoices']['moneda']
            monto = float(venc['monto_vencimiento'])
            
            if moneda == 'USD':
                proyeccion_semanal[semana]['salidas_usd'] += monto
            else:
                proyeccion_semanal[semana]['salidas_clp'] += monto
            
            proyeccion_semanal[semana]['vencimientos'].append({
                'fecha': venc['fecha_vencimiento'],
                'monto': monto,
                'moneda': moneda,
                'factura': venc['invoices']['numero_factura'],
                'proveedor': venc['invoices']['suppliers']['nombre']
            })
        
        # Calcular anticipos disponibles para cobertura
        anticipos_disponibles = supabase.table('advance_payments').select('monto, moneda').eq('estado', 'disponible').execute()
        total_anticipos_usd = sum(float(adv['monto']) for adv in anticipos_disponibles.data if adv['moneda'] == 'USD')
        total_anticipos_clp = sum(float(adv['monto']) for adv in anticipos_disponibles.data if adv['moneda'] == 'CLP')
        
        # Totales del período
        total_salidas_usd = sum(sem['salidas_usd'] for sem in proyeccion_semanal.values())
        total_salidas_clp = sum(sem['salidas_clp'] for sem in proyeccion_semanal.values())
        
        # Calcular cobertura
        cobertura_usd = (total_anticipos_usd / total_salidas_usd * 100) if total_salidas_usd > 0 else 100
        cobertura_clp = (total_anticipos_clp / total_salidas_clp * 100) if total_salidas_clp > 0 else 100
        
        return {
            "success": True,
            "data": {
                "periodo": {
                    "inicio": fecha_inicio.isoformat(),
                    "fin": fecha_fin.isoformat(),
                    "semanas": semanas
                },
                "resumen": {
                    "total_salidas_usd": round(total_salidas_usd, 2),
                    "total_salidas_clp": round(total_salidas_clp, 2),
                    "anticipos_disponibles_usd": round(total_anticipos_usd, 2),
                    "anticipos_disponibles_clp": round(total_anticipos_clp, 2),
                    "cobertura_usd": round(cobertura_usd, 2),
                    "cobertura_clp": round(cobertura_clp, 2)
                },
                "proyeccion_semanal": {str(k): {**v, 'salidas_usd': round(v['salidas_usd'], 2), 'salidas_clp': round(v['salidas_clp'], 2)} for k, v in proyeccion_semanal.items()}
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando proyección de flujo de caja: {str(e)}")

@router.get("/vencimientos-proximos", response_model=dict)
async def get_upcoming_dues(dias: int = Query(30, ge=1, le=365)):
    """Reporte de vencimientos próximos"""
    try:
        supabase = get_supabase()
        
        # Calcular fecha límite
        fecha_limite = (date.today() + timedelta(days=dias)).isoformat()
        
        # Obtener vencimientos próximos
        vencimientos_result = supabase.table('invoice_due').select('''
            *,
            invoices!invoice_due_invoice_id_fkey(
                numero_factura, monto_total, moneda,
                suppliers!invoices_supplier_id_fkey(nombre, contacto)
            )
        ''').lte('fecha_vencimiento', fecha_limite).eq('estado', 'pendiente').order('fecha_vencimiento').execute()
        
        # Agrupar por urgencia
        hoy = date.today()
        vencidos = []
        proximos_7_dias = []
        proximos_30_dias = []
        
        for venc in vencimientos_result.data:
            fecha_venc = datetime.fromisoformat(venc['fecha_vencimiento']).date()
            dias_hasta_venc = (fecha_venc - hoy).days
            
            venc_info = {
                **venc,
                'dias_hasta_vencimiento': dias_hasta_venc,
                'urgencia': 'normal'
            }
            
            if dias_hasta_venc < 0:
                venc_info['urgencia'] = 'vencido'
                vencidos.append(venc_info)
            elif dias_hasta_venc <= 7:
                venc_info['urgencia'] = 'critico'
                proximos_7_dias.append(venc_info)
            elif dias_hasta_venc <= 30:
                venc_info['urgencia'] = 'alto'
                proximos_30_dias.append(venc_info)
        
        # Calcular totales por moneda
        def calcular_totales(lista):
            total_usd = sum(float(v['monto_vencimiento']) for v in lista if v['invoices']['moneda'] == 'USD')
            total_clp = sum(float(v['monto_vencimiento']) for v in lista if v['invoices']['moneda'] == 'CLP')
            return {'usd': round(total_usd, 2), 'clp': round(total_clp, 2)}
        
        return {
            "success": True,
            "data": {
                "resumen": {
                    "total_vencimientos": len(vencimientos_result.data),
                    "vencidos": {
                        "cantidad": len(vencidos),
                        "totales": calcular_totales(vencidos)
                    },
                    "proximos_7_dias": {
                        "cantidad": len(proximos_7_dias),
                        "totales": calcular_totales(proximos_7_dias)
                    },
                    "proximos_30_dias": {
                        "cantidad": len(proximos_30_dias),
                        "totales": calcular_totales(proximos_30_dias)
                    }
                },
                "vencimientos": {
                    "vencidos": vencidos,
                    "proximos_7_dias": proximos_7_dias,
                    "proximos_30_dias": proximos_30_dias
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando reporte de vencimientos: {str(e)}")

@router.get("/proveedor/{supplier_id}/detalle", response_model=dict)
async def get_supplier_detail_report(supplier_id: UUID):
    """Reporte detallado de un proveedor específico"""
    try:
        supabase = get_supabase()
        
        # Verificar que el proveedor existe
        supplier_result = supabase.table('suppliers').select('*').eq('id', str(supplier_id)).execute()
        if not supplier_result.data:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        supplier = supplier_result.data[0]
        
        # Órdenes de compra
        pos_result = supabase.table('purchase_orders').select('*').eq('supplier_id', str(supplier_id)).order('created_at', desc=True).execute()
        
        # Facturas
        invoices_result = supabase.table('invoices').select('*').eq('supplier_id', str(supplier_id)).order('created_at', desc=True).execute()
        
        # Anticipos (de las órdenes de este proveedor)
        po_ids = [po['id'] for po in pos_result.data]
        advances_result = []
        if po_ids:
            advances_result = supabase.table('advance_payments').select('''
                *,
                purchase_orders!advance_payments_po_id_fkey(numero_orden)
            ''').in_('po_id', po_ids).order('fecha_pago', desc=True).execute().data
        
        # Embarques relacionados
        shipment_supplier_result = supabase.table('shipment_supplier').select('''
            shipments!shipment_supplier_shipment_id_fkey(*)
        ''').eq('supplier_id', str(supplier_id)).execute()
        
        shipments = [item['shipments'] for item in shipment_supplier_result.data]
        
        # Calcular estadísticas
        total_ordenes = sum(float(po['total_oc']) for po in pos_result.data)
        total_facturas = sum(float(inv['monto_total']) for inv in invoices_result.data)
        total_saldo_pendiente = sum(float(inv.get('saldo_pendiente', 0)) for inv in invoices_result.data)
        total_anticipos = sum(float(adv['monto']) for adv in advances_result)
        
        # Vencimientos próximos (30 días)
        fecha_limite = (date.today() + timedelta(days=30)).isoformat()
        invoice_ids = [inv['id'] for inv in invoices_result.data]
        
        vencimientos_proximos = []
        if invoice_ids:
            vencimientos_proximos = supabase.table('invoice_due').select('*').in_('invoice_id', invoice_ids).lte('fecha_vencimiento', fecha_limite).eq('estado', 'pendiente').order('fecha_vencimiento').execute().data
        
        return {
            "success": True,
            "data": {
                "proveedor": supplier,
                "estadisticas": {
                    "total_ordenes": round(total_ordenes, 2),
                    "total_facturas": round(total_facturas, 2),
                    "saldo_pendiente": round(total_saldo_pendiente, 2),
                    "total_anticipos": round(total_anticipos, 2),
                    "cantidad_ordenes": len(pos_result.data),
                    "cantidad_facturas": len(invoices_result.data),
                    "cantidad_embarques": len(shipments),
                    "vencimientos_proximos": len(vencimientos_proximos)
                },
                "ordenes_compra": pos_result.data,
                "facturas": invoices_result.data,
                "anticipos": advances_result,
                "embarques": shipments,
                "vencimientos_proximos": vencimientos_proximos
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando reporte de proveedor: {str(e)}")
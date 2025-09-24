#!/usr/bin/env python3
"""
Script completo para probar la nueva API SGF v2.0
Ejecutar: python test_api.py
"""

import requests
import json
from datetime import date, datetime
import time

BASE_URL = "http://localhost:8000"

def print_step(step, description):
    print(f"\n🔍 PASO {step}: {description}")
    print("-" * 60)

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_info(message):
    print(f"ℹ️  {message}")

def test_health():
    """Test 1: Verificar que el sistema esté funcionando"""
    print_step(1, "Verificando estado del sistema")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print_success("Sistema funcionando correctamente")
            print_info(f"Estado: {data.get('status')}")
            print_info(f"Base de datos: {data.get('database')}")
            print_info(f"Proveedores en BD: {data.get('suppliers_count', 0)}")
            return True
        else:
            print_error(f"Error HTTP: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error de conexión: {str(e)}")
        print_info("¿Está corriendo el servidor? Ejecuta: python main.py")
        return False

def test_suppliers():
    """Test 2: CRUD completo de proveedores"""
    print_step(2, "Probando gestión de proveedores")
    
    # Crear proveedor
    supplier_data = {
        "nombre": "Proveedor Test API v2.0",
        "activo": True,
        "puerto_salida_default": "Shanghai",
        "contacto": "test@proveedor.com",
        "notas": "Creado por test automatizado - API v2.0"
    }
    
    try:
        # CREATE - Crear proveedor
        print_info("Creando proveedor...")
        response = requests.post(f"{BASE_URL}/api/suppliers/", json=supplier_data)
        if response.status_code == 200:
            supplier = response.json()['data']
            supplier_id = supplier['id']
            print_success(f"Proveedor creado: {supplier['nombre']}")
            
            # READ - Obtener lista
            print_info("Obteniendo lista de proveedores...")
            response = requests.get(f"{BASE_URL}/api/suppliers/")
            if response.status_code == 200:
                suppliers_list = response.json()
                print_success(f"Lista obtenida: {suppliers_list['total']} proveedores")
                
                # READ - Obtener específico
                print_info("Obteniendo proveedor específico...")
                response = requests.get(f"{BASE_URL}/api/suppliers/{supplier_id}")
                if response.status_code == 200:
                    specific_supplier = response.json()['data']
                    print_success(f"Proveedor específico obtenido: {specific_supplier['nombre']}")
                    
                    # UPDATE - Actualizar proveedor
                    print_info("Actualizando proveedor...")
                    update_data = {"notas": "Actualizado por test API v2.0"}
                    response = requests.put(f"{BASE_URL}/api/suppliers/{supplier_id}", json=update_data)
                    if response.status_code == 200:
                        print_success("Proveedor actualizado correctamente")
                        return supplier_id
                    
            print_error("Error en operaciones CRUD de proveedores")
            return None
            
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None

def test_purchase_orders(supplier_id):
    """Test 3: Gestión de órdenes de compra"""
    print_step(3, "Probando órdenes de compra")
    
    if not supplier_id:
        print_info("⚠️  Saltando prueba - no hay proveedor disponible")
        return None
    
    po_data = {
        "supplier_id": supplier_id,
        "numero_orden": f"PO-TEST-{int(time.time())}",
        "moneda": "USD",
        "total_oc": 7500.00,
        "fecha": date.today().isoformat(),
        "estado": "pendiente",
        "notas": "Orden de compra de prueba API v2.0"
    }
    
    try:
        # Crear orden
        print_info("Creando orden de compra...")
        response = requests.post(f"{BASE_URL}/api/purchase-orders/", json=po_data)
        if response.status_code == 200:
            po = response.json()['data']
            po_id = po['id']
            print_success(f"Orden creada: {po['numero_orden']} - ${po['total_oc']}")
            
            # Obtener lista de órdenes
            print_info("Obteniendo lista de órdenes...")
            response = requests.get(f"{BASE_URL}/api/purchase-orders/")
            if response.status_code == 200:
                orders_list = response.json()
                print_success(f"Lista de órdenes obtenida: {orders_list['total']} órdenes")
                return po_id
                
        print_error("Error creando orden de compra")
        return None
        
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None

def test_advances(po_id):
    """Test 4: Gestión de anticipos"""
    print_step(4, "Probando anticipos")
    
    if not po_id:
        print_info("⚠️  Saltando prueba - no hay orden disponible")
        return None
    
    advance_data = {
        "po_id": po_id,
        "monto": 2000.00,
        "moneda": "USD",
        "fecha_pago": date.today().isoformat(),
        "metodo_pago": "transferencia",
        "usuario_pago": "test_user",
        "notas": "Anticipo de prueba API v2.0"
    }
    
    try:
        print_info("Creando anticipo...")
        response = requests.post(f"{BASE_URL}/api/advances/", json=advance_data)
        if response.status_code == 200:
            advance = response.json()['data']
            advance_id = advance['id']
            print_success(f"Anticipo creado: ${advance['monto']} {advance['moneda']}")
            
            # Obtener anticipos por orden
            print_info("Obteniendo anticipos de la orden...")
            response = requests.get(f"{BASE_URL}/api/advances/por-orden/{po_id}")
            if response.status_code == 200:
                po_advances = response.json()['data']
                print_success(f"Anticipos de la orden: ${po_advances['resumen']['total_anticipos']}")
                return advance_id
                
        print_error("Error creando anticipo")
        return None
        
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None

def test_invoices(supplier_id):
    """Test 5: Gestión de facturas (nueva lógica)"""
    print_step(5, "Probando facturas con nueva lógica")
    
    if not supplier_id:
        print_info("⚠️  Saltando prueba - no hay proveedor disponible")
        return None
    
    invoice_data = {
        "supplier_id": supplier_id,
        "numero_factura": f"FACT-TEST-{int(time.time())}",
        "fecha_emision": date.today().isoformat(),
        "moneda": "USD",
        "monto_total": 3500.00,
        "tipo_factura": "producto",
        "concepto": "Productos de prueba API v2.0",
        "notas": "Factura creada por test automatizado"
    }
    
    try:
        print_info("Creando factura (solo con proveedor)...")
        response = requests.post(f"{BASE_URL}/api/invoices/", json=invoice_data)
        if response.status_code == 200:
            invoice = response.json()['data']
            invoice_id = invoice['id']
            print_success(f"Factura creada: {invoice['numero_factura']}")
            print_info(f"   💰 Monto: ${invoice['monto_total']}")
            print_info(f"   📊 Saldo pendiente: ${invoice.get('saldo_pendiente', 0)}")
            
            # Obtener vencimientos de la factura
            print_info("Obteniendo vencimientos...")
            response = requests.get(f"{BASE_URL}/api/invoices/{invoice_id}/vencimientos")
            if response.status_code == 200:
                vencimientos = response.json()['data']
                print_success(f"Vencimientos generados: {len(vencimientos)}")
                return invoice_id
                
        print_error("Error creando factura")
        return None
        
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None

def test_shipments():
    """Test 6: Gestión de embarques"""
    print_step(6, "Probando embarques")
    
    shipment_data = {
        "codigo": f"SHIP-TEST-{int(time.time())}",
        "puerto_origen": "Shanghai",
        "puerto_destino": "Valparaíso",
        "fecha_embarque": date.today().isoformat(),
        "estado": "en_transito",
        "naviera": "Test Shipping Line",
        "notas": "Embarque de prueba API v2.0"
    }
    
    try:
        print_info("Creando embarque...")
        response = requests.post(f"{BASE_URL}/api/shipments/", json=shipment_data)
        if response.status_code == 200:
            shipment = response.json()['data']
            shipment_id = shipment['id']
            print_success(f"Embarque creado: {shipment['codigo']}")
            print_info(f"   🚢 Ruta: {shipment['puerto_origen']} → {shipment['puerto_destino']}")
            print_info(f"   📅 Estado: {shipment['estado']}")
            
            # Obtener embarques en tránsito
            print_info("Obteniendo embarques en tránsito...")
            response = requests.get(f"{BASE_URL}/api/shipments/en-transito")
            if response.status_code == 200:
                transit_shipments = response.json()['data']
                print_success(f"Embarques en tránsito: {transit_shipments['estadisticas']['total_embarques']}")
                return shipment_id
                
        print_error("Error creando embarque")
        return None
        
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None

def test_reports():
    """Test 7: Sistema de reportes"""
    print_step(7, "Probando sistema de reportes")
    
    try:
        # Dashboard ejecutivo
        print_info("Generando dashboard ejecutivo...")
        response = requests.get(f"{BASE_URL}/api/reports/dashboard-ejecutivo")
        if response.status_code == 200:
            dashboard = response.json()['data']
            print_success("Dashboard ejecutivo generado")
            print_info(f"   📊 Proveedores: {dashboard['conteos']['suppliers']}")
            print_info(f"   🛒 Órdenes: {dashboard['conteos']['purchase_orders']}")
            print_info(f"   🧾 Facturas: {dashboard['conteos']['invoices']}")
            print_info(f"   🚢 Embarques: {dashboard['conteos']['shipments']}")
            
            # Conciliación de órdenes
            print_info("Generando reporte de conciliación...")
            response = requests.get(f"{BASE_URL}/api/reports/conciliacion-ordenes")
            if response.status_code == 200:
                conciliacion = response.json()['data']
                print_success("Reporte de conciliación generado")
                print_info(f"   📈 Órdenes completas: {conciliacion['resumen']['completas']}")
                print_info(f"   ⏳ Órdenes pendientes: {conciliacion['resumen']['pendientes']}")
                
                # Proyección de flujo de caja
                print_info("Generando proyección de flujo de caja...")
                response = requests.get(f"{BASE_URL}/api/reports/flujo-caja-proyectado?semanas=4")
                if response.status_code == 200:
                    flujo_caja = response.json()['data']
                    print_success("Proyección de flujo de caja generada")
                    print_info(f"   💸 Salidas proyectadas USD: ${flujo_caja['resumen']['total_salidas_usd']}")
                    print_info(f"   💰 Cobertura anticipos: {flujo_caja['resumen']['cobertura_usd']:.1f}%")
                    return True
                    
        print_error("Error generando reportes")
        return False
        
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_dashboard_api():
    """Test 8: API de estadísticas del dashboard"""
    print_step(8, "Probando API de dashboard")
    
    try:
        print_info("Obteniendo estadísticas del dashboard...")
        response = requests.get(f"{BASE_URL}/api/stats/dashboard")
        if response.status_code == 200:
            stats = response.json()['data']
            print_success("Dashboard API funcionando")
            print_info(f"   📊 Total proveedores: {stats['conteos']['suppliers']}")
            print_info(f"   💰 Total órdenes USD: ${stats['financial']['total_pos_usd']}")
            print_info(f"   💸 Saldo pendiente: ${stats['financial']['saldo_pendiente']}")
            return True
            
        print_error("Error obteniendo estadísticas del dashboard")
        return False
        
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_payments(invoice_id):
    """Test 9: Sistema de pagos"""
    print_step(9, "Probando sistema de pagos")
    
    if not invoice_id:
        print_info("⚠️  Saltando prueba - no hay factura disponible")
        return None
    
    payment_data = {
        "invoice_id": invoice_id,
        "monto_pagado": 1500.00,
        "fecha": date.today().isoformat(),
        "metodo_pago": "transferencia",
        "referencia": f"TEST-PAY-{int(time.time())}",
        "notas": "Pago de prueba API v2.0"
    }
    
    try:
        print_info("Registrando pago...")
        response = requests.post(f"{BASE_URL}/api/payments/", json=payment_data)
        if response.status_code == 200:
            payment = response.json()['data']
            payment_id = payment['id']
            print_success(f"Pago registrado: ${payment['monto_pagado']}")
            print_info(f"   💳 Método: {payment['metodo_pago']}")
            print_info(f"   🏦 Referencia: {payment['referencia']}")
            
            # Obtener pagos de la factura
            print_info("Obteniendo pagos de la factura...")
            response = requests.get(f"{BASE_URL}/api/payments/por-factura/{invoice_id}")
            if response.status_code == 200:
                invoice_payments = response.json()['data']
                print_success(f"Pagos de factura: ${invoice_payments['resumen']['total_pagos']}")
                return payment_id
                
        print_error("Error registrando pago")
        return None
        
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None

def cleanup_test_data(supplier_id, po_id, invoice_id, shipment_id, advance_id, payment_id):
    """Limpieza opcional de datos de prueba"""
    print_step(10, "Limpieza de datos de prueba (opcional)")
    
    try:
        cleanup_count = 0
        
        # Eliminar pago (si existe)
        if payment_id:
            try:
                response = requests.delete(f"{BASE_URL}/api/payments/{payment_id}")
                if response.status_code == 200:
                    cleanup_count += 1
                    print_info("✓ Pago eliminado")
            except:
                pass
        
        # Eliminar anticipo (si no tiene aplicaciones)
        if advance_id:
            try:
                response = requests.delete(f"{BASE_URL}/api/advances/{advance_id}")
                if response.status_code == 200:
                    cleanup_count += 1
                    print_info("✓ Anticipo eliminado")
            except:
                pass
        
        # Eliminar embarque (si no tiene facturas)
        if shipment_id:
            try:
                response = requests.delete(f"{BASE_URL}/api/shipments/{shipment_id}")
                if response.status_code == 200:
                    cleanup_count += 1
                    print_info("✓ Embarque eliminado")
            except:
                pass
        
        # Eliminar factura (si no tiene pagos)
        if invoice_id:
            try:
                response = requests.delete(f"{BASE_URL}/api/invoices/{invoice_id}")
                if response.status_code == 200:
                    cleanup_count += 1
                    print_info("✓ Factura eliminada")
            except:
                pass
        
        # Eliminar orden (si no tiene anticipos ni facturas)
        if po_id:
            try:
                response = requests.delete(f"{BASE_URL}/api/purchase-orders/{po_id}")
                if response.status_code == 200:
                    cleanup_count += 1
                    print_info("✓ Orden eliminada")
            except:
                pass
        
        # Eliminar proveedor (si no tiene órdenes ni facturas)
        if supplier_id:
            try:
                response = requests.delete(f"{BASE_URL}/api/suppliers/{supplier_id}")
                if response.status_code == 200:
                    cleanup_count += 1
                    print_info("✓ Proveedor eliminado")
            except:
                pass
        
        if cleanup_count > 0:
            print_success(f"Limpieza completada: {cleanup_count} elementos eliminados")
        else:
            print_info("No se eliminaron elementos (pueden tener dependencias)")
            
    except Exception as e:
        print_info(f"Error en limpieza: {str(e)}")

def run_comprehensive_tests():
    """Ejecutar suite completa de tests"""
    print("🚀 PROBANDO SGF - SISTEMA DE GESTIÓN FINANCIERA v2.0")
    print("=" * 70)
    print("🎯 Objetivo: Verificar funcionalidad completa de la Fase 1")
    print("=" * 70)
    
    start_time = time.time()
    test_results = {}
    
    # Ejecutar tests paso a paso
    test_results['health'] = test_health()
    if not test_results['health']:
        print("\n❌ Sistema no disponible. Abortando tests.")
        return
    
    supplier_id = test_suppliers()
    test_results['suppliers'] = supplier_id is not None
    
    po_id = test_purchase_orders(supplier_id)
    test_results['purchase_orders'] = po_id is not None
    
    advance_id = test_advances(po_id)
    test_results['advances'] = advance_id is not None
    
    invoice_id = test_invoices(supplier_id)
    test_results['invoices'] = invoice_id is not None
    
    payment_id = test_payments(invoice_id)
    test_results['payments'] = payment_id is not None
    
    shipment_id = test_shipments()
    test_results['shipments'] = shipment_id is not None
    
    test_results['reports'] = test_reports()
    test_results['dashboard'] = test_dashboard_api()
    
    # Resumen final
    elapsed_time = time.time() - start_time
    print("\n" + "=" * 70)
    print("📊 RESUMEN DE PRUEBAS COMPLETADAS")
    print("=" * 70)
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    success_rate = (passed_tests / total_tests) * 100
    
    print(f"\n📈 ESTADÍSTICAS:")
    print(f"   Tests pasados: {passed_tests}/{total_tests}")
    print(f"   Tasa de éxito: {success_rate:.1f}%")
    print(f"   Tiempo total: {elapsed_time:.2f} segundos")
    
    if success_rate >= 80:
        print(f"\n🎉 ¡EXCELENTE! La API está funcionando correctamente")
        print("✅ Sistema listo para uso en producción")
        
        # Preguntar por limpieza
        print(f"\n🧹 ¿Deseas limpiar los datos de prueba? (y/n)")
        try:
            choice = input().lower().strip()
            if choice in ['y', 'yes', 'sí', 's']:
                cleanup_test_data(supplier_id, po_id, invoice_id, shipment_id, advance_id, payment_id)
        except:
            print("ℹ️  Limpieza omitida")
            
    elif success_rate >= 60:
        print(f"\n⚠️  Sistema funcionando con algunos errores")
        print("🔧 Revisa los tests fallidos para depuración")
    else:
        print(f"\n❌ Sistema con errores críticos")
        print("🚨 Revisa la configuración y dependencias")
    
    print(f"\n💡 PRÓXIMOS PASOS:")
    print("   1. Revisar documentación: http://localhost:8000/docs")
    print("   2. Crear frontend básico para visualizar datos")
    print("   3. Deploy a Render + Netlify")
    print("   4. Implementar Fase 2 (SKUs y costeo)")

if __name__ == "__main__":
    try:
        run_comprehensive_tests()
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Tests interrumpidos por el usuario")
    except Exception as e:
        print(f"\n\n💥 Error inesperado: {str(e)}")
        print("🔧 Revisa que el servidor esté corriendo: python main.py")
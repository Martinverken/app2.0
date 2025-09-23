# =============================================
# test_connections.py - Verificar todas las conexiones
# =============================================

import asyncio
import json
from supabase import create_client, Client

# Configuración de Supabase (mismas credenciales que main.py)
SUPABASE_URL = "https://ponpwlirxrkqduyqhfhf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBvbnB3bGlyeHJrcWR1eXFoZmhmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc5NzM0MDcsImV4cCI6MjA3MzU0OTQwN30.mwPG4GjJQrNLpD9snPJgEYlMPsDLICyqSl8U8xJqMoA"

def print_separator(title):
    print("\n" + "="*50)
    print(f"🔍 {title}")
    print("="*50)

def test_supabase_connection():
    """Probar conexión directa con Supabase"""
    print_separator("PRUEBA 1: Conexión Directa con Supabase")
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Probar obtener proveedores
        result = supabase.table('proveedores').select('*').execute()
        
        print(f"✅ Conexión exitosa con Supabase")
        print(f"📊 Proveedores encontrados: {len(result.data)}")
        
        if result.data:
            print(f"📋 Primer proveedor: {result.data[0]['nombre']}")
        
        # Probar todas las tablas
        tables = ['proveedores', 'ordenes_compra', 'embarques', 'facturas', 
                 'costos_fijos_recurrentes', 'flujo_caja_movimientos']
        
        print(f"\n📈 Estado de todas las tablas:")
        for table in tables:
            try:
                count_result = supabase.table(table).select("count", count="exact").execute()
                print(f"   {table}: {count_result.count} registros")
            except Exception as e:
                print(f"   ❌ {table}: Error - {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
        return False

def test_api_endpoints():
    """Probar endpoints de la API con requests"""
    print_separator("PRUEBA 2: Endpoints de la API")
    
    try:
        import requests
    except ImportError:
        print("⚠️  Instalando requests...")
        import subprocess
        subprocess.check_call(['pip', 'install', 'requests'])
        import requests
    
    base_url = "http://localhost:8000"
    
    endpoints = [
        ("GET", "/", "Página principal"),
        ("GET", "/health", "Estado de salud"),
        ("GET", "/api/proveedores", "Lista de proveedores"),
        ("GET", "/api/stats", "Estadísticas"),
    ]
    
    for method, endpoint, description in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {description}: OK ({response.status_code})")
                
                # Mostrar datos si es JSON
                try:
                    data = response.json()
                    if endpoint == "/api/proveedores" and 'data' in data:
                        print(f"   📊 Proveedores: {len(data['data'])}")
                    elif endpoint == "/api/stats" and 'estadisticas' in data:
                        stats = data['estadisticas']
                        print(f"   📈 Stats: P:{stats['proveedores']} O:{stats['ordenes_compra']} E:{stats['embarques']} F:{stats['facturas']}")
                except:
                    pass
            else:
                print(f"❌ {description}: Error {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {description}: No se puede conectar (¿Está corriendo el servidor?)")
        except Exception as e:
            print(f"❌ {description}: {str(e)}")

def test_create_proveedor():
    """Probar crear un proveedor de prueba"""
    print_separator("PRUEBA 3: Crear Proveedor de Prueba")
    
    try:
        import requests
        
        # Datos del proveedor de prueba
        proveedor_data = {
            "nombre": "Proveedor Prueba Conexión",
            "pais_origen": "Chile",
            "contacto": "prueba@conexion.com"
        }
        
        # Intentar crear
        response = requests.post(
            "http://localhost:8000/api/proveedores",
            json=proveedor_data,
            timeout=5
        )
        
        if response.status_code == 201:
            result = response.json()
            print(f"✅ Proveedor creado exitosamente")
            print(f"📝 ID: {result['data']['id']}")
            print(f"📝 Nombre: {result['data']['nombre']}")
            
            # Intentar eliminarlo
            proveedor_id = result['data']['id']
            delete_response = requests.delete(
                f"http://localhost:8000/api/proveedores/{proveedor_id}",
                timeout=5
            )
            
            if delete_response.status_code == 200:
                print(f"✅ Proveedor eliminado exitosamente (limpieza)")
            else:
                print(f"⚠️  Proveedor creado pero no se pudo eliminar")
                
        else:
            print(f"❌ Error al crear proveedor: {response.status_code}")
            print(f"   Respuesta: {response.text}")
            
    except Exception as e:
        print(f"❌ Error en prueba de creación: {str(e)}")

def test_frontend_connection():
    """Verificar si el frontend puede conectarse"""
    print_separator("PRUEBA 4: Preparación Frontend")
    
    print("📁 Verificando archivos del frontend...")
    
    import os
    
    # Verificar que existe la carpeta frontend
    if os.path.exists('frontend'):
        print("✅ Carpeta 'frontend' existe")
        
        # Verificar que existe index.html
        if os.path.exists('frontend/index.html'):
            print("✅ Archivo 'index.html' existe")
            
            # Verificar que tiene la URL correcta de la API
            with open('frontend/index.html', 'r') as f:
                content = f.read()
                if 'localhost:8000' in content:
                    print("✅ Frontend configurado para conectar a localhost:8000")
                else:
                    print("⚠️  Revisar URL de API en el frontend")
        else:
            print("❌ Archivo 'index.html' no encontrado")
    else:
        print("❌ Carpeta 'frontend' no encontrada")
    
    print("\n📋 Para probar el frontend:")
    print("1. Abre 'frontend/index.html' en tu navegador")
    print("2. Abre las herramientas de desarrollador (F12)")
    print("3. Ve a la pestaña 'Console' para ver errores")
    print("4. Ve a la pestaña 'Network' para ver las peticiones HTTP")

def run_all_tests():
    """Ejecutar todas las pruebas"""
    print("🚀 INICIANDO PRUEBAS DE CONEXIÓN COMPLETAS")
    print("=" * 60)
    
    # Prueba 1: Supabase
    supabase_ok = test_supabase_connection()
    
    # Prueba 2: API
    test_api_endpoints()
    
    # Prueba 3: CRUD
    test_create_proveedor()
    
    # Prueba 4: Frontend
    test_frontend_connection()
    
    # Resumen final
    print_separator("RESUMEN DE CONEXIONES")
    
    if supabase_ok:
        print("✅ Base de datos: CONECTADA")
    else:
        print("❌ Base de datos: ERROR")
    
    print("✅ Backend: Revisar mensajes arriba")
    print("✅ Frontend: Revisar en navegador")
    
    print("\n🎯 PRÓXIMOS PASOS:")
    print("1. Si todo está ✅, tu sistema está listo")
    print("2. Si hay ❌, revisa los errores específicos")
    print("3. Abre http://localhost:8000/docs para probar la API")
    print("4. Abre frontend/index.html para probar la interfaz")

if __name__ == "__main__":
    run_all_tests()
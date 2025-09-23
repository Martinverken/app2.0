import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

def print_step(step, message):
    print(f"\n🔍 PASO {step}: {message}")
    print("-" * 50)

def test_env_variables():
    print_step(1, "Verificando variables de entorno")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if supabase_url and supabase_key:
        print("✅ Variables de entorno cargadas correctamente")
        print(f"📍 URL: {supabase_url[:30]}...")
        return True
    else:
        print("❌ Variables de entorno no encontradas")
        return False

def test_backend_local():
    print_step(2, "Probando conexión al backend local")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend respondiendo correctamente")
            data = response.json()
            print(f"📊 Status: {data.get('status', 'N/A')}")
            return True
    except requests.exceptions.ConnectionError:
        print("❌ Backend no está corriendo")
        print("💡 Ejecuta: uvicorn main:app --reload")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_database_operations():
    print_step(3, "Probando operaciones de base de datos")
    
    try:
        # Probar GET proveedores
        response = requests.get("http://localhost:8000/api/proveedores")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Proveedores: {data.get('total', 0)} encontrados")
            
            # Probar stats
            response = requests.get("http://localhost:8000/api/stats")
            if response.status_code == 200:
                stats = response.json()
                print("✅ Estadísticas obtenidas correctamente")
                return True
    except Exception as e:
        print(f"❌ Error en operaciones de BD: {str(e)}")
        return False

def run_all_tests():
    print("🚀 EJECUTANDO PRUEBAS LOCALES")
    print("=" * 60)
    
    results = []
    results.append(test_env_variables())
    results.append(test_backend_local())
    results.append(test_database_operations())
    
    print("\n" + "=" * 60)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    if all(results):
        print("✅ TODAS LAS PRUEBAS PASARON")
        print("🚀 ¡Listo para hacer commit!")
    else:
        print("❌ ALGUNAS PRUEBAS FALLARON")
        print("🔧 Revisa los errores antes de continuar")
    
    return all(results)

if __name__ == "__main__":
    run_all_tests()
# test_connection.py - Prueba rápida de conexión
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_connection():
    try:
        from supabase import create_client
        
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        print("🧪 PROBANDO CONEXIÓN A SUPABASE")
        print("=" * 40)
        print(f"🔗 URL: {url[:30]}...")
        print(f"🔑 Key: {key[:30]}...")
        
        supabase = create_client(url, key)
        result = supabase.table('suppliers').select('nombre').limit(5).execute()
        
        print(f"\n✅ CONEXIÓN EXITOSA!")
        print(f"📊 Proveedores encontrados: {len(result.data)}")
        
        if result.data:
            print("📋 Lista de proveedores:")
            for i, supplier in enumerate(result.data, 1):
                print(f"   {i}. {supplier['nombre']}")
        else:
            print("⚠️  No se encontraron proveedores")
            
        return True
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\n🔧 Verifica:")
        print("   1. Que tu .env esté en la carpeta correcta")
        print("   2. Que las credenciales sean correctas") 
        print("   3. Que las tablas estén creadas en Supabase")
        return False

if __name__ == "__main__":
    success = test_connection()
    if success:
        print(f"\n🎉 ¡Todo listo para continuar!")
    else:
        print(f"\n🚨 Arregla los errores antes de continuar")
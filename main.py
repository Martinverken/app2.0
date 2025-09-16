# =============================================
# main.py - Backend con FastAPI y Supabase
# =============================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
from typing import Optional

# Configuración de Supabase (TUS CREDENCIALES)
SUPABASE_URL = "https://ponpwlirxrkqduyqhfhf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBvbnB3bGlyeHJrcWR1eXFoZmhmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc5NzM0MDcsImV4cCI6MjA3MzU0OTQwN30.mwPG4GjJQrNLpD9snPJgEYlMPsDLICyqSl8U8xJqMoA"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Crear la aplicación FastAPI
app = FastAPI(title="Sistema de Inventario", version="1.0.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos de datos
class ProveedorCreate(BaseModel):
    nombre: str
    pais_origen: str
    contacto: Optional[str] = None

class ProveedorUpdate(BaseModel):
    nombre: Optional[str] = None
    pais_origen: Optional[str] = None
    contacto: Optional[str] = None

# =============================================
# RUTAS BÁSICAS
# =============================================

@app.get("/")
async def root():
    return {"message": "¡Hola! Tu API del Sistema de Inventario está funcionando!"}

@app.get("/health")
async def health_check():
    """Verificar que la conexión con Supabase funciona"""
    try:
        result = supabase.table('proveedores').select("count", count="exact").execute()
        return {
            "status": "✅ Todo funcionando perfecto", 
            "database": "✅ Conectado a Supabase",
            "proveedores_en_db": result.count
        }
    except Exception as e:
        return {"status": "❌ Error", "message": str(e)}

# =============================================
# RUTAS DE PROVEEDORES
# =============================================

@app.get("/api/proveedores")
async def get_proveedores():
    """Obtener todos los proveedores"""
    try:
        result = supabase.table('proveedores').select("*").order('created_at', desc=True).execute()
        return {
            "success": True,
            "data": result.data,
            "total": len(result.data),
            "message": f"Se encontraron {len(result.data)} proveedores"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener proveedores: {str(e)}")

@app.get("/api/proveedores/{proveedor_id}")
async def get_proveedor(proveedor_id: str):
    """Obtener un proveedor específico por ID"""
    try:
        result = supabase.table('proveedores').select("*").eq('id', proveedor_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        return {
            "success": True,
            "data": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener proveedor: {str(e)}")

@app.post("/api/proveedores")
async def create_proveedor(proveedor: ProveedorCreate):
    """Crear un nuevo proveedor"""
    try:
        # Validar datos
        if not proveedor.nombre.strip():
            raise HTTPException(status_code=400, detail="El nombre del proveedor es requerido")
        
        if not proveedor.pais_origen.strip():
            raise HTTPException(status_code=400, detail="El país de origen es requerido")
        
        # Crear el proveedor
        result = supabase.table('proveedores').insert({
            "nombre": proveedor.nombre.strip(),
            "pais_origen": proveedor.pais_origen.strip(),
            "contacto": proveedor.contacto.strip() if proveedor.contacto else None
        }).execute()
        
        return {
            "success": True,
            "message": f"✅ Proveedor '{proveedor.nombre}' creado exitosamente",
            "data": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear proveedor: {str(e)}")

@app.put("/api/proveedores/{proveedor_id}")
async def update_proveedor(proveedor_id: str, proveedor: ProveedorUpdate):
    """Actualizar un proveedor existente"""
    try:
        # Preparar datos para actualizar
        update_data = {}
        if proveedor.nombre is not None:
            update_data["nombre"] = proveedor.nombre.strip()
        if proveedor.pais_origen is not None:
            update_data["pais_origen"] = proveedor.pais_origen.strip()
        if proveedor.contacto is not None:
            update_data["contacto"] = proveedor.contacto.strip() if proveedor.contacto else None
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No hay datos para actualizar")
        
        # Actualizar en Supabase
        result = supabase.table('proveedores').update(update_data).eq('id', proveedor_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        
        return {
            "success": True,
            "message": "✅ Proveedor actualizado exitosamente",
            "data": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar proveedor: {str(e)}")

@app.delete("/api/proveedores/{proveedor_id}")
async def delete_proveedor(proveedor_id: str):
    """Eliminar un proveedor"""
    try:
        # Verificar si tiene órdenes de compra
        ordenes_result = supabase.table('ordenes_compra').select("id").eq('proveedor_id', proveedor_id).limit(1).execute()
        
        if ordenes_result.data:
            raise HTTPException(
                status_code=400, 
                detail="❌ No se puede eliminar: el proveedor tiene órdenes de compra asociadas"
            )
        
        # Eliminar el proveedor
        result = supabase.table('proveedores').delete().eq('id', proveedor_id).execute()
        
        return {
            "success": True,
            "message": "✅ Proveedor eliminado exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar proveedor: {str(e)}")

# =============================================
# INFORMACIÓN DE LA API
# =============================================

@app.get("/api/stats")
async def get_stats():
    """Obtener estadísticas del sistema"""
    try:
        proveedores = supabase.table('proveedores').select("count", count="exact").execute()
        ordenes = supabase.table('ordenes_compra').select("count", count="exact").execute()
        embarques = supabase.table('embarques').select("count", count="exact").execute()
        facturas = supabase.table('facturas').select("count", count="exact").execute()
        
        return {
            "success": True,
            "sistema": "Sistema de Inventario",
            "estadisticas": {
                "proveedores": proveedores.count,
                "ordenes_compra": ordenes.count,
                "embarques": embarques.count,
                "facturas": facturas.count
            },
            "mensaje": "Estadísticas actualizadas"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas: {str(e)}")

# =============================================
# EJECUTAR LA APLICACIÓN
# =============================================

if __name__ == "__main__":
    import uvicorn
    print("\n🚀 ¡Iniciando tu Sistema de Inventario!")
    print("📊 Documentación interactiva: http://localhost:8000/docs")
    print("🔧 API funcionando en: http://localhost:8000")
    print("💾 Conectado a tu base de datos Supabase")
    print("✨ ¡Todo listo para usar!\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
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


# =============================================
# AGREGAR ESTO A main.py - ÓRDENES DE COMPRA
# =============================================

# Agregar estos imports al inicio de main.py (después de los existentes)
from datetime import date
from typing import Optional

# Agregar estos modelos después de los modelos de Proveedor
class OrdenCompraCreate(BaseModel):
    numero_orden: str
    fecha: Optional[date] = None
    marca: str  # 'Verken' o 'Kaut'
    proveedor_id: str
    valor_usd: float
    monto_anticipo_pagado: Optional[float] = 0
    fecha_pago_anticipo: Optional[date] = None
    usuario_pago_anticipo: Optional[str] = None
    notas_anticipo: Optional[str] = None

class OrdenCompraUpdate(BaseModel):
    numero_orden: Optional[str] = None
    fecha: Optional[date] = None
    marca: Optional[str] = None
    proveedor_id: Optional[str] = None
    valor_usd: Optional[float] = None
    monto_anticipo_pagado: Optional[float] = None
    fecha_pago_anticipo: Optional[date] = None
    usuario_pago_anticipo: Optional[str] = None
    notas_anticipo: Optional[str] = None

# =============================================
# ENDPOINTS DE ÓRDENES DE COMPRA
# =============================================

@app.get("/api/ordenes")
async def get_ordenes():
    """Obtener todas las órdenes de compra con información del proveedor"""
    try:
        result = supabase.table('ordenes_compra').select("""
            *,
            proveedores!ordenes_compra_proveedor_id_fkey (
                id,
                nombre,
                pais_origen
            )
        """).order('created_at', desc=True).execute()
        
        return {
            "success": True,
            "data": result.data,
            "total": len(result.data),
            "message": f"Se encontraron {len(result.data)} órdenes de compra"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener órdenes: {str(e)}")

@app.get("/api/ordenes/{orden_id}")
async def get_orden(orden_id: str):
    """Obtener una orden de compra específica por ID"""
    try:
        result = supabase.table('ordenes_compra').select("""
            *,
            proveedores!ordenes_compra_proveedor_id_fkey (
                id,
                nombre,
                pais_origen
            )
        """).eq('id', orden_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
        
        return {
            "success": True,
            "data": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener orden: {str(e)}")

@app.post("/api/ordenes")
async def create_orden(orden: OrdenCompraCreate):
    """Crear una nueva orden de compra"""
    try:
        # Validaciones
        if not orden.numero_orden.strip():
            raise HTTPException(status_code=400, detail="El número de orden es requerido")
        
        if orden.marca not in ["Verken", "Kaut"]:
            raise HTTPException(status_code=400, detail="La marca debe ser 'Verken' o 'Kaut'")
        
        if orden.valor_usd <= 0:
            raise HTTPException(status_code=400, detail="El valor debe ser mayor a 0")
        
        # Verificar que el proveedor existe
        proveedor_result = supabase.table('proveedores').select('id').eq('id', orden.proveedor_id).execute()
        if not proveedor_result.data:
            raise HTTPException(status_code=400, detail="El proveedor especificado no existe")
        
        # Verificar que el número de orden no existe
        orden_existente = supabase.table('ordenes_compra').select('id').eq('numero_orden', orden.numero_orden).execute()
        if orden_existente.data:
            raise HTTPException(status_code=400, detail="Ya existe una orden con ese número")
        
        # Preparar datos para insertar
        orden_data = {
            "numero_orden": orden.numero_orden.strip(),
            "fecha": orden.fecha.isoformat() if orden.fecha else None,
            "marca": orden.marca,
            "proveedor_id": orden.proveedor_id,
            "valor_usd": orden.valor_usd,
            "monto_anticipo_pagado": orden.monto_anticipo_pagado or 0,
            "fecha_pago_anticipo": orden.fecha_pago_anticipo.isoformat() if orden.fecha_pago_anticipo else None,
            "usuario_pago_anticipo": orden.usuario_pago_anticipo.strip() if orden.usuario_pago_anticipo else None,
            "notas_anticipo": orden.notas_anticipo.strip() if orden.notas_anticipo else None
        }
        
        # Crear la orden
        result = supabase.table('ordenes_compra').insert(orden_data).execute()
        
        return {
            "success": True,
            "message": f"✅ Orden de compra '{orden.numero_orden}' creada exitosamente",
            "data": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear orden: {str(e)}")

@app.put("/api/ordenes/{orden_id}")
async def update_orden(orden_id: str, orden: OrdenCompraUpdate):
    """Actualizar una orden de compra existente"""
    try:
        # Preparar datos para actualizar (solo los campos que no son None)
        update_data = {}
        
        if orden.numero_orden is not None:
            # Verificar que el nuevo número no existe en otra orden
            orden_existente = supabase.table('ordenes_compra').select('id').eq('numero_orden', orden.numero_orden).neq('id', orden_id).execute()
            if orden_existente.data:
                raise HTTPException(status_code=400, detail="Ya existe otra orden con ese número")
            update_data["numero_orden"] = orden.numero_orden.strip()
        
        if orden.fecha is not None:
            update_data["fecha"] = orden.fecha.isoformat() if orden.fecha else None
            
        if orden.marca is not None:
            if orden.marca not in ["Verken", "Kaut"]:
                raise HTTPException(status_code=400, detail="La marca debe ser 'Verken' o 'Kaut'")
            update_data["marca"] = orden.marca
            
        if orden.proveedor_id is not None:
            # Verificar que el proveedor existe
            proveedor_result = supabase.table('proveedores').select('id').eq('id', orden.proveedor_id).execute()
            if not proveedor_result.data:
                raise HTTPException(status_code=400, detail="El proveedor especificado no existe")
            update_data["proveedor_id"] = orden.proveedor_id
            
        if orden.valor_usd is not None:
            if orden.valor_usd <= 0:
                raise HTTPException(status_code=400, detail="El valor debe ser mayor a 0")
            update_data["valor_usd"] = orden.valor_usd
            
        if orden.monto_anticipo_pagado is not None:
            update_data["monto_anticipo_pagado"] = orden.monto_anticipo_pagado
            
        if orden.fecha_pago_anticipo is not None:
            update_data["fecha_pago_anticipo"] = orden.fecha_pago_anticipo.isoformat() if orden.fecha_pago_anticipo else None
            
        if orden.usuario_pago_anticipo is not None:
            update_data["usuario_pago_anticipo"] = orden.usuario_pago_anticipo.strip() if orden.usuario_pago_anticipo else None
            
        if orden.notas_anticipo is not None:
            update_data["notas_anticipo"] = orden.notas_anticipo.strip() if orden.notas_anticipo else None
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No hay datos para actualizar")
        
        # Actualizar en Supabase
        result = supabase.table('ordenes_compra').update(update_data).eq('id', orden_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
        
        return {
            "success": True,
            "message": "✅ Orden de compra actualizada exitosamente",
            "data": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar orden: {str(e)}")

@app.delete("/api/ordenes/{orden_id}")
async def delete_orden(orden_id: str):
    """Eliminar una orden de compra"""
    try:
        # Verificar si la orden tiene facturas asociadas
        facturas_result = supabase.table('facturas').select("id").eq('orden_compra_id', orden_id).limit(1).execute()
        
        if facturas_result.data:
            raise HTTPException(
                status_code=400, 
                detail="❌ No se puede eliminar: la orden tiene facturas asociadas"
            )
        
        # Eliminar la orden
        result = supabase.table('ordenes_compra').delete().eq('id', orden_id).execute()
        
        return {
            "success": True,
            "message": "✅ Orden de compra eliminada exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar orden: {str(e)}")

# =============================================
# ENDPOINT ADICIONAL: RESUMEN DE ÓRDENES
# =============================================

@app.get("/api/ordenes/stats/resumen")
async def get_ordenes_resumen():
    """Obtener resumen estadístico de órdenes de compra"""
    try:
        # Obtener todas las órdenes
        ordenes = supabase.table('ordenes_compra').select('*').execute()
        
        if not ordenes.data:
            return {
                "success": True,
                "data": {
                    "total_ordenes": 0,
                    "total_valor_usd": 0,
                    "total_anticipos": 0,
                    "por_marca": {"Verken": 0, "Kaut": 0},
                    "por_estado": {}
                }
            }
        
        # Calcular estadísticas
        total_ordenes = len(ordenes.data)
        total_valor_usd = sum(orden['valor_usd'] for orden in ordenes.data)
        total_anticipos = sum(orden['monto_anticipo_pagado'] or 0 for orden in ordenes.data)
        
        # Por marca
        por_marca = {"Verken": 0, "Kaut": 0}
        for orden in ordenes.data:
            if orden['marca'] in por_marca:
                por_marca[orden['marca']] += 1
        
        # Por estado
        por_estado = {}
        for orden in ordenes.data:
            estado = orden.get('estado', 'pendiente')
            por_estado[estado] = por_estado.get(estado, 0) + 1
        
        return {
            "success": True,
            "data": {
                "total_ordenes": total_ordenes,
                "total_valor_usd": round(total_valor_usd, 2),
                "total_anticipos": round(total_anticipos, 2),
                "por_marca": por_marca,
                "por_estado": por_estado
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen: {str(e)}")

# =============================================
# ACTUALIZAR ENDPOINT DE STATS GENERAL
# =============================================

# Actualizar la función get_stats existente para incluir órdenes
@app.get("/api/stats")
async def get_stats():
    """Obtener estadísticas del sistema (ACTUALIZADA)"""
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
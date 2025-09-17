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
    allow_origins=[
        "*",
        "https://timely-pasca-ade359.netlify.app",
        "https://68c8b28a01bd92ae6f8486ac--singular-crumble-9a1b9d.netlify.app",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
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
# MODELOS PARA EMBARQUES
# =============================================

class EmbarqueCreate(BaseModel):
    numero_embarque: str
    fecha_embarque: Optional[date] = None
    fecha_llegada_estimada: Optional[date] = None
    fecha_llegada_real: Optional[date] = None

class EmbarqueUpdate(BaseModel):
    numero_embarque: Optional[str] = None
    fecha_embarque: Optional[date] = None
    fecha_llegada_estimada: Optional[date] = None
    fecha_llegada_real: Optional[date] = None

# =============================================
# ENDPOINTS DE EMBARQUES
# =============================================

@app.get("/api/embarques")
async def get_embarques():
    """Obtener todos los embarques"""
    try:
        result = supabase.table('embarques').select("*").order('created_at', desc=True).execute()
        
        return {
            "success": True,
            "data": result.data,
            "total": len(result.data),
            "message": f"Se encontraron {len(result.data)} embarques"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener embarques: {str(e)}")

@app.post("/api/embarques")
async def create_embarque(embarque: EmbarqueCreate):
    """Crear un nuevo embarque"""
    try:
        # Validaciones
        if not embarque.numero_embarque.strip():
            raise HTTPException(status_code=400, detail="El número de embarque es requerido")
        
        # Verificar que el número no existe
        embarque_existente = supabase.table('embarques').select('id').eq('numero_embarque', embarque.numero_embarque).execute()
        if embarque_existente.data:
            raise HTTPException(status_code=400, detail="Ya existe un embarque con ese número")
        
        # Preparar datos
        embarque_data = {
            "numero_embarque": embarque.numero_embarque.strip(),
            "fecha_embarque": embarque.fecha_embarque.isoformat() if embarque.fecha_embarque else None,
            "fecha_llegada_estimada": embarque.fecha_llegada_estimada.isoformat() if embarque.fecha_llegada_estimada else None,
            "fecha_llegada_real": embarque.fecha_llegada_real.isoformat() if embarque.fecha_llegada_real else None,
            "estado": "en_transito"
        }
        
        # Crear embarque
        result = supabase.table('embarques').insert(embarque_data).execute()
        
        return {
            "success": True,
            "message": f"✅ Embarque '{embarque.numero_embarque}' creado exitosamente",
            "data": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear embarque: {str(e)}")

# =============================================
# MODELOS PARA COSTOS FIJOS
# =============================================

# Actualizar modelo de CostoFijoCreate
class CostoFijoCreate(BaseModel):
    nombre_costo: str
    monto: float
    moneda: str = "CLP"  # Agregar este campo
    frecuencia: str
    fecha_inicio: date
    categoria: Optional[str] = None
    activo: Optional[bool] = True



# =============================================
# ENDPOINTS DE COSTOS FIJOS
# =============================================

@app.get("/api/costos-fijos")
async def get_costos_fijos():
    """Obtener todos los costos fijos"""
    try:
        result = supabase.table('costos_fijos_recurrentes').select("*").order('created_at', desc=True).execute()
        
        return {
            "success": True,
            "data": result.data,
            "total": len(result.data),
            "message": f"Se encontraron {len(result.data)} costos fijos"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener costos fijos: {str(e)}")

@app.post("/api/costos-fijos")
async def create_costo_fijo(costo: CostoFijoCreate):
    """Crear un nuevo costo fijo"""
    try:
        # Validaciones
        if not costo.nombre_costo.strip():
            raise HTTPException(status_code=400, detail="El nombre del costo es requerido")
        
        if costo.monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")

        if costo.moneda not in ["USD", "CLP"]:
            raise HTTPException(status_code=400, detail="La moneda debe ser USD o CLP")
            
        if costo.frecuencia not in ["mensual", "trimestral", "anual"]:
            raise HTTPException(status_code=400, detail="La frecuencia debe ser mensual, trimestral o anual")
        
        # Crear costo fijo
        costo_data = {
            "nombre_costo": costo.nombre_costo.strip(),
            "monto": costo.monto,
            "frecuencia": costo.frecuencia,
            "fecha_inicio": costo.fecha_inicio.isoformat(),
            "categoria": costo.categoria.strip() if costo.categoria else None,
            "moneda": costo.moneda,
            "activo": costo.activo if costo.activo is not None else True
            
        }
        
        result = supabase.table('costos_fijos_recurrentes').insert(costo_data).execute()
        
        return {
            "success": True,
            "message": f"✅ Costo fijo '{costo.nombre_costo}' creado exitosamente",
            "data": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear costo fijo: {str(e)}")

# =============================================
# MODELOS PARA OTROS COSTOS
# =============================================

# Actualizar modelo de OtroCostoCreate
class OtroCostoCreate(BaseModel):
    fecha: date
    concepto: str
    monto: float
    moneda: str = "CLP"  # Agregar este campo
    categoria: Optional[str] = None
    notas: Optional[str] = None

# =============================================
# ENDPOINTS DE OTROS COSTOS
# =============================================

@app.get("/api/otros-costos")
async def get_otros_costos():
    """Obtener todos los otros costos"""
    try:
        result = supabase.table('flujo_caja_movimientos').select("*").eq('categoria', 'extraordinario').order('fecha', desc=True).execute()
        
        return {
            "success": True,
            "data": result.data,
            "total": len(result.data),
            "message": f"Se encontraron {len(result.data)} otros costos"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener otros costos: {str(e)}")

@app.post("/api/otros-costos")
async def create_otro_costo(costo: OtroCostoCreate):
    """Crear un nuevo otro costo"""
    try:
        # Validaciones
        if not costo.concepto.strip():
            raise HTTPException(status_code=400, detail="El concepto es requerido")

        if costo.moneda not in ["USD", "CLP"]:
            raise HTTPException(status_code=400, detail="La moneda debe ser USD o CLP")
        
        if costo.monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor a 0")
        
        # Crear movimiento en flujo de caja
        costo_data = {
            "año": costo.fecha.year,
            "mes": costo.fecha.month,
            "fecha": costo.fecha.isoformat(),
            "tipo_movimiento": "egreso",
            "categoria": "extraordinario",
            "concepto": costo.concepto.strip(),
            "monto": costo.monto,
            "moneda": costo.moneda,
            "notas": costo.notas.strip() if costo.notas else None
        }
        
        result = supabase.table('flujo_caja_movimientos').insert(costo_data).execute()
        
        return {
            "success": True,
            "message": f"✅ Costo '{costo.concepto}' registrado exitosamente",
            "data": result.data[0]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear otro costo: {str(e)}")

# =============================================
# MODELOS ACTUALIZADOS PARA FACTURAS CON VENCIMIENTOS
# =============================================

from typing import List

class VencimientoCreate(BaseModel):
    numero_cuota: int  # 1, 2, o 3
    fecha_vencimiento: date
    monto_cuota: float

class FacturaCreateConVencimientos(BaseModel):
    numero_factura: str
    embarque_id: str
    orden_compra_id: Optional[str] = None
    monto_base: float
    moneda: str
    iva: Optional[float] = 0
    monto_total: float
    tipo_factura: str
    concepto: Optional[str] = None
    proveedor_servicio: Optional[str] = None
    vencimientos: List[VencimientoCreate]

# =============================================
# REEMPLAZAR ENDPOINTS DE FACTURAS EXISTENTES
# =============================================

@app.get("/api/facturas")
async def get_facturas_con_vencimientos():
    """Obtener todas las facturas con sus vencimientos"""
    try:
        # Obtener facturas
        facturas_result = supabase.table('facturas').select("""
            *,
            embarques!facturas_embarque_id_fkey (
                id,
                numero_embarque
            ),
            ordenes_compra!facturas_orden_compra_id_fkey (
                id,
                numero_orden,
                marca
            )
        """).order('created_at', desc=True).execute()
        
        # Obtener vencimientos
        vencimientos_result = supabase.table('facturas_vencimientos').select("*").order('numero_cuota').execute()
        
        # Combinar datos
        facturas_con_vencimientos = []
        for factura in facturas_result.data:
            vencimientos = [v for v in vencimientos_result.data if v['factura_id'] == factura['id']]
            factura['vencimientos'] = vencimientos
            facturas_con_vencimientos.append(factura)
        
        return {
            "success": True,
            "data": facturas_con_vencimientos,
            "total": len(facturas_con_vencimientos)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener facturas: {str(e)}")

@app.post("/api/facturas")
async def create_factura_con_vencimientos(factura: FacturaCreateConVencimientos):
    """Crear una nueva factura con sus vencimientos"""
    try:
        # Validaciones básicas
        if not factura.numero_factura.strip():
            raise HTTPException(status_code=400, detail="El número de factura es requerido")
        
        if not factura.embarque_id:
            raise HTTPException(status_code=400, detail="El embarque es requerido")
            
        if factura.moneda not in ["USD", "CLP"]:
            raise HTTPException(status_code=400, detail="La moneda debe ser USD o CLP")
            
        if factura.tipo_factura not in ["producto", "servicio"]:
            raise HTTPException(status_code=400, detail="El tipo debe ser 'producto' o 'servicio'")
        
        # Validar vencimientos
        if not factura.vencimientos or len(factura.vencimientos) == 0:
            raise HTTPException(status_code=400, detail="Debe tener al menos un vencimiento")
            
        if len(factura.vencimientos) > 3:
            raise HTTPException(status_code=400, detail="Máximo 3 vencimientos permitidos")
        
        # Validar que la suma de cuotas = monto total
        suma_cuotas = sum(v.monto_cuota for v in factura.vencimientos)
        if abs(suma_cuotas - factura.monto_total) > 0.01:  # Tolerancia de 1 centavo
            raise HTTPException(status_code=400, detail=f"La suma de cuotas ({suma_cuotas}) debe igualar el monto total ({factura.monto_total})")
        
        # Verificar números de cuota únicos y válidos
        numeros_cuota = [v.numero_cuota for v in factura.vencimientos]
        if len(set(numeros_cuota)) != len(numeros_cuota):
            raise HTTPException(status_code=400, detail="Los números de cuota deben ser únicos")
            
        for num in numeros_cuota:
            if num not in [1, 2, 3]:
                raise HTTPException(status_code=400, detail="Los números de cuota deben ser 1, 2 o 3")
        
        # Verificar que el embarque existe
        embarque_result = supabase.table('embarques').select('id').eq('id', factura.embarque_id).execute()
        if not embarque_result.data:
            raise HTTPException(status_code=400, detail="El embarque especificado no existe")
        
        # Si tiene orden de compra, verificar que existe
        if factura.orden_compra_id:
            orden_result = supabase.table('ordenes_compra').select('id').eq('id', factura.orden_compra_id).execute()
            if not orden_result.data:
                raise HTTPException(status_code=400, detail="La orden de compra especificada no existe")
        
        # Verificar que el número no existe
        factura_existente = supabase.table('facturas').select('id').eq('numero_factura', factura.numero_factura).execute()
        if factura_existente.data:
            raise HTTPException(status_code=400, detail="Ya existe una factura con ese número")
        
        # Crear factura principal
        factura_data = {
            "numero_factura": factura.numero_factura.strip(),
            "embarque_id": factura.embarque_id,
            "orden_compra_id": factura.orden_compra_id,
            "monto_base": factura.monto_base,
            "moneda": factura.moneda,
            "iva": factura.iva,
            "monto_total": factura.monto_total,
            "tipo_factura": factura.tipo_factura,
            "concepto": factura.concepto.strip() if factura.concepto else None,
            "proveedor_servicio": factura.proveedor_servicio.strip() if factura.proveedor_servicio else None,
            "estado": "pendiente",
        }
        
        factura_result = supabase.table('facturas').insert(factura_data).execute()
        factura_id = factura_result.data[0]['id']
        
        # Crear vencimientos
        vencimientos_data = []
        for venc in factura.vencimientos:
            vencimientos_data.append({
                "factura_id": factura_id,
                "numero_cuota": venc.numero_cuota,
                "fecha_vencimiento": venc.fecha_vencimiento.isoformat(),
                "monto_cuota": venc.monto_cuota,
                "estado": "pendiente"
            })
        
        vencimientos_result = supabase.table('facturas_vencimientos').insert(vencimientos_data).execute()
        
        return {
            "success": True,
            "message": f"✅ Factura '{factura.numero_factura}' creada con {len(factura.vencimientos)} vencimientos",
            "data": {
                "factura": factura_result.data[0],
                "vencimientos": vencimientos_result.data
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear factura: {str(e)}")

@app.get("/api/facturas/{factura_id}/vencimientos")
async def get_vencimientos_factura(factura_id: str):
    """Obtener los vencimientos de una factura específica"""
    try:
        result = supabase.table('facturas_vencimientos').select("*").eq('factura_id', factura_id).order('numero_cuota').execute()
        
        return {
            "success": True,
            "data": result.data,
            "total": len(result.data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener vencimientos: {str(e)}")

@app.delete("/api/facturas/{factura_id}")
async def delete_factura_con_vencimientos(factura_id: str):
    """Eliminar una factura y sus vencimientos"""
    try:
        # Los vencimientos se eliminan automáticamente por ON DELETE CASCADE
        result = supabase.table('facturas').delete().eq('id', factura_id).execute()
        
        return {
            "success": True,
            "message": "✅ Factura y sus vencimientos eliminados exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar factura: {str(e)}")

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
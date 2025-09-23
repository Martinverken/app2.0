# =============================================
# NUEVO BACKEND MODULAR - FASE 1 FINANZAS CORE
# Estructura de carpetas propuesta:
#
# backend/
# ├── main.py (este archivo)
# ├── config.py
# ├── database.py
# ├── models/
# │   ├── __init__.py
# │   ├── supplier.py
# │   ├── purchase_order.py
# │   ├── invoice.py
# │   └── shipment.py
# ├── routers/
# │   ├── __init__.py
# │   ├── suppliers.py
# │   ├── purchase_orders.py
# │   ├── invoices.py
# │   ├── shipments.py
# │   └── reports.py
# └── services/
#     ├── __init__.py
#     ├── supplier_service.py
#     ├── invoice_service.py
#     └── advance_service.py
# =============================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

# Configuración
from config import settings
from database import init_database

# Routers
from routers import suppliers, purchase_orders, invoices, shipments, advances, reports

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando SGF - Sistema de Gestión Financiera")
    print("🔧 Conectando a base de datos...")
    await init_database()
    print("✅ Base de datos conectada")
    yield
    # Shutdown
    print("🛑 Cerrando aplicación")

# Crear aplicación
app = FastAPI(
    title="SGF - Sistema de Gestión Financiera",
    description="Sistema modular para gestión financiera de importaciones - Fase 1",
    version="2.0.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "http://localhost:3000",
        "http://localhost:8000", 
        "https://*.netlify.app",
        "https://*.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================
# RUTAS PRINCIPALES
# =============================================

@app.get("/")
async def root():
    return {
        "message": "🚀 SGF - Sistema de Gestión Financiera v2.0",
        "status": "✅ Funcionando",
        "fase": "1 - Finanzas Core",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """Verificar estado del sistema"""
    try:
        from database import get_supabase
        supabase = get_supabase()
        
        # Test de conexión
        result = supabase.table('suppliers').select("count", count="exact").execute()
        
        return {
            "status": "✅ Sistema funcionando",
            "database": "✅ Conectado a Supabase", 
            "suppliers_count": result.count,
            "version": "2.0.0",
            "fase": "1 - Finanzas Core"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error de sistema: {str(e)}")

# =============================================
# INCLUIR ROUTERS MODULARES
# =============================================

# Proveedores
app.include_router(
    suppliers.router,
    prefix="/api/suppliers",
    tags=["Suppliers"]
)

# Órdenes de Compra  
app.include_router(
    purchase_orders.router,
    prefix="/api/purchase-orders",
    tags=["Purchase Orders"]
)

# Facturas
app.include_router(
    invoices.router,
    prefix="/api/invoices", 
    tags=["Invoices"]
)

# Embarques
app.include_router(
    shipments.router,
    prefix="/api/shipments",
    tags=["Shipments"]
)

# Anticipos
app.include_router(
    advances.router,
    prefix="/api/advances",
    tags=["Advances"]
)

# Reportes y Dashboards
app.include_router(
    reports.router,
    prefix="/api/reports",
    tags=["Reports"]
)

# =============================================
# ENDPOINTS GENERALES DE STATS
# =============================================

@app.get("/api/stats/dashboard")
async def get_dashboard_stats():
    """Estadísticas principales para el dashboard"""
    try:
        from database import get_supabase
        supabase = get_supabase()
        
        # Conteos básicos
        suppliers_count = supabase.table('suppliers').select("count", count="exact").execute().count
        pos_count = supabase.table('purchase_orders').select("count", count="exact").execute().count
        invoices_count = supabase.table('invoices').select("count", count="exact").execute().count
        shipments_count = supabase.table('shipments').select("count", count="exact").execute().count
        
        # Estadísticas financieras
        invoices_pendientes = supabase.table('invoices').select("count", count="exact").eq('estado', 'pendiente').execute().count
        invoices_pagadas = supabase.table('invoices').select("count", count="exact").eq('estado', 'pagada_completa').execute().count
        
        # Totales de órdenes
        pos_result = supabase.table('purchase_orders').select('total_oc').execute()
        total_pos_usd = sum(float(po.get('total_oc', 0)) for po in pos_result.data)
        
        # Totales de facturas
        invoices_result = supabase.table('invoices').select('monto_total, saldo_pendiente').execute()
        total_facturas = sum(float(inv.get('monto_total', 0)) for inv in invoices_result.data)
        total_saldo_pendiente = sum(float(inv.get('saldo_pendiente', 0)) for inv in invoices_result.data)
        
        return {
            "success": True,
            "data": {
                "conteos": {
                    "suppliers": suppliers_count,
                    "purchase_orders": pos_count,
                    "invoices": invoices_count,
                    "shipments": shipments_count
                },
                "financial": {
                    "invoices_pendientes": invoices_pendientes,
                    "invoices_pagadas": invoices_pagadas,
                    "total_pos_usd": round(total_pos_usd, 2),
                    "total_facturas": round(total_facturas, 2),
                    "saldo_pendiente": round(total_saldo_pendiente, 2)
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")

# =============================================
# EJECUTAR APLICACIÓN
# =============================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 SGF - Sistema de Gestión Financiera v2.0")
    print("📊 Documentación: http://localhost:8000/docs")
    print("🔧 API: http://localhost:8000")
    print("💾 Base de datos: Nueva estructura Fase 1")
    print("✨ ¡Listo para usar!")
    print("="*50 + "\n")
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=["./"]
    )
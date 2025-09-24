# =============================================
# routers/__init__.py - Actualizado con todos los routers
# =============================================

from .suppliers import router as suppliers_router
from .purchase_orders import router as purchase_orders_router
from .invoices import router as invoices_router
from .shipments import router as shipments_router
from .advances import router as advances_router
from .payments import router as payments_router
from .reports import router as reports_router

__all__ = [
    "suppliers_router",
    "purchase_orders_router", 
    "invoices_router",
    "shipments_router",
    "advances_router",
    "payments_router",
    "reports_router"
]

# =============================================
# main.py - Actualizado con todos los routers
# =============================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

# Configuración
from config import settings
from database import init_database

# Routers
from routers import (
    suppliers_router, 
    purchase_orders_router, 
    invoices_router, 
    shipments_router, 
    advances_router,
    payments_router,
    reports_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando SGF - Sistema de Gestión Financiera")
    print("🔧 Conectando a base de datos...")
# =============================================
# config.py - Configuración del sistema
# =============================================

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Supabase
    supabase_url: str = "https://ponpwlirxrkqduyqhfhf.supabase.co"
    supabase_key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBvbnB3bGlyeHJrcWR1eXFoZmhmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTc5NzM0MDcsImV4cCI6MjA3MzU0OTQwN30.mwPG4GjJQrNLpD9snPJgEYlMPsDLICyqSl8U8xJqMoA"
    
    # App
    app_name: str = "SGF - Sistema de Gestión Financiera"
    app_version: str = "2.0.0"
    debug: bool = True
    
    # CORS
    cors_origins: list = [
        "http://localhost:3000",
        "http://localhost:8080", 
        "https://*.netlify.app",
        "https://*.vercel.app"
    ]
    
    class Config:
        env_file = ".env"

settings = Settings()

# =============================================
# database.py - Configuración de base de datos
# =============================================

from supabase import create_client, Client
from config import settings
import asyncio

# Cliente global de Supabase
_supabase_client: Optional[Client] = None

async def init_database():
    """Inicializar conexión a la base de datos"""
    global _supabase_client
    try:
        _supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        
        # Test de conexión
        result = _supabase_client.table('suppliers').select("count", count="exact").execute()
        print(f"✅ Base de datos conectada - {result.count} suppliers encontrados")
        
    except Exception as e:
        print(f"❌ Error conectando a base de datos: {str(e)}")
        raise

def get_supabase() -> Client:
    """Obtener cliente de Supabase"""
    global _supabase_client
    if _supabase_client is None:
        raise RuntimeError("Base de datos no inicializada. Llama a init_database() primero.")
    return _supabase_client

# =============================================
# models/__init__.py - Modelos base
# =============================================

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

class BaseResponse(BaseModel):
    """Respuesta base para todas las APIs"""
    success: bool
    message: Optional[str] = None
    data: Optional[dict] = None

class PaginatedResponse(BaseResponse):
    """Respuesta paginada"""
    total: int
    page: int
    per_page: int
    pages: int

# =============================================
# models/supplier.py - Modelo de Proveedores
# =============================================

class SupplierBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    activo: bool = True
    puerto_salida_default: Optional[str] = None
    contacto: Optional[str] = None
    notas: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class SupplierUpdate(BaseModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None
    puerto_salida_default: Optional[str] = None
    contacto: Optional[str] = None
    notas: Optional[str] = None

class Supplier(SupplierBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# =============================================
# models/purchase_order.py - Modelo de Órdenes
# =============================================

class PurchaseOrderBase(BaseModel):
    supplier_id: UUID
    numero_orden: str = Field(..., min_length=1)
    moneda: str = Field(..., pattern="^(USD|CLP)$")
    total_oc: Decimal = Field(..., gt=0)
    fecha: Optional[date] = None
    estado: str = Field(default="pendiente", pattern="^(pendiente|parcial|completada|cancelada)$")
    notas: Optional[str] = None

class PurchaseOrderCreate(PurchaseOrderBase):
    pass

class PurchaseOrderUpdate(BaseModel):
    supplier_id: Optional[UUID] = None
    numero_orden: Optional[str] = None
    moneda: Optional[str] = None
    total_oc: Optional[Decimal] = None
    fecha: Optional[date] = None
    estado: Optional[str] = None
    notas: Optional[str] = None

class PurchaseOrder(PurchaseOrderBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# =============================================
# models/invoice.py - Modelo de Facturas
# =============================================

class InvoiceBase(BaseModel):
    supplier_id: UUID  # SIEMPRE requerido - cambio clave
    numero_factura: str = Field(..., min_length=1)
    fecha_emision: Optional[date] = None
    moneda: str = Field(..., pattern="^(USD|CLP)$")
    monto_total: Decimal = Field(..., gt=0)
    estado: str = Field(default="pendiente", pattern="^(pendiente|pagada_parcial|pagada_completa|vencida)$")
    tipo_factura: Optional[str] = Field(None, pattern="^(producto|servicio|mixta)$")
    concepto: Optional[str] = None
    notas: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    pass

class InvoiceUpdate(BaseModel):
    supplier_id: Optional[UUID] = None
    numero_factura: Optional[str] = None
    fecha_emision: Optional[date] = None
    moneda: Optional[str] = None
    monto_total: Optional[Decimal] = None
    estado: Optional[str] = None
    tipo_factura: Optional[str] = None
    concepto: Optional[str] = None
    notas: Optional[str] = None

class Invoice(InvoiceBase):
    id: UUID
    saldo_pendiente: Optional[Decimal]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# =============================================
# models/advance.py - Modelo de Anticipos
# =============================================

class AdvancePaymentBase(BaseModel):
    po_id: UUID
    monto: Decimal = Field(..., gt=0)
    moneda: str = Field(..., pattern="^(USD|CLP)$")
    fecha_pago: date
    metodo_pago: Optional[str] = None
    usuario_pago: Optional[str] = None
    estado: str = Field(default="disponible", pattern="^(disponible|aplicado|devuelto)$")
    notas: Optional[str] = None

class AdvancePaymentCreate(AdvancePaymentBase):
    pass

class AdvancePayment(AdvancePaymentBase):
    id: UUID
    created_at: datetime
    
    class Config:
        from_attributes = True
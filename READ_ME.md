# 🚀 SGF - Sistema de Gestión Financiera v2.0

Sistema modular para gestión financiera de importaciones desarrollado con **FastAPI** y **Supabase**.
x|
## 📋 Descripción

El SGF es un sistema ERP modular diseñado específicamente para empresas importadoras. Esta es la **Fase 1 - Finanzas Core** que incluye gestión completa de:

- ✅ **Proveedores** con información de contacto y puertos
- ✅ **Órdenes de Compra** con control de estados  
- ✅ **Anticipos** ligados a órdenes con aplicación flexible
- ✅ **Facturas** independientes con sistema de vencimientos
- ✅ **Embarques** con relación a múltiples proveedores y facturas
- ✅ **Pagos** con aplicación granular a vencimientos
- ✅ **Reportes** y dashboards ejecutivos
- ✅ **Conciliación** automática por orden y embarque

## 🏗️ Arquitectura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FRONTEND      │    │    BACKEND      │    │   BASE DATOS    │
│   (React/HTML)  │◄──►│   (FastAPI)     │◄──►│   (Supabase)    │
│   Netlify       │    │   Render        │    │   PostgreSQL    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Estructura del Backend

```
backend/
├── main.py              # 🚀 Aplicación principal FastAPI
├── config.py            # ⚙️ Configuración y variables de entorno
├── database.py          # 🔌 Conexión a Supabase
├── models/              # 📋 Modelos Pydantic
│   ├── supplier.py      # Modelo de proveedores
│   ├── invoice.py       # Modelo de facturas
│   ├── purchase_order.py # Modelo de órdenes
│   └── advance.py       # Modelo de anticipos
├── routers/             # 🛣️ Endpoints API REST
│   ├── suppliers.py     # CRUD proveedores
│   ├── invoices.py      # CRUD facturas + vencimientos
│   ├── purchase_orders.py # CRUD órdenes
│   ├── advances.py      # CRUD anticipos + aplicaciones
│   ├── shipments.py     # CRUD embarques + cuadres
│   ├── payments.py      # CRUD pagos
│   └── reports.py       # Reportes y analytics
├── requirements.txt     # 📦 Dependencias Python
└── test_api.py         # 🧪 Tests automatizados
```

## 🗄️ Base de Datos

### Tablas Principales (15 tablas)

**Core:**
- `suppliers` - Proveedores
- `purchase_orders` - Órdenes de compra
- `invoices` - Facturas
- `shipments` - Embarques  
- `advance_payments` - Anticipos

**Relaciones:**
- `invoice_pos` - Facturas ↔ Órdenes
- `shipment_invoices` - Embarques ↔ Facturas
- `shipment_suppliers` - Embarques ↔ Proveedores
- `advance_allocations` - Aplicaciones de anticipos
- `invoice_dues` - Vencimientos de facturas
- `invoice_due_payments` - Pagos a vencimientos
- `invoice_payments` - Pagos de facturas

**Flujo de Caja:**
- `costos_fijos_recurrentes` - Costos mensuales
- `flujo_caja_movimientos` - Movimientos de caja
- `flujo_caja_resumen_mensual` - Resúmenes mensuales

## 🚀 Instalación y Configuración

### 1. Prerrequisitos

- Python 3.8+
- Cuenta en Supabase
- Git

### 2. Clonar y Configurar

```bash
# Clonar repositorio
git clone <tu-repo>
cd sgf-backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno

Crear archivo `.env`:

```env
# Supabase
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu-anon-key

# App
APP_NAME="SGF - Sistema de Gestión Financiera"
APP_VERSION="2.0.0"
DEBUG=true
```

### 4. Ejecutar

```bash
# Modo desarrollo
python main.py

# O con uvicorn directamente
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 🧪 Testing

### Ejecutar Tests Automatizados

```bash
python test_api.py
```

El script ejecuta tests completos de:
- ✅ Estado del sistema
- ✅ CRUD de proveedores
- ✅ Gestión de órdenes de compra  
- ✅ Anticipos y aplicaciones
- ✅ Facturas con vencimientos
- ✅ Pagos granulares
- ✅ Embarques y cuadres
- ✅ Reportes ejecutivos
- ✅ Dashboard APIs

### Test Manual via Swagger

Acceder a: `http://localhost:8000/docs`

## 📚 API Endpoints

### Proveedores
```
GET    /api/suppliers/              # Listar proveedores
POST   /api/suppliers/              # Crear proveedor
GET    /api/suppliers/{id}          # Obtener específico
PUT    /api/suppliers/{id}          # Actualizar
DELETE /api/suppliers/{id}          # Eliminar
GET    /api/suppliers/{id}/dashboard # Dashboard del proveedor
```

### Órdenes de Compra
```
GET    /api/purchase-orders/                    # Listar órdenes
POST   /api/purchase-orders/                    # Crear orden
GET    /api/purchase-orders/{id}                # Obtener específica
PUT    /api/purchase-orders/{id}                # Actualizar
DELETE /api/purchase-orders/{id}                # Eliminar
GET    /api/purchase-orders/{id}/anticipos-dashboard # Dashboard anticipos
```

### Facturas (Nueva Lógica)
```
GET    /api/invoices/                          # Listar facturas
POST   /api/invoices/                          # Crear factura (solo proveedor)
GET    /api/invoices/{id}                      # Obtener específica
PUT    /api/invoices/{id}                      # Actualizar
DELETE /api/invoices/{id}                      # Eliminar
POST   /api/invoices/{id}/link-oc              # Vincular a orden
POST   /api/invoices/{id}/aplicar-anticipo     # Aplicar anticipo
GET    /api/invoices/{id}/vencimientos         # Ver vencimientos
```

### Anticipos
```
GET    /api/advances/                          # Listar anticipos
POST   /api/advances/                          # Crear anticipo
GET    /api/advances/{id}                      # Obtener específico
PUT    /api/advances/{id}                      # Actualizar
DELETE /api/advances/{id}                      # Eliminar
POST   /api/advances/{id}/devolver             # Marcar como devuelto
GET    /api/advances/por-orden/{po_id}         # Anticipos por orden
GET    /api/advances/disponibles/{po_id}       # Anticipos disponibles
```

### Embarques
```
GET    /api/shipments/                         # Listar embarques
POST   /api/shipments/                         # Crear embarque
GET    /api/shipments/{id}                     # Obtener específico
PUT    /api/shipments/{id}                     # Actualizar
DELETE /api/shipments/{id}                     # Eliminar
POST   /api/shipments/{id}/proveedores         # Vincular proveedores
POST   /api/shipments/{id}/facturas            # Vincular facturas
GET    /api/shipments/{id}/cuadre              # Cuadre financiero
GET    /api/shipments/en-transito              # Embarques en tránsito
POST   /api/shipments/{id}/marcar-arribado     # Marcar como arribado
```

### Pagos
```
GET    /api/payments/                          # Listar pagos
POST   /api/payments/                          # Registrar pago
GET    /api/payments/{id}                      # Obtener específico
PUT    /api/payments/{id}                      # Actualizar
DELETE /api/payments/{id}                      # Eliminar
GET    /api/payments/por-factura/{invoice_id}  # Pagos por factura
```

### Reportes
```
GET    /api/reports/dashboard-ejecutivo        # Dashboard ejecutivo
GET    /api/reports/conciliacion-ordenes       # Conciliación OC vs facturas
GET    /api/reports/flujo-caja-proyectado      # Proyección flujo de caja
GET    /api/reports/vencimientos-proximos      # Vencimientos próximos
GET    /api/reports/proveedor/{id}/detalle     # Reporte detallado proveedor
```

### Estadísticas
```
GET    /api/stats/dashboard                    # Stats generales dashboard
```

## 💡 Características Clave

### 1. Nueva Lógica de Facturas
- **Facturas independientes**: Solo requieren proveedor
- **Vinculación flexible**: Se pueden vincular a órdenes después
- **Vencimientos automáticos**: Sistema de cuotas configurable
- **Pagos granulares**: Aplicación a vencimientos específicos

### 2. Gestión Avanzada de Anticipos
- **Ligados a órdenes**: Cada anticipo pertenece a una OC específica
- **Aplicación flexible**: Se pueden aplicar a cualquier factura del proveedor
- **Control de saldos**: Seguimiento automático de disponible vs aplicado
- **Estados automáticos**: Disponible → Aplicado → Devuelto

### 3. Embarques Multiproveedor
- **Relación N:M**: Un embarque puede tener múltiples proveedores
- **Facturas múltiples**: Múltiples facturas pueden ir en un embarque
- **Cuadre automático**: Conciliación de montos por proveedor
- **Estados de transporte**: Control completo del ciclo de vida

### 4. Conciliación Automática
- **Por orden**: OC = Anticipos + Facturas + Saldo
- **Por embarque**: Facturas vs anticipos disponibles
- **Por proveedor**: Vista consolidada de todas las operaciones

## 🚀 Deploy a Producción

### Backend (Render)

1. **Crear servicio en Render**
2. **Configurar variables de entorno**
3. **Deploy automático desde Git**

```bash
# Build Command
pip install -r requirements.txt

# Start Command  
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Frontend (Netlify)

1. **Build y deploy del frontend React/HTML**
2. **Configurar variables de entorno con URL del backend**
3. **CORS configurado automáticamente**

## 📈 Roadmap

### ✅ Fase 1 - Finanzas Core (Actual)
- Gestión completa de proveedores, órdenes, facturas, anticipos
- Sistema de vencimientos y pagos
- Embarques multiproveedor
- Reportes y conciliación

### 🔄 Fase 2 - SKUs y Costeo (Próximo)
- Gestión de SKUs/productos
- Líneas de detalle en órdenes, embarques y facturas  
- Costeo por producto
- Conciliación de cantidades

### 🔮 Fase 3 - Flujo de Caja Proyectado (Futuro)
- Proyecciones a 4 semanas, 6 meses, 1 año
- Integración con costos fijos y créditos
- Alertas de liquidez
- Planificación financiera avanzada

## 🤝 Contribuir

1. Fork del repositorio
2. Crear rama: `git checkout -b feature/nueva-feature`
3. Commit: `git commit -m 'Agregar nueva feature'`
4. Push: `git push origin feature/nueva-feature`
5. Pull Request

## 📝 Licencia

MIT License - Ver archivo LICENSE para detalles.

## 🆘 Soporte

- **Documentación API**: `http://localhost:8000/docs`
- **Issues**: GitHub Issues
- **Tests**: `python test_api.py`

---

**Desarrollado con ❤️ para empresas importadoras**
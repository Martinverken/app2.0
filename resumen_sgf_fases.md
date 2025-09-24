
# 📦 Sistema de Gestión Financiera - Roadmap Técnico por Fases

## 🎯 Objetivo
Desarrollar un sistema financiero integral que evolucione por fases:
1. **Finanzas (core):** gestión de proveedores, OCs, anticipos, embarques, facturas, pagos y vencimientos.
2. **Detalle de SKUs:** embarques y facturas con líneas por SKU, costeo de productos y conciliación de cantidades.
3. **Flujo de Caja Proyectado:** proyecciones a 4 semanas, 6 meses y 1 año integrando vencimientos futuros, costos fijos, créditos, ventas y compras planeadas.

---

# 🚀 Fase 1 - Finanzas Core

## 🗄️ Modelo de Datos
- supplier (id, nombre, activo, puerto_salida_default?)
- purchase_order (id, supplier_id, moneda, total_oc, fecha, estado)
- advance_payment (id, po_id, monto, moneda, fecha_pago, estado)
- shipment (id, codigo, puertos, fechas, estado)
- shipment_supplier (shipment_id, supplier_id)
- invoice (id, supplier_id NOT NULL, numero_factura, fecha_emision, moneda, monto_total, estado)
- shipment_invoice (shipment_id, invoice_id, monto_asignado opcional)
- invoice_po (invoice_id, po_id)
- invoice_due (id, invoice_id, monto_vencimiento, fecha_vencimiento, estado)
- advance_allocation (id, anticipo_id, invoice_id, monto_aplicado, fecha)
- invoice_payment (id, invoice_id, monto_pagado, fecha, metodo_pago, ref)
- invoice_due_payment (id, due_id, source (anticipo|pago), source_id, monto_aplicado, fecha)

## 🔗 Reglas clave
- Factura se crea solo con **proveedor** (sin OC ni embarque obligatorio).
- Embarque administra relación factura↔embarque.
- Anticipos siempre ligados a una OC.
- Aplicaciones de anticipo y pagos se asignan a facturas y, opcionalmente, a vencimientos específicos.
- Vencimientos: cada factura genera una o varias cuotas; estado se actualiza al aplicar anticipos/pagos.

## 🌐 Endpoints esenciales
- POST /api/ordenes, /api/anticipos, /api/embarques, /api/facturas
- POST /api/embarques/{id}/facturas
- POST /api/facturas/{id}/link-oc
- PUT /api/facturas/{id}/aplicar-anticipo (opcional due_id)
- POST /api/pagos-facturas (con due_id opcional)
- GET /api/ordenes/{id}/anticipos-dashboard
- GET /api/embarques/{id}/cuadre
- GET /api/facturas/{id}/vencimientos

## 📊 Conciliación
- OC: Σ Facturas = Σ AnticiposAplicados + Σ PagosBalance + Σ Pendientes
- Anticipos: Σ AnticiposPagados = Σ Aplicados + Saldo + Devueltos
- Factura: Total = Σ Vencimientos
- Vencimiento: monto = Σ anticipos_aplicados + Σ pagos

---

# 🧩 Fase 2 - SKUs y Costeo

## 🗄️ Nuevas Tablas
- sku (id, codigo, descripcion, unidad, categoria_id?, activo)
- supplier_sku (supplier_id, sku_id, codigo_proveedor, precio_base, lead_time)
- po_line (id, po_id, sku_id, cantidad, precio_unitario, subtotal)
- shipment_item (id, shipment_id, sku_id, supplier_id, cantidad, valor_unitario, moneda)
- invoice_line (id, invoice_id, sku_id, po_line_id?, cantidad, precio_unitario, subtotal)

## 🔗 Reglas adicionales
- OCs, embarques y facturas referencian SKUs.
- Validar que SKUs embarcados y facturados correspondan al proveedor.
- Control de cantidades: facturado ≤ OC, embarcado ≤ OC.
- Permite cálculo de **costo de producto** a nivel SKU.

## 📊 Beneficios
- Reportes de conciliación en **unidades y montos**.
- Costeo de inventarios y márgenes más precisos.

---

# 📈 Fase 3 - Flujo de Caja Proyectado

## 🗄️ Fuentes de datos
- **Entradas futuras**: vencimientos de facturas de clientes (ventas proyectadas).
- **Salidas futuras**: vencimientos de facturas de proveedores, pagos planificados de OCs, costos mensuales fijos, créditos bancarios.
- **Compras planeadas**: OCs futuras + embarques estimados.

## 🔗 Lógica
- Proyecciones de caja en horizontes de 4 semanas, 6 meses, 1 año.
- Consolidar flujos en una tabla `cashflow_projection`:
  - id, fecha, tipo (entrada|salida), fuente (factura_cliente, factura_proveedor, costo_fijo, credito, compra), monto, notas
- Agregar dashboards con curvas acumuladas de saldo proyectado.

## 📊 Beneficios
- Visibilidad de liquidez a corto, mediano y largo plazo.
- Alertas tempranas de déficit o exceso de caja.
- Integración con decisiones de compras y financiamiento.

---

# ✅ Roadmap de Implementación
1. **Fase 1 (Finanzas Core):** implementar modelo de proveedores, OCs, anticipos, embarques, facturas, pagos, vencimientos, conciliación por OC/embarque.  
2. **Fase 2 (SKUs y Costeo):** agregar detalle SKU en OCs, embarques y facturas; validar cantidades y calcular costos.  
3. **Fase 3 (Flujo de Caja):** construir motor de proyecciones con vencimientos, costos fijos, créditos, ventas estimadas y compras futuras.


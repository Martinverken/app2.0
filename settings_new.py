# =============================================
# settings_new.py - Configuración nueva
# =============================================

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class ConfigSGF:
    def __init__(self):
        print("🔧 Inicializando configuración...")
        
        # Supabase
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        
        # App
        self.app_name = os.getenv('APP_NAME', 'SGF - Sistema de Gestión Financiera')
        self.app_version = os.getenv('APP_VERSION', '2.0.0')
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.debug = os.getenv('DEBUG', 'true').lower() == 'true'
        
        print(f"📋 Environment: {self.environment}")
        if self.supabase_url:
            print(f"📋 URL: {self.supabase_url[:30]}...")
        else:
            print("📋 URL: NO ENCONTRADA")
        
        # Validar variables críticas
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("❌ SUPABASE_URL y SUPABASE_KEY son requeridas en .env")

# Crear instancia
settings = ConfigSGF()

def get_environment_info():
    return {
        "environment": settings.environment,
        "app_name": settings.app_name,
        "debug": settings.debug,
        "supabase_url": settings.supabase_url[:30] + "..." if settings.supabase_url else "No configurado"
    }

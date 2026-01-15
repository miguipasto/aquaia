#!/usr/bin/env python3
"""
Script de inicio para AquaAI API.
"""
import sys
import os
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.config import settings

if __name__ == "__main__":
    print(f"""
    ========================================================
    
     AquaAI - API de Predicción de Embalses
    
     Versión: {settings.app_version}
     Puerto: {settings.port}
     
     Documentación: http://localhost:{settings.port}/docs
    
    ========================================================
    """)
    
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )

"""
demonio.py — Proceso demonio que monitorea entrada/ y procesa archivos nuevos
Guía 5: Sistema Multipropósito

Ejecutar ANTES o en paralelo al servidor:
    python3 demonio.py
"""

import os
import shutil
import threading
import time
from datetime import datetime

# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────
BASE_DIR = os.path.expanduser("~/servidor_archivos")
ENTRADA_DIR = os.path.join(BASE_DIR, "entrada")
PROCESADOS_DIR = os.path.join(BASE_DIR, "procesados")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(BASE_DIR, "registro.log")

INTERVALO = 10  # segundos entre cada escaneo

# Semáforo: permite hasta 2 procesamientos simultáneos (ajustable)
semaforo = threading.Semaphore(2)

# Mutex para acceso exclusivo al log (compartido con servidor si corre junto)
log_lock = threading.Lock()

# Conjunto de archivos ya procesados (en esta sesión)
procesados_en_sesion: set = set()
sesion_lock = threading.Lock()


# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
def registrar(mensaje: str):
    """Escribe en registro.log con timestamp. Usa Lock para evitar corrupción."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{timestamp}] [DEMONIO] {mensaje}\n"
    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linea)
    print(f"  LOG → {linea.strip()}")


#def procesar_archivo(nombre: str):

#def ciclo_monitoreo():


#def main():

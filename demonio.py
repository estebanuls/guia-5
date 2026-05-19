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


# ─────────────────────────────────────────────
# Procesamiento de archivo (se ejecuta en un hilo)
# ─────────────────────────────────────────────
def procesar_archivo(nombre: str):
    """
    Mueve un archivo de entrada/ a procesados/.
    Protegido por semáforo para limitar concurrencia.
    """
    origen = os.path.join(ENTRADA_DIR, nombre)
    destino = os.path.join(PROCESADOS_DIR, nombre)

    semaforo.acquire()
    try:
        # Verificar que sigue existiendo (otro hilo pudo procesarlo antes)
        if not os.path.isfile(origen):
            registrar(f"'{nombre}' ya no existe en entrada/ (procesado por otro hilo)")
            return

        # Simular procesamiento (en producción aquí iría lógica real)
        time.sleep(1)

        shutil.move(origen, destino)
        registrar(f"'{nombre}' movido de entrada/ → procesados/")

        # Registrar en logs/ también un archivo individual de confirmación
        log_individual = os.path.join(LOGS_DIR, f"{nombre}.log")
        with open(log_individual, "w") as lf:
            lf.write(f"Procesado: {datetime.now().isoformat()}\n")
            lf.write(f"Origen: {origen}\n")
            lf.write(f"Destino: {destino}\n")

    except FileNotFoundError:
        registrar(f"ERROR: '{nombre}' no encontrado al intentar moverlo")
    except PermissionError:
        registrar(f"ERROR: sin permisos para mover '{nombre}'")
    except Exception as e:
        registrar(f"ERROR procesando '{nombre}': {e}")
    finally:
        semaforo.release()


# ─────────────────────────────────────────────

#def ciclo_monitoreo():


#def main():

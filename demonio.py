import os
import shutil
import threading
import time
from datetime import datetime

BASE_DIR = os.path.expanduser("~/servidor_archivos")
ENTRADA_DIR = os.path.join(BASE_DIR, "entrada")
PROCESADOS_DIR = os.path.join(BASE_DIR, "procesados")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(BASE_DIR, "registro.log")

INTERVALO = 10  # segundos entre cada escaneo

# Semáforo: permite hasta 2 procesamientos simultáneos
semaforo = threading.Semaphore(2)

# Mutex para acceso exclusivo al log (compartido con servidor si corre junto)
log_lock = threading.Lock()

# Conjunto de archivos ya procesados (en esta sesión)
procesados_en_sesion: set = set()
sesion_lock = threading.Lock()


# Logging

def registrar(mensaje: str):

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{timestamp}] [DEMONIO] {mensaje}\n"
    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linea)
    print(f"  LOG → {linea.strip()}")



# Procesamiento de archivo (se ejecuta en un hilo)

def procesar_archivo(nombre: str):
    """
    Mueve un archivo de entrada/ a procesados/.
    Protegido por semáforo para limitar concurrencia.
    """
    origen = os.path.join(ENTRADA_DIR, nombre)
    destino = os.path.join(PROCESADOS_DIR, nombre)

    semaforo.acquire()
    try:
        # Verificar que sigue existiendo 
        if not os.path.isfile(origen):
            registrar(f"'{nombre}' ya no existe en entrada/ (procesado por otro hilo)")
            return

        # Simular procesamiento 
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



# Ciclo del demonio

def ciclo_monitoreo():
    """
    Escanea entrada/ cada INTERVALO segundos.
    Por cada archivo nuevo lanza un hilo de procesamiento.
    """
    registrar(f"Demonio iniciado — monitoreando cada {INTERVALO}s")

    while True:
        try:
            archivos = os.listdir(ENTRADA_DIR)
        except FileNotFoundError:
            registrar("ERROR: directorio entrada/ no encontrado, reintentando...")
            time.sleep(INTERVALO)
            continue

        nuevos = []
        with sesion_lock:
            for archivo in archivos:
                ruta = os.path.join(ENTRADA_DIR, archivo)
                if os.path.isfile(ruta) and archivo not in procesados_en_sesion:
                    nuevos.append(archivo)
                    procesados_en_sesion.add(archivo)

        if nuevos:
            registrar(f"Nuevos archivos detectados: {nuevos}")
            for nombre in nuevos:
                hilo = threading.Thread(
                    target=procesar_archivo,
                    args=(nombre,),
                    daemon=True,
                    name=f"Proc-{nombre}"
                )
                hilo.start()
        else:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] Sin archivos nuevos en entrada/")

        time.sleep(INTERVALO)


def main():
    # Crear directorios si no existen
    for d in (ENTRADA_DIR, PROCESADOS_DIR, LOGS_DIR):
        os.makedirs(d, exist_ok=True)

    print(f"""
{'='*50}
  DEMONIO DE PROCESAMIENTO
  Base  : {BASE_DIR}
  Ciclo : cada {INTERVALO} segundos
  Semáforo: hasta 2 hilos simultáneos
{'='*50}
Presiona Ctrl+C para detener.
""")

    try:
        ciclo_monitoreo()
    except KeyboardInterrupt:
        registrar("Demonio detenido por el usuario")
        print("\n[!] Demonio detenido.")


if __name__ == "__main__":
    main()

"""
servidor.py — Servidor multihilo para gestión de archivos remotos
Guía 5: Sistema Multipropósito
"""

import socket
import threading
import os
import shutil
import json
from datetime import datetime

# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = 9999
BASE_DIR = os.path.expanduser("~/servidor_archivos")
ENTRADA_DIR = os.path.join(BASE_DIR, "entrada")
PROCESADOS_DIR = os.path.join(BASE_DIR, "procesados")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(BASE_DIR, "registro.log")

# Mutex global para acceso sincronizado al log y al sistema de archivos
log_lock = threading.Lock()
file_lock = threading.Lock()


# ─────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────
def registrar(mensaje: str):
    """Escribe una línea en registro.log con timestamp. Protegido por Lock."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"[{timestamp}] {mensaje}\n"
    with log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(linea)
    print(f"  LOG → {linea.strip()}")


def enviar_respuesta(conn: socket.socket, datos: dict):
    """Serializa un dict como JSON y lo envía con longitud de cabecera."""
    payload = json.dumps(datos, ensure_ascii=False).encode("utf-8")
    # Cabecera de 8 bytes con la longitud del payload
    header = len(payload).to_bytes(8, "big")
    conn.sendall(header + payload)


def recibir_mensaje(conn: socket.socket) -> dict | None:
    """Lee cabecera + payload y devuelve el dict deserializado."""
    try:
        header = b""
        while len(header) < 8:
            chunk = conn.recv(8 - len(header))
            if not chunk:
                return None
            header += chunk
        length = int.from_bytes(header, "big")

        payload = b""
        while len(payload) < length:
            chunk = conn.recv(min(4096, length - len(payload)))
            if not chunk:
                return None
            payload += chunk
        return json.loads(payload.decode("utf-8"))
    except Exception as e:
        print(f"  [!] Error recibiendo mensaje: {e}")
        return None


# ─────────────────────────────────────────────
# Comandos del servidor
# ─────────────────────────────────────────────
def cmd_listar(addr) -> dict:
    """Lista archivos en el directorio entrada/."""
    with file_lock:
        archivos = os.listdir(ENTRADA_DIR)
    registrar(f"[{addr}] LISTAR → {len(archivos)} archivo(s)")
    return {"ok": True, "archivos": archivos}


def cmd_leer(nombre: str, addr) -> dict:
    """Lee el contenido de un archivo en entrada/."""
    ruta = os.path.join(ENTRADA_DIR, nombre)
    with file_lock:
        if not os.path.isfile(ruta):
            registrar(f"[{addr}] LEER '{nombre}' → NO ENCONTRADO")
            return {"ok": False, "error": f"Archivo '{nombre}' no encontrado"}
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            contenido = f.read()
    registrar(f"[{addr}] LEER '{nombre}' → OK ({len(contenido)} bytes)")
    return {"ok": True, "contenido": contenido}


def cmd_copiar(nombre: str, addr) -> dict:
    """Copia un archivo de entrada/ a procesados/."""
    origen = os.path.join(ENTRADA_DIR, nombre)
    destino = os.path.join(PROCESADOS_DIR, nombre)
    with file_lock:
        if not os.path.isfile(origen):
            registrar(f"[{addr}] COPIAR '{nombre}' → NO ENCONTRADO")
            return {"ok": False, "error": f"Archivo '{nombre}' no encontrado"}
        shutil.copy2(origen, destino)
    registrar(f"[{addr}] COPIAR '{nombre}' → entrada/ ✓ procesados/")
    return {"ok": True, "mensaje": f"'{nombre}' copiado a procesados/"}


def cmd_subir(nombre: str, contenido: str, addr) -> dict:
    """Guarda un archivo enviado por el cliente en entrada/."""
    ruta = os.path.join(ENTRADA_DIR, nombre)
    with file_lock:
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
    registrar(f"[{addr}] SUBIR '{nombre}' → OK ({len(contenido)} bytes)")
    return {"ok": True, "mensaje": f"'{nombre}' guardado en entrada/"}


def cmd_descargar(nombre: str, addr) -> dict:
    """Envía el contenido de un archivo desde entrada/ al cliente."""
    ruta = os.path.join(ENTRADA_DIR, nombre)
    with file_lock:
        if not os.path.isfile(ruta):
            # Buscar también en procesados/
            ruta2 = os.path.join(PROCESADOS_DIR, nombre)
            if not os.path.isfile(ruta2):
                registrar(f"[{addr}] DESCARGAR '{nombre}' → NO ENCONTRADO")
                return {"ok": False, "error": f"'{nombre}' no encontrado"}
            ruta = ruta2
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            contenido = f.read()
    registrar(f"[{addr}] DESCARGAR '{nombre}' → OK")
    return {"ok": True, "nombre": nombre, "contenido": contenido}


def cmd_ver_logs(addr) -> dict:
    """Retorna el contenido del registro.log al cliente."""
    with log_lock:
        if os.path.isfile(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = f.read()
        else:
            logs = "(sin registros aún)"
    registrar(f"[{addr}] VER_LOGS → OK")
    return {"ok": True, "logs": logs}


# ─────────────────────────────────────────────
# Hilo por cliente
# ─────────────────────────────────────────────
def manejar_cliente(conn: socket.socket, addr):
    """Función ejecutada en un hilo separado por cada cliente conectado."""
    print(f"\n[+] Cliente conectado: {addr}")
    registrar(f"[{addr}] CONEXIÓN establecida")

    try:
        while True:
            msg = recibir_mensaje(conn)
            if msg is None:
                break

            comando = msg.get("cmd", "").upper()

            if comando == "LISTAR":
                resp = cmd_listar(addr)
            elif comando == "LEER":
                resp = cmd_leer(msg.get("nombre", ""), addr)
            elif comando == "COPIAR":
                resp = cmd_copiar(msg.get("nombre", ""), addr)
            elif comando == "SUBIR":
                resp = cmd_subir(msg.get("nombre", ""), msg.get("contenido", ""), addr)
            elif comando == "DESCARGAR":
                resp = cmd_descargar(msg.get("nombre", ""), addr)
            elif comando == "VER_LOGS":
                resp = cmd_ver_logs(addr)
            elif comando == "SALIR":
                registrar(f"[{addr}] DESCONEXIÓN solicitada")
                enviar_respuesta(conn, {"ok": True, "mensaje": "Hasta luego"})
                break
            else:
                resp = {"ok": False, "error": f"Comando desconocido: '{comando}'"}

            enviar_respuesta(conn, resp)

    except Exception as e:
        print(f"  [!] Error con cliente {addr}: {e}")
        registrar(f"[{addr}] ERROR: {e}")
    finally:
        conn.close()
        print(f"[-] Cliente desconectado: {addr}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────
def main():
    # Crear estructura de directorios si no existe
    for d in (ENTRADA_DIR, PROCESADOS_DIR, LOGS_DIR):
        os.makedirs(d, exist_ok=True)

    # Generar 3 archivos de prueba en entrada/ si no hay ninguno
    if not os.listdir(ENTRADA_DIR):
        for i in range(1, 4):
            ruta = os.path.join(ENTRADA_DIR, f"prueba_{i}.txt")
            with open(ruta, "w") as f:
                f.write(f"Archivo de prueba #{i}\n" * 5)
        print("[*] Archivos de prueba creados en entrada/")

    registrar("=== SERVIDOR INICIADO ===")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(10)

    print(f"\n{'='*50}")
    print(f"  Servidor escuchando en {HOST}:{PORT}")
    print(f"  Base: {BASE_DIR}")
    print(f"{'='*50}\n")

    try:
        while True:
            conn, addr = server.accept()
            hilo = threading.Thread(
                target=manejar_cliente,
                args=(conn, addr),
                daemon=True,
                name=f"Cliente-{addr[1]}"
            )
            hilo.start()
            print(f"  [*] Hilos activos: {threading.active_count() - 1}")
    except KeyboardInterrupt:
        print("\n[!] Servidor detenido por el usuario")
        registrar("=== SERVIDOR DETENIDO ===")
    finally:
        server.close()


if __name__ == "__main__":
    main()


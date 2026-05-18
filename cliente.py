import socket
import json
import os


HOST = "127.0.0.1"   # Cambiar ip si es que se hace en otro server ojitooo
PORT = 9999


def enviar_mensaje(sock: socket.socket, datos: dict):
    payload = json.dumps(datos, ensure_ascii=False).encode("utf-8")
    header = len(payload).to_bytes(8, "big")
    sock.sendall(header + payload)


def recibir_respuesta(sock: socket.socket) -> dict | None:
    #Lee la respuesta del servidor (cabecera + payload JSON).
    try:
        header = b""
        while len(header) < 8:
            chunk = sock.recv(8 - len(header))
            if not chunk:
                return None
            header += chunk
        length = int.from_bytes(header, "big")

        payload = b""
        while len(payload) < length:
            chunk = sock.recv(min(4096, length - len(payload)))
            if not chunk:
                return None
            payload += chunk
        return json.loads(payload.decode("utf-8"))
    except Exception as e:
        print(f"  [!] Error recibiendo respuesta: {e}")
        return None


def accion_listar(sock):
    enviar_mensaje(sock, {"cmd": "LISTAR"})
    resp = recibir_respuesta(sock)
    if resp and resp.get("ok"):
        archivos = resp["archivos"]
        if archivos:
            print(f"\n  Archivos en entrada/ ({len(archivos)}):")
            for a in archivos:
                print(f"    · {a}")
        else:
            print("  (directorio entrada/ vacío)")
    else:
        print(f"  Error: {resp.get('error') if resp else 'sin respuesta'}")


def accion_leer(sock):
    nombre = input("  Nombre del archivo a leer: ").strip()
    if not nombre:
        return
    enviar_mensaje(sock, {"cmd": "LEER", "nombre": nombre})
    resp = recibir_respuesta(sock)
    if resp and resp.get("ok"):
        print(f"\n  ─── Contenido de '{nombre}' ───")
        print(resp["contenido"])
        print("  ──────────────────────────────")
    else:
        print(f"  Error: {resp.get('error') if resp else 'sin respuesta'}")


def accion_copiar(sock):
    nombre = input("  Nombre del archivo a copiar a procesados/: ").strip()
    if not nombre:
        return
    enviar_mensaje(sock, {"cmd": "COPIAR", "nombre": nombre})
    resp = recibir_respuesta(sock)
    if resp and resp.get("ok"):
        print(f"  ✓ {resp['mensaje']}")
    else:
        print(f"  Error: {resp.get('error') if resp else 'sin respuesta'}")


def accion_subir(sock):
    ruta_local = input("  Ruta del archivo local a subir: ").strip()
    if not ruta_local:
        return
    if not os.path.isfile(ruta_local):
        print(f"  [!] Archivo '{ruta_local}' no encontrado localmente.")
        return
    nombre = os.path.basename(ruta_local)
    with open(ruta_local, "r", encoding="utf-8", errors="replace") as f:
        contenido = f.read()
    enviar_mensaje(sock, {"cmd": "SUBIR", "nombre": nombre, "contenido": contenido})
    resp = recibir_respuesta(sock)
    if resp and resp.get("ok"):
        print(f"  ✓ {resp['mensaje']}")
    else:
        print(f"  Error: {resp.get('error') if resp else 'sin respuesta'}")


def accion_descargar(sock):
    nombre = input("  Nombre del archivo a descargar: ").strip()
    if not nombre:
        return
    enviar_mensaje(sock, {"cmd": "DESCARGAR", "nombre": nombre})
    resp = recibir_respuesta(sock)
    if resp and resp.get("ok"):
        destino = os.path.join(os.getcwd(), resp["nombre"])
        with open(destino, "w", encoding="utf-8") as f:
            f.write(resp["contenido"])
        print(f"  ✓ Descargado como '{destino}'")
    else:
        print(f"  Error: {resp.get('error') if resp else 'sin respuesta'}")


def accion_ver_logs(sock):
    enviar_mensaje(sock, {"cmd": "VER_LOGS"})
    resp = recibir_respuesta(sock)
    if resp and resp.get("ok"):
        print("\n  ─── registro.log ───")
        print(resp["logs"])
        print("  ────────────────────")
    else:
        print(f"  Error: {resp.get('error') if resp else 'sin respuesta'}")



# Menú principal

MENU = """
╔══════════════════════════════════════╗
║     SISTEMA DE ARCHIVOS REMOTOS     ║
╠══════════════════════════════════════╣
║  1. Listar archivos en entrada/     ║
║  2. Leer contenido de un archivo    ║
║  3. Copiar archivo a procesados/    ║
║  4. Subir archivo local al servidor ║
║  5. Descargar archivo del servidor  ║
║  6. Ver logs del servidor           ║
║  7. Salir                           ║
╚══════════════════════════════════════╝
Opción: """

ACCIONES = {
    "1": accion_listar,
    "2": accion_leer,
    "3": accion_copiar,
    "4": accion_subir,
    "5": accion_descargar,
    "6": accion_ver_logs,
}


def main():
    print(f"\nConectando a {HOST}:{PORT}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        print("  ✓ Conectado al servidor\n")
    except ConnectionRefusedError:
        print(f"  [!] No se pudo conectar a {HOST}:{PORT}.")
        print("      Asegúrate de que servidor.py esté corriendo.")
        return

    try:
        while True:
            opcion = input(MENU).strip()

            if opcion in ACCIONES:
                ACCIONES[opcion](sock)
            elif opcion == "7":
                enviar_mensaje(sock, {"cmd": "SALIR"})
                resp = recibir_respuesta(sock)
                if resp:
                    print(f"  {resp.get('mensaje', 'Desconectado')}")
                break
            else:
                print("  Opción inválida, elige entre 1 y 7.")
    except (BrokenPipeError, ConnectionResetError):
        print("\n  [!] Conexión con el servidor perdida.")
    except KeyboardInterrupt:
        print("\n  Saliendo...")
    finally:
        sock.close()
        print("  Conexión cerrada.")


if __name__ == "__main__":
    main()


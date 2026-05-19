# Guía 5 — Sistema Multipropósito: Terminal, Hilos y Sincronización

##### Integrantes: Maximiliano Uribe, Bruce Inostroza, Matias Paolini, Esteban Cortés

## Instrucciones de ejecución

### 1. Preparación del entorno

```bash
# Crear estructura de carpetas (el servidor lo hace automáticamente,
# pero se puede hacer manualmente también)
mkdir -p ~/servidor_archivos/{entrada,procesados,logs}

# Asignar permisos adecuados
chmod 755 ~/servidor_archivos
chmod 755 ~/servidor_archivos/entrada
chmod 755 ~/servidor_archivos/procesados
chmod 755 ~/servidor_archivos/logs

# Generar archivos de prueba en entrada/
for i in 1 2 3; do
  python3 -c "import random,string; print(''.join(random.choices(string.ascii_letters+' \n', k=200)))" \
    > ~/servidor_archivos/entrada/prueba_$i.txt
done
```

### 2. Ejecutar el servidor (Terminal 1)

```bash
python3 servidor.py
```

El servidor:
- Escucha en `0.0.0.0:9999`
- Crea automáticamente los directorios y archivos de prueba si no existen
- Lanza un **hilo separado** por cada cliente que se conecta

### 3. Ejecutar el demonio (Terminal 2)

```bash
python3 demonio.py
```

El demonio:
- Escanea `entrada/` cada **10 segundos**
- Por cada archivo nuevo, lanza un hilo para moverlo a `procesados/`
- Puede correr en la misma máquina que el servidor o en otra

### 4. Ejecutar clientes (Terminales 3 y 4)

```bash
python3 cliente.py
```

> Si el servidor está en otra máquina, editar la línea `HOST = "127.0.0.1"` 
> en `cliente.py` con la IP correspondiente.

### Demostración en clase (dos clientes simultáneos)

```
Terminal 1: python3 servidor.py
Terminal 2: python3 demonio.py
Terminal 3: python3 cliente.py   ← Alumno A
Terminal 4: python3 cliente.py   ← Alumno B
```

Ambos clientes pueden operar al mismo tiempo; el servidor los atiende
en hilos independientes.

---

## Respuestas a las preguntas

### 1-¿Cómo evitó condiciones de carrera en el servidor?

Se usaron dos objetos de sincronización de la librería `threading`:

- **`log_lock` (Lock):** protege las escrituras al archivo `registro.log`.  
  Antes de escribir cualquier línea en el log, el hilo debe adquirir este lock.
  Si otro hilo ya lo tiene, espera hasta que se libere. Esto garantiza que las
  líneas del log nunca se mezclen ni corrompan, incluso con múltiples clientes
  escribiendo al mismo tiempo.

- **`file_lock` (Lock):** protege las operaciones sobre el sistema de archivos
  (listar, leer, copiar, subir, descargar). Evita que dos hilos intenten acceder
  o modificar el mismo archivo de forma concurrente, lo cual podría causar lecturas
  parciales o escrituras superpuestas.

En el demonio, además se usa un **Semáforo** (`threading.Semaphore(2)`) que
limita a 2 los hilos de procesamiento simultáneos, evitando que muchos hilos
compitan por los mismos archivos a la vez.

---

### 2-¿Qué ventajas tiene usar threads en lugar de procesos para este caso?

| Aspecto | Threads | Procesos |
|---|---|---|
| Memoria | Comparten el mismo espacio de memoria | Cada proceso tiene su propia memoria |
| Comunicación | Directa (variables compartidas) | Requiere IPC (pipes, sockets, etc.) |
| Creación | Más rápido y liviano | Más costoso en recursos |
| Sincronización | Lock, Semáforo, etc. | Más compleja (señales, shared memory) |
| Caso de uso | I/O-bound (esperar archivos, red) | CPU-bound (cálculos intensivos) |

Para este sistema, los threads son **ideales** porque:

1. Las operaciones son mayoritariamente **I/O-bound** (leer/escribir archivos,
   enviar/recibir por socket): los hilos pueden esperar sin bloquear a los demás.

2. La **memoria compartida** es una ventaja: `log_lock` y `file_lock` pueden
   ser accedidos directamente por todos los hilos del servidor sin mecanismos
   adicionales de IPC.

3. El overhead de crear un hilo nuevo por cliente es mínimo comparado con
   crear un proceso hijo (`fork`).

En Python, el GIL (Global Interpreter Lock) limita la paralelización real
en tareas CPU-bound, pero para tareas I/O-bound como ésta, los hilos se
liberan del GIL durante las operaciones bloqueantes y permiten verdadera
concurrencia efectiva.

---

### 3-Explique el método de sincronización elegido

Se eligió la combinación de **Lock** (mutex) y **Semáforo**:

#### Lock (threading.Lock) — para el log y el sistema de archivos

Un Lock es un mutex binario: solo un hilo puede tenerlo a la vez.
Cuando un hilo llama a `lock.acquire()`, si el lock está libre lo toma;
si está ocupado, el hilo queda **bloqueado** hasta que se libere.
El bloque `with log_lock:` garantiza la liberación automática aunque
ocurra una excepción (equivalente a un try/finally).

```
Hilo A: acquire(log_lock) → escribe → release(log_lock)
Hilo B: acquire(log_lock) → BLOQUEADO hasta que A libere → escribe → release
```

Esto garantiza **exclusión mutua**: nunca dos hilos escriben al log
simultáneamente.

#### Semáforo (threading.Semaphore) — para el demonio

Un Semáforo mantiene un **contador interno**. Se inicializa en 2, lo que
significa que hasta 2 hilos pueden estar procesando archivos al mismo tiempo.
Cuando un tercer hilo intenta entrar, se bloquea hasta que uno de los dos
anteriores termine y libere el semáforo.

```
Semáforo(2):
  Hilo 1 → acquire() → contador=1 → procesa archivo_A
  Hilo 2 → acquire() → contador=0 → procesa archivo_B
  Hilo 3 → acquire() → BLOQUEADO (contador=0)
  Hilo 1 → release() → contador=1 → Hilo 3 puede continuar
```

Este enfoque es superior a un Lock simple para el demonio porque permite
**concurrencia controlada**: no serializa completamente el procesamiento,
sino que lo limita a un número razonable de operaciones paralelas.

La alternativa mencionada en la guía (Algoritmo del Panadero) es una
solución de bajo nivel que implementa exclusión mutua sin primitivas del SO;
es útil para entender los fundamentos, pero en Python las primitivas de
`threading` son más robustas y seguras para producción.

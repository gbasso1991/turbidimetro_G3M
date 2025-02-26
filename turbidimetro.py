#%% turbidimetro.py
# Sebastian Rabal y Giuliano Basso
#%% Librerias
import serial
import serial.tools.list_ports
import time
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk
import threading
import os  

#%% Funciones
def obtener_nombre_archivo():
    """Genera un nombre de archivo basado en la fecha y hora actual."""
    fecha_hora = datetime.now().strftime("%y%m%d_%H%M%S")  # Formato aammdd_hhmmss
    return f"mediciones_{fecha_hora}.txt"

def crear_subdirectorio():
    """Crea un subdirectorio con la nomenclatura aammdd_hhmmss y devuelve su ruta."""
    nombre_subdirectorio = datetime.now().strftime("%y%m%d_%H%M%S")
    ruta_subdirectorio = os.path.join(os.getcwd(), nombre_subdirectorio)
    
    if not os.path.exists(ruta_subdirectorio):
        os.makedirs(ruta_subdirectorio)
    
    return ruta_subdirectorio

def medir_intensidad(ser):
    """Envía el comando 'medir' a Arduino y devuelve la intensidad recibida."""
    ser.write("medir\n".encode())  # Enviar comando a Arduino
    
    while True:
        linea = ser.readline().decode("utf-8").strip()
        
        if not linea:
            continue  # Ignora líneas vacías
        
        try:
            intensidad = float(linea)
            return intensidad
        except ValueError:
            print(f"Error al convertir datos: {linea}")
            return None
#%% Funciones adicionales
def guardar_grafico(ruta_archivo):
    """Guarda el gráfico actual en un archivo .png con el mismo nombre que el archivo .txt."""
    nombre_grafico = os.path.splitext(ruta_archivo)[0] + ".png"  # Cambia la extensión a .png
    fig.savefig(nombre_grafico, dpi=300)  # Guarda el gráfico con DPI 300
    print(f"Gráfico guardado en {nombre_grafico}")

#%% realizar_mediciones
def realizar_mediciones(ser, duracion, archivo, tiempos, intensidades, grafico_activo):
    """Realiza mediciones durante el tiempo especificado y almacena los datos en un archivo."""
    inicio = time.time()

    with open(archivo, "w") as archivo:
        archivo.write("Tiempo (s), Intensidad\n")
        
        while grafico_activo.is_set() and (duracion is None or time.time() - inicio < duracion):
            tiempo_actual = round(time.time() - inicio, 2)  # Tiempo relativo en segundos
            intensidad = medir_intensidad(ser)              # le pido la medida al Arduino
            
            if intensidad is not None:
                archivo.write(f"{tiempo_actual}, {intensidad}\n")
                archivo.flush()  # Asegura que los datos se escriban en el archivo inmediatamente
                tiempos.append(tiempo_actual)
                intensidades.append(intensidad)
                print(f"Tiempo: {tiempo_actual}s - Intensidad: {intensidad}")
            
            time.sleep(1)  # Ajusta el intervalo entre mediciones
    
    print(f"Mediciones completadas. Datos guardados en {archivo}")
    
    if duracion is not None and time.time() - inicio >= duracion:
        messagebox.showinfo("Medición completada", "La medición ha concluido correctamente.")
        guardar_grafico(archivo.name)  # Guarda el gráfico antes de limpiar
        grafico_activo.clear()  # Desactiva el evento para detener la medición
        tiempos.clear()  # Limpia las listas para una nueva medición
        intensidades.clear()


#%% Iniciar medicion
def iniciar_medicion():
    """Inicia la medición en un hilo separado."""
    global ser, grafico_activo, hilo_medicion

    if grafico_activo.is_set():
        messagebox.showwarning("Advertencia", "Ya hay una medición en curso.")
        return

    try:
        duracion = float(entry_tiempo.get()) if entry_tiempo.get() else None
    except ValueError:
        messagebox.showerror("Error", "Ingrese un tiempo de medición válido.")
        return
    
    grafico_activo.set()
    ruta_subdirectorio = crear_subdirectorio()  # Crear subdirectorio
    nombre_archivo = os.path.join(ruta_subdirectorio, obtener_nombre_archivo())  # Ruta completa del archivo
    tiempos.clear()
    intensidades.clear()

    hilo_medicion = threading.Thread(target=realizar_mediciones, args=(ser, duracion, nombre_archivo, tiempos, intensidades, grafico_activo))
    hilo_medicion.start()

    actualizar_grafico()
#%% Cancelar Medida
def cancelar_medicion():
    """Cancela la medición en curso."""
    global grafico_activo

    if grafico_activo.is_set():
        guardar_grafico(os.path.join(crear_subdirectorio(), obtener_nombre_archivo()))  # Guarda el gráfico antes de limpiar
        grafico_activo.clear()
        messagebox.showinfo("Información", "Medición cancelada.")
    else:
        messagebox.showwarning("Advertencia", "No hay una medición en curso.")
#%% Act grafico
def actualizar_grafico():
    """Actualiza el gráfico en tiempo real."""
    if grafico_activo.is_set():
        ax.clear()
        ax.plot(tiempos, intensidades, 'o-')
        ax.grid()
        ax.set_xlabel("Tiempo (s)")
        ax.set_ylabel("Intensidad")
        ax.set_title("Medición de Turbidez en Tiempo Real")
        canvas.draw()

    if grafico_activo.is_set():
        root.after(1000, actualizar_grafico)  # Actualizar cada segundo

#%% Conexión con Arduino
puertos_disponibles = serial.tools.list_ports.comports()  # Listar los puertos seriales disponibles
puerto_activo = None
# Buscar el primer puerto USB activo (ttyUSB*)
for puerto in puertos_disponibles:
    print(f"Puerto: {puerto.device}")
    if "ttyUSB" in puerto.device:  # Verificar si el puerto es ttyUSB*
        try:
            # Intenta abrir el puerto
            conexion = serial.Serial(puerto.device)
            conexion.close()  # Cierra la conexión
            print(f"Puerto activo: {puerto.device}")
            puerto_activo = puerto.device  # Guardar el nombre del puerto activo
            break  # Salir del bucle después de encontrar el primer ttyUSB* activo
        except (serial.SerialException, OSError):
            print(f"Puerto inactivo: {puerto.device}")

# Verificar si se encontró un puerto USB activo
if puerto_activo:
    print('-' * 40, '\n', f"Puerto seleccionado: {puerto_activo}")
else:
    print("No se encontraron puertos USB activos.")
    exit()

#%% Configuración del puerto serie
puerto = puerto_activo  # lo detecta automaticamente para que sea cross plataform 
baudrate = 9600

#%% Iniciar la interfaz gráfica
root = tk.Tk()
root.title("Turbidímetro")

# Variables globales
tiempos = []
intensidades = []
grafico_activo = threading.Event()

# Crear el gráfico
fig, ax = plt.subplots()
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

# Crear los botones y el campo de entrada
frame_controles = tk.Frame(root)
frame_controles.pack(side=tk.BOTTOM, fill=tk.X)

btn_iniciar = tk.Button(frame_controles, text="Iniciar Medición", bg="green", command=iniciar_medicion)
btn_iniciar.pack(side=tk.LEFT, padx=10, pady=10)

btn_cancelar = tk.Button(frame_controles, text="Cancelar Medición", bg="red", command=cancelar_medicion)
btn_cancelar.pack(side=tk.LEFT, padx=10, pady=10)

label_tiempo = tk.Label(frame_controles, text="Tiempo de medición (s):")
label_tiempo.pack(side=tk.LEFT, padx=10, pady=10)

entry_tiempo = tk.Entry(frame_controles)
entry_tiempo.pack(side=tk.LEFT, padx=10, pady=10)

# Conectar con Arduino
try:
    ser = serial.Serial(puerto, baudrate, timeout=1)
    time.sleep(1)  # Esperar a que Arduino esté listo
    print("Conectado a Arduino.")
except serial.SerialException:
    messagebox.showerror("Error", f"No se pudo abrir el puerto {puerto}. Verifique la conexión.")
    exit()

# Iniciar la interfaz gráfica
root.mainloop()

# Cerrar la conexión con Arduino al salir
if 'ser' in locals() and ser.is_open:
    ser.close()
    print("Conexión cerrada.")
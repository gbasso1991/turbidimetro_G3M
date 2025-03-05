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
from tkinter import messagebox
import threading
import os  

#%% guardar_resultados
def guardar_resultados(ruta_subdirectorio, tiempos, intensidades, absorbancias):
    '''Guarda tabla en .txt y gráfico Abs_vs_t en .png en el subdirectorio especificado.'''
    fecha_nombre = datetime.now().strftime("%y%m%d_%H%M%S")  # Formato aammdd_hhmmss

    # Guardar datos en .txt
    nombre_archivo_txt = os.path.join(ruta_subdirectorio, f"mediciones_{fecha_nombre}.txt")
    with open(nombre_archivo_txt, "w") as archivo:
        archivo.write("Tiempo (s), Intensidad, Absorbancia\n")
        for t, i, a in zip(tiempos, intensidades, absorbancias):
            archivo.write(f"{t}, {i}, {a}\n")
    print(f"Datos guardados en {nombre_archivo_txt}")

    # Guardar gráfico en .png
    nombre_grafico = os.path.join(ruta_subdirectorio, f"grafico_{fecha_nombre}.png")
    fig.savefig(nombre_grafico, dpi=300)  # Guarda el gráfico con DPI 300
    print(f"Gráfico guardado en {nombre_grafico}")
#%% medir_intensidad c/Arduino
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
#%% realizar_mediciones 
def realizar_mediciones(ser, duracion, ruta_subdirectorio, tiempos, intensidades, absorbancias, grafico_activo):
    """Realiza mediciones durante el tiempo especificado y almacena los datos en un archivo."""
    inicio = time.time()

    while grafico_activo.is_set() and (duracion is None or time.time() - inicio < duracion):
        tiempo_actual = round(time.time() - inicio, 2)  # Tiempo relativo en segundos
        intensidad = medir_intensidad(ser)              # Le pido la medida al Arduino
        # Absorbancia: el valor 3520 corresponde a la intensidad maxima registrada con la cubeta con agua
        abs_rel = np.log10(3520/intensidad) if intensidad is not None else None  
        if intensidad is not None:
            tiempos.append(tiempo_actual)
            intensidades.append(intensidad)
            absorbancias.append(abs_rel)
            print(f"Tiempo: {tiempo_actual}s - Intensidad: {intensidad} - Absorbancia rel: {abs_rel}")

        time.sleep(0.88)  # Ajusta el intervalo entre mediciones

    print("Medición concluida.")
    
    if duracion is not None and time.time() - inicio >= duracion:
        messagebox.showinfo("Medición completada", "La medición ha concluido correctamente.")
    guardar_resultados(ruta_subdirectorio, tiempos, intensidades, absorbancias)  # Guardar resultados
    grafico_activo.clear()  # Desactiva el evento para detener la medición
    tiempos.clear()  # Limpia las listas para una nueva medición
    intensidades.clear()
    absorbancias.clear()
#%% iniciar_medicion
def iniciar_medicion():
    """Inicia la medición en un hilo separado."""
    global ser, grafico_activo, hilo_medicion, ruta_subdirectorio

    if grafico_activo.is_set():
        messagebox.showwarning("Advertencia", "Ya hay una medición en curso.")
        return
    try:
        duracion = float(entry_tiempo.get()) if entry_tiempo.get() else None
    except ValueError:
        messagebox.showerror("Error", "Ingrese un tiempo de medición válido.")
        return
    
    grafico_activo.set()
    tiempos.clear()
    intensidades.clear()
    absorbancias.clear()

    # Crear subdirectorio al inicio de la medición
    fecha_nombre = datetime.now().strftime("%y%m%d_%H%M%S")  # Formato aammdd_hhmmss
    ruta_subdirectorio = os.path.join(os.getcwd(), fecha_nombre)
    if not os.path.exists(ruta_subdirectorio):
        os.makedirs(ruta_subdirectorio)

    # Pasar todos los argumentos necesarios a realizar_mediciones
    hilo_medicion = threading.Thread(
        target=realizar_mediciones,
        args=(ser, duracion, ruta_subdirectorio, tiempos, intensidades, absorbancias, grafico_activo)
    )
    hilo_medicion.start()

    actualizar_grafico()
#%% detener medicion
def detener_medicion():
    """Cancela la medición en curso."""
    global grafico_activo, ruta_subdirectorio

    if grafico_activo.is_set():
        #guardar_resultados(ruta_subdirectorio, tiempos, intensidades, absorbancias)  # Guardar resultados
        grafico_activo.clear()
        messagebox.showinfo("Información", "Medición detenida.")

    else:
        messagebox.showwarning("Advertencia", "No hay una medición en curso.")
#%% Actualizar grafico
def actualizar_grafico():
    """Actualiza el gráfico en tiempo real."""
    if grafico_activo.is_set():
        ax.clear()
        ax.plot(tiempos, absorbancias, 'o-')
        ax.grid()
        ax.set_xlabel("Tiempo (s)")
        ax.set_ylabel("Absorbancia (u.a.)")
        ax.set_title("Turbidimetría")
        canvas.draw()

    if grafico_activo.is_set():
        root.after(1000, actualizar_grafico)  # Actualizar cada segundo

#%% Deteccion de puerto y Conexión con Arduino
puertos_disponibles = serial.tools.list_ports.comports()  # Listar los puertos seriales disponibles
puerto_activo = None
# Buscar el primer puerto USB activo (ttyUSB* o COM*)
for puerto in puertos_disponibles:
    print(f"Puerto: {puerto.device}")
    if "ttyUSB" in puerto.device or "COM" in puerto.device:  # Verificar si el puerto es ttyUSB* o COM*
        try:
            # Intenta abrir el puerto
            conexion = serial.Serial(puerto.device)
            conexion.close()  # Cierra la conexión
            print(f"Puerto activo: {puerto.device}")
            puerto_activo = puerto.device  # Guardar el nombre del puerto activo
            break  # Salir del bucle después de encontrar el primer puerto activo
        except (serial.SerialException, OSError):
            print(f"Puerto inactivo: {puerto.device}")

# Verificar si se encontró un puerto activo
if puerto_activo:
    print('-' * 40, '\n', f"Puerto seleccionado: {puerto_activo}")
else:
    print("No se encontraron puertos activos.")
    exit()

#%% Configuración del puerto serie
puerto = puerto_activo  # lo detecta automaticamente para que sea cross plataform 
baudrate = 9600  

#%% Iniciar la interfaz gráfica
root = tk.Tk()
root.title("G3M - Turbidímetro")

# Variables globales
tiempos = []
intensidades = []
absorbancias = []
grafico_activo = threading.Event()
ruta_subdirectorio = None  # Ruta del subdirectorio actual

# Crear el gráfico
fig, ax = plt.subplots()
canvas = FigureCanvasTkAgg(fig, master=root)
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

# Crear los botones y el campo de entrada
frame_controles = tk.Frame(root)
frame_controles.pack(side=tk.BOTTOM, fill=tk.X)

btn_iniciar = tk.Button(frame_controles, text="Iniciar Medición", bg="green", command=iniciar_medicion)
btn_iniciar.pack(side=tk.LEFT, padx=10, pady=10)

btn_cancelar = tk.Button(frame_controles, text="Detener Medición", bg="red", command=detener_medicion)
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
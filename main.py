import os


from escape_metro import *
from animar_trayectoria import animar

if __name__ == "__main__":
    carpeta = os.path.dirname(os.path.abspath(__file__))
    grafo, mision, clausuras = leer_entrada(os.path.join(carpeta, "input.txt"))
    plan = planificar(grafo, mision, clausuras)
    ruta_salida = os.path.join(carpeta, "output.txt")
    escribir_salida(ruta_salida, grafo, plan)
    escribir_json(os.path.join(carpeta, "output.json"), grafo, mision, plan)

    with open(ruta_salida, encoding="utf-8") as archivo:
        print(archivo.read())

    animar()

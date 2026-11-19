import os
import heapq
import re
import math

INFINITO = float("inf")


class Grafo:
    def __init__(self, ids, transbordos, tuneles, lineas_retrasadas):
        self.n = len(ids)
        self.ids = ids
        self.indice = {ident: i for i, ident in enumerate(ids)}
        self.transbordo = [transbordos[ident] for ident in ids]
        self.punto = [0] * (self.n + 1)
        for origen, _, _, _ in tuneles:
            self.punto[self.indice[origen] + 1] += 1
        for i in range(self.n):
            self.punto[i + 1] += self.punto[i]
        m = len(tuneles)
        self.destino = [0] * m
        self.tiempo = [0] * m
        self.linea = [""] * m
        siguiente = self.punto[:self.n]
        for origen, destino, tiempo, linea in tuneles:
            u = self.indice[origen]
            k = siguiente[u]
            siguiente[u] += 1
            self.destino[k] = self.indice[destino]
            self.tiempo[k] = tiempo * 2 if linea in lineas_retrasadas else tiempo
            self.linea[k] = linea

    def arcos_salientes(self, u):
        return range(self.punto[u], self.punto[u + 1])


class Ruta:
    def __init__(self, costo, estaciones, arcos):
        self.costo = costo
        self.estaciones = estaciones
        self.arcos = arcos


class Itinerario:
    def __init__(self, grafo, ruta, salida):
        self.salida = salida
        self.pasos = []
        self.estadias = []
        self.tramos = []
        self.transbordos = []
        t = salida
        llegada = 0
        for i, k in enumerate(ruta.arcos):
            u = ruta.estaciones[i]
            if i > 0 and grafo.linea[ruta.arcos[i - 1]] != grafo.linea[k]:
                fin = t + grafo.transbordo[u]
                self.transbordos.append((t, fin, grafo.linea[ruta.arcos[i - 1]], grafo.linea[k]))
                self.pasos.append((fin, u, "transbordo", grafo.linea[k]))
                t = fin
            self.estadias.append((u, llegada, t))
            v = grafo.destino[k]
            self.tramos.append(((min(u, v), max(u, v), grafo.linea[k]), t, t + grafo.tiempo[k]))
            t += grafo.tiempo[k]
            llegada = t
            self.pasos.append((t, v, "viaje", grafo.linea[k]))
        self.estadias.append((ruta.estaciones[-1], llegada, t))

    def respeta_clausuras(self, clausuras):
        for inicio, fin, anterior, nueva in self.transbordos:
            for linea, desde, hasta in clausuras:
                if linea in (anterior, nueva) and inicio <= hasta and fin >= desde:
                    return False
        return True


def leer_entrada(ruta_archivo):
    with open(ruta_archivo, encoding="utf-8-sig", errors="ignore") as archivo:
        filas = [linea.split() for linea in archivo if linea.strip() and not linea.strip().startswith("#")]
    n, m = int(filas[0][0]), int(filas[0][1])
    ids = [int(fila[0]) for fila in filas[1:n + 1]]
    transbordos = {int(fila[0]): int(fila[1]) for fila in filas[1:n + 1]}
    tuneles = [(int(f[0]), int(f[1]), int(f[2]), f[3]) for f in filas[n + 1:n + m + 1]]
    mision = [int(x) for x in filas[n + m + 1][:4]]
    clausuras = []
    lineas_retrasadas = set()
    for fila in filas[n + m + 2:]:
        if fila[0].upper() == "CLAUSURA":
            clausuras.append((fila[1], int(fila[2]), int(fila[3])))
        elif fila[0].upper() == "RETRASO":
            lineas_retrasadas.add(fila[1])
    return Grafo(ids, transbordos, tuneles, lineas_retrasadas), mision, clausuras


def cotas_hasta(grafo, destino):
    cota = [INFINITO] * grafo.n
    cota[destino] = 0
    for _ in range(grafo.n - 1):
        hubo_cambio = False
        for u in range(grafo.n):
            for k in grafo.arcos_salientes(u):
                candidato = grafo.tiempo[k] + cota[grafo.destino[k]]
                if candidato < cota[u]:
                    cota[u] = candidato
                    hubo_cambio = True
        if not hubo_cambio:
            break
    return cota


def rutas_en_orden(grafo, origen, destino):
    cota = cotas_hasta(grafo, destino)
    if cota[origen] == INFINITO:
        return
    cola = [(cota[origen], 0, 0, (origen,), ())]
    contador = 1
    while cola:
        _, costo, _, estaciones, arcos = heapq.heappop(cola)
        u = estaciones[-1]
        if u == destino:
            yield Ruta(costo, estaciones, arcos)
            continue
        for k in grafo.arcos_salientes(u):
            v = grafo.destino[k]
            if v in estaciones or cota[v] == INFINITO:
                continue
            nuevo_costo = costo + grafo.tiempo[k]
            if arcos and grafo.linea[arcos[-1]] != grafo.linea[k]:
                nuevo_costo += grafo.transbordo[u]
            heapq.heappush(cola, (nuevo_costo + cota[v], nuevo_costo, contador, estaciones + (v,), arcos + (k,)))
            contador += 1


def hay_colision(itin_p, itin_a):
    ultima_p = len(itin_p.estadias) - 1
    ultima_a = len(itin_a.estadias) - 1
    for i, (v, a1, b1) in enumerate(itin_p.estadias):
        for j, (w, a2, b2) in enumerate(itin_a.estadias):
            if v == w and max(a1, a2) <= min(b1, b2) and (i, j) != (ultima_p, ultima_a):
                return True
    for tunel_p, a1, b1 in itin_p.tramos:
        for tunel_a, a2, b2 in itin_a.tramos:
            if tunel_p == tunel_a and max(a1, a2) < min(b1, b2):
                return True
    return False


def evaluar_par(grafo, ruta_p, ruta_a, clausuras):
    total = max(ruta_p.costo, ruta_a.costo)
    itin_p = Itinerario(grafo, ruta_p, total - ruta_p.costo)
    itin_a = Itinerario(grafo, ruta_a, total - ruta_a.costo)
    if not itin_p.respeta_clausuras(clausuras) or not itin_a.respeta_clausuras(clausuras):
        return None
    if hay_colision(itin_p, itin_a):
        return None
    return total, ruta_p, ruta_a, itin_p, itin_a


def planificar(grafo, mision, clausuras):
    origen_p, origen_a, destino_p, destino_a = (grafo.indice[x] for x in mision)
    generadores = [rutas_en_orden(grafo, origen_p, destino_p), rutas_en_orden(grafo, origen_a, destino_a)]
    proximas = [next(generadores[0], None), next(generadores[1], None)]
    encontradas = [[], []]
    while proximas[0] is not None or proximas[1] is not None:
        if any(proximas[i] is None and not encontradas[i] for i in (0, 1)):
            return None
        if proximas[1] is None or (proximas[0] is not None and proximas[0].costo <= proximas[1].costo):
            quien = 0
        else:
            quien = 1
        nueva = proximas[quien]
        encontradas[quien].append(nueva)
        proximas[quien] = next(generadores[quien], None)
        for otra in encontradas[1 - quien]:
            ruta_p, ruta_a = (nueva, otra) if quien == 0 else (otra, nueva)
            plan = evaluar_par(grafo, ruta_p, ruta_a, clausuras)
            if plan is not None:
                return plan
    return None


def escribir_salida(ruta_archivo, grafo, plan):
    lineas = ["=== PLAN DE ESCAPE CONFIGURADO ==="]
    if plan is None:
        lineas.append("Resultado de Sincronización: FRACASO. No existe un par de rutas sin colisiones que permita la llegada simultánea al búnker.")
    else:
        total, ruta_p, ruta_a, itin_p, itin_a = plan
        personajes = [("Pierre", "D1", ruta_p, itin_p), ("Amélie", "D2", ruta_a, itin_a)]
        lineas.append(f"Tiempo Total de la Operación: {total} minutos")
        lineas.append("")
        lineas.append("[PROGRAMACIÓN DE SALIDAS]")
        for nombre, _, _, itin in personajes:
            texto = f"* {nombre} arranca en el minuto: {itin.salida}"
            if itin.salida > 0:
                texto += f" (Debe esperar {itin.salida} minutos en su estación de origen)"
            lineas.append(texto)
        for nombre, compuerta, ruta, itin in personajes:
            lineas.append("")
            lineas.append(f"[RUTA DE {nombre.upper()} (Tiempo total de viaje: {ruta.costo} min)]")
            inicio = "Origen - Inicia Movimiento" if itin.salida > 0 else "Origen"
            lineas.append(f"Minuto {itin.salida}: Estación {grafo.ids[ruta.estaciones[0]]} ({inicio})")
            for i, (minuto, estacion, tipo, linea) in enumerate(itin.pasos):
                if i == len(itin.pasos) - 1:
                    detalle = f"Destino Compuerta {compuerta}"
                elif tipo == "transbordo":
                    detalle = f"Termina Transbordo a {linea}"
                else:
                    detalle = f"Viaje {linea}"
                lineas.append(f"Minuto {minuto}: Estación {grafo.ids[estacion]} ({detalle})")
        lineas.append("")
        lineas.append(f"Resultado de Sincronización: ÉXITO. Llegada simultánea en el minuto {total}.")
    with open(ruta_archivo, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas) + "\n")


def main():
    carpeta = os.path.dirname(os.path.abspath(__file__))
    grafo, mision, clausuras = leer_entrada(os.path.join(carpeta, "input.txt"))
    plan = planificar(grafo, mision, clausuras)
    escribir_salida(os.path.join(carpeta, "output.txt"), grafo, plan)
    ruta_salida = os.path.join(carpeta, "output.txt")
    escribir_salida(ruta_salida, grafo, plan)

    with open(ruta_salida, encoding="utf-8") as archivo:
        print(archivo.read())


if __name__ == "__main__":
    main()

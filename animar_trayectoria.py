import json
import math
from pathlib import Path
from textwrap import fill

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.animation import FuncAnimation
from matplotlib.lines import Line2D
from matplotlib.widgets import Button


def cargar_datos():
    ruta_json = Path(__file__).with_name("output.json")
    if not ruta_json.exists():
        raise FileNotFoundError(
            "No se encontró output.json. Ejecuta primero escape_metro.py."
        )

    with ruta_json.open(encoding="utf-8") as archivo:
        datos = json.load(archivo)
    if not datos.get("plan"):
        raise ValueError("output.json no contiene un plan de escape válido.")
    return datos


def crear_tramos(ruta, tiempos_transbordo):
    tramos = []
    minuto = ruta["minuto_salida"]
    linea_anterior = None

    for tunel in ruta["tuneles"]:
        transbordo = None
        if linea_anterior is not None and tunel["linea"] != linea_anterior:
            fin_transbordo = minuto + tiempos_transbordo[tunel["origen"]]
            transbordo = {
                "inicio": minuto,
                "fin": fin_transbordo,
                "estacion": tunel["origen"],
                "linea_anterior": linea_anterior,
                "linea_siguiente": tunel["linea"],
            }
            minuto = fin_transbordo

        llegada = minuto + tunel["tiempo_viaje"]
        tramos.append({
            "inicio": minuto,
            "fin": llegada,
            "origen": tunel["origen"],
            "destino": tunel["destino"],
            "linea": tunel["linea"],
            "transbordo": transbordo,
        })
        minuto = llegada
        linea_anterior = tunel["linea"]

    return tramos


def estado_del_viajero(ruta, tramos, minuto):
    origen = ruta["estaciones"][0]
    if minuto < ruta["minuto_salida"]:
        if tramos:
            primero = tramos[0]
            decision = (
                f"Salir en minuto {ruta['minuto_salida']:g} hacia estación "
                f"{primero['destino']} por {primero['linea']}."
            )
        else:
            decision = f"Esperar hasta minuto {ruta['minuto_salida']:g}."
        elegido = (primero["destino"], primero["linea"]) if tramos else None
        return origen, "esperando", decision, elegido

    for tramo in tramos:
        transbordo = tramo["transbordo"]
        if transbordo and transbordo["inicio"] <= minuto < transbordo["fin"]:
            decision = (
                f"Cambiar de {transbordo['linea_anterior']} a "
                f"{transbordo['linea_siguiente']}; luego ir a estación "
                f"{tramo['destino']}."
            )
            elegido = (tramo["destino"], tramo["linea"])
            return transbordo["estacion"], "transbordo", decision, elegido
        if minuto < tramo["inicio"]:
            elegido = (tramo["destino"], tramo["linea"])
            return (
                tramo["origen"],
                "esperando",
                f"Ir a estación {tramo['destino']} por {tramo['linea']}.",
                elegido,
            )
        if minuto < tramo["fin"]:
            decision = (
                f"Continuar a estación {tramo['destino']} por "
                f"{tramo['linea']}; llegada en minuto {tramo['fin']:g}."
            )
            elegido = (tramo["destino"], tramo["linea"])
            return tramo["origen"], f"en túnel hacia {tramo['destino']}", decision, elegido

    destino = ruta["estaciones"][-1]
    return destino, "destino alcanzado", f"Destino {ruta['compuerta']} alcanzado.", None


def obtener_vecinos(grafo):
    vecinos = {estacion["id"]: set() for estacion in grafo["estaciones"]}
    for tunel in grafo["tuneles"]:
        vecinos[tunel["origen"]].add((tunel["destino"], tunel["linea"]))
    return {
        estacion: sorted(opciones)
        for estacion, opciones in vecinos.items()
    }


def posicion_en_trayecto(tramos, estaciones, posiciones, minuto):
    if not tramos:
        x, y = posiciones[estaciones[0]]
        return x, y

    for tramo in tramos:
        if minuto < tramo["inicio"]:
            x, y = posiciones[tramo["origen"]]
            return x, y
        if minuto < tramo["fin"]:
            x0, y0 = posiciones[tramo["origen"]]
            x1, y1 = posiciones[tramo["destino"]]
            fraccion = (minuto - tramo["inicio"]) / (tramo["fin"] - tramo["inicio"])
            return x0 + fraccion * (x1 - x0), y0 + fraccion * (y1 - y0)

    x, y = posiciones[tramos[-1]["destino"]]
    return x, y


def reiniciar_animacion(animacion):
    animacion.event_source.stop()
    animacion.frame_seq = animacion.new_frame_seq()
    animacion.event_source.start()


def animar():
    datos = cargar_datos()
    estaciones = {estacion["id"]: estacion for estacion in datos["grafo"]["estaciones"]}
    vecinos = obtener_vecinos(datos["grafo"])
    tiempos_transbordo = {
        estacion["id"]: estacion["tiempo_transbordo"]
        for estacion in datos["grafo"]["estaciones"]
    }
    rutas = datos["plan"]["rutas"]

    grafo = nx.Graph()
    grafo.add_nodes_from(estaciones)
    grafo.add_edges_from(
        (tunel["origen"], tunel["destino"])
        for tunel in datos["grafo"]["tuneles"]
    )
    posiciones = nx.spring_layout(
        grafo,
        seed=7,
        k=1.2 / math.sqrt(max(grafo.number_of_nodes(), 1)),
        iterations=120,
        weight=None,
    )
    tramos_por_personaje = {
        ruta["personaje"]: crear_tramos(ruta, tiempos_transbordo)
        for ruta in rutas
    }

    fig, ax = plt.subplots(figsize=(12, 8))
    fig.subplots_adjust(right=0.69, bottom=0.16)
    nx.draw_networkx_edges(
        grafo, posiciones, ax=ax, edge_color="#cbd5e1", width=1.5
    )
    nx.draw_networkx_nodes(
        grafo,
        posiciones,
        ax=ax,
        node_color="#f8fafc",
        edgecolors="#334155",
        linewidths=1.5,
        node_size=430,
    )
    nx.draw_networkx_labels(
        grafo, posiciones, ax=ax, font_size=9, font_weight="bold"
    )

    lineas = sorted({
        tunel["linea"]
        for ruta in rutas
        for tunel in ruta["tuneles"]
    })
    mapa_colores = plt.get_cmap("tab10")
    colores_linea = {
        linea: mapa_colores(i % mapa_colores.N)
        for i, linea in enumerate(lineas)
    }
    for ruta in rutas:
        for tunel in ruta["tuneles"]:
            x0, y0 = posiciones[tunel["origen"]]
            x1, y1 = posiciones[tunel["destino"]]
            ax.plot(
                (x0, x1),
                (y0, y1),
                color=colores_linea[tunel["linea"]],
                linewidth=4,
                alpha=0.8,
                solid_capstyle="round",
                zorder=2,
            )

    colores_personaje = {
        "Pierre": "#dc2626",
        "Amélie": "#2563eb",
    }
    marcadores = {}
    for ruta in rutas:
        personaje = ruta["personaje"]
        marcadores[personaje] = ax.scatter(
            [],
            [],
            s=180,
            marker="o",
            color=colores_personaje.get(personaje, "#7c3aed"),
            edgecolors="white",
            linewidths=1.5,
            zorder=5,
            label=personaje,
        )

    leyenda = [
        Line2D([0], [0], color=colores_linea[linea], lw=4, label=linea)
        for linea in lineas
    ]
    leyenda.extend(
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=colores_personaje.get(ruta["personaje"], "#7c3aed"),
            markeredgecolor="white",
            markersize=10,
            label=ruta["personaje"],
        )
        for ruta in rutas
    )
    fig.legend(
        handles=leyenda,
        loc="upper left",
        bbox_to_anchor=(0.72, 0.98),
        frameon=False,
    )
    estado_texto = fig.text(
        0.72,
        0.70,
        "",
        va="top",
        fontsize=9,
        wrap=True,
        bbox={
            "boxstyle": "round,pad=0.6",
            "facecolor": "#f8fafc",
            "edgecolor": "#cbd5e1",
        },
    )

    tiempo_total = datos["plan"]["tiempo_total"]
    reloj = ax.text(
        0.02,
        0.98,
        "",
        transform=ax.transAxes,
        va="top",
        fontsize=12,
        bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "#cbd5e1"},
    )
    ax.set_title("Escape del metro: recorrido animado")
    ax.set_axis_off()
    ax.margins(0.18)

    cantidad_frames = max(2, int(tiempo_total * 5) + 1)
    minutos = [
        i * tiempo_total / (cantidad_frames - 1)
        for i in range(cantidad_frames)
    ]
    animacion_ref = [None]

    def actualizar(minuto):
        reloj.set_text(f"Minuto {minuto:.1f} / {tiempo_total}")
        estados = ["Estado actual y siguiente decisión"]
        for ruta in rutas:
            personaje = ruta["personaje"]
            nodo, estado, decision, vecino_elegido = estado_del_viajero(
                ruta, tramos_por_personaje[personaje], minuto
            )
            opciones = ", ".join(
                f"{destino} ({linea})"
                for destino, linea in vecinos[nodo]
            ) or "ninguno"
            if vecino_elegido is None:
                elegido_texto = (
                    "ninguno (destino alcanzado)"
                    if estado == "destino alcanzado"
                    else "ninguno"
                )
            else:
                elegido_texto = f"{vecino_elegido[0]} ({vecino_elegido[1]})"
            decision_texto = fill(
                "Decisión: " + decision,
                width=40,
                subsequent_indent="  ",
            )
            vecinos_texto = fill(
                "Vecinos disponibles: " + opciones,
                width=40,
                subsequent_indent="  ",
            )
            elegido_texto = fill(
                "Vecino elegido: " + elegido_texto,
                width=40,
                subsequent_indent="  ",
            )
            estados.append(
                f"{personaje}\nNodo actual: estación {nodo} ({estado})\n"
                f"{vecinos_texto}\n{elegido_texto}\n{decision_texto}"
            )
            posicion = posicion_en_trayecto(
                tramos_por_personaje[personaje],
                ruta["estaciones"],
                posiciones,
                minuto,
            )
            marcadores[personaje].set_offsets([posicion])
        estados.append(
            fill(
                "Las rutas se exploran por costo estimado y se validan "
                "contra cierres y colisiones.",
                width=40,
            )
        )
        estado_texto.set_text("\n\n".join(estados))
        animacion = animacion_ref[0]
        if minuto >= tiempo_total and animacion is not None:
            animacion.event_source.stop()
        return (*marcadores.values(), reloj, estado_texto)

    animacion = FuncAnimation(
        fig,
        actualizar,
        frames=minutos,
        interval=80,
        repeat=True,
        blit=False,
    )
    animacion_ref[0] = animacion
    boton_ax = fig.add_axes([0.39, 0.035, 0.22, 0.065])
    boton_reiniciar = Button(boton_ax, "Reiniciar")
    boton_reiniciar.on_clicked(lambda _: reiniciar_animacion(animacion))
    plt.show()
    return animacion


if __name__ == "__main__":
    animar()

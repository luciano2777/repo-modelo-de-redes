# repo-modelo-de-redes

Ejecuta `python escape_metro.py` para generar `output.txt` y `output.json`.
El JSON contiene las estaciones y túneles dirigidos del grafo, la misión y
las rutas calculadas para Pierre y Amélie. Los tiempos de los túneles reflejan
los retrasos técnicos indicados en `input.txt`.

Para animar el recorrido, instala las dependencias con
`python3 -m pip install -r requirements.txt` y ejecuta
`python3 animar_trayectoria.py`. La animación lee las rutas de `output.json`;
si cambias la entrada, ejecuta primero `python3 escape_metro.py` para
regenerarlo. La ventana incluye un botón para reiniciar la animación y un
panel que muestra el nodo actual, sus vecinos y el vecino elegido para cada
viajero, además de un resumen del criterio usado para seleccionar las rutas.

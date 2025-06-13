import Creation_map as Map
from Interface import HTMLViewerApp
import os

# Configuration des chemins
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_FILE = os.path.join(BASE_DIR, "alger_reseau.graphml")
EMPTY_PLOT = os.path.join(BASE_DIR, "empty_plot.html")
FULL_PLOT = os.path.join(BASE_DIR, "plot.html")
DIJKSTRA_PLOT = os.path.join(BASE_DIR, "dijkstra.html")

# Initialisation du réseau
transport_network = Map.TransportNetwork()
transport_network.load_graph(filepath=GRAPH_FILE)

# Création des fichiers HTML si nécessaire
if not os.path.exists(EMPTY_PLOT):
    fig = Map.TransportNetwork.empty_map()
    fig.write_html(EMPTY_PLOT)

if not os.path.exists(FULL_PLOT):
    transport_network.save_html(FULL_PLOT)

# Lancement de l'application
app = HTMLViewerApp(html_path=EMPTY_PLOT, transport_network=transport_network)
app.MainLoop()
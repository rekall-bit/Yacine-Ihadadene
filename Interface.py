import csv
import os
from datetime import datetime
import networkx as nx
import osmnx as ox
import requests
import wx
import wx.html2
import Creation_map as Transport_network


class PathInputDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Entrer les points du chemin", size=(500, 300))
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.start_label = wx.StaticText(panel, label="Point de départ:")
        self.start_text = wx.TextCtrl(panel)
        main_sizer.Add(self.start_label, 0, wx.ALL, 5)
        main_sizer.Add(self.start_text, 0, wx.EXPAND | wx.ALL, 5)

        self.mid_label = wx.StaticText(panel, label="point a eviter:")
        self.mid_text = wx.TextCtrl(panel)
        main_sizer.Add(self.mid_label, 0, wx.ALL, 5)
        main_sizer.Add(self.mid_text, 0, wx.EXPAND | wx.ALL, 5)

        self.end_label = wx.StaticText(panel, label="Point d'arrivée:")
        self.end_text = wx.TextCtrl(panel)
        main_sizer.Add(self.end_label, 0, wx.ALL, 5)
        main_sizer.Add(self.end_text, 0, wx.EXPAND | wx.ALL, 5)

        btn_sizer = wx.StdDialogButtonSizer()
        btn_ok = wx.Button(panel, wx.ID_OK)
        btn_cancel = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(main_sizer)

class PathInputDialog1(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="Entrer les points du chemin", size=(300, 300))
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.start_label = wx.StaticText(panel, label="Point de choix:")
        self.start_text = wx.TextCtrl(panel)
        main_sizer.Add(self.start_label, 0, wx.ALL, 5)
        main_sizer.Add(self.start_text, 0, wx.EXPAND | wx.ALL, 5)

        btn_sizer = wx.StdDialogButtonSizer()
        btn_ok = wx.Button(panel, wx.ID_OK)
        btn_cancel = wx.Button(panel, wx.ID_CANCEL)
        btn_sizer.AddButton(btn_ok)
        btn_sizer.AddButton(btn_cancel)
        btn_sizer.Realize()
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(main_sizer)


class HTMLViewerApp(wx.App):
    def __init__(self, html_path, transport_network):
        self.html_path = html_path
        self.transport_network = transport_network
        super().__init__(clearSigInt=True)

    def OnInit(self):
        self.frame = MainFrame(html_path=self.html_path, transport_network=self.transport_network)
        self.frame.Show()
        return True


class MainFrame(wx.Frame):
    def __init__(self, html_path, transport_network):
        super().__init__(None, title="Visualiseur de réseau de transport", size=(1000, 800))
        self.current_network = transport_network
        self.base_network = transport_network
        self.base_network.load_graph("alger_reseau.graphml")
        self.html_path = html_path
        self.panel = wx.Panel(self)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self._setup_widgets()
        self._load_html_content()

    def _setup_widgets(self):
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)

        buttons = [
            ("Statistiques du graphe", self.on_show_info),
            ("Trouver un chemin djikstra", self.trouver_chemin),
            ("Trouver un chemin court", self.trouver_chemin_court),
            ("Retour", self.on_retour),
            ("Carte complète", self.map_full),
            ("afficher la matrice", self.matrice),
            ("afficher les voisins", self.voisinage)
        ]

        for label, handler in buttons:
            btn = wx.Button(self.panel, label=label)
            btn.Bind(wx.EVT_BUTTON, handler)
            button_sizer.Add(btn, 0, wx.ALL, 5)

        self.browser = wx.html2.WebView.New(self.panel)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(button_sizer, 0, wx.EXPAND)
        main_sizer.Add(self.browser, 1, wx.EXPAND)
        self.panel.SetSizer(main_sizer)

    def _load_html_content(self):
        if os.path.exists(self.html_path):
            self.browser.LoadURL(f"file:///{os.path.abspath(self.html_path)}")
        else:
            wx.MessageBox(f"Fichier introuvable: {self.html_path}", "Erreur", wx.OK | wx.ICON_ERROR)

    def on_show_info(self, event):
        network = self.current_network

        message = (
            "=== Informations de base ===\n"
            f"Nombre de nœuds: {len(network.G.nodes)}\n"
            f"Nombre d'arêtes: {len(network.G.edges)}\n"
            f"Type de vue: {'Chemin Dijkstra' if network != self.base_network else 'Réseau complet'} \n"
            f"les degrés des sommets du graphe: {self.base_network.calculer_degres()} \n"
            f"le chemin est eulerien: {self.base_network.cycle_eulerien()} \n"
        )
        wx.MessageBox(message, "Statistiques", wx.OK | wx.ICON_INFORMATION)

    @staticmethod
    def get_coordinates(place_name):
        base_url = "https://nominatim.openstreetmap.org/search"
        params = {'q': place_name, 'format': 'json', 'limit': 1}
        headers = {'User-Agent': 'TransportNetworkApp/1.0'}

        try:
            response = requests.get(base_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
        except Exception:
            pass
        return None, None

    def trouver_chemin(self, event):
        dlg = PathInputDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            start_place = dlg.start_text.GetValue()
            mid_place = dlg.mid_text.GetValue()
            end_place = dlg.end_text.GetValue()

            try:
                start_lat, start_lon = self.get_coordinates(start_place)
                end_lat, end_lon = self.get_coordinates(end_place)

                if None in (start_lat, start_lon):
                    wx.MessageBox("Impossible de localiser les points", "Erreur", wx.OK | wx.ICON_ERROR)
                    return

                source_node = self.base_network.get_nodes_by_attribute('nearest', point=(start_lat, start_lon))
                target_node = self.base_network.get_nodes_by_attribute('nearest', point=(end_lat, end_lon))
                if not source_node or not target_node:
                    wx.MessageBox("Nœuds obligatoires non trouvés", "Erreur", wx.OK | wx.ICON_ERROR)
                    return

                # Créer une copie du graphe pour modification
                G_temp = self.base_network.G.copy()

                # Zone d'exclusion si un point à éviter est spécifié
                if mid_place:
                    ignore_lat, ignore_lon = self.get_coordinates(mid_place)
                    # Définir le rayon d'exclusion (en mètres)
                    exclusion_radius = 500  # 500 mètres

                    # Trouver tous les nœuds dans le rayon d'exclusion
                    avoid_nodes = []
                    for node, data in G_temp.nodes(data=True):
                        node_lat = data['y']
                        node_lon = data['x']

                        # Calculer la distance (méthode simplifiée)
                        distance = ox.distance.great_circle(
                            ignore_lat, ignore_lon,
                            node_lat, node_lon
                        )

                        if distance <= exclusion_radius:
                            avoid_nodes.append(node)

                    # Augmenter considérablement le poids des arêtes dans la zone
                    for u, v, data in G_temp.edges(data=True):
                        if u in avoid_nodes or v in avoid_nodes:
                            if 'length' in data:
                                data['weight'] = data['length'] * 100  # Rend la zone très peu attractive

                    # Calculer le chemin en évitant la zone
                    full_path = nx.dijkstra_path(
                        G_temp,
                        source_node,
                        target_node,
                        weight='weight'
                    )
                else:
                    # Essayer sans pénalités si aucun chemin n'est trouvé
                    full_path = nx.dijkstra_path(
                        self.base_network.G,
                        source_node,
                        target_node,
                        weight='length'
                    )

                    # Création du graphe du chemin
                path_subgraph = self.base_network.G.subgraph(full_path).copy()
                path_subgraph.graph['crs'] = "EPSG:4326"

                # Marquage des points importants
                path_subgraph.nodes[source_node]['important'] = True
                path_subgraph.nodes[target_node]['important'] = True

                path_network = Transport_network.TransportNetwork()
                path_network.G = path_subgraph
                path_network.process_graph_data()

                # Sauvegarde et affichage
                output_path = os.path.join(self.base_dir, "djikstra.html")
                path_network.save_html(output_path)
                self.current_network = path_network
                self.html_path = output_path
                self._load_html_content()
                wx.MessageBox(f"Chemin trouver, il est de longeur {len(path_network.G.nodes)} \nle chemin est eulerien:{path_network.cycle_eulerien()}", "CHEMIN TROUVE!", wx.OK | wx.ICON_INFORMATION)

                # Sauvegarde historique
                with open('saved_paths.csv', 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([start_place, end_place, datetime.now().isoformat()])

            except nx.NetworkXNoPath:
                wx.MessageBox("Aucun chemin trouvé entre les points", "Erreur", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.MessageBox(f"Erreur: {str(e)}", "Erreur", wx.OK | wx.ICON_ERROR)

        dlg.Destroy()

    def trouver_chemin_court(self, event):
        dlg = PathInputDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            start_place = dlg.start_text.GetValue()
            mid_place = dlg.mid_text.GetValue()
            end_place = dlg.end_text.GetValue()

            try:
                start_lat, start_lon = self.get_coordinates(start_place)
                end_lat, end_lon = self.get_coordinates(end_place)

                if None in (start_lat, start_lon):
                    wx.MessageBox("Impossible de localiser les points", "Erreur", wx.OK | wx.ICON_ERROR)
                    return

                source_node = self.base_network.get_nodes_by_attribute('nearest', point=(start_lat, start_lon))
                target_node = self.base_network.get_nodes_by_attribute('nearest', point=(end_lat, end_lon))
                if not source_node or not target_node:
                    wx.MessageBox("Nœuds obligatoires non trouvés", "Erreur", wx.OK | wx.ICON_ERROR)
                    return

                # Créer une copie du graphe pour modification
                G_temp = self.base_network.G.copy()

                # Zone d'exclusion si un point à éviter est spécifié
                if mid_place:
                    ignore_lat, ignore_lon = self.get_coordinates(mid_place)
                    # Définir le rayon d'exclusion (en mètres)
                    exclusion_radius = 500  # 500 mètres

                    # Trouver tous les nœuds dans le rayon d'exclusion
                    avoid_nodes = []
                    for node, data in G_temp.nodes(data=True):
                        node_lat = data['y']
                        node_lon = data['x']

                        # Calculer la distance (méthode simplifiée)
                        distance = ox.distance.great_circle(
                            ignore_lat, ignore_lon,
                            node_lat, node_lon
                        )

                        if distance <= exclusion_radius:
                            avoid_nodes.append(node)

                    # Augmenter considérablement le poids des arêtes dans la zone
                    for u, v, data in G_temp.edges(data=True):
                        if u in avoid_nodes or v in avoid_nodes:
                            if 'length' in data:
                                data['weight'] = data['length'] * 100  # Rend la zone très peu attractive

                    # Calculer le chemin en évitant la zone
                    full_path = nx.dijkstra_path(
                        G_temp,
                        source_node,
                        target_node,
                        weight='weight'
                    )
                else:
                    # Essayer sans pénalités si aucun chemin n'est trouvé
                    full_path = nx.dijkstra_path(
                        self.base_network.G,
                        source_node,
                        target_node,
                        weight='weight'
                    )

                    # Création du graphe du chemin
                path_subgraph = self.base_network.G.subgraph(full_path).copy()
                path_subgraph.graph['crs'] = "EPSG:4326"

                # Marquage des points importants
                path_subgraph.nodes[source_node]['important'] = True
                path_subgraph.nodes[target_node]['important'] = True

                path_network = Transport_network.TransportNetwork()
                path_network.G = path_subgraph
                path_network.process_graph_data()

                # Sauvegarde et affichage
                output_path = os.path.join(self.base_dir, "djikstra.html")
                path_network.save_html(output_path)
                self.current_network = path_network
                self.html_path = output_path
                self._load_html_content()
                wx.MessageBox(f"Chemin trouver, il est de longeur {len(path_network.G.nodes)} \nle chemin est eulerien:{path_network.cycle_eulerien()}", "CHEMIN TROUVE!", wx.OK | wx.ICON_INFORMATION)

                # Sauvegarde historique
                with open('saved_paths.csv', 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([start_place, end_place, datetime.now().isoformat()])

            except nx.NetworkXNoPath:
                wx.MessageBox("Aucun chemin trouvé entre les points", "Erreur", wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.MessageBox(f"Erreur: {str(e)}", "Erreur", wx.OK | wx.ICON_ERROR)

        dlg.Destroy()

    def on_retour(self, event):
        empty_plot = os.path.join(self.base_dir, "empty_plot.html")
        if self.html_path == empty_plot:
            wx.MessageBox("Vous êtes déjà sur la carte principale", "Information", wx.OK | wx.ICON_INFORMATION)
        else:
            # Restaurer le réseau de base
            self.current_network = self.base_network
            self.html_path = empty_plot
            self._load_html_content()

    def map_full(self, event):
        full_map = os.path.join(self.base_dir, "plot.html")
        if self.html_path == full_map:
            wx.MessageBox("Vous êtes déjà sur la carte complète", "Information", wx.OK | wx.ICON_INFORMATION)
        else:
            # Utiliser le réseau de base pour la carte complète
            self.current_network = self.base_network
            self.html_path = full_map
            self._load_html_content()

    def matrice(self, event):
        network = self.current_network
        message = (
            f"{nx.adjacency_matrix(network.G)} "
        )
        wx.MessageBox(message, "Matrice d'adjacence", wx.OK | wx.ICON_INFORMATION)

    def voisinage(self, event):
        dlg = PathInputDialog1(self)
        if dlg.ShowModal() == wx.ID_OK:
            point = dlg.start_text.GetValue()
            point_lat, point_lon = self.get_coordinates(point)

            # Vérifier les coordonnées
            if None in (point_lat, point_lon):
                wx.MessageBox("Impossible de localiser le point", "Erreur", wx.OK | wx.ICON_ERROR)
                dlg.Destroy()
                return

            try:
                point_node = self.base_network.get_nodes_by_attribute('nearest', point=(point_lat, point_lon))

                # Ajouter un message de débogage
                debug_info = (
                    f"Point: {point}\n"
                    f"Coordonnées: ({point_lat}, {point_lon})\n"
                    f"Nœud trouvé: {point_node}\n"
                    f"Dans le graphe: {'Oui' if point_node in self.base_network.G else 'Non'}\n"
                    f"Dans le GeoDataFrame: {'Oui' if point_node in self.base_network.nodes_gdf.index else 'Non'}"
                )
                wx.MessageBox(debug_info, "Débogage", wx.OK | wx.ICON_INFORMATION)
            except:
                pass

            # Vérifier si les coordonnées sont valides
            if None in (point_lat, point_lon):
                wx.MessageBox("Impossible de localiser le point", "Erreur", wx.OK | wx.ICON_ERROR)
                dlg.Destroy()
                return

            try:
                point_node = self.base_network.get_nodes_by_attribute('nearest', point=(point_lat, point_lon))

                # Vérifier si le nœud est valide
                if point_node is None:
                    wx.MessageBox("Aucun nœud trouvé à proximité", "Erreur", wx.OK | wx.ICON_ERROR)
                    return

                # Vérifier que le nœud existe dans le graphe
                if point_node not in self.base_network.G:
                    wx.MessageBox(f"Le nœud {point_node} n'existe pas dans le graphe", "Erreur", wx.OK | wx.ICON_ERROR)
                    return

                # Sauvegarde et affichage
                output_path = os.path.join(self.base_dir, "voisinage.html")
                self.base_network.is_courte = False
                self.base_network.process_graph_data()
                neighbors = list(self.base_network.G.neighbors(point_node))
                print(neighbors)
                fig = self.base_network.visualize_neighborhood(point_node, point_lat, point_lon)
                fig.write_html(output_path)
                self.html_path = output_path
                self._load_html_content()
                self.base_network.is_courte = True
            except Exception as e:
                wx.MessageBox(f"Erreur: {str(e)}", "Erreur", wx.OK | wx.ICON_ERROR)
        dlg.Destroy()
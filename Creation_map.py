import networkx as nx
import numpy as np
import osmnx as ox
import plotly.graph_objects as go


class TransportNetwork:
    def __init__(self, filepath=None):
        self.G = None
        self.nodes_gdf = None
        self.edges_gdf = None
        self.all_edges_trace = None
        self.is_courte = True
        self.crs = "EPSG:4326"
        if filepath:
            self.load_graph(filepath)

    @staticmethod
    def create_graph(place_name, network_type='drive', custom_filter=None):
        ox.settings(nominatim_delay=2, timeout=60)
        return ox.graph_from_place(
            place_name,
            network_type=network_type,
            simplify=True,
            custom_filter=custom_filter
        )

    def load_graph(self, filepath):
        self.G = ox.io.load_graphml(filepath)
        self.process_graph_data()

    def process_graph_data(self):

        if not self.is_courte:
            if self.G is None:
                raise ValueError("Graphe non chargé")

                # Convertir le graphe en GeoDataFrames
            self.nodes_gdf, self.edges_gdf = ox.graph_to_gdfs(self.G)
            self.nodes_gdf.set_crs(self.crs, inplace=True)
            self.edges_gdf.set_crs(self.crs, inplace=True)

            # Conserver l'ID OSM comme index
            self.nodes_gdf = self.nodes_gdf.reset_index()

            # Vérifier le type de la colonne 'osmid'
            if isinstance(self.nodes_gdf['osmid'].iloc[0], list):
                # Si c'est une liste, prendre le premier élément
                self.nodes_gdf['node_id'] = self.nodes_gdf['osmid'].apply(lambda x: x[0])
            else:
                self.nodes_gdf['node_id'] = self.nodes_gdf['osmid']

            # Définir l'index sur node_id
            self.nodes_gdf.set_index('node_id', inplace=True)

            # Renommer les colonnes de coordonnées
            self.nodes_gdf.rename(columns={
                'y': 'latitude',
                'x': 'longitude'
            }, inplace=True)
        else:
            if self.G is None:
                raise ValueError("Graphe non chargé")

            self.nodes_gdf, self.edges_gdf = ox.graph_to_gdfs(self.G)
            self.nodes_gdf.set_crs(self.crs, inplace=True)
            self.edges_gdf.set_crs(self.crs, inplace=True)

            self.nodes_gdf = self.nodes_gdf.reset_index().rename(columns={
                'y': 'latitude',
                'x': 'longitude',
                'osmid': 'node_id'
            })

    def show_basic_info(self):
        if self.G is None:
            print("Aucun graphe chargé")
            return

        print("\n=== Informations de base ===")
        print(f"Nombre de nœuds: {len(self.G.nodes)}")
        print(f"Nombre d'arêtes: {len(self.G.edges)}")
        print("Colonnes disponibles:", self.nodes_gdf.columns.tolist())
        print("\nExtrait des données géographiques :")
        print(self.nodes_gdf[['node_id', 'latitude', 'longitude']].head())

    def visualize_network_djikstra(self, map_style="open-street-map", zoom=12):
        fig = go.Figure()
        all_lats = []
        all_lons = []

        # Ajout des arêtes
        for _, edge in self.edges_gdf.iterrows():
            color = 'red' if edge.get('in_dijkstra_path', False) else 'blue'
            width = 3 if edge.get('in_dijkstra_path', False) else 1

            if hasattr(edge['geometry'], 'coords'):
                coords = list(edge['geometry'].coords)
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
            else:
                lons = [edge['u'].x, edge['v'].x]
                lats = [edge['u'].y, edge['v'].y]

            all_lats.extend(lats)
            all_lons.extend(lons)

            fig.add_trace(go.Scattermapbox(
                lon=lons,
                lat=lats,
                mode='lines',
                line=dict(width=width, color=color),
                hoverinfo='none'
            ))

        # Ajout des nœuds
        fig.add_trace(go.Scattermapbox(
            lat=self.nodes_gdf['latitude'],
            lon=self.nodes_gdf['longitude'],
            mode='markers',
            marker=dict(size=6, color='green'),
            text=self.nodes_gdf['node_id'],
            hoverinfo='text'
        ))

        # Ajouter les coordonnées des nœuds
        all_lats.extend(self.nodes_gdf['latitude'].tolist())
        all_lons.extend(self.nodes_gdf['longitude'].tolist())

        # Calcul du centre dynamique
        if all_lats and all_lons:
            center_lat = np.mean(all_lats)
            center_lon = np.mean(all_lons)
        else:
            center_lat, center_lon = 36.7538, 3.0588  # Alger par défaut

        fig.update_layout(
            hovermode='closest',
            mapbox_style=map_style,
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            showlegend=False,
            mapbox=dict(
                center=dict(lat=center_lat, lon=center_lon),
                zoom=zoom
            )
        )
        return fig

    def save_html(self, filename="network_plot.html"):
        fig = self.visualize_network_djikstra()
        fig.write_html(filename)

    def get_nodes_by_attribute(self, attribute, value=None, point=None):
        try:
            if attribute == 'nearest' and point:
                if not hasattr(self, 'G') or self.G is None:
                    raise ValueError("Graphe non initialisé")

                lat, lon = point
                node_id = ox.distance.nearest_nodes(self.G, lon, lat)

                # Convertir en type compatible avec l'index
                if node_id not in self.nodes_gdf.index:
                    # Essayer de convertir en int si possible
                    try:
                        node_id = int(node_id)
                    except (ValueError, TypeError):
                        pass

                return node_id

        except Exception as e:
            print(f"Erreur recherche nœud: {e}")

        return None
    @staticmethod
    def empty_map():
        fig = go.Figure(go.Scattermap(
            lat=['36.7538'],
            lon=['3.0588'],
            mode='markers',
            marker=go.scattermap.Marker(
                size=14
            ),
            text=['Alger'],
        ))

        fig.update_layout(
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            hovermode='closest',
            map=dict(
                bearing=0,
                center=go.layout.map.Center(
                    lat=36.7538,
                    lon=3.0588
                ),
                pitch=0,
                zoom=10
            )
        )

    def creer_matrice_vide(self, n):
        """1. Crée une matrice d'adjacence vide de taille n x n"""
        self.matrice_adjacence = [[0] * n for _ in range(n)]

    def ajouter_arete(self, u, v, poids=1):
        """2. Ajoute une arête entre u et v"""
        self.G.add_edge(u, v, weight=poids)
        self._update_matrice()

    def supprimer_arete(self, u, v):
        """3. Supprime l'arête entre u et v"""
        self.G.remove_edge(u, v)
        self._update_matrice()

    def ajouter_sommet(self, n):
        """4. Ajoute n nouveaux sommets"""
        for _ in range(n):
            new_node = max(self.G.nodes) + 1 if self.G.nodes else 0
            self.G.add_node(new_node)
        self._update_matrice()

    def supprimer_sommet(self, node):
        """5. Supprime un sommet"""
        self.G.remove_node(node)
        self._update_matrice()

    def ordre_graphe(self):
        """7. Retourne l'ordre du graphe"""
        return len(self.G.nodes)

    def calculer_degres(self):
        """8. Calcule les degrés des sommets"""
        return len(dict(self.G.degree()))

    def voisinage(self, node):
        """9. Affiche le voisinage d'un sommet"""
        return self.G.neighbors(node)

    def chemin_longueur_L(self, u, v, L):
        """10. Vérifie l'existence d'un chemin de longueur L"""
        mat_puissance = nx.linalg.matrix_power(self.matrice_adjacence, L)
        return mat_puissance[u][v] > 0

    def cycle_eulerien(self):
        """11. Vérifie l'existence d'un cycle eulérien"""
        return nx.is_eulerian(self.G)

    def chemin_hamiltonien(self):
        """12. Cherche un chemin hamiltonien (approximation)"""
        return nx.approximation.traveling_salesman_problem(self.G)

    def est_connexe(self):
        """13. Vérifie la connexité"""
        return nx.is_connected(self.G)

    def cout_extension(self):
        """16. Coût minimum d'extension (Arbre couvrant min)"""
        return nx.minimum_spanning_tree(self.G)

    # Méthodes auxiliaires
    def _update_matrice(self):
        """Met à jour la matrice d'adjacence"""
        nodes = sorted(self.G.nodes)
        size = len(nodes)
        self.matrice_adjacence = [[0] * size for _ in range(size)]

        node_index = {node: i for i, node in enumerate(nodes)}
        for u, v, data in self.G.edges(data=True):
            i = node_index[u]
            j = node_index[v]
            poids = data.get('weight', 1)
            self.matrice_adjacence[i][j] = poids
            self.matrice_adjacence[j][i] = poids  # Pour graphe non orienté

    def visualize_neighborhood(self, center_node, center_lat, center_lon, map_style="open-street-map", zoom=15):
        fig = go.Figure()

        # Vérifier dans le graphe
        if center_node not in self.G:
            raise ValueError(f"Le nœud {center_node} n'existe pas dans le graphe")


        # Limiter le nombre de voisins traités
        neighbors = list(self.G.neighbors(center_node))
        if len(neighbors) > 100:  # Augmenter la limite pour voir plus de connexions
            neighbors = neighbors[:100]

        # Stockage de toutes les coordonnées pour le centrage
        all_lats = [center_lat]
        all_lons = [center_lon]

        # 1. Ajouter toutes les arêtes en gris clair - CORRECTION: utiliser une seule trace
        all_lons_edges = []
        all_lats_edges = []
        for u, v, data in self.G.edges(data=True):
            if 'geometry' in data:
                geometry = data['geometry']
                if hasattr(geometry, 'coords'):
                    coords = list(geometry.coords)
                    lons = [c[0] for c in coords]
                    lats = [c[1] for c in coords]
                    all_lons_edges.extend(lons)
                    all_lats_edges.extend(lats)
                    all_lons_edges.append(None)  # Séparateur
                    all_lats_edges.append(None)

        if all_lons_edges and all_lats_edges:
            fig.add_trace(go.Scattermapbox(
                lon=all_lons_edges,
                lat=all_lats_edges,
                mode='lines',
                line=dict(width=1, color='lightgray'),
                hoverinfo='none',
                showlegend=False
            ))

        # 2. Ajouter les arêtes connectées au nœud central en rouge
        for neighbor in neighbors:
            edge_data = self.G.get_edge_data(center_node, neighbor)
            if edge_data:
                # Prendre la première arête (pour MultiGraph)
                data = list(edge_data.values())[0]

                if 'geometry' in data:
                    geometry = data['geometry']
                    if hasattr(geometry, 'coords'):
                        coords = list(geometry.coords)
                        lons = [c[0] for c in coords]
                        lats = [c[1] for c in coords]
                    else:
                        # Si pas de géométrie, utiliser les coordonnées des nœuds
                        neighbor_data = self.nodes_gdf.loc[neighbor]
                        lons = [center_lon, neighbor_data['longitude']]
                        lats = [center_lat, neighbor_data['latitude']]
                else:
                    # Si pas de géométrie, utiliser les coordonnées des nœuds
                    neighbor_data = self.nodes_gdf.loc[neighbor]
                    lons = [center_lon, neighbor_data['longitude']]
                    lats = [center_lat, neighbor_data['latitude']]

                fig.add_trace(go.Scattermapbox(
                    lon=lons,
                    lat=lats,
                    mode='lines',
                    line=dict(width=3, color='red'),
                    hoverinfo='none',
                    showlegend=False
                ))

                all_lats.extend(lats)
                all_lons.extend(lons)

        # 3. Ajouter les nœuds voisins en bleu
        neighbor_lats = []
        neighbor_lons = []
        for neighbor in neighbors:
            try:
                neighbor_data = self.nodes_gdf.loc[neighbor]
                neighbor_lats.append(neighbor_data['latitude'])
                neighbor_lons.append(neighbor_data['longitude'])
                all_lats.append(neighbor_data['latitude'])
                all_lons.append(neighbor_data['longitude'])
            except KeyError:
                continue  # Passer si le nœud n'est pas trouvé

        if neighbor_lats and neighbor_lons:
            fig.add_trace(go.Scattermapbox(
                lon=neighbor_lons,
                lat=neighbor_lats,
                mode='markers',
                marker=dict(size=10, color='blue'),
                text=[f"Voisin {n}" for n in neighbors],
                hoverinfo='text',
                name='Voisins'
            ))

        # 4. Ajouter le nœud central en violet et plus gros
        fig.add_trace(go.Scattermapbox(
            lon=[center_lon],
            lat=[center_lat],
            mode='markers+text',
            marker=dict(size=15, color='purple'),
            text=[f"Centre: {center_node}"],
            hoverinfo='text',
            name='Nœud central'
        ))

        # Calcul du centre et du zoom optimal
        if all_lats and all_lons:
            center_lat = sum(all_lats) / len(all_lats)
            center_lon = sum(all_lons) / len(all_lons)
            # Ajustement automatique du zoom en fonction de l'étendue
            lat_span = max(all_lats) - min(all_lats)
            lon_span = max(all_lons) - min(all_lons)
            max_span = max(lat_span, lon_span)
            zoom = max(14, 18 - int(max_span * 100))  # Formule empirique

        fig.update_layout(
            mapbox_style=map_style,
            mapbox=dict(
                center=dict(lat=center_lat, lon=center_lon),
                zoom=zoom
            ),
            margin={"r": 0, "t": 0, "l": 0, "b": 0},
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        return fig

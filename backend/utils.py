from sknetwork.clustering import Louvain
from scipy.sparse import csc_matrix
from collections import defaultdict

def get_clusters(adj_matrix: csc_matrix) -> dict:
    
    louvain = Louvain()
    labels = louvain.fit_predict(adj_matrix)

    clusters = defaultdict(list)

    for node_id, cluster_id in enumerate(labels):
        clusters[int(cluster_id)].append(node_id)

    return dict(clusters)

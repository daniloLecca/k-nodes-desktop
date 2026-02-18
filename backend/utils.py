from sknetwork.clustering import Louvain
from scipy.sparse import csc_matrix
from collections import defaultdict
from pydantic import BaseModel

def get_clusters(adj_matrix: csc_matrix) -> dict:
    """
    Returns a dictionary which for every cluster contains the list of nodes
    
    :param adj_matrix: adjacency matrix
    :type adj_matrix: csc_matrix
    :return: {cluster1: [node1, node2, ..., nodeN], cluster2: [node3, node4, ..., nodeM], ...}
    :rtype: dict
    """
    louvain = Louvain()
    labels = louvain.fit_predict(adj_matrix)

    clusters = defaultdict(list)

    for node_id, cluster_id in enumerate(labels):
        clusters[int(cluster_id)].append(node_id)

    return dict(clusters)


class ClusterRequest(BaseModel):
    clusterID: str


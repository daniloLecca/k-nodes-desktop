from sknetwork.clustering import Louvain
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import eigsh
from collections import defaultdict
from pydantic import BaseModel

class ComplexNetwork():
    adj: csc_matrix
    largest_eigenvalue: float
    token: str
    clusters: dict

    def __init__(self, adj: csc_matrix, token: str):
        self.adj = adj
        self.token = token
        self._get_clusters()
        self.largest_eigenvalue = eigsh(self.adj, k=1, which='LA', return_eigenvectors=False)[0]

    def _get_clusters(self):
        louvain = Louvain()
        labels = louvain.fit_predict(self.adj)

        self.clusters = defaultdict(list)

        for node_id, cluster_id in enumerate(labels):
            self.clusters[int(cluster_id)].append(node_id)

    def nodes(self) -> int: 
        return self.adj.shape[0]
    
    def edges(self) -> int: 
        return self.adj.size
    
    def size_of_clusters(self) -> dict:
        sizes: dict = {}

        # for each cluster compute the size of the cluster
        for cluster in self.clusters.keys():
            sizes[cluster] = len(self.clusters[cluster])

        return sizes

    def numberOfClusters(self) -> int: 
        return len(self.size_of_clusters().keys())
    

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

class ExpRequest(BaseModel):
    node: int

class ResRequest(ExpRequest):
    alpha: float
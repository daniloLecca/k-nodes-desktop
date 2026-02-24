from sknetwork.clustering import Louvain
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import eigsh
from collections import defaultdict
from pydantic import BaseModel, model_validator
from typing import Union, Literal

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

class RandomComplexNetworkRequest(BaseModel):
    nnodes: int
    model: Literal["small_world", "scale_free"]
    k: int
    p: float | None = None

    @model_validator(mode="after")
    def check_p_consistency(self):
        if self.model == "small_world":
            if self.p is None:
                raise ValueError(f"'p' is required for 'watts_strogatz' model")
            if not (0 <= self.p <= 1):
                raise ValueError("'p' must be between 0 and 1")

        if self.model == "scale_free":
            if self.p is not None:
                raise ValueError("'p' must not be provided for 'barabasi_albert'")

        return self
    
class LowRankSubgraphCentrality(BaseModel):
    shift: bool 
    fun_name: str | None = None
    nnodes: int | None = None
    alpha: float | None = None
    max_iter: int | None = None
    batch_size: int | None = None
    tol: float | None = None
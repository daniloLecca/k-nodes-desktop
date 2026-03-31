from sknetwork.clustering import Louvain
from scipy.sparse import csc_matrix
from collections import defaultdict
from pydantic import BaseModel, model_validator
from typing import Literal


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
    low_rank_tol: float | None = None

class LowRankCommunicability(LowRankSubgraphCentrality):
    i: int

class GaussSubgraphCentrality(BaseModel):
    nnodes: int | None = None
    fun_name: str | None = None
    alpha: float | None = None
    max_iter: int | None = None
    gauss_tol: float | None = None

class GaussCommunicability(GaussSubgraphCentrality):
    i: int

class HybridSubgraphCentrality(BaseModel):
    shift: bool | None = None
    fun_name: str | None = None
    nnodes: int | None = None
    low_rank_nnodes: int | None = None
    alpha: float | None = None
    max_iter: int | None = None
    batch_size: int | None = None
    gauss_tol: float | None = None
    low_rank_tol: float | None = None

class HybridCommunicability(HybridSubgraphCentrality):
    i: int
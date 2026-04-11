from sknetwork.hierarchy import LouvainIteration, cut_balanced
from sknetwork.clustering import Louvain
from scipy.sparse import csc_matrix
from scipy.io import loadmat
from collections import defaultdict
from pydantic import BaseModel, model_validator
from typing import Literal
from networkx import read_gexf, to_scipy_sparse_array, Graph
from xml.etree.ElementTree import parse
from layout import entire_network_layout
import math
import numpy as np
import logging
import json

logger = logging.getLogger(__name__) # for printing logs in dev
logging.basicConfig(level=logging.INFO)


def adjust_cluster_positions_by_size(clusters_layout: dict, clusters: dict[int, list[int]]) -> dict:
    """
    Recenter and spread cluster positions using cluster cardinality as radius proxy.
    This keeps cluster nodes positioned proportionally to the amount of represented nodes.
    """

    nodes = clusters_layout.get("nodes", [])
    if not nodes:
        return clusters_layout

    # radius proxy: sqrt(cardinality) reduces the dynamic range across very small/large clusters
    radii = {
        int(cluster_id): max(1.0, math.sqrt(len(cluster_nodes)))
        for cluster_id, cluster_nodes in clusters.items()
    }

    total_weight = 0.0
    centroid_x = 0.0
    centroid_y = 0.0

    for node in nodes:
        cluster_id = int(node["key"])
        weight = float(len(clusters.get(cluster_id, [])) or 1)
        total_weight += weight
        centroid_x += node["attributes"]["x"] * weight
        centroid_y += node["attributes"]["y"] * weight

    if total_weight > 0:
        centroid_x /= total_weight
        centroid_y /= total_weight

    for node in nodes:
        node["attributes"]["x"] -= centroid_x
        node["attributes"]["y"] -= centroid_y

    # push overlapping clusters apart using their inferred radii
    n_nodes = len(nodes)
    if n_nodes > 1:
        for _ in range(40):
            moved = False
            for i in range(n_nodes):
                node_i = nodes[i]
                id_i = int(node_i["key"])
                ri = radii.get(id_i, 1.0)
                xi = node_i["attributes"]["x"]
                yi = node_i["attributes"]["y"]

                for j in range(i + 1, n_nodes):
                    node_j = nodes[j]
                    id_j = int(node_j["key"])
                    rj = radii.get(id_j, 1.0)
                    xj = node_j["attributes"]["x"]
                    yj = node_j["attributes"]["y"]

                    dx = xj - xi
                    dy = yj - yi
                    dist = math.hypot(dx, dy)
                    min_dist = 1.3 * (ri + rj)

                    if dist < min_dist:
                        moved = True
                        if dist == 0:
                            angle = (i + j + 1) * 0.61803398875
                            ux = math.cos(angle)
                            uy = math.sin(angle)
                        else:
                            ux = dx / dist
                            uy = dy / dist

                        shift = 0.5 * (min_dist - dist)
                        node_i["attributes"]["x"] -= ux * shift
                        node_i["attributes"]["y"] -= uy * shift
                        node_j["attributes"]["x"] += ux * shift
                        node_j["attributes"]["y"] += uy * shift

                        xi = node_i["attributes"]["x"]
                        yi = node_i["attributes"]["y"]

            if not moved:
                break

    # expose size to the frontend renderer so larger clusters are visually larger too.
    for node in nodes:
        cluster_id = int(node["key"])
        node["attributes"]["size"] = radii.get(cluster_id, 1.0)

    return clusters_layout

def extract_complex_network_from_file(contents, format: Literal[".mat", ".gexf", ".json"]) -> csc_matrix:
    """
    :param contents: file-like object
    :param format: format of the file, must be '.mat' or '.gexf'

    :return network: csc_matrix of complex network
    """ 

    if (format == ".mat"): 
        mat_data = loadmat(contents)
        mat_data = {k: v for k, v in mat_data.items() if not k.startswith('__')}

        # check that the file contains exactly one variable
        if len(mat_data) != 1:
            raise ValueError("the file must contain exactly one variable. ")

        # get the adjacency matrix and normalize to scipy sparse matrix format
        _, network = next(iter(mat_data.items()))
        network = csc_matrix(network)
        if (network.shape[0] != network.shape[1]) or ((network != network.T).nnz != 0): 
            raise ValueError("the adjacency matrix must represent an undirected graph")
    
        return network

    elif(format == ".json"): 
        contents = json.load(contents)
        nnodes = len(contents["nodes"])
        nedges = len(contents["edges"])

        node_keys = [n["key"] for n in contents["nodes"]]
        key_to_index = {k: i for i, k in enumerate(node_keys)} # the file could have "holes" in nodes id

        data = np.ones(nedges, dtype=int)
        # sometimes the id of each node is a floating number
        rows, cols = zip(*[(int(float(key_to_index[edge["source"]])), int(float(key_to_index[edge["target"]]))) for edge in contents["edges"]])

        network = csc_matrix((data, (rows, cols)), shape=(nnodes, nnodes))
        network = (network + network.T > 0).astype(int) 

        if (network.shape[0] != network.shape[1]) or ((network != network.T).nnz != 0): 
            raise ValueError("the adjacency matrix must represent an undirected graph")

        return network
    else:

        try:
            # read the gexf file
            # G = read_gexf("graphs/WebAtlas_EuroSiS.gexf")
            # G = read_gexf("graphs/yeast.gexf")
            G = read_gexf(contents)
        except Exception as e_read:
            # fallback parser for namespace incompatibilities
            try:
                if hasattr(contents, "seek"):
                    contents.seek(0)

                tree = parse(contents)
                root = tree.getroot()

                # empty graph
                G = Graph()

                # parse by local tag name, so any XML namespace is supported.
                for elem in root.iter():
                    tag = elem.tag.split('}', 1)[-1]

                    if tag == 'node':
                        node_id = elem.get('id')
                        if node_id is not None:
                            G.add_node(node_id)

                    if tag == 'edge':
                        source = elem.get('source')
                        target = elem.get('target')
                        if source is not None and target is not None:
                            G.add_edge(source, target)
            except Exception as e_parse:
                raise ValueError(
                    f"unable to read the gexf file. networkx parser error: {e_read}. "
                    f"xml fallback parser error: {e_parse}"
                )

        # ensure a non-empty graph before converting to sparse matrix
        if G.number_of_nodes() == 0 and G.number_of_edges() == 0:
            raise ValueError(
                "the uploaded gexf graph is empty or could not be parsed: Graph has no nodes or edges"
            )

        # convert to scipy csc_matrix
        A = to_scipy_sparse_array(Graph(G), weight=None, format="csc")

        if (A.shape[0] != A.shape[1]):
            raise ValueError("the adjacency matrix must be a square matrix")

        # make the adjacency matrix symmetric and unweighted
        network = csc_matrix((A + A.T > 0).astype(int))

    # if the matrix is not square or is not symmetric -> not valid adjacency matrix 
    if (network.shape[0] != network.shape[1]) or ((network != network.T).nnz != 0): 
        raise ValueError("the adjacency matrix must represent an undirected graph")
    
    return network


def get_clusters(adj_matrix: csc_matrix) -> dict:
    """
    Returns a dictionary which for every cluster contains the list of nodes
    
    :param adj_matrix: adjacency matrix
    :type adj_matrix: csc_matrix
    :return: {cluster1: [node1, node2, ..., nodeN], cluster2: [node3, node4, ..., nodeM], ...}
    :rtype: dict
    """

    n = adj_matrix.shape[0]
    nnz = adj_matrix.nnz

    if n == 0:
        return {}

    # can fail on very small or complex networks.
    # in that case, fall back to a single cluster containing all nodes.
    if n < 100 or nnz == 0:
        return {0: list(range(n))}
    
    # 51k nodes, 5 starting edges -> 300 clusters of max 700 nodes
    
    if nnz >= 1_000_000:
        return {0: list(range(n))}

    louvain = LouvainIteration(depth=2, n_aggregations=10)
    try:
        hierarchy = louvain.fit_predict(adj_matrix)
        labels = cut_balanced(hierarchy, max_cluster_size=min(n, 700))
    except RecursionError:
        logger.warning("cut_balanced hit recursion limit")
        labels = Louvain().fit_predict(adj_matrix)
    except Exception as error:
        logger.warning("Falling back to a single cluster: %s", error)
        return {0: list(range(n))}

    clusters = defaultdict(list)

    for node_id, cluster_id in enumerate(labels):
        clusters[int(cluster_id)].append(node_id)

    clusters_adj_matrix = estimate_links_between_clusters(A=adj_matrix, labels=labels)
    logger.info("Computed links between clusters")
    clusters_adj_matrix.setdiag(0)
    clusters_layout = entire_network_layout(clusters_adj_matrix)
    clusters_layout = adjust_cluster_positions_by_size(clusters_layout, dict(clusters))
    logger.info("Computed position of clusters")
    logger.info(f"Clusters layout: {len(clusters_layout['nodes'])} nodes and {len(clusters_layout['edges'])} edges")

    return dict(clusters_layout)

def estimate_links_between_clusters(A: csc_matrix, labels: list) -> csc_matrix: 
    nnodes = A.shape[0]
    n_clusters = max(labels) + 1


    M = csc_matrix((np.ones(nnodes), (np.arange(nnodes), labels)), shape=(nnodes, n_clusters))
    C = M.T @ A @ M
    
    off_diag = C.copy()
    off_diag.setdiag(0)
    threshold = off_diag.max() * 0.2

    C.setdiag(0)
    C.data[C.data < threshold] = 0
    C.eliminate_zeros()

    return C


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
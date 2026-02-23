from networkx import barabasi_albert_graph, watts_strogatz_graph, to_scipy_sparse_array
from scipy.sparse import csc_matrix, triu
from typing import Union

def generate_scale_free_complex_network(nnodes: int, k: Union[int, None] = 5) -> csc_matrix:
    G = barabasi_albert_graph(nnodes, k)
    A = to_scipy_sparse_array(G, format="csc")
    A = triu(A, k=1)
    return csc_matrix(A)

def generate_small_world_complex_network(nnodes: int, k: int = 5, probability: float = 0.01) -> csc_matrix:
    G = watts_strogatz_graph(nnodes, k, probability)
    A = to_scipy_sparse_array(G, format="csc")
    A = triu(A, k=1)  # only upper triangular (excluding main diagonal -> no self-loops)
    return csc_matrix(A)
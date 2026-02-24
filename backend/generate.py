from networkx import barabasi_albert_graph, watts_strogatz_graph, to_scipy_sparse_array
from scipy.sparse import csc_matrix
from typing import Union

def generate_scale_free_complex_network(nnodes: int, k: Union[int, None] = 5) -> csc_matrix:
    """Generate a scale-free network using Barabási-Albert model.
    
    Returns a symmetric adjacency matrix (required for undirected graphs).
    """
    G = barabasi_albert_graph(nnodes, k)
    A = to_scipy_sparse_array(G, format="csc")
    # make symmetric: A = A + A^T (for undirected graphs)
    A = A + A.T
    A.eliminate_zeros()  # Remove any zeros
    return csc_matrix(A, dtype=float)

def generate_small_world_complex_network(nnodes: int, k: int = 5, probability: float = 0.01) -> csc_matrix:
    """Generate a small-world network using Watts-Strogatz model.
    
    Returns a symmetric adjacency matrix (required for undirected graphs).
    """
    G = watts_strogatz_graph(nnodes, k, probability)
    A = to_scipy_sparse_array(G, format="csc")
    # make symmetric: A = A + A^T (for undirected graphs)
    A = A + A.T
    A.eliminate_zeros()  # Remove any zeros
    return csc_matrix(A, dtype=float)
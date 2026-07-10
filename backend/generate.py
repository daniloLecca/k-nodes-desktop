from networkx import barabasi_albert_graph, watts_strogatz_graph, to_scipy_sparse_array
from scipy.sparse import csc_matrix

def generate_scale_free_complex_network(nnodes: int, k: int = 5) -> csc_matrix:
    """Generate a scale-free network using Barabási-Albert model.
    
    Returns a symmetric adjacency matrix (required for undirected graphs).
    """
    G = barabasi_albert_graph(nnodes, k)
    A = to_scipy_sparse_array(G, format="csc", dtype=float)

    return csc_matrix(A)

def generate_small_world_complex_network(nnodes: int, k: int = 5, probability: float = 0.01) -> csc_matrix:
    """Generate a small-world network using Watts-Strogatz model.
    
    Returns a symmetric adjacency matrix (required for undirected graphs).
    """
    G = watts_strogatz_graph(nnodes, k, probability)
    A = to_scipy_sparse_array(G, format="csc", dtype=float)
    
    return csc_matrix(A)
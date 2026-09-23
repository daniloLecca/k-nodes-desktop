import numpy as np
from networkx import from_scipy_sparse_array
from networkx import (
    degree_centrality,
    eigenvector_centrality,
    katz_centrality,
    pagerank,
    betweenness_centrality,
    closeness_centrality,
)
from scipy.sparse import csc_matrix
from typing import Tuple


def _extract_top_nodes(centralities: dict, nnodes: int) -> Tuple[np.ndarray, np.ndarray]:
    """Extract top nnodes from centralities list

    Args:
        centralities (dict): centrality for each node
        nnodes (int): number of nodes

    Returns:
        Tuple[np.ndarray, np.ndarray]: ordered tuple of nnodes with their respective centralities
    """
    nodes = np.array(list(centralities.keys()))
    values = np.array(list(centralities.values()))

    
    sorted_order = np.argsort(values)[::-1]
    top_indices = sorted_order[:nnodes]

    vip_nodes = nodes[top_indices]
    vip_centralities = values[top_indices]

    return vip_nodes, vip_centralities


def compute_degree_centrality(network: csc_matrix, nnodes: int) -> Tuple[np.ndarray, np.ndarray]:
    """Computes the degree centrality of a network

    Args:
        network (csc_matrix): network
        nnodes (int): number of nodes

    Returns:
        Tuple[np.ndarray, np.ndarray]: ordered tuple of nnodes with their respective centralities
    """
    G = from_scipy_sparse_array(network)
    centralities = degree_centrality(G)

    return _extract_top_nodes(centralities, nnodes)


def compute_eigenvector_centrality(network: csc_matrix, nnodes: int, max_iter: int = 1000, tol: float = 1e-6) -> Tuple[np.ndarray, np.ndarray]:
    """Computes the eigenvector centrality of a network

    Args:
        network (csc_matrix): network
        nnodes (int): number of nodes
        max_iter (int, optional): max iterations for power method. Defaults to 1000.
        tol (float, optional): tolerance for power method iteration. Defaults to 1e-6.

    Returns:
        Tuple[np.ndarray, np.ndarray]: ordered tuple of nnodes with their respective centralities
    """
    G = from_scipy_sparse_array(network)
    centralities = eigenvector_centrality(G, max_iter=max_iter, tol=tol)

    return _extract_top_nodes(centralities, nnodes)


def compute_katz_centrality(network: csc_matrix, nnodes: int, alpha: float = 0.1, beta: float = 1.0, max_iter: int = 1000, tol: float = 1e-6) -> Tuple[np.ndarray, np.ndarray]:
    """Computes the Katz centrality of a network

    Args:
        network (csc_matrix): network
        nnodes (int): number of nodes
        alpha (float, optional): damping factor for Katz centrality. Defaults to 0.1.
        beta (float, optional): initial centrality. Defaults to 1.0.
        max_iter (int, optional): max iterations for power method. Defaults to 1000.
        tol (float, optional): tolerance for power method iteration. Defaults to 1e-6.

    Returns:
        Tuple[np.ndarray, np.ndarray]: ordered tuple of nnodes with their respective centralities
    """
    G = from_scipy_sparse_array(network)
    centralities = katz_centrality(G, alpha=alpha, beta=beta, max_iter=max_iter, tol=tol)

    return _extract_top_nodes(centralities, nnodes)


def compute_pagerank(network: csc_matrix, nnodes: int, alpha: float = 0.85, max_iter: int = 1000, tol: float = 1e-6) -> Tuple[np.ndarray, np.ndarray]:
    """Computes the PageRank of a network
    
        Args:
            network (csc_matrix): network
            nnodes (int): number of nodes
            alpha (float, optional): damping parameter for PageRank. Defaults to 0.1.
            max_iter (int, optional): max iterations for power method. Defaults to 1000.
            tol (float, optional): tolerance for power method iteration. Defaults to 1e-6.
    
        Returns:
            Tuple[np.ndarray, np.ndarray]: ordered tuple of nnodes with their respective centralities
        """
    G = from_scipy_sparse_array(network)
    centralities = pagerank(G, alpha, max_iter=max_iter, tol=tol)

    return _extract_top_nodes(centralities, nnodes)


def compute_betweenness_centrality(network: csc_matrix, nnodes: int) -> Tuple[np.ndarray, np.ndarray]:
    """Computes the betweenness centrality of a network

    Args:
        network (csc_matrix): network
        nnodes (int): number of nodes

    Returns:
        Tuple[np.ndarray, np.ndarray]: ordered tuple of nnodes with their respective centralities
    """
    G = from_scipy_sparse_array(network)
    centralities = betweenness_centrality(G)

    return _extract_top_nodes(centralities, nnodes)


def compute_closeness_centrality(network: csc_matrix, nnodes: int) -> Tuple[np.ndarray, np.ndarray]:
    """Computes the closeness centrality of a network
    
        Args:
            network (csc_matrix): network
            nnodes (int): number of nodes
    
        Returns:
            Tuple[np.ndarray, np.ndarray]: ordered tuple of nnodes with their respective centralities
        """
    G = from_scipy_sparse_array(network)
    centralities = closeness_centrality(G)

    return _extract_top_nodes(centralities, nnodes)

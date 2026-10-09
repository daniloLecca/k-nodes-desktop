import numpy as np
from gauss import gauss_exp, gauss_res
from lowrank import sgcenlr, commlr, stconvlr
from scipy.sparse.linalg import eigsh
from scipy.sparse import csc_matrix
from scipy.sparse.csgraph import connected_components
from typing import Literal, Optional, Tuple, Dict, Any
from time import perf_counter
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def sgcenhyb(A: csc_matrix, 
            fun_name: Literal["exp", "res"] = "exp", 
            nnodes: int = 1, 
            opts: Optional[Dict[str, Any]] = None) -> Tuple[
                np.ndarray, np.ndarray, bool, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, list, 
                Literal['no convergence', 'strong convergence', 'weak convergence']]:
    """
    Computes subgraph centrality via a two-stage hybrid algorithm and identifies the top K-nodes.
    Stage 1: Computes a low-rank approximation (PRIMME) to prune the network down to a candidate set of nodes (k_lr).
    Stage 2: Runs high-precision Gauss quadrature only on the candidate nodes to compute their exact subgraph centrality,
    then sorts them to identify the final top K-nodes.

    Parameters:
    ----------
    A : csc_matrix
        Adjacency matrix of the network (column sparse, symmetric, and unweighted).
    fun_name : Literal["exp", "res"]
        Matrix function: 'exp' for exponential subgraph centrality [exp(A)]_{ii},
        'res' for resolvent subgraph centrality [(I - alpha*A)^(-1)]_{ii}. Defaults to 'exp'.
    nnodes : int
        Number of final top K-nodes to identify.
    opts : Optional[Dict[str, Any]]
        Merged dictionary of options for both low-rank and Gauss quadrature stages:
        - 'lr_nnodes' (int): Number of candidate nodes sought during low-rank filtering (typically larger than nnodes).
        - 'gauss_tol' (float): Tolerance for Gauss quadrature convergence (default: 1e-3).
        - 'gauss_max_iterations' (int): Maximum Lanczos iterations per candidate node in Gauss stage (default: 200).
        - 'gauss_largest_eigenvalue' (float): Upper bound on lambda_max(A) (default: computed via eigsh).
        - 'alpha' (float): Resolvent attenuation factor (required if fun_name == 'res').
        - Low-rank options passed to sgcenlr ('lr_max_iterations', 'lr_approximation_tol', 'lr_primme_batch_size', etc.).

    Returns:
    -------
    Tuple[np.ndarray, np.ndarray, bool, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, list, Literal['no convergence', 'strong convergence', 'weak convergence']]:
        - k_nodes (np.ndarray): Indices of the top K-nodes identified after Gauss quadrature, sorted in descending order of score.
        - k_sgc (np.ndarray): Subgraph centrality scores of the final top K-nodes.
        - flag (bool): True if Gauss quadrature reached gauss_max_iterations on any evaluated candidate node.
        - iters (np.ndarray): Number of matrix-vector products performed by Gauss quadrature for each evaluated candidate node.
        - allsg (np.ndarray): Subgraph centrality scores computed via Gauss quadrature for all candidate nodes in k_lr.
        - k_lr (np.ndarray): Indices of candidate nodes selected by the first-stage low-rank approximation.
        - ksgc_lr (np.ndarray): Subgraph centrality scores estimated by the low-rank approximation for k_lr.
        - realN_lr (int): Number of eigenpairs used during the low-rank approximation stage.
        - S_history_lr (list): Candidate bounds history log throughout the low-rank approximation.
        - low_rank_convergence (str): Convergence outcome of the low-rank stage:
            'strong convergence' if exactly lr_nnodes were retained,
            'weak convergence' if additional nodes were retained,
            'no convergence' if all nodes in the network were retained.
    """
    if opts is None: 
        opts = {}

    gauss_tol = opts.get("gauss_tol", 1e-3)
    gauss_max_iterations = opts.get("gauss_max_iterations", 200)
    gauss_largest_eigenvalue = opts.get("gauss_largest_eigenvalue", eigsh(A, k=1, which='LA', return_eigenvectors=False)[0])
    alpha = opts.get("alpha", 0.0)

    n = A.shape[0]

    k_lr, ksgc_lr, realN_lr, S_history_lr = sgcenlr(A, fun_name=fun_name, nnodes=opts["lr_nnodes"], opts=opts)

    low_rank_size = k_lr.shape[0]
    allsg = np.zeros(low_rank_size)
    iters = np.zeros(low_rank_size)
    ei = np.zeros(n)

    info = 0

    theta = gauss_largest_eigenvalue
    if fun_name == 'res' and not (0 < alpha < 1 / theta):
        raise ValueError(f"alpha must be in (0, {1/theta:.6f}), got {alpha}")

    for i in range(low_rank_size):
        ei[k_lr[i]] = 1
        t0 = perf_counter()
        allsg[i], iters[i] = gauss_exp(A, ei, theta, opts) if fun_name == "exp" else gauss_res(A, ei, theta, alpha, opts)
        ei[k_lr[i]] = 0
        info += 1 if iters[i] >= gauss_max_iterations else 0
        logger.info(f"matrix-vector products, maxn, node, elapsed time: {iters[i]}, {gauss_max_iterations}, {i}, {perf_counter() - t0:.4f}")
        
    
    indx = np.argsort(allsg)[::-1]
    allsg = allsg[indx]

    k_nodes = k_lr[indx[:nnodes]]
    k_sgc = allsg[:nnodes]

    if low_rank_size == n:
        low_rank_convergence = "no convergence"
    elif low_rank_size == opts["lr_nnodes"]: 
        low_rank_convergence = "strong convergence"
    else:
        low_rank_convergence = "weak convergence"

    return k_nodes, k_sgc, info > 0, iters, allsg, k_lr, ksgc_lr, realN_lr, S_history_lr, low_rank_convergence

def commhyb(A: csc_matrix, 
            i: int,
            fun_name: Literal["exp", "res"] = "exp", 
            nnodes: int = 1, 
            opts: Optional[Dict[str, Any]] = None) -> Tuple[
                np.ndarray, np.ndarray, bool, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, list, 
                Literal['no convergence', 'strong convergence', 'weak convergence']]:
    """
    Computes node communicability from a source node i via a two-stage hybrid algorithm and identifies the top K-nodes.
    Stage 1: Extracts the connected component of node i (since nodes outside have 0 communicability), then computes
             a low-rank approximation (PRIMME) on the component to prune candidates down to a set k_lr.
    Stage 2: Runs high-precision Gauss-Radau quadrature on the selected candidate nodes using the polarization identity
             to evaluate bilinear forms e_i^T f(A) e_j, sorts them, and extracts the top K-nodes.

    Parameters:
    ----------
    A : csc_matrix
        Adjacency matrix of the network (column sparse, symmetric, and unweighted).
    i : int
        Index (0-based) of the source node from which communicability is measured.
    fun_name : Literal["exp", "res"]
        Matrix function: 'exp' for exponential communicability [exp(A)]_{ij},
        'res' for resolvent communicability [(I - alpha*A)^(-1)]_{ij}. Defaults to 'exp'.
    nnodes : int
        Number of final top K-nodes to identify.
    opts : Optional[Dict[str, Any]]
        Merged configuration dictionary for low-rank and Gauss quadrature stages:
        - 'lr_nnodes' (int): Candidate pool size sought during the low-rank stage (commlr).
        - 'gauss_tol' (float): Convergence tolerance for Gauss-Radau quadrature (default: 1e-3).
        - 'gauss_max_iterations' (int): Maximum Lanczos iterations per polarization vector in Gauss stage (default: 200).
        - 'gauss_largest_eigenvalue' (float): Upper bound on lambda_max(A_sub) (default: computed via eigsh on component).
        - 'alpha' (float): Resolvent attenuation factor in (0, 1/lambda_max) (required if fun_name == 'res').
        - Low-rank options passed to commlr ('lr_max_iterations', 'lr_approximation_tol', 'lr_primme_batch_size', etc.).

    Returns:
    -------
    Tuple[np.ndarray, np.ndarray, bool, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, list, Literal['no convergence', 'strong convergence', 'weak convergence']]:
        - k_nodes (np.ndarray): Indices of the top K-nodes with highest communicability to node i, sorted in descending order.
        - k_comm (np.ndarray): Communicability values [f(A)]_{ij} for the top K-nodes.
        - flag (bool): True if Gauss quadrature reached gauss_max_iterations on any evaluated node.
        - iters_full (np.ndarray): Array of length n containing matrix-vector products performed by Gauss quadrature (nonzero at k_lr).
        - allcomm_full (np.ndarray): Array of length n containing computed Gauss communicability for candidate nodes k_lr (zeros elsewhere).
        - k_lr (np.ndarray): Indices of candidate nodes selected by the low-rank approximation stage.
        - kcomm_lr (np.ndarray): Communicability values estimated by the low-rank approximation for k_lr.
        - realN_lr (int): Number of eigenpairs used during the low-rank approximation stage.
        - S_history_lr (list): Candidate bounds history log throughout the low-rank iterations.
        - low_rank_convergence (str): Convergence outcome of the low-rank stage:
            'strong convergence' if exactly lr_nnodes were retained,
            'weak convergence' if additional nodes were retained,
            'no convergence' if all nodes in the connected component were retained.
    """
    if i < 0 or i >= A.shape[0]:
        raise ValueError(f"node {i} not found, must be in the range [0, {A.shape[0]})") 
    
    if np.sum(A[:, i]) == 0:
        raise ValueError(f"node {i + 1} is not connected to any other node (degree 0).")

    ################################## START CONNECTED COMPONENT EXTRACTION ##########################
    n_components, labels = connected_components(csgraph=A, directed=False, return_labels=True)
    target_label = labels[i]
    component_mask = (labels == target_label)
    original_indices = np.where(component_mask)[0]
    
    A_sub = A[component_mask, :][:, component_mask]
    local_i = np.where(original_indices == i)[0][0]
    n_sub = A_sub.shape[0]
    
    if n_sub == 1:
        logger.warning(f"the connected component of node {i} contains only the node itself.")
        return np.array([]), np.array([]), False, np.array([]), np.array([]), np.array([]), np.array([]), 0, [], "strong convergence"

    logger.info(f"Extracted isolated network: {n_sub} nodes (original: {A.shape[0]} nodes).")

    ################################## END CONNECTED COMPONENT EXTRACTION ##########################
    if opts is None: 
        opts = {}

    gauss_tol = opts.get("gauss_tol", 1e-3)
    gauss_max_iterations = opts.get("gauss_max_iterations", 200)
    # compute the largest eigenvalue of the adjacency matrix of the connected component ("gauss_largest_eigenvalue" must be never given)
    gauss_largest_eigenvalue = opts.get("gauss_largest_eigenvalue", eigsh(A_sub, k=1, which='LA', return_eigenvectors=False)[0])
    alpha = opts.get("alpha", 0.0)

    theta = gauss_largest_eigenvalue
    if fun_name == 'res' and not (0 < alpha < 1 / theta):
        raise ValueError(f"alpha must be in (0, {1/theta:.6f}), got {alpha}")

    # WARNING: nnodes (parameter commlr) should be big enough otherwise some nodes get filtered out
    k_lr, kcomm_lr, realN_lr, S_history_lr = commlr(A, i, fun_name=fun_name, nnodes=opts["lr_nnodes"], opts=opts)

    low_rank_size = k_lr.shape[0]
    allcomm_local = np.zeros(low_rank_size)
    iters_local = np.zeros(low_rank_size)
    y_local = np.zeros(n_sub)

    info = 0

    # mapping from original indexes to A_sub 
    # given that original_indices is an ordered array, searchsorted is used to find the "positions"
    k_lr_local_indices = np.searchsorted(original_indices, k_lr)

    y_local[local_i] = 1
    
    # perform Gauss quadrature only on the nodes identified by the low rank approximation
    for idx, j_local in enumerate(k_lr_local_indices):
        t0 = perf_counter()
        if j_local == local_i:
            allcomm_local[idx], iters_local[idx] = gauss_exp(A_sub, y_local, theta, opts) if fun_name == "exp" else gauss_res(A_sub, y_local, theta, alpha, opts)
        else: 
            y_local[j_local] = 1
            allcomm1, iters1 = gauss_exp(A_sub, y_local/np.sqrt(2), theta, opts) if fun_name == "exp" else gauss_res(A_sub, y_local/np.sqrt(2), theta, alpha, opts)
            iters_local[idx] = iters1
            
            y_local[j_local] = -1
            allcomm2, iters2 = gauss_exp(A_sub, y_local/np.sqrt(2), theta, opts) if fun_name == "exp" else gauss_res(A_sub, y_local/np.sqrt(2), theta, alpha, opts)
            iters_local[idx] += iters2
            
            allcomm_local[idx] = 0.5 * (allcomm1 - allcomm2)
            y_local[j_local] = 0
            
        info += 1 if iters_local[idx] >= gauss_max_iterations else 0
        logger.info(f"matrix-vector products, maxn, node, elapsed time: {iters_local[idx]}, {gauss_max_iterations}, {k_lr[idx]}, {perf_counter() - t0:.4f}")
        
    # ordering of the indexes and communicabilities 
    indx_local = np.argsort(allcomm_local)[::-1]
    allcomm_sorted = allcomm_local[indx_local]

    # the final k nodes are a subset of the nodes selected through the low rank approximation
    k_nodes = k_lr[indx_local[:nnodes]]
    k_comm = allcomm_sorted[:nnodes]

    # check low rank convergence
    if low_rank_size == n_sub:
        low_rank_convergence = "no convergence"
    elif low_rank_size == opts["lr_nnodes"]: 
        low_rank_convergence = "strong convergence"
    else:
        low_rank_convergence = "weak convergence"

    # insert the k communicabilities into the original vector
    n = A.shape[0]
    allcomm_full = np.zeros(n)
    allcomm_full[k_lr] = allcomm_local
    
    iters_full = np.zeros(n)
    iters_full[k_lr] = iters_local

    logger.info("commhyb function completed")

    return k_nodes, k_comm, info > 0, iters_full, allcomm_full, k_lr, kcomm_lr, realN_lr, S_history_lr, low_rank_convergence

def stconvhyb(A: csc_matrix, 
            fun_name: Literal["exp", "res"] = "exp", 
            nnodes: int = 1, 
            opts: Optional[Dict[str, Any]] = None) -> Tuple[
                np.ndarray, np.ndarray, bool, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, list, 
                Literal['no convergence', 'strong convergence', 'weak convergence']]:
    """
    Computes starting convenience via a two-stage hybrid algorithm and identifies the top K-nodes.
    Stage 1: Computes a low-rank approximation (PRIMME) via stconvlr to prune the network down to a candidate set k_lr.
    Stage 2: Runs high-precision Gauss-Radau quadrature on the candidate nodes using the polarization identity,
             compute exact starting convenience e_i^T f(A) 1, sorts them, and identifies the final top K-nodes.

    Parameters:
    ----------
    A : csc_matrix
        Adjacency matrix of the network (column sparse, symmetric, and unweighted).
    fun_name : Literal["exp", "res"]
        Matrix function: 'exp' for exponential starting convenience [exp(A) 1]_i,
        'res' for resolvent starting convenience [(I - alpha*A)^(-1) 1]_i. Defaults to 'exp'.
    nnodes : int
        Number of final top K-nodes to identify.
    opts : Optional[Dict[str, Any]]
        Merged configuration dictionary for low-rank and Gauss quadrature stages:
        - 'lr_nnodes' (int): Candidate pool size sought during the low-rank stage (stconvlr).
        - 'gauss_tol' (float): Convergence tolerance for Gauss-Radau quadrature (default: 1e-3).
        - 'gauss_max_iterations' (int): Maximum Lanczos iterations per polarization vector in Gauss stage (default: 200).
        - 'gauss_largest_eigenvalue' (float): Upper bound on lambda_max(A) (default: computed via eigsh).
        - 'alpha' (float): Resolvent attenuation factor in (0, 1/lambda_max) (required if fun_name == 'res').
        - Low-rank options passed to stconvlr ('lr_max_iterations', 'lr_approximation_tol', 'lr_primme_batch_size', etc.).

    Returns:
    -------
    Tuple[np.ndarray, np.ndarray, bool, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, list, Literal['no convergence', 'strong convergence', 'weak convergence']]:
        - k_nodes (np.ndarray): Indices of the top K-nodes with highest starting convenience, sorted in descending order.
        - k_stconv (np.ndarray): Starting convenience scores of the top K-nodes.
        - flag (bool): True if Gauss quadrature reached gauss_max_iterations on any evaluated node.
        - iters_full (np.ndarray): Array of length n containing matrix-vector products performed by Gauss quadrature (nonzero at k_lr).
        - allstconv_full (np.ndarray): Array of length n containing computed Gauss starting convenience for candidate nodes k_lr (zeros elsewhere).
        - k_lr (np.ndarray): Indices of candidate nodes selected by the low-rank approximation stage.
        - kstconv_lr (np.ndarray): Starting convenience scores estimated by the low-rank approximation for k_lr.
        - realN_lr (int): Number of eigenpairs used during the low-rank approximation stage.
        - S_history_lr (list): Candidate bounds history log throughout the low-rank iterations.
        - low_rank_convergence (str): Convergence outcome of the low-rank stage:
            'strong convergence' if exactly lr_nnodes were retained,
            'weak convergence' if additional nodes were retained,
            'no convergence' if all nodes in the network were retained.
    """
    if opts is None: 
        opts = {}

    gauss_tol = opts.get("gauss_tol", 1e-3)
    gauss_max_iterations = opts.get("gauss_max_iterations", 200)
    gauss_largest_eigenvalue = opts.get("gauss_largest_eigenvalue", eigsh(A, k=1, which='LA', return_eigenvectors=False)[0])
    alpha = opts.get("alpha", 0.0)

    n = A.shape[0]

    if n == 1:
        logger.warning("the network has only 1 node, returning trivial result")
        return np.array([0]), np.array([1.0]), False, np.array([0]), np.array([1.0]), np.array([0]), np.array([1.0]), 0, [], "strong convergence"

    k_lr, kstconv_lr, realN_lr, S_history_lr = stconvlr(A, fun_name=fun_name, nnodes=opts["lr_nnodes"], opts=opts)

    low_rank_size = k_lr.shape[0]
    allstconv = np.zeros(low_rank_size)
    iters = np.zeros(low_rank_size)
    y = np.ones(n)

    info = 0

    theta = gauss_largest_eigenvalue
    if fun_name == 'res' and not (0 < alpha < 1 / theta):
        raise ValueError(f"alpha must be in (0, {1/theta:.6f}), got {alpha}")

    np3 = n + 3
    nm1 = n - 1

    # perform Gauss quadrature only on the nodes identified by the low rank approximation
    for idx, i in enumerate(k_lr):
        y[i] = 2  
        t0 = perf_counter()

        allstconv1, inf = gauss_exp(A, y/np.sqrt(np3), theta, opts) if fun_name == "exp" else gauss_res(A, y/np.sqrt(np3), theta, alpha, opts)
        iters[idx] = inf
        
        y[i] = 0  

        allstconv2, inf = gauss_exp(A, y/np.sqrt(nm1), theta, opts) if fun_name == "exp" else gauss_res(A, y/np.sqrt(nm1), theta, alpha, opts)
        allstconv[idx] = (np3 * allstconv1 - nm1 * allstconv2) / 4
        iters[idx] += inf

        info += 1 if iters[idx] >= gauss_max_iterations else 0
        y[i] = 1  
        logger.info(f"matrix-vector products, maxn, node, elapsed time: {iters[idx]}, {gauss_max_iterations}, {i}, {perf_counter() - t0:.4f}")
    
    # ordering of the indexes and communicabilities 
    indx = np.argsort(allstconv)[::-1]
    allstconv = allstconv[indx]

    # the final k nodes are a subset of the nodes selected through the low rank approximation
    k_nodes = k_lr[indx[:nnodes]]
    k_stconv = allstconv[:nnodes]

    # check low rank convergence
    if low_rank_size == n:
        low_rank_convergence = "no convergence"
    elif low_rank_size == opts["lr_nnodes"]: 
        low_rank_convergence = "strong convergence"
    else:
        low_rank_convergence = "weak convergence"

    # insert the k starting conveniences into the original vector
    allstconv_full = np.zeros(n)
    allstconv_full[k_lr] = allstconv
    iters_full = np.zeros(n)
    iters_full[k_lr] = iters

    logger.info("stconvhyb function completed")

    return k_nodes, k_stconv, info > 0, iters_full, allstconv_full, k_lr, kstconv_lr, realN_lr, S_history_lr, low_rank_convergence


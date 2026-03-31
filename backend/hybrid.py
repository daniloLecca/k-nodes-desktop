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
    Subgraph centrality computation via hybrid algorithm. First a low rank approximation is computed, 
    to retrieve a reduced list of candidate nodes, then a more accurate computation of the
    subgraph centrality is performed on the remaining nodes. 

    :param A: adjacency matrix
    :param fun_name: function name, must be either "exp" (exponential) or "res" (resolvent)
    :param nnodes: number of vip nodes seeked

    :return vip_nodes: vip nodes seeked
    :return vip_sgc: corresponding subgraph centralities of the vip nodes
    :return convergence: "exceeded max iterations number" if info > 0, "satisfied" otherwise (referring to Gauss quadrature)
    :return iters: number of matrix-vector products performed by the Gauss quadrature 
    :return vip_lr: vip nodes yielded by the low rank approximation
    :return vipsgc_lr: corresponding subgraph centralities for the vip nodes yielded by the low rank approximation
    :return realN_lr: number of used eigenpairs during the low rank approximation
    :return S_history_lr: log of the candidate nodes throughout the low rank approximation
    :return low_rank_convergence: 
        "no convergence" if the number of selected nodes by the low rank approximation equals the number of nodes of the network
        "weak convergence" if the number of selected nodes by the low rank approximation is smaller than the number of nodes of the network
        "strong convergence" if the number of selected nodes by the low rank approximation equals the number of seeked nodes
    """
    if opts is None: 
        opts = {}

    gauss_tol = opts.get("gauss_tol", 1e-3)
    gauss_max_iterations = opts.get("gauss_max_iterations", 200)
    gauss_largest_eigenvalue = opts.get("gauss_largest_eigenvalue", eigsh(A, k=1, which='LA', return_eigenvectors=False)[0])
    alpha = opts.get("alpha", 0.0)

    n = A.shape[0]

    vip_lr, vipsgc_lr, realN_lr, S_history_lr = sgcenlr(A, fun_name=fun_name, nnodes=opts["lr_nnodes"], opts=opts)

    low_rank_size = vip_lr.shape[0]
    allsg = np.zeros(low_rank_size)
    iters = np.zeros(low_rank_size)
    ei = np.zeros(n)

    info = 0

    theta = gauss_largest_eigenvalue
    if fun_name == 'res' and not (0 < alpha < 1 / theta):
        raise ValueError(f"alpha must be in (0, {1/theta:.6f}), got {alpha}")

    for i in range(low_rank_size):
        ei[vip_lr[i]] = 1
        t0 = perf_counter()
        allsg[i], iters[i] = gauss_exp(A, ei, theta, opts) if fun_name == "exp" else gauss_res(A, ei, theta, alpha, opts)
        ei[vip_lr[i]] = 0
        info += 1 if iters[i] >= gauss_max_iterations else 0
        logger.info(f"matrix-vector products, maxn, node, elapsed time: {iters[i]}, {gauss_max_iterations}, {i}, {perf_counter() - t0:.4f}")
        
    
    indx = np.argsort(allsg)[::-1]
    allsg = allsg[indx]

    vip_nodes = vip_lr[indx[:nnodes]]
    vip_sgc = allsg[:nnodes]

    if low_rank_size == n:
        low_rank_convergence = "no convergence"
    elif low_rank_size == opts["lr_nnodes"]: 
        low_rank_convergence = "strong convergence"
    else:
        low_rank_convergence = "weak convergence"

    return vip_nodes, vip_sgc, info > 0, iters, allsg, vip_lr, vipsgc_lr, realN_lr, S_history_lr, low_rank_convergence

def commhyb(A: csc_matrix, 
            i: int,
            fun_name: Literal["exp", "res"] = "exp", 
            nnodes: int = 1, 
            opts: Optional[Dict[str, Any]] = None) -> Tuple[
                np.ndarray, np.ndarray, bool, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, list, 
                Literal['no convergence', 'strong convergence', 'weak convergence']]:
    """
    Communicability computation via hybrid algorithm. First a low rank approximation is computed, 
    to retrieve a reduced list of candidate nodes, then a more accurate computation of the
    communicability is performed on the remaining nodes using Gauss quadrature. 
    For numerical stability and performance, only the communicabilities of the nodes that belong in the same connected component as 
    the node "i" are computed.

    :param A: adjacency matrix
    :param fun_name: function name, must be either "exp" (exponential) or "res" (resolvent)
    :param nnodes: number of vip nodes seeked

    :return vip_nodes: vip nodes seeked
    :return vip_comm: corresponding communicabilities of the vip nodes
    :return convergence: "exceeded max iterations number" if info > 0, "satisfied" otherwise (referring to Gauss quadrature)
    :return iters_full: number of matrix-vector products performed by the Gauss quadrature 
    :return allcomm_full: all communicabilities of the connected component of i
    :return vip_lr: vip nodes yielded by the low rank approximation
    :return vipcomm_lr: corresponding communicabilites for the vip nodes yielded by the low rank approximation
    :return realN_lr: number of used eigenpairs during the low rank approximation
    :return S_history_lr: log of the candidate nodes throughout the low rank approximation
    :return low_rank_convergence: 
        "no convergence" if the number of selected nodes by the low rank approximation equals the number of nodes of the network
        "weak convergence" if the number of selected nodes by the low rank approximation is smaller than the number of nodes of the network
        "strong convergence" if the number of selected nodes by the low rank approximation equals the number of seeked nodes
    
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
    vip_lr, vipcomm_lr, realN_lr, S_history_lr = commlr(A, i, fun_name=fun_name, nnodes=opts["lr_nnodes"], opts=opts)

    low_rank_size = vip_lr.shape[0]
    allcomm_local = np.zeros(low_rank_size)
    iters_local = np.zeros(low_rank_size)
    y_local = np.zeros(n_sub)

    info = 0

    # mapping from original indexes to A_sub 
    # given that original_indices is an ordered array, searchsorted is used to find the "positions"
    vip_lr_local_indices = np.searchsorted(original_indices, vip_lr)

    y_local[local_i] = 1
    
    # perform Gauss quadrature only on the nodes identified by the low rank approximation
    for idx, j_local in enumerate(vip_lr_local_indices):
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
        logger.info(f"matrix-vector products, maxn, node, elapsed time: {iters_local[idx]}, {gauss_max_iterations}, {vip_lr[idx]}, {perf_counter() - t0:.4f}")
        
    # ordering of the indexes and communicabilities 
    indx_local = np.argsort(allcomm_local)[::-1]
    allcomm_sorted = allcomm_local[indx_local]

    # the final vip nodes are a subset of the nodes selected through the low rank approximation
    vip_nodes = vip_lr[indx_local[:nnodes]]
    vip_comm = allcomm_sorted[:nnodes]

    # check low rank convergence
    if low_rank_size == n_sub:
        low_rank_convergence = "no convergence"
    elif low_rank_size == opts["lr_nnodes"]: 
        low_rank_convergence = "strong convergence"
    else:
        low_rank_convergence = "weak convergence"

    # insert the vip communicabilities into the original vector
    n = A.shape[0]
    allcomm_full = np.zeros(n)
    allcomm_full[vip_lr] = allcomm_local
    
    iters_full = np.zeros(n)
    iters_full[vip_lr] = iters_local

    logger.info("commhyb function completed")

    return vip_nodes, vip_comm, info > 0, iters_full, allcomm_full, vip_lr, vipcomm_lr, realN_lr, S_history_lr, low_rank_convergence

def stconvhyb(A: csc_matrix, 
            fun_name: Literal["exp", "res"] = "exp", 
            nnodes: int = 1, 
            opts: Optional[Dict[str, Any]] = None) -> Tuple[
                np.ndarray, np.ndarray, bool, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, list, 
                Literal['no convergence', 'strong convergence', 'weak convergence']]:
    """
    Starting convenience computation via hybrid algorithm. First a low rank approximation is computed, 
    to retrieve a reduced list of candidate nodes, then a more accurate computation of the
    starting convenience is performed on the remaining nodes. 

    :param A: adjacency matrix
    :param fun_name: function name, must be either "exp" (exponential) or "res" (resolvent)
    :param nnodes: number of vip nodes seeked

    :return vip_nodes: vip nodes seeked
    :return vip_sgc: corresponding starting conveniences of the vip nodes
    :return convergence: "exceeded max iterations number" if info > 0, "satisfied" otherwise (referring to Gauss quadrature)
    :return iters: number of matrix-vector products performed by the Gauss quadrature 
    :return vip_lr: vip nodes yielded by the low rank approximation
    :return vipsgc_lr: corresponding starting conveniences for the vip nodes yielded by the low rank approximation
    :return realN_lr: number of used eigenpairs during the low rank approximation
    :return S_history_lr: log of the candidate nodes throughout the low rank approximation
    :return low_rank_convergence: 
        "no convergence" if the number of selected nodes by the low rank approximation equals the number of nodes of the network
        "weak convergence" if the number of selected nodes by the low rank approximation is smaller than the number of nodes of the network
        "strong convergence" if the number of selected nodes by the low rank approximation equals the number of seeked nodes
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

    vip_lr, vipstconv_lr, realN_lr, S_history_lr = stconvlr(A, fun_name=fun_name, nnodes=opts["lr_nnodes"], opts=opts)

    low_rank_size = vip_lr.shape[0]
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
    for idx, i in enumerate(vip_lr):
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

    # the final vip nodes are a subset of the nodes selected through the low rank approximation
    vip_nodes = vip_lr[indx[:nnodes]]
    vip_stconv = allstconv[:nnodes]

    # check low rank convergence
    if low_rank_size == n:
        low_rank_convergence = "no convergence"
    elif low_rank_size == opts["lr_nnodes"]: 
        low_rank_convergence = "strong convergence"
    else:
        low_rank_convergence = "weak convergence"

    # insert the vip starting conveniences into the original vector
    allstconv_full = np.zeros(n)
    allstconv_full[vip_lr] = allstconv
    iters_full = np.zeros(n)
    iters_full[vip_lr] = iters

    logger.info("stconvhyb function completed")

    return vip_nodes, vip_stconv, info > 0, iters_full, allstconv_full, vip_lr, vipstconv_lr, realN_lr, S_history_lr, low_rank_convergence


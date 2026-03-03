import numpy as np
from math import sqrt
from gauss import gauss_exp, gauss_res, commgauss
from lowrank import sgcenlr, commlr, stconvlr
from scipy.sparse.linalg import eigsh
from scipy.sparse import csc_matrix
from scipy.sparse.csgraph import connected_components
from typing import Literal, Optional, Tuple, Dict, Any, Union
from time import perf_counter
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def sgcenhyb(A: csc_matrix, 
            fun_name: Literal["exp", "res"] = "exp", 
            nnodes: int = 1, 
            opts: Optional[Dict[str, Any]] = None):
    """
    Subgraph centrality computation via hybrid algorithm. First a low rank approximation is computed, 
    to retrieve a reduced list of candidate nodes, then a more accurate computation of the
    subgraph centrality is performed on the remaining nodes. 
    """
    if opts is None: 
        opts = {}

    gausstolq = opts.get("gausstolq", 1e-3)
    gaussmaxn = opts.get("gaussmaxn", 200)
    gaussmu = opts.get("gaussmu", eigsh(A, k=1, which='LA', return_eigenvectors=False)[0])
    alpha = opts.get("alpha", 0.0)

    n = A.shape[0]

    vip_lr, vipsgc_lr, realN_lr, S_history_lr = sgcenlr(A, fun_name=fun_name, nnodes=nnodes, opts=opts)

    low_rank_size = vip_lr.shape[0]
    allsg = np.zeros(low_rank_size)
    iters = np.zeros(low_rank_size)
    ei = np.zeros(n)

    info = 0

    theta = gaussmu
    if fun_name == 'res' and not (0 < alpha < 1 / theta):
        raise ValueError(f"alpha must be in (0, {1/theta:.6f}), got {alpha}")

    for i in range(low_rank_size):
        ei[vip_lr[i]] = 1
        t0 = perf_counter()
        allsg[i], iters[i] = gauss_exp(A, ei, theta, opts) if fun_name == "exp" else gauss_res(A, ei, theta, alpha, opts)
        ei[vip_lr[i]] = 0
        info += 1 if iters[i] >= gaussmaxn else 0
        logger.info(f"matrix-vector products, maxn, node, elapsed time: {iters[i]}, {gaussmaxn}, {i}, {perf_counter() - t0:.4f}")
        
    
    indx = np.argsort(allsg)[::-1]
    allsg = allsg[indx]

    vip_nodes = vip_lr[indx[:nnodes]]
    vip_sgc = allsg[:nnodes]

    if low_rank_size == n:
        low_rank_convergence = "no convergence"
    elif low_rank_size == nnodes: 
        low_rank_convergence = "strong convergence"
    else:
        low_rank_convergence = "weak convergence"

    return vip_nodes, vip_sgc, info > 0, iters, allsg, vip_lr, vipsgc_lr, realN_lr, S_history_lr, low_rank_convergence

def commhyb(A: csc_matrix, 
            i: int,
            fun_name: Literal["exp", "res"] = "exp", 
            nnodes: int = 1, 
            opts: Optional[Dict[str, Any]] = None):
    """
    Communicability computation via hybrid algorithm. First a low rank approximation is computed, 
    to retrieve a reduced list of candidate nodes, then a more accurate computation of the
    communicability is performed on the remaining nodes using Gauss quadrature. 
    """
    if i < 0 or i >= A.shape[0]:
        raise ValueError(f"node {i} not found, must be in the range [0, {A.shape[0]})") 
    
    if np.sum(A[:, i]) == 0:
        raise ValueError(f"node {i} is not connected to any other node (degree 0).")

    # Estrazione della componente connessa (come in commgauss)
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

    if opts is None: 
        opts = {}

    gausstolq = opts.get("gausstolq", 1e-3)
    gaussmaxn = opts.get("gaussmaxn", 200)
    # Calcolo del raggio spettrale sulla componente connessa isolata per la quadratura di Gauss
    gaussmu = opts.get("gaussmu", eigsh(A_sub, k=1, which='LA', return_eigenvectors=False)[0])
    alpha = opts.get("alpha", 0.0)

    theta = gaussmu
    if fun_name == 'res' and not (0 < alpha < 1 / theta):
        raise ValueError(f"alpha must be in (0, {1/theta:.6f}), got {alpha}")

    # Fase Low-rank: ricava i nodi candidati (indici riferiti alla matrice originale A)
    # BUG: nnodes (parameter commlr) should be big enough otherwise some nodes get filtered out
    vip_lr, vipcomm_lr, realN_lr, S_history_lr = commlr(A, i, fun_name=fun_name, nnodes=int(0.09 * n_sub), opts=opts)

    low_rank_size = vip_lr.shape[0]
    allcomm_local = np.zeros(low_rank_size)
    iters_local = np.zeros(low_rank_size)
    y_local = np.zeros(n_sub)

    info = 0

    # Mappatura degli indici restituiti da commlr (matrice originale) agli indici di A_sub
    # Poiché original_indices è un array ordinato, possiamo usare searchsorted per trovare le posizioni
    vip_lr_local_indices = np.searchsorted(original_indices, vip_lr)

    y_local[local_i] = 1
    
    # Esegue la quadratura di Gauss SOLO sui candidati identificati dalla Low-rank
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
            
        info += 1 if iters_local[idx] >= gaussmaxn else 0
        logger.info(f"matrix-vector products, maxn, node, elapsed time: {iters_local[idx]}, {gaussmaxn}, {vip_lr[idx]}, {perf_counter() - t0:.4f}")
        
    # Ordinamento dei risultati post-Gauss
    indx_local = np.argsort(allcomm_local)[::-1]
    allcomm_sorted = allcomm_local[indx_local]

    # I nodi vip aggiornati e le loro communicabilities
    vip_nodes = vip_lr[indx_local[:nnodes]]
    vip_comm = allcomm_sorted[:nnodes]

    # Verifica stato di convergenza del low rank
    if low_rank_size == n_sub:
        low_rank_convergence = "no convergence"
    elif low_rank_size == nnodes: 
        low_rank_convergence = "strong convergence"
    else:
        low_rank_convergence = "weak convergence"

    # Crea array completi per mantenere la compatibilità con l'estrazione e i log originali
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
            opts: Optional[Dict[str, Any]] = None):
    """
    Starting convenience computation via hybrid algorithm. First a low rank approximation is computed, 
    to retrieve a reduced list of candidate nodes, then a more accurate computation of the
    starting convenience is performed on the remaining nodes. 
    """
    if opts is None: 
        opts = {}

    gausstolq = opts.get("gausstolq", 1e-3)
    gaussmaxn = opts.get("gaussmaxn", 200)
    gaussmu = opts.get("gaussmu", eigsh(A, k=1, which='LA', return_eigenvectors=False)[0])
    alpha = opts.get("alpha", 0.0)

    n = A.shape[0]

    if n == 1:
        logger.warning("the network has only 1 node, returning trivial result")
        return np.array([0]), np.array([1.0]), False, np.array([0]), np.array([1.0]), np.array([0]), np.array([1.0]), 0, [], "strong convergence"

    # Low-rank phase
    vip_lr, vipstconv_lr, realN_lr, S_history_lr = stconvlr(A, fun_name=fun_name, nnodes=nnodes, opts=opts)

    low_rank_size = vip_lr.shape[0]
    allstconv = np.zeros(low_rank_size)
    iters = np.zeros(low_rank_size)
    y = np.ones(n)

    info = 0

    theta = gaussmu
    if fun_name == 'res' and not (0 < alpha < 1 / theta):
        raise ValueError(f"alpha must be in (0, {1/theta:.6f}), got {alpha}")

    np3 = n + 3
    nm1 = n - 1

    for idx, i in enumerate(vip_lr):
        y[i] = 2  
        t0 = perf_counter()

        allstconv1, inf = gauss_exp(A, y/np.sqrt(np3), theta, opts) if fun_name == "exp" else gauss_res(A, y/np.sqrt(np3), theta, alpha, opts)
        iters[idx] = inf
        
        y[i] = 0  

        allstconv2, inf = gauss_exp(A, y/np.sqrt(nm1), theta, opts) if fun_name == "exp" else gauss_res(A, y/np.sqrt(nm1), theta, alpha, opts)
        allstconv[idx] = (np3 * allstconv1 - nm1 * allstconv2) / 4
        iters[idx] += inf

        info += 1 if iters[idx] >= gaussmaxn else 0
        y[i] = 1  
        logger.info(f"matrix-vector products, maxn, node, elapsed time: {iters[idx]}, {gaussmaxn}, {i}, {perf_counter() - t0:.4f}")
    
    indx = np.argsort(allstconv)[::-1]
    allstconv = allstconv[indx]

    vip_nodes = vip_lr[indx[:nnodes]]
    vip_stconv = allstconv[:nnodes]

    if low_rank_size == n:
        low_rank_convergence = "no convergence"
    elif low_rank_size == nnodes: 
        low_rank_convergence = "strong convergence"
    else:
        low_rank_convergence = "weak convergence"

    # Create full-size arrays for compatibility
    allstconv_full = np.zeros(n)
    allstconv_full[vip_lr] = allstconv
    iters_full = np.zeros(n)
    iters_full[vip_lr] = iters

    logger.info("stconvhyb function completed")

    return vip_nodes, vip_stconv, info > 0, iters_full, allstconv_full, vip_lr, vipstconv_lr, realN_lr, S_history_lr, low_rank_convergence


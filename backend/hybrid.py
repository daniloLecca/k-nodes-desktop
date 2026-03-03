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


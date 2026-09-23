import numpy as np
from math import sqrt
from scipy.sparse.linalg import eigsh
from scipy.sparse import csc_matrix
from scipy.sparse.csgraph import connected_components
from scipy.linalg import norm, eigh_tridiagonal
from typing import Literal, Optional, Tuple, Dict, Any, Union
from time import perf_counter
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def expm_eig(T: np.ndarray, mu: float = 0.0) -> float:
    """
    Compute u * exp(T) * u', where T is the Lanczos tridiagonal matrix

    :param T: tridiagonal Lanczos matrix
    :param mu: spectral shift parameter
    :return: the computed exponent
    """
    eigvals, V = np.linalg.eigh(T)
    exp_vals = np.exp(eigvals - mu)
    return float(np.sum((V[0, :] ** 2) * exp_vals))

def res(T: np.ndarray, alpha: float) -> float:
    """
    Computes the resolvent (I - alpha*T)^(-1) using spectral decomposition and 
    taking advantage of the structure of T (tridiagonal).
    
    :param T: Lanczos tridiagonal matrix
    :param alpha: spectral shift parameter (must satisfy 0 < alpha < 1/lambda_max(T))
    :return: (I - alpha*T)^(-1)
    """
    d = np.diag(T)
    e = np.diag(T, k=-1)
    eigvals, V = eigh_tridiagonal(d, e)
    
    diag_elements = 1 / (1 - alpha * eigvals)
    return float(np.sum((V[0, :] ** 2) * diag_elements))


def opolyval(alfa: np.ndarray, beta: np.ndarray, beta0: float, x: float) -> Tuple[float, float]:
    """
    Computes orthonormal polynomials via recurrence

    Args:
        alfa (np.ndarray): _description_
        beta (np.ndarray): _description_
        beta0 (float): _description_
        x (float): _description_

    Returns:
        Tuple[float, float]: _description_
    """
    p1 = 1.0 / beta0
    p = (x - alfa[0]) / beta[0]
    
    # starting from second element
    for k in range(1, len(alfa)):
        p0 = p1
        p1 = p
        p = ((x - alfa[k]) * p1 - beta[k-1] * p0) / beta[k]
        
    return float(p), float(p1)

def gauss_exp(A: Union[csc_matrix, np.ndarray], u: np.ndarray, theta: Optional[float] = None, opts: Optional[Dict[str, Any]] = None) -> Tuple[float, int]:
    """
    Computes u' * expm(A) * u using Gauss quadrature.
    
    :param A: csc_matrix or ndarray
    :param u: column vector
    :param theta: estimate of the largest eigenvalue of A (if not given is computed)
    :param opts: options dictionary
    :return: (fval, info) - quadrature value and number of iterations
    """
    # default options
    default_opts = {
        "gauss_tol": 1e-3,
        "gausstau": 1e-10,
        "gauss_max_iterations": 100,
        "gauss_largest_eigenvalue": None,     # if None then default is theta
        "gaussreorth": 0,    # 0: no, 1: MGS, 2: CGS, 3: Double CGS
        "gaussmgs": True     # True for using MGS in the main step
    }

    if opts is None:
        opts = {}
    # options merge
    options = {**default_opts, **opts}
    
    # handling theta
    if theta is None:
        # if not given, the largest eigenvalue is computed
        # 'LA' = Largest Algebraic
        t0 = perf_counter()
        theta = eigsh(A, k=1, which='LA', return_eigenvectors=False)[0]
        print(f"Tempo eigsh: {perf_counter() - t0:.4f} s")            

    # Use options["gauss_largest_eigenvalue"] if explicitly set (even if 0.0), otherwise use theta
    mu = theta if options["gauss_largest_eigenvalue"] is None else options["gauss_largest_eigenvalue"]
    
    # making sure that u is a column vector
    u = np.array(u, dtype=np.float64).ravel()
    m = u.shape[0]
    
    # matrix-vector product operator
    A_csr = A.tocsr()
    mvprod = lambda x: A_csr.dot(x)

    beta = norm(u)
    sqrt_eps = np.sqrt(np.finfo(float).eps)
    
    # max iterations number, (the max number of iterations can't be larger than the number of rows of the matrix A)
    max_n = min(options["gauss_max_iterations"], m)
    
    if options["gaussreorth"]: Q = np.zeros((m, max_n + 1))
        
    T = np.zeros((max_n + 1, max_n + 1))
    alf = np.zeros(max_n)
    bet = np.zeros(max_n + 1)
    bet[0] = beta
    
    q_0 = np.zeros_like(u)
    q = u / beta
    
    if options["gaussreorth"]: Q[:, 0] = q.ravel()

    dif = 1000.0
    g = 0.0
    gr = 0.0 # g with an additional step
    
    # Lanczos loop
    i = 0 
    t0 = perf_counter()
    while (dif > options["gauss_tol"] * abs(g)) and (i < max_n):
        
        # compute the product between the adjacency matrix and the vector
        
        v = mvprod(q)
        # local orthogonalization
        if options["gaussmgs"]:
            v -= beta * q_0
            alfa = float(q.dot(v))
            v -= alfa * q
        else:
            alfa = float(q.dot(v))
            v -= beta * q_0 - alfa * q
            
        # global re-orthogonalization
        if options["gaussreorth"]:
            # Q[:, :i+1] previous vectors
            v_flat = v.ravel()
            
            reorth_type = options["gaussreorth"]
            
            if reorth_type == 1: # MGS
                for j in range(i + 1):
                    q_j = Q[:, j]
                    proj = np.dot(v_flat, q_j)
                    v_flat -= proj * q_j
                v = v_flat.reshape(-1, 1)
            elif reorth_type == 2: # CGS
                Q_curr = Q[:, :i+1]
                v_flat -= Q_curr @ (Q_curr.T @ v_flat)
                v = v_flat.reshape(-1, 1)
                
            elif reorth_type == 3: # Double CGS
                Q_curr = Q[:, :i+1]
                c = Q_curr.T @ v_flat
                v_flat -= Q_curr @ c
                if norm(c) > sqrt_eps: # second step if necessary
                    c1 = Q_curr.T @ v_flat
                    v_flat -= Q_curr @ c1
                v = v_flat.reshape(-1, 1)

        # update of beta
        beta = sqrt(v.dot(v))
        q_0 = q # save current q for the next step
        
        # Check breakdown
        if beta < options["gausstau"]:
            # Breakdown: exact convergence
            T[i, i] = alfa
            # compute exponential
            g = expm_eig(T[:i+1, :i+1], mu)
            gr = g
            break
        else:
            q = v / beta
            
        if options["gaussreorth"]:
            Q[:, i+1] = q.ravel()
            
        # save Lanczos coefficients
        alf[i] = alfa
        bet[i+1] = beta # bet[0] is the initial norm, bet[1] is beta_1, etc.
        
        # --- Gauss Quadrature ---
        
        # computing orthogonal polynomials for the missing node
        # alf and bet are passed to the current iteration
        # In Matlab: opolyval(alf(1:i),bet(2:i+1),1,theta)
        # Python slicing: alf[:i+1], bet[1:i+2]
        pm, pm1 = opolyval(alf[:i+1], bet[1:i+2], 1.0, theta)
        # alfk1 (extra node for the extended quadrature)
        # alfk1 = theta - bet(i+1)*(pm1/pm)
        # bet[i+1] corresponds to the beta just calculated
        alfk1 = theta - beta * (pm1 / pm)
        
        # building extended T (tridiagonal matrix)
        
        T[i, i] = alfa
        T[i, i+1] = beta
        T[i+1, i] = beta
        T[i+1, i+1] = alfk1 # new node for the estimate
        
        # estimate the integral with T_k 
        g = expm_eig(T[:i+1, :i+1], mu)
        
        # estimate the integral with T_{k + 1}
        gr = expm_eig(T[:i+2, :i+2], mu)
        
        dif = abs(gr - g) / 2.0
        
        i += 1 
    print(f"Tempo fine ciclo: {perf_counter() - t0:.4f} s")            
    # final result
    # fval = bet(1)^2 * (gr + g)/2
    # bet[0] is the initial norm of u
    fval = (bet[0]**2) * (gr + g) / 2.0
    info = i

    e_mu = np.exp(mu)
    if np.isfinite(e_mu):
        fval = e_mu * fval
    else:
        print(f"Warning: Result is scaled by exp({mu:.2e})")
    
    return fval, info # return the final value, iterations

# usage example:
# A = np.array([[2., -1.], [-1., 2.]])
# u = np.array([1., 0.])
# val, steps = gaussexp(A, u, theta=3.0)
# print(val, steps)




def gauss_res(A: Union[csc_matrix, np.ndarray], u: np.ndarray, rho: float, alpha: float, opts: Optional[Dict[str, Any]] = None) -> Tuple[float, int]:
    """
    Computes (A - alpha*I)^(-1) Gauss quadrature.
    
    :param A: csc_matrix or ndarray
    :param u: column vector
    :param rho: estimate of the largest eigenvalue of A (if not given is computed)
    :param alpha: alpha for resolvent
    :param opts: options dictionary
    :return: (fval, info) - quadrature value and number of iterations
    """
    # default options
    default_opts = {
        "gauss_tol": 1e-3,
        "gausstau": 1e-10,
        "gauss_max_iterations": 100,
        "gaussreorth": 0,    # 0: no, 1: MGS, 2: CGS, 3: Double CGS
        "gaussmgs": True     # True for using MGS in the main step
    }

    opts = opts or {}
    # options merge
    options = {**default_opts, **opts}
    
    # Validate alpha is in valid range
    if not (0 < alpha < 1 / rho):
        raise ValueError(f"alpha must be in (0, {1/rho:.6f}), got {alpha}")
    
    # theta is used in the polynomial approximation (set to largest eigenvalue)
    theta = rho
    
    # making sure that u is a column vector
    u = np.array(u, dtype=np.float64).ravel()
    m = u.shape[0]
    
    # matrix-vector product operator
    A_csr = A.tocsr()
    mvprod = lambda x: A_csr.dot(x)

    beta = norm(u)
    sqrt_eps = np.sqrt(np.finfo(float).eps)
    
    # max iterations number, (the max number of iterations can't be larger than the number of rows of the matrix A)
    max_n = min(options["gauss_max_iterations"], m)
    
    if options["gaussreorth"]: Q = np.zeros((m, max_n + 1))
        
    T = np.zeros((max_n + 1, max_n + 1))
    alf = np.zeros(max_n)
    bet = np.zeros(max_n + 1)
    bet[0] = beta
    
    q_0 = np.zeros_like(u)
    q = u / beta
    
    if options["gaussreorth"]: Q[:, 0] = q.ravel()

    dif = 1000.0
    g = 0.0
    gr = 0.0 # g with an additional step
    
    # Lanczos loop
    i = 0 
    while (dif > options["gauss_tol"] * abs(g)) and (i < max_n):
        
        # compute the product between the adjacency matrix and the 
        v = mvprod(q)
        
        # local orthogonalization
        if options["gaussmgs"]:
            v -= beta * q_0
            alfa = float(q.dot(v))
            v -= alfa * q
        else:
            alfa = float(q.dot(v))
            v -= beta * q_0 - alfa * q
            
        # global re-orthogonalization
        if options["gaussreorth"]:
            # Q[:, :i+1] previous vectors
            v_flat = v.ravel()
            
            reorth_type = options["gaussreorth"]
            
            if reorth_type == 1: # MGS
                for j in range(i + 1):
                    q_j = Q[:, j]
                    proj = np.dot(v_flat, q_j)
                    v_flat -= proj * q_j
                v = v_flat.reshape(-1, 1)
                    
            elif reorth_type == 2: # CGS
                Q_curr = Q[:, :i+1]
                v_flat -= Q_curr @ (Q_curr.T @ v_flat)
                v = v_flat.reshape(-1, 1)
                
            elif reorth_type == 3: # Double CGS
                Q_curr = Q[:, :i+1]
                c = Q_curr.T @ v_flat
                v_flat -= Q_curr @ c
                if norm(c) > sqrt_eps: # second step if necessary
                    c1 = Q_curr.T @ v_flat
                    v_flat -= Q_curr @ c1
                v = v_flat.reshape(-1, 1)

        # update of beta
        beta = sqrt(v.dot(v))
        q_0 = q # save current q for the next step
        
        # Check breakdown
        if beta < options["gausstau"]:
            # Breakdown: exact convergence
            T[i, i] = alfa
            # compute exponential
            T_sub = T[:i+1, :i+1]
            g = res(T_sub, alpha)
            gr = g
            break
        else:
            q = v / beta
            
        if options["gaussreorth"]:
            Q[:, i+1] = q.ravel()
            
        # save Lanczos coefficients
        alf[i] = alfa
        bet[i+1] = beta # bet[0] is the initial norm, bet[1] is beta_1, etc.
        
        # --- Gauss Quadrature ---
        
        # computing orthogonal polynomials for the missing node
        # alf and bet are passed to the current iteration
        # In Matlab: opolyval(alf(1:i),bet(2:i+1),1,theta)
        # Python slicing: alf[:i+1], bet[1:i+2]
        
        pm, pm1 = opolyval(alf[:i+1], bet[1:i+2], 1.0, theta)
        
        # alfk1 (extra node for the extended quadrature)
        # alfk1 = theta - bet(i+1)*(pm1/pm)
        # bet[i+1] corresponds to the beta just calculated
        alfk1 = theta - beta * (pm1 / pm)
        
        # building extended T (tridiagonal matrix)
        
        T[i, i] = alfa
        T[i, i+1] = beta
        T[i+1, i] = beta
        T[i+1, i+1] = alfk1 # new node for the estimate
        
        # estimate the integral with T_k 
        g = res(T[:i+1, :i+1], alpha)
        
        # estimate the integral with T_{k + 1}
        gr = res(T[:i+2, :i+2], alpha)
        
        dif = abs(gr - g) / 2.0
        
        i += 1 
        
    # final result
    # fval = bet(1)^2 * (gr + g)/2
    # bet[0] is the initial norm of u
    fval = (bet[0]**2) * (gr + g) / 2.0
    info = i
        
    return fval, info # return the final value and the number of iterations


def sgcengauss(A: csc_matrix, 
            fun_name: Literal["exp", "res"] = "exp", 
            nnodes: int = 1, 
            opts: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, np.ndarray, bool, np.ndarray, np.ndarray]:
    
    if opts is None: 
        opts = {}

    gauss_tol = opts.get("gauss_tol", 1e-3)
    gauss_max_iterations = opts.get("gauss_max_iterations", 200)
    gauss_largest_eigenvalue = opts.get("gauss_largest_eigenvalue", eigsh(A, k=1, which='LA', return_eigenvectors=False)[0])
    alpha = opts.get("alpha", 0.0)

    logger.info(f"Starting sgcengauss: nnodes = {nnodes}, options = {opts}")

    n = A.shape[0]

    allsg = np.zeros(n)
    iters = np.zeros(n)
    ei = np.zeros(n)

    info = 0

    theta = gauss_largest_eigenvalue
    if fun_name == 'res' and not (0 < alpha < 1 / theta):
        raise ValueError(f"alpha must be in (0, {1/theta:.6f}), got {alpha}")

    for i in range(n):
        ei[i] = 1
        t0 = perf_counter()
        allsg[i], iters[i] = gauss_exp(A, ei, theta, opts) if fun_name == "exp" else gauss_res(A, ei, theta, alpha, opts)
        ei[i] = 0
        info += 1 if iters[i] >= gauss_max_iterations else 0
        logger.info(f"matrix-vector products, maxn, node, elapsed time: {iters[i]}, {gauss_max_iterations}, {i}, {perf_counter() - t0:.4f}")
        
    
    indx = np.argsort(allsg)[::-1]
    allsg = allsg[indx]

    vip_nodes = indx[:nnodes]
    vip_sgc = allsg[:nnodes]

    logger.info("gauss function completed")

    return vip_nodes, vip_sgc, info > 0, iters, allsg


def commgauss(A: csc_matrix, 
            i: int, 
            fun_name: Literal["exp", "res"] = "exp", 
            nnodes: int = 1, 
            opts: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, np.ndarray, bool, np.ndarray, np.ndarray]:
    
    if i < 0 or i >= A.shape[0]:
        raise ValueError(f"node {i} not found, must be in the range [0, {A.shape[0]})") 
    
    if np.sum(A[:, i]) == 0:
        raise ValueError(f"node {i + 1} is not connected to any other node (degree 0).")
    
    # extracting connected component
    n_components, labels = connected_components(csgraph=A, directed=False, return_labels=True)
    target_label = labels[i]
    component_mask = (labels == target_label)
    original_indices = np.where(component_mask)[0]
    
    A_sub = A[component_mask, :][:, component_mask]
    local_i = np.where(original_indices == i)[0][0]
    n_sub = A_sub.shape[0]
    
    if n_sub == 1:
        logger.warning(f"the connected component of node {i} contains only the node itself.")
        return np.array([]), np.array([]), False, np.array([]), np.array([])

    logger.info(f"Extracted isolated network: {n_sub} nodes (original: {A.shape[0]} nodes).")

    if opts is None: 
        opts = {}

    gauss_tol = opts.get("gauss_tol", 1e-3)
    gauss_max_iterations = opts.get("gauss_max_iterations", 200)
    # Compute largest eigenvalue of A_sub instead of A
    gauss_largest_eigenvalue = opts.get("gauss_largest_eigenvalue", eigsh(A_sub, k=1, which='LA', return_eigenvectors=False)[0])
    alpha = opts.get("alpha", 0.0)
    logger.info(alpha)

    logger.info(f"Starting commgauss: nnodes = {nnodes}, options = {opts}")

    allcomm_local = np.zeros(n_sub)
    iters_local = np.zeros(n_sub)
    y_local = np.zeros(n_sub)

    info = 0

    theta = gauss_largest_eigenvalue
    logger.info(theta)
    if fun_name == 'res' and not (0 < alpha < 1 / theta):
        raise ValueError(f"alpha must be in (0, {1/theta:.6f}), got {alpha}")

    y_local[local_i] = 1
    for j in range(n_sub):
        t0 = perf_counter()
        if j == local_i:
            allcomm_local[j], iters_local[j] = gauss_exp(A_sub, y_local, theta, opts) if fun_name == "exp" else gauss_res(A_sub, y_local, theta, alpha, opts)
        else: 
            y_local[j] = 1
            allcomm1, iters1 = gauss_exp(A_sub, y_local/np.sqrt(2), theta, opts) if fun_name == "exp" else gauss_res(A_sub, y_local/np.sqrt(2), theta, alpha, opts)
            iters_local[j] = iters1
            y_local[j] = -1
            allcomm2, iters2 = gauss_exp(A_sub, y_local/np.sqrt(2), theta, opts) if fun_name == "exp" else gauss_res(A_sub, y_local/np.sqrt(2), theta, alpha, opts)
            iters_local[j] += iters2
            allcomm_local[j] = 0.5 * (allcomm1 - allcomm2)
            y_local[j] = 0
        info += 1 if iters_local[j] >= gauss_max_iterations else 0
        logger.info(f"matrix-vector products, maxn, node, elapsed time: {iters_local[j]}, {gauss_max_iterations}, {original_indices[j]}, {perf_counter() - t0:.4f}")
        
    
    indx_local = np.argsort(allcomm_local)[::-1]
    allcomm_sorted = allcomm_local[indx_local]

    vip_local_indices = indx_local[:nnodes]
    vip_comm = allcomm_sorted[:nnodes]

    # mapping to original matrix
    vip_nodes = original_indices[vip_local_indices]
    allcomm_original = np.zeros(A.shape[0])
    allcomm_original[original_indices] = allcomm_local
    iters_original = np.zeros(A.shape[0])
    iters_original[original_indices] = iters_local

    logger.info("commgauss function completed")

    return vip_nodes, vip_comm, info > 0, iters_original, allcomm_original  


def stconvgauss(A: csc_matrix, 
            fun_name: Literal["exp", "res"] = "exp", 
            nnodes: int = 1, 
            opts: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, np.ndarray, bool, np.ndarray, np.ndarray]:
    
    if opts is None: 
        opts = {}

    gauss_tol = opts.get("gauss_tol", 1e-3)
    gauss_max_iterations = opts.get("gauss_max_iterations", 200)
    gauss_largest_eigenvalue = opts.get("gauss_largest_eigenvalue", eigsh(A, k=1, which='LA', return_eigenvectors=False)[0])
    alpha = opts.get("alpha", 0.0)

    n = A.shape[0]

    logger.info(f"Starting stconvgauss: nnodes = {nnodes}, options = {opts}")
    
    if n == 1:
        logger.warning("the network has only 1 node, returning trivial result")
        return np.array([0]), np.array([1.0]), False, np.array([0]), np.array([1.0])

    allstconv = np.zeros(n)
    allstconv1 = 0.0
    allstconv2 = 0.0
    iters = np.zeros(n)
    y = np.ones(n)  

    info = 0

    theta = gauss_largest_eigenvalue
    if fun_name == 'res' and not (0 < alpha < 1 / theta):
        raise ValueError(f"alpha must be in (0, {1/theta:.6f}), got {alpha}")

    np3 = n + 3
    nm1 = n - 1

    for i in range(n):
        y[i] = 2  
        t0 = perf_counter()

        allstconv1, inf = gauss_exp(A, y/np.sqrt(np3), theta, opts) if fun_name == "exp" else gauss_res(A, y/np.sqrt(np3), theta, alpha, opts)
        iters[i] = inf
        
        y[i] = 0  

        allstconv2, inf = gauss_exp(A, y/np.sqrt(nm1), theta, opts) if fun_name == "exp" else gauss_res(A, y/np.sqrt(nm1), theta, alpha, opts)
        allstconv[i] = (np3 * allstconv1 - nm1 * allstconv2) / 4
        iters[i] += inf

        info += 1 if iters[i] >= gauss_max_iterations else 0
        y[i] = 1  
        logger.info(f"matrix-vector products, maxn, node, elapsed time: {iters[i]}, {gauss_max_iterations}, {i}, {perf_counter() - t0:.4f}")
        
    
    indx = np.argsort(allstconv)[::-1]
    allstconv = allstconv[indx]

    vip_nodes = indx[:nnodes]
    vip_stconv = allstconv[:nnodes]

    logger.info("gauss function completed")

    return vip_nodes, vip_stconv, info > 0, iters, allstconv
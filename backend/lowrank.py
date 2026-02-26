import numpy as np
from scipy.sparse import csc_matrix
import primme
from typing import Optional, Dict, Any, Literal, Tuple
import warnings
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def sgcenlr(A: csc_matrix, 
            fun_name: Literal["exp", "res"] = "exp", 
            nnodes: int = 1, 
            opts: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, np.ndarray, int, list]:
    """
    Determine the VIP nodes of an undirected, unweighted complex network depending on the subgraph-centrality of each node,
    via low-rank approximation of the adjacency matrix.
    
    Paramaters:
    ----------
    A : csc_matrix
        adjacency matrix (column sparse and symmetric)
    fun_name : str
        'exp' for exponential, 'res' for resolvent
    nnodes : int
        number of VIP nodes
    opts : dict, optional
        options both for algorithm and for PRIMME (irbleigs in MATLAB) (sgcmaxn, toll, ecc.).
        
    Returns:
    -------
    vip : np.ndarray
        vector of the VIP nodes (each element corresponds to the index)

    vipsgc : np.ndarray
        vector of the approximated subgraph centralities matching the element in vip array
        vip[i] |-> vipsgc[i]
    
    realN : int
        number of used eigenpairs

    S_history : list
        history of the candidate nodes for each iteration
        [[i_1, i_2, ..., i_m, i_{m + 1}..., i_n]] -> [[i_1, i_2, ..., i_m, i_{m + 1}..., i_n], [i_1, i_2, ..., i_m, i_{m + 1}]]
    """
    if opts is None:
        opts = {}
        
    # unpack default options
    sgcmaxn = opts.get('sgcmaxn', 300) # max number of iterations
    sgcmaxva = opts.get('sgcmaxva', 200) # max size of eigenvectors database
    sgctoll = opts.get('sgctoll', 0.0) # tolerance for exit condition (lower bound stagnation)
    sgctau = opts.get('sgctau', 1e-1) # tolerance for weak convergence
    sgcminkappa = opts.get('sgcminkappa', 5) # min number of additional VIP nodes (weak convergence)
    sgcmaxkappa = opts.get('sgcmaxkappa', 100) # max number of additional VIP nodes (weak convergence)
    sgcshift = opts.get('sgcshift', True) # spectrum shift, default: True
    alpha = opts.get('alpha', 0.0) # alpha for resolvent
    
    # PRIMME options
    k = opts.get('k', 20) # batch size
    tol = opts.get('tol', 1e-3) # tolerance for PRIMME
    primme_maxiter = opts.get('primme_maxiter', 1000) # max number of iterations for PRIMME
    return_S = opts.get('return_S', True) # return the history of candidate nodes, default: True

    restype = 1  # restart type -> 1 = new eigenbatch, 2 = eigenvectors close to the smallest eigenvalue
    n = A.shape[0] # number of nodes of the network
    
    logger.info(f"Starting sgcenlr: n={n}, k={k}, nnodes={nnodes}, sgcmaxn={sgcmaxn}")
    
    # compute the first batch (default batch_size = k = 20)
    logger.info(f"Computing first eigenbatch with k={min(k, n)}...")
    evals, evecs = primme.eigsh(A, k=min(k, n), which='LA', tol=tol, maxiter=primme_maxiter)
    logger.info(f"First eigenbatch computed successfully")
    
    # descending ordering
    idx = np.argsort(evals)[::-1]
    lam = evals[idx]
    V = evecs[:, idx]
    
    musave = lam[0] # largest eigenvalue
    
    # definition of 'exp' or 'res', therefore f(A) = exp(A - mu) or (I - mu*x)^-1
    if fun_name == 'exp':
        mu = musave if sgcshift else 0.0
        def fun(x, mu_val): return np.exp(x - mu_val)
    elif fun_name == 'res':
        mu = alpha
        if not (0 < alpha < 1 / musave):
            raise ValueError(f"alpha must be in (0, {1/musave:.6f}), got {alpha}")
        def fun(x, mu_val): return 1.0 / (1.0 - mu_val * x)
    else:
        raise ValueError(f"unbound function {fun_name}, choose between 'exp' or 'res'")

    F = np.zeros(n) # initialize lower bound of the subgraph centrality of the nodes
    vsum = np.zeros(n) # sum of all eigenvectors
    S_history = [] # history of candidate nodes
    
    N = 0 # number of eigenpairs used in the current batch
    realN = 0 # total number of iterations of the while-loop 
    flag = True # exit condition (checks if the VIP nodes are determined or the lower bounds stagnate)
    VA = None # contains all the computed eigenvectors
    
    while flag and (realN < min(sgcmaxn, n)):
        # if all the eigenpairs of the current batch are used then a restart is needed
        if N == len(lam):
            
            if restype == 1:
                # --- CASE 1: save the previous eigenvectors and compute new ones (new batch) ---
                if VA is None:
                    VA = V
                else:
                    VA = np.hstack((VA, V)) # the last batch is added
                
                if VA.shape[1] >= n:
                    break # max number of iterations is reached
                
                # compute new eigenbatch orthogonal to the previous one 
                k_new = min(k, n - VA.shape[1]) # minimum between standard dimension of eigenbatch (k in options)
                # and remaining space in memory (eigenvectors database)
                try:
                    evals, evecs = primme.eigsh(A, k=k_new, which='LA', ortho=VA, tol=tol, maxiter=primme_maxiter) # new batch
                    
                except ValueError as e: 
                    warnings.warn(f"tolerance = {tol}, try reducing tolerance for eigenvalue computation")
                    break
                except primme.PrimmeError as e:
                    warnings.warn(f"PRIMME couldn't converge in case 1, switching to case 2: {e}")
                    break
                
                # descending ordering
                idx = np.argsort(evals)[::-1]
                lam = evals[idx]
                V = evecs[:, idx]
                
                N = 0 # reset of the count of eigenvectors used in the current eigenbatch
                
                # if VA is too large -> switch to the second type of restart for future restarts
                if VA.shape[1] >= sgcmaxva:
                    restype = 2

            elif restype == 2:
                # --- CASE 2: Shift and Invert near sigma ---
                # shift and invert of PRIMME computes the eigenvalues and eigenvectors near sigma
            
                sigma = lam[-1] # sigma is the smallest eigenvalue computed until now
                
                try:
                    evals, evecs = primme.eigsh(A, k=k, targetShifts=[sigma], which='LM', tol=tol, maxiter=primme_maxiter)
                except primme.PrimmeError as e:
                    warnings.warn(f"PRIMME couldn't converge to restart (case 2): {e}")
                    break
                
                # descending ordering
                idx = np.argsort(evals)[::-1]
                lam = evals[idx]
                V = evecs[:, idx]
                
                # index of the smallest eigenvalue we had, this avoids to count multiple times the same eigenvalue
                ill = np.argmin(np.abs(lam - sigma))
                
                # continue from the point where there is no overlap
                N = ill + 1
                
            else:
                raise ValueError("Wrong restart type")
            
        f_lam = fun(lam[N], mu) # f(\lambda_i - mu) 
        v_sq = V[:, N] ** 2 # eigenvector squared (to compute f(\lambda) - v_{i}^2)
        vsum += v_sq # update sum of all eigenvectors
        F += f_lam * v_sq # subgraph centrality of current node
        
        L = F.copy() # make a copy of the subraph centralities
        U = L + f_lam * (1.0 - vsum) # estimate of the upper bound
        
        # descending order of the lower bounds 
        indx = np.argsort(L)[::-1]
        Ls = L[indx]
        
        # m-th largest lower bound
        Lmax = Ls[nnodes - 1] 
        
        # determine the nodes in which the upper bound is larger than the m-th largest lower bound
        lis = np.where(U >= Lmax)[0]
        
        if return_S:
            S_history.append(lis)
            
        # exit condition check 
        flag = (len(lis) > nnodes) and ((f_lam / n) > (sgctoll * Lmax))
        
        N += 1
        realN += 1

    logger.info(f"Loop completed: realN={realN}, flag={flag}, converged={not flag}")
    
    # check convergence
    if flag:
        # no convergence
        warnings.warn("too few eigenvalues to compute VIP nodes successfully.")
        nvip = len(lis)
    else:
        if len(lis) > nnodes: 
            # weak convergence
            # add additional nodes which have a lower bound very close to Lmax
            ivec = np.where((Lmax - Ls[nnodes:]) < (sgctau * Lmax))[0]
            incr = min(len(ivec), sgcmaxkappa)
            incr = max(incr, sgcminkappa)
            logger.info(f"Weak convergence, added {incr} additional nodes")
        else:
            # strong convergence
            incr = 0 

        nvip = nnodes + incr # number of VIP nodes = number of VIP nodes searched + incremental VIP nodes  

    vip = indx[:nvip] # extract VIP nodes 
    vipsgc = Ls[:nvip] # extract subgraph centrality of VIP nodes

    # shift back 
    if fun_name == 'exp' and np.isfinite(np.exp(mu)):
        vipsgc = np.exp(mu) * vipsgc

    return vip, vipsgc, realN * k + N,  S_history



def commlr(A: csc_matrix, 
            i: int,
            fun_name: Literal["exp", "res"] = "exp", 
            nnodes: int = 1, 
            opts: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, np.ndarray, int, list]:
    """
    Determine the VIP nodes of an undirected, unweighted complex network depending on the communicability of each node with the node i,
    via low-rank approximation of the adjacency matrix.
    
    Paramaters:
    ----------
    A : csc_matrix
        adjacency matrix (column sparse and symmetric)
    i : int
        node to consider for the communicability
    fun_name : str
        'exp' for exponential, 'res' for resolvent
    nnodes : int
        number of VIP nodes
    opts : dict, optional
        options both for algorithm and for PRIMME (irbleigs in MATLAB) (sgcmaxn, toll, ecc.).
        
    Returns:
    -------
    vip : np.ndarray
        vector of the VIP nodes (each element corresponds to the index)

    vipsgc : np.ndarray
        vector of the approximated subgraph centralities matching the element in vip array
        vip[i] |-> vipsgc[i]
    
    realN : int
        number of used eigenpairs

    S_history : list
        history of the candidate nodes for each iteration
        [[i_1, i_2, ..., i_m, i_{m + 1}..., i_n]] -> [[i_1, i_2, ..., i_m, i_{m + 1}..., i_n], [i_1, i_2, ..., i_m, i_{m + 1}]]
    """

    # TODO: consider the connected components of the node i -> this way we exclude the computation of communicability with the nodes 
    # not connected with node i

    if i < 0 or i >= A.shape[0]:
        raise ValueError(f"node {i} not found, must be in the range [0, {A.shape[0]})") 
    
    if np.sum(A[:, i]) == 0:
        raise ValueError(f"node {i} is not connected to any other node in the network")

    if opts is None:
        opts = {}
        
    # unpack default options
    sgcmaxn = opts.get('sgcmaxn', 300) # max number of iterations
    sgcmaxva = opts.get('sgcmaxva', 200) # max size of eigenvectors database
    sgctoll = opts.get('sgctoll', 0.0) # tolerance for exit condition (lower bound stagnation)
    sgctau = opts.get('sgctau', 1e-1) # tolerance for weak convergence
    sgcminkappa = opts.get('sgcminkappa', 1) # min number of additional VIP nodes (weak convergence)
    sgcmaxkappa = opts.get('sgcmaxkappa', 100) # max number of additional VIP nodes (weak convergence)
    sgcshift = opts.get('sgcshift', True) # spectrum shift, default: True
    alpha = opts.get('alpha', 0.0) # alpha for resolvent
    
    # PRIMME options
    k = opts.get('k', 20) # batch size
    tol = opts.get('tol', 1e-3) # tolerance for PRIMME
    primme_maxiter = opts.get('primme_maxiter', 1000) # max number of iterations for PRIMME
    return_S = opts.get('return_S', True) # return the history of candidate nodes, default: True

    restype = 1  # restart type -> 1 = new eigenbatch, 2 = eigenvectors close to the smallest eigenvalue
    n = A.shape[0] # number of nodes of the network
    
    logger.info(f"Starting commlr: n={n}, k={k}, nnodes={nnodes}, sgcmaxn={sgcmaxn}")
    
    # compute the first batch (default batch_size = k = 20)
    evals, evecs = primme.eigsh(A, k=min(k, n), which='LA', tol=tol, maxiter=primme_maxiter)
    
    # order the eigenvectors with the same exact ordering of the eigenvalues (the eigenvalues are ordered descendigly)
    idx = np.argsort(evals)[::-1]
    lam = evals[idx]
    V = evecs[:, idx]
    
    musave = lam[0] # largest eigenvalue
    
    # definition of 'exp' or 'res', therefore f(A) = exp(A - mu) or (I - mu*x)^-1
    if fun_name == 'exp':
        mu = musave if sgcshift else 0.0
        def fun(x, mu_val): return np.exp(x - mu_val)
    elif fun_name == 'res':
        mu = alpha
        if not (0 < alpha < 1 / musave):
            raise ValueError(f"alpha must be in (0, {1/musave:.6f}), got {alpha}")
        def fun(x, mu_val): return 1.0 / (1.0 - mu_val * x)
    else:
        raise ValueError(f"unbound function {fun_name}, choose between 'exp' or 'res'")

    F = np.zeros(n) # initialize lower bound of the subgraph centrality of the nodes
    vsum = np.zeros(n) # sum of all eigenvectors
    S_history = [] # history of candidate nodes

    u_tilde_k = 0 # will be used to store v_{k}^2, where v_k is the corresponding eigenvector
    w_tilde_k = np.zeros(n)
    
    N = 0 # number of eigenpairs used in the current batch
    realN = 0 # total number of iterations of the while-loop 
    flag = True # exit condition (checks if the VIP nodes are determined or the lower bounds stagnate)
    VA = None # contains all the computed eigenvectors
    
    while flag and (realN < min(sgcmaxn, n)):
        # if all the eigenpairs of the current batch are used then a restart is needed
        if N == len(lam):
            
            if restype == 1:
                # --- CASE 1: save the previous eigenvectors and compute new ones (new batch) ---
                if VA is None:
                    VA = V
                else:
                    VA = np.hstack((VA, V)) # the last batch is added
                
                if VA.shape[1] >= n:
                    break # max number of iterations is reached
                
                # compute new eigenbatch orthogonal to the previous one 
                k_new = min(k, n - VA.shape[1]) # minimum between standard dimension of eigenbatch (k in options)
                # and remaining space in memory (eigenvectors database)
                try:
                    evals, evecs = primme.eigsh(A, k=k_new, which='LA', ortho=VA, tol=tol, maxiter=primme_maxiter) # new batch
                    
                except ValueError as e: 
                    warnings.warn(f"tolerance = {tol}, try reducing tolerance for eigenvalue computation")
                    break
                except primme.PrimmeError as e:
                    warnings.warn(f"PRIMME couldn't converge in case 1, switching to case 2: {e}")
                    break
                
                # descending ordering
                idx = np.argsort(evals)[::-1]
                lam = evals[idx]
                V = evecs[:, idx]
                
                N = 0 # reset of the count of eigenvectors used in the current eigenbatch
                
                # if VA is too large -> switch to the second type of restart for future restarts
                if VA.shape[1] >= sgcmaxva:
                    restype = 2

            elif restype == 2:
                # --- CASE 2: Shift and Invert near sigma ---
                # shift and invert of PRIMME computes the eigenvalues and eigenvectors near sigma
            
                sigma = lam[-1] # sigma is the smallest eigenvalue computed until now
                
                try:
                    evals, evecs = primme.eigsh(A, k=k, targetShifts=[sigma], which='LM', tol=tol, maxiter=primme_maxiter)
                except primme.PrimmeError as e:
                    warnings.warn(f"PRIMME couldn't converge to restart in case 2: {e}")
                    break
                
                # order the eigenvectors with the same exact ordering of the eigenvalues (the eigenvalues are ordered descendigly)
                idx = np.argsort(evals)[::-1]
                lam = evals[idx]
                V = evecs[:, idx]
                
                # index of the smallest eigenvalue obtained, this prevents from counting the same eigenvalue multiple times
                ill = np.argmin(np.abs(lam - sigma))
                
                # continue from the point where there is no overlap
                N = ill + 1
                
            else:
                raise ValueError("Wrong restart type")
            
        f_lam = fun(lam[N], mu) # f(\lambda_i - mu) 
        v_sq = V[:, N] ** 2 # eigenvector squared 
        u_tilde_k += v_sq[i] # this allows to choose the node i
        w_tilde_k += v_sq # this sums all the entries for the column i 
        contr = f_lam * V[:, N][i] * V[:, N] 
        # contr corresponds to (f(\lambda_N)) * (1 - \sum_{k=1}^N{utildek_{k}^2}^1/2) * (1 - \sum_{k=1}^N{wtildek_{k}^2}^1/2)
        F += contr # this represents all the communicabilities towards node i (lower bounds)
        
        G = f_lam * np.sqrt(1 - u_tilde_k) * np.sqrt(1 - w_tilde_k) 
        # G represents the difference between the lower bound and the upper bound, 
        # in fact L + G = U - G

        L = F - G # still unused, will be used to plot the bounds and the candidate nodes
        U = F + G
        
        # order the communicabilities
        indx = np.argsort(F)[::-1]
        Fs = F[indx]
        logger.info(Fs)
        
        # m-th largest lower bound
        Fmax = Fs[nnodes - 1] 
        
        # determine the nodes in which the upper bound is larger than the m-th largest lower bound
        lis = np.where(U >= Fmax)[0]
        
        if return_S:
            S_history.append(lis)
            
        # exit condition check (while there are more candidate nodes than the number of requested ones and the eigenvalues
        # are still "big enough")
        flag = (len(lis) > nnodes) and ((np.abs(np.mean(contr))) > (sgctoll * Fmax))

        N += 1
        realN += 1

    logger.info(f"Loop completed: realN={realN}, flag={flag}, converged={not flag}")
    
    # check convergence
    if flag:
        # no convergence
        nvip = len(lis)
        logger.info("no convergence, too few eigenvalues to compute VIP nodes successfully.")
        logger.info(f"selected {nvip} number of VIP nodes")
    else:
        if len(lis) > nnodes: 
            # weak convergence
            # add additional nodes which have a lower bound very close to Fmax
            ivec = np.where((Fmax - Fs[nnodes:]) < (sgctau * Fmax))[0]
            incr = min(len(ivec), sgcmaxkappa)
            incr = max(incr, sgcminkappa)
            logger.info(f"Weak convergence, added {incr} additional nodes")
        else:
            # strong convergence
            logger.info("Strong convergence, no additional node is needed")
            incr = 0 

        nvip = nnodes + incr # number of VIP nodes = number of VIP nodes searched + incremental VIP nodes  

    vip = indx[:nvip] # extract VIP nodes 
    vipcomm = Fs[:nvip] # extract communicabilities of VIP nodes

    # shift back 
    if fun_name == 'exp' and np.isfinite(np.exp(mu)):
        vipcomm = np.exp(mu) * vipcomm

    # realN is the number of iterations of the while loop -> one iteration for each eigenpair -> realN = number of used eigenpairs
    return vip, vipcomm, realN, S_history


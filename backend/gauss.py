import numpy as np
from scipy.sparse.linalg import eigsh
from scipy.sparse import csc_matrix
from scipy.linalg import norm, eigh
from typing import Optional, Tuple, Dict, Any, Union

def expm_eig(T: np.ndarray, mu: float = 0.0) -> np.ndarray:
    """
    Compute expm(T) using spectral decomposition
    """
    eigvals, V = eigh(T)
    # eigvals = ndarray, V = ndarray
    # V @ diag(exp(...)) @ V.T
    # this is column vector multiplied for 
    return V @ (np.exp(eigvals - mu)[:, None] * V.T)

def opolyval(alfa: np.ndarray, beta: np.ndarray, beta0: float, x: Union[float, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes orthonormal polynomials via recurrence.
    """
    x = np.atleast_1d(x)
    # p1 corrisponde a p_0(x) nella notazione matematica, p a p_1(x) ecc.
    p1 = np.ones(x.shape) / beta0
    p = (x - alfa[0]) / beta[0]
    
    # Inizia dal secondo elemento di alfa (indice 1 in Python)
    for k in range(1, len(alfa)):
        p0 = p1
        p1 = p
        # Ricorrenza: b_k * p_{k+1} = (x - a_k) * p_k - b_{k-1} * p_{k-1}
        p = ((x - alfa[k]) * p1 - beta[k-1] * p0) / beta[k]
        
    return p, p1

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
        "gausstolq": 1e-3,
        "gausstau": 1e-10,
        "gaussmaxn": 100,
        "gaussmu": None,     # if None then default is theta
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
        eigvals_A, _ = eigsh(A, k=1, which='LA') 
        theta = eigvals_A[0]

    if options["gaussmu"] is None:
        options["gaussmu"] = theta
        
    mu = options["gaussmu"]
    
    
    # making sure that u is a column vector
    u = np.array(u).reshape(-1, 1)
    m = u.shape[0]
    
    # matrix-vector product operator
    
    mvprod = lambda x: A @ x

    beta = norm(u)
    sqrt_eps = np.sqrt(np.finfo(float).eps)
    
    # max iterations number, (the max number of iterations can't be larger than the number of rows of the matrix A)
    max_n = min(options["gaussmaxn"], m)
    
    if options["gaussreorth"]:
        Q = np.zeros((m, max_n + 1))
        
    T = np.zeros((max_n + 1, max_n + 1))
    alf = np.zeros(max_n)
    bet = np.zeros(max_n + 1)
    bet[0] = beta
    
    q_0 = np.zeros_like(u)
    q = u / beta
    
    if options["gaussreorth"]:
        Q[:, 0] = q.flatten()

    dif = 1000.0
    g = 0.0
    gr = 0.0 # g with an additional step
    
    # Lanczos loop
    i = 0 
    while (dif > options["gausstolq"] * abs(g)) and (i < max_n):
        
        # compute the product between the adjacency matrix and the 
        v = mvprod(q)
        
        # local orthogonalization
        if options["gaussmgs"]:
            v = v - beta * q_0
            alfa = float(q.T @ v)
            v = v - alfa * q
        else:
            alfa = float(q.T @ v)
            v = v - beta * q_0 - alfa * q
            
        # global re-orthogonalization
        if options["gaussreorth"]:
            # Q[:, :i+1] previous vectors
            v_flat = v.flatten()
            
            reorth_type = options["gaussreorth"]
            
            if reorth_type == 1: # MGS
                for j in range(i + 1):
                    q_j = Q[:, j]
                    # proiezione
                    proj = np.dot(v_flat, q_j)
                    v_flat = v_flat - proj * q_j
                v = v_flat.reshape(-1, 1)
                    
            elif reorth_type == 2: # CGS
                Q_curr = Q[:, :i+1]
                v_flat = v_flat - Q_curr @ (Q_curr.T @ v_flat)
                v = v_flat.reshape(-1, 1)
                
            elif reorth_type == 3: # Double CGS
                Q_curr = Q[:, :i+1]
                c = Q_curr.T @ v_flat
                v_flat = v_flat - Q_curr @ c
                if norm(c) > sqrt_eps: # second step if necessary
                    c1 = Q_curr.T @ v_flat
                    v_flat = v_flat - Q_curr @ c1
                v = v_flat.reshape(-1, 1)

        # update of beta
        beta = norm(v)
        q_0 = q.copy() # save current q for the next step
        
        # Check breakdown
        if beta < options["gausstau"]:
            # Breakdown: exact convergence
            T[i, i] = alfa
            # compute exponential
            T_sub = T[:i+1, :i+1]
            S = expm_eig(T_sub, mu)
            g = S[0, 0]
            gr = g
            break
        else:
            q = v / beta
            
        if options["gaussreorth"]:
            Q[:, i+1] = q.flatten()
            
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
        S = expm_eig(T[:i+1, :i+1], mu)
        g = S[0, 0]
        
        # estimate the integral with T_{k + 1}
        S_ext = expm_eig(T[:i+2, :i+2], mu)
        gr = S_ext[0, 0]
        
        dif = abs(gr - g) / 2.0
        
        i += 1 
        
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
        
    return fval, info # return the final value and the number of iterations

# usage example:
# A = np.array([[2., -1.], [-1., 2.]])
# u = np.array([1., 0.])
# val, steps = gaussexp(A, u, theta=3.0)
# print(val, steps)
"""
If PRIMME is installed then is directly used; otherwise (es. Windows) spectral deflation is employed.
"""
import logging

import numpy as np
from scipy.sparse import csc_matrix, identity, issparse
from scipy.sparse.linalg import (
    ArpackError,
    LinearOperator,
    eigsh as scipy_eigsh,
    splu,
)

try:
    import primme
except ImportError:  # es. Windows
    primme = None

logger = logging.getLogger(__name__)

_USE_PRIMME = primme is not None

# convergence exception
SOLVER_ERRORS = (ArpackError,) if primme is None else (primme.PrimmeError, ArpackError)


def _select(w, k, which, sigma):
    """
    Indices of the k requested eigenvalues 

    Args:
        w (float): _description_
        k (int): _description_
        which (str): "Largest Algebraic", "Smallest Algebraic", "Largest Magnitude", "Smallest Magnitude"
        sigma (float, optional): shift value. Defaults to None.

    Raises:
        ValueError: 'which' not supported
    """
    which = which.upper()
    if sigma is not None:
        idx = np.argsort(np.abs(w - sigma))[:k]
    elif which == "LA":
        idx = np.argsort(w)[-k:]
    elif which == "SA":
        idx = np.argsort(w)[:k]
    elif which == "LM":
        idx = np.argsort(np.abs(w))[-k:]
    elif which == "SM":
        idx = np.argsort(np.abs(w))[:k]
    else:
        raise ValueError(f"which='{which}' not supported")
    return idx[np.argsort(w[idx])]


def _orthonormal_basis(lock, n, rtol=1e-10):
    """
    Orthonormal basis (n x m) of span(lock).

    SVD is employed instead of QR to discard numerically dependent columns (after a large number of batches is possible).
    """
    VA = np.asarray(lock, dtype=np.float64)
    if VA.ndim == 1:
        VA = VA[:, None]
    if VA.ndim != 2 or VA.shape[0] != n:
        raise ValueError(f"lock must have shape ({n}, m), got {VA.shape}")
    U, s, _ = np.linalg.svd(VA, full_matrices=False)
    keep = s > rtol * s[0]
    if not np.all(keep):
        logger.warning(
            "lock: %d numerically dependent columns have been discarded", int((~keep).sum())
        )
    return U[:, keep]


def true_residuals(A, w, X):
    """True residuals ||A x_i - w_i x_i|| with respect to A (not to deflationated operator)."""
    return np.linalg.norm(A @ X - X * w[None, :], axis=0)



def _dense_batch(A, k, which, VA, sigma=None):
    """
    Dense diagonalization of A restricted to the orthogonal complement of VA.

    Dense path, optimal only for small networks or end of spectrum. 

    Useful when k close to n - m (approximately last batch), 
    where ARPACK can't work (requires k < n). Cost O(n^3). 
    """
    M = A.toarray() if issparse(A) else np.asarray(A, dtype=np.float64)
    Q = None
    if VA is not None:
        m = VA.shape[1]
        Q = np.linalg.qr(VA, mode="complete")[0][:, m:]  # base of span(VA)^perp
        M = Q.T @ M @ Q
    w, U = np.linalg.eigh(M)
    idx = _select(w, min(k, w.size), which, sigma)
    X = U[:, idx]
    if Q is not None:
        X = Q @ X
    return w[idx], X


_MAX_SIGMA_RETRIES = 3

def _shift_invert_plain(A, k, sigma, tol, maxiter, v0, ncv):
    """
    eigsh in shift-invert mode; if A - sigma*I is singular perturb sigma.
    """
    s = sigma
    for attempt in range(_MAX_SIGMA_RETRIES + 1):
        try:
            return scipy_eigsh(A, k=k, sigma=s, which="LM", tol=tol,
                               maxiter=maxiter, v0=v0, ncv=ncv)
        except ArpackError:      # ArpackError e' sottoclasse di RuntimeError:
            raise                # needs to be raised before singularity check'
        except RuntimeError as e:
            if "singular" not in str(e).lower() or attempt == _MAX_SIGMA_RETRIES:
                raise
            s = sigma + (attempt + 1) * 1e-6 * max(abs(sigma), 1.0)
            logger.warning("A - sigma*I is singular, retrying with sigma=%.12g", s)


def _deflated_shift_invert(A, k, sigma, VA, tol, maxiter, v0, ncv):
    """
    Deflationated shift-invert: operator P (A - sigma I)^-1 P.

    If span(VA) is invariante per A, commutes with P and has eigenvalues
    1/(lambda_j - sigma) on V-perp and 0 on V. The false zeros are the lowest in module "LM", 
    therefore they never get selected. 
    """
    n = A.shape[0]
    VAH = VA.T
    s = sigma
    lu = None
    for attempt in range(_MAX_SIGMA_RETRIES + 1):
        try:
            lu = splu(csc_matrix(A - s * identity(n, format="csc")))
            break
        except RuntimeError as e:
            if "singular" not in str(e).lower() or attempt == _MAX_SIGMA_RETRIES:
                raise
            s = sigma + (attempt + 1) * 1e-6 * max(abs(sigma), 1.0)
            logger.warning("A - sigma*I singular, trying again with sigma=%.12g", s)

    def matvec(x):
        x = x - VA @ (VAH @ x)
        y = lu.solve(np.asarray(x, dtype=np.float64))
        return y - VA @ (VAH @ y)

    op = LinearOperator((n, n), matvec=matvec, dtype=np.float64)
    mu, X = scipy_eigsh(op, k=k, which="LM", tol=tol, maxiter=maxiter,
                        v0=v0, ncv=ncv)
    if np.any(np.abs(mu) < 1e-14):
        logger.warning("operator eigenvalue ~= 0 in deflationated shift-invert.")
    lam = s + 1.0 / mu
    order = np.argsort(lam)
    return lam[order], X[:, order]


def eigsh_batch(A, k, which="LA", tol=1e-6, maxiter=1000, lock=None, sigma=None,
                shift=None, v0=None, ncv=None, check_residual=False):
    """
    Compute k eigenpairs of A excluding the eigenvalues in lock.

    Parameters
    ---------
    A : real sparse symmetric matrix (n x n)
    k : number of eigenpairs to compute
    which : 'LA' | 'SA' | 'LM' (con lock); 'SM' without lock, via dense
    tol : ARPACK tolerance (relative to |lambda|). With deflation is convenient
          using strict tolerances (1e-6 or less).
    lock : (n, m) already computed eigenvectors (no need to be orthonormal, an orthonormal basis calculation is performed)
    sigma : shift-invert near sigma (which='LM' returns the eigenvalues closer to sigma)
    shift : for spurious eigenvalues shift. If None the largest row-sum is used.
    v0 : initial vector (gets projected to span(lock)^perp)
    check_residual : if True computes the true residuals and warns if they're high

    Returns (w, X) with w in ascending order, exactly as eigsh(SciPy).
    """
    n = A.shape[0]
    if k <= 0:
        raise ValueError(f"k must be positive, got {k}")

    # --- PRIMME is available: natively employ it ---
    if _USE_PRIMME:
        return primme.eigsh(A, k=k, which=which, tol=tol, maxiter=maxiter,
                            lock=lock, sigma=sigma)

    # --- Fallback SciPy ---
    if issparse(A):
        A = A.astype(np.float64, copy=False)  # int/bool matrices make eigsh (SciPy) fail
    else:
        A = np.asarray(A, dtype=np.float64)

    VA = None
    if lock is not None:
        VA = _orthonormal_basis(lock, n)
        if VA.shape[1] == 0:
            VA = None
    m = 0 if VA is None else VA.shape[1]
    n_eff = n - m
    if n_eff <= 0:
        raise ValueError(f"lock spans the entire space (n={n}, m={m})")
    if k > n_eff:
        raise ValueError(f"k must be <= n - m (k={k}, n={n}, m={m})")

    # ARPACK requires k < dim: close to n - m gets switched to dense path
    if k >= n_eff - 1:
        w, X = _dense_batch(A, k, which, VA, sigma)
    elif sigma is not None:
        if VA is None:
            w, X = _shift_invert_plain(A, k, sigma, tol, maxiter, v0, ncv)
        else:
            w, X = _deflated_shift_invert(A, k, sigma, VA, tol, maxiter, v0, ncv)
    elif VA is None:
        w, X = scipy_eigsh(A, k=k, which=which, tol=tol, maxiter=maxiter,
                           v0=v0, ncv=ncv)
    else:
        w, X = _deflated_eigsh(A, k, which, tol, maxiter, VA, shift, v0, ncv)

    if check_residual:
        res = true_residuals(A, w, X)
        limit = 10.0 * tol * max(1.0, float(np.max(np.abs(w))))
        msg = f"real max residual = {res.max():.2e}"
        if VA is not None:
            msg += f", ||V^T X|| max = {np.abs(VA.T @ X).max():.2e}"
        if res.max() > limit:
            logger.warning("%s (threshold %.2e): the deflation is accumulating error; "
                           "tighten tol in the previous batches", msg, limit)
        else:
            logger.info(msg)
    return w, X


def _deflated_eigsh(A, k, which, tol, maxiter, VA, shift, v0, ncv):
    """eigsh on operator B = P A P + s V V^T  (P = I - V V^T).

    Eigenvalues of B: the eigenvalues of A restricted to V-perp, plus m false eigenvalues
    equal to S. S is chosen outside the region of interest:
        LA -> s = -(c+1)   (the spurious stay below the spectrum)
        SA -> s = +(c+1)   (the spurious stay above)
        LM -> s = 0        (the spurious have minimum module, they are not selected)
    where c is a majorant of the spectral radius of A. 
    """
    n = A.shape[0]
    w = which.upper()
    if w in ("LA", "SA"):
        if shift is None:
            c = float(abs(A).sum(axis=1).max()) if issparse(A) \
                else float(np.abs(A).sum(axis=1).max())
        else:
            c = float(shift)
        s = -(c + 1.0) if w == "LA" else (c + 1.0)
    elif w == "LM":
        s = 0.0
    else:
        raise NotImplementedError(
            f"which='{which}' not supported with lock (usa LA, SA, LM o sigma)"
        )

    VAH = VA.T  # VA is real: the conjugate coincides

    def matvec(x):
        coef = VAH @ x                     # V^T x
        y = A @ (x - VA @ coef)            # A P x
        y = y - VA @ (VAH @ y)             # P A P x
        if s != 0.0:
            y = y + s * (VA @ coef)        # shifts the spurious eigenvalues
        return y

    op = LinearOperator((n, n), matvec=matvec, dtype=np.float64)

    if v0 is None:
        v0 = np.random.default_rng(0).standard_normal(n)
    v0 = np.asarray(v0, dtype=np.float64).ravel()
    v0 = v0 - VA @ (VAH @ v0)              # initial vector in V-perp

    return scipy_eigsh(op, k=k, which=which, tol=tol, maxiter=maxiter,
                       v0=v0, ncv=ncv)


# alias
_eigsh_batch = eigsh_batch


# autotest
def _selftest(n=10000, m=10, k=10, seed=1):
    """Run with: python spectral_deflation.py"""
    import scipy.sparse as sp

    global _USE_PRIMME
    old = _USE_PRIMME
    _USE_PRIMME = False  # force SciPy fallback
    try:
        G = sp.random(n, n, density=0.03, random_state=seed, format="csr")
        G = sp.triu(G, 1)
        A = csc_matrix(((G + G.T) > 0).astype(np.float64))  # symmetric, null diagonal

        ref = np.linalg.eigvalsh(A.toarray())  # crescente

        # LA
        w1, V1 = eigsh_batch(A, m, "LA", tol=1e-10)
        w2, V2 = eigsh_batch(A, k, "LA", tol=1e-10, lock=V1, check_residual=True)
        err_la = np.max(np.abs(np.sort(w2)[::-1] - ref[::-1][m:m + k]))
        print(f"LA : eigenvalues max error = {err_la:.2e}  "
              f"orthogonality' V1/V2 = {np.abs(V1.T @ V2).max():.2e}")

        # SA
        s1, U1 = eigsh_batch(A, m, "SA", tol=1e-10)
        s2, U2 = eigsh_batch(A, k, "SA", tol=1e-10, lock=U1)
        err_sa = np.max(np.abs(np.sort(s2) - ref[m:m + k]))
        print(f"SA : eigenvalues max error = {err_sa:.2e}")

        # Shift-invert with lock
        sig = float(ref[n // 2] + 0.01)
        t, _ = eigsh_batch(A, 5, "LM", tol=1e-10, lock=V1, sigma=sig)
        mask = np.ones(n, dtype=bool)
        mask[np.argsort(ref)[::-1][:m]] = False
        cand = ref[mask]
        expected = np.sort(cand[np.argsort(np.abs(cand - sig))[:5]])
        print(f"SI : eigenvalues max error = {np.max(np.abs(np.sort(t) - expected)):.2e}")
    finally:
        _USE_PRIMME = old


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _selftest()

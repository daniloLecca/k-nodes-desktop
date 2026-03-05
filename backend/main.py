import io
import numpy as np
import scipy
import logging
import pickle
import generate as gnt
from scipy import sparse
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import eigsh
from fastapi import FastAPI, File, UploadFile, Request, Header, Depends, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from utils import get_clusters, ClusterRequest, ExpRequest, ResRequest, RandomComplexNetworkRequest
from utils import LowRankSubgraphCentrality, LowRankCommunicability, GaussSubgraphCentrality, GaussCommunicability
from utils import HybridSubgraphCentrality, HybridCommunicability
from gauss import gauss_exp, gauss_res, sgcengauss, commgauss, stconvgauss
from lowrank import sgcenlr, commlr, stconvlr
from hybrid import sgcenhyb, commhyb, stconvhyb
from primme import PrimmeError
from secrets import token_urlsafe

# middleware to limit body size (of the HTTP request)
class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_size: int = 100 * 1024 * 1024):  # default: 100MB
        super().__init__(app)
        self.max_body_size = max_body_size
    
    async def dispatch(self, request: Request, call_next):
        # checks content-length in the header
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_body_size:
            return JSONResponse(
                status_code=413,
                content={"error": f"File too large. Maximum size allowed is {self.max_body_size / (1024 * 1024):.0f} MB"}
            )
        
        response = await call_next(request)
        return response

app = FastAPI()

# adds middleware
app.add_middleware(BodySizeLimitMiddleware, max_body_size=100 * 1024 * 1024)  # 100 MB

# Inizializza il client Redis
# Nel docker-compose abbiamo definito REDIS_URL=redis://redis:6379/0
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

# Tempo di scadenza della sessione in secondi (es. 24 ore)
SESSION_EXPIRE_TIME = 86400

# --- DEPENDENCY PER IL TOKEN ---
# Questa funzione verrà usata per estrarre e deserializzare i dati da Redis per ogni rotta
def get_network_session(x_network_token: str = Header(...)):
    if not x_network_token:
        raise HTTPException(status_code=400, detail="token is missing")
    
    data_bytes = redis_client.get(x_network_token)
    if not data_bytes:
        raise HTTPException(status_code=404, detail="session expired or not existing, try uploading the file to '/api/'")
    
    # Rinnova la scadenza della sessione (opzionale, se vuoi che scada per inattività)
    redis_client.expire(x_network_token, SESSION_EXPIRE_TIME)
    
    return pickle.loads(data_bytes)

clusters = {}
network: csc_matrix = None # the adjacency matrix
leig: float = 0.0 # largest eigenvalue


@app.get("/api/")
def read_root():
    return {"Hello": "World"}


@app.post("/api/")
async def overview(file: UploadFile = File(...)):
    """
    Processes the adjacency matrix in the .mat file and returns the network info and the clusters.
    
    Response JSON:
    {
        "filename": str,
        "nodes": int,
        "edges": int,
        "clusters": {
            "clusterID": node_count,
            ...
        },
        "numberOfClusters": int
    }
    """
    global clusters, network, leig
    
    # check that the file sent in the body has .mat extension
    if not file.filename.endswith('.mat'):
        return JSONResponse(
            status_code=400,
            content={"error": "the file muste have .mat extension"}
        )
    
    try:
        # read file content
        contents = await file.read()
        
        # loadfile
        mat_data = scipy.io.loadmat(io.BytesIO(contents))
        
        # remove MATLAB headers
        mat_data = {k: v for k, v in mat_data.items() if not k.startswith('__')}

        # check that the file contains exactly one variable
        if len(mat_data) != 1:
            return JSONResponse(
                status_code=400,
                content={"error": "the file must contain exactly one variable"}
            )

        # get the adjacency matrix
        _, adj = next(iter(mat_data.items()))

        # if the matrix is not square or is not symmetric -> not valid adjacency matrix 
        if (adj.shape[0] != adj.shape[1]) or ((adj != adj.T).nnz != 0): 
            return JSONResponse(
                status_code=400,
                content={
                    "error": "the adjacency matrix must represent an undirected graph"
                }
            )

        number_of_self_loops: int = 0
        # convert the sparse matrix in column sparse format if it's not already
        if sparse.issparse(adj):
            adj = adj.tocsc()
            number_of_self_loops = np.sum(adj.diagonal())
            adj.setdiag(0) # all the elements in the diagonal will be equal to 0
            adj.eliminate_zeros() # delete the zero entries
            network = adj
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "the variable must be a sparse adjacency matrix"
                }
            )
        
        leig = eigsh(network, k=1, which='LA', return_eigenvectors=False)[0]
        clusters = get_clusters(adj)
        size_of_clusters = {}

        # for each cluster compute the size of the cluster
        for cluster in clusters.keys():
            size_of_clusters[cluster] = len(clusters[cluster])

        # 1. Genera un token univoco
        token = token_urlsafe(32)
        
        # 2. Prepara i dati da salvare
        session_data = {
            "network": network,
            "leig": leig,
            "clusters": clusters
        }
        
        # 3. Salva in Redis (serializzato con pickle) con scadenza
        redis_client.setex(
            token, 
            SESSION_EXPIRE_TIME, 
            pickle.dumps(session_data)
        )
        
        return {
            "token": token,
            "filename": file.filename,
            "nodes": int(list(adj.shape)[0]),
            "edges": int(adj.nnz), 
            "largest eigenvalue": leig,
            "max value for alpha": float(1 / leig),
            "self loops": int(number_of_self_loops),
            "clusters": size_of_clusters,
            "numberOfClusters": len(size_of_clusters.keys())
        }
        
        # generic error
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"error processing the file: {str(e)}"}
        )
    
    finally:
        await file.close()


@app.post("/api/cluster")
def nodes_of_cluster(request: ClusterRequest):
    """
    Returns the nodes of the specified cluster.
    
    Body JSON:
    {
        "clusterID": str (number of the cluster as a string)
    }
    """
    try:
        cluster_id = int(request.clusterID)
        if cluster_id in clusters:
            return {"clusterID": cluster_id, "nodes": clusters[cluster_id]}
        else:
            return JSONResponse(
                status_code=404,
                content={"error": f"Cluster {cluster_id} not found"}
            )
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"error": f"clusterID must be an integer"}
        )
    
@app.post("/api/gaussexp")
def get_gauss_exp(request: ExpRequest, session: dict = Depends(get_network_session)):

    network = session["network"]
    leig = session["leig"]

    if network is None:
        return JSONResponse(status_code=400, content={"error": "network not initialized yet. First send a .mat file to /api/."})

    u = np.zeros(network.shape[0])
    u[request.node] = 1.0
    val, steps = gauss_exp(network, u, leig)
    return {
        "exp": val, 
        "steps": steps
    }

@app.post("/api/gaussres")
def get_gauss_res(request: ResRequest):
    """
    Computes the resolvent using Gauss quadrature.
    
    Response JSON:
    {
        "res": float (the resolvent value)
    }
    """
    if network is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "network not initialized yet. First send a .mat file to /api/."}
        )

    try:
        u = np.zeros(network.shape[0])
        u[request.node] = 1.0
                
        val, steps = gauss_res(network, u, leig, request.alpha)
        return {
            "res": val
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error computing resolvent: {str(e)}"}
        )
    
@app.post("/api/random")
def get_random_complex_network(request: RandomComplexNetworkRequest): 
    global network, leig, clusters
    if request.model == "scale_free": 
        network = gnt.generate_scale_free_complex_network(request.nnodes, request.k)
    else:
        network = gnt.generate_small_world_complex_network(request.nnodes, request.k, request.p)

    leig = eigsh(network, k=1, which='LA', return_eigenvectors=False)[0]
    clusters = get_clusters(network)

    return {
        "nodes": network.shape[0], 
        "edges": network.nnz, 
        "largest_eigenvalue": leig, 
        "max value for alpha": 1 / leig,
        "clusters": clusters
    }

@app.post("/api/sgclr")
async def get_sgclr(request: LowRankSubgraphCentrality):
    logger = logging.getLogger(__name__)
    
    # Low-rank options for Gauss quadrature
    options = {
        "lr_max_iterations": request.max_iter or 300, 
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": request.tol or 1e-3,
        "lr_weak_convergence_tol": 1e-3,
        "lr_min_additional_nodes": 5,
        "lr_max_additional_nodes": 100,
        "lr_shift": request.shift if request.shift is not None else True, 
        "alpha": request.alpha or 0.0, 
        "lr_primme_batch_size": request.batch_size or 20,
        "lr_primme_tol": 1e-5,
        "lr_primme_max_iterations": 5000,
        "lr_return_S": True  
    }

    if network is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "network not initialized yet. First send a .mat file to /api/."}
        )
    
    logger.info(f"Starting sgclr computation with {network.shape[0]} nodes, fun={request.fun_name}, nnodes={request.nnodes}")
    vip_nodes, vip_sgc, num_eigs, candidates_history = sgcenlr(network, request.fun_name or "exp", request.nnodes or 1, options)
    
    # TODO: check default parameters to prevent missing convergence

    return {
        "vip_nodes": vip_nodes.tolist(),
        "vip_sgc": vip_sgc.tolist(),
        "used_eigenpairs": num_eigs, 
        "candidates_history": [c.tolist() for c in candidates_history]
    }


@app.post("/api/commlr")
async def get_commlr(request: LowRankCommunicability):
    logger = logging.getLogger(__name__)
    
    # Low-rank options for communicability
    options = {
        "lr_max_iterations": request.max_iter or 300, 
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": request.tol or 0,
        "lr_weak_convergence_tol": 1e-1,
        "lr_min_additional_nodes": 1,
        "lr_max_additional_nodes": 100,
        "lr_shift": request.shift if request.shift is not None else True, 
        "alpha": request.alpha or 0.0, 
        "lr_primme_batch_size": request.batch_size or 20,
        "lr_primme_tol": 1e-3,
        "lr_primme_max_iterations": 5000,
        "lr_return_S": True  
    }

    if network is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "network not initialized yet. First send a .mat file to /api/."}
        )
    
    logger.info(f"Starting commlr computation with {network.shape[0]} nodes, fun={request.fun_name}, nnodes={request.nnodes}")
    vip_nodes, vip_comm, num_eigs, candidates_history = commlr(network, request.i, request.fun_name or "exp", request.nnodes or 1, options)
    
    # TODO: check default parameters to prevent missing convergence

    return {
        "vip_nodes": vip_nodes.tolist(),
        "vip_comm": vip_comm.tolist(),
        "used_eigenpairs": num_eigs, 
        "candidates_history": [c.tolist() for c in candidates_history]
    }

@app.post("/api/stconvlr")
async def get_stconvlr(request: LowRankSubgraphCentrality):
    logger = logging.getLogger(__name__)
    
    # Low-rank options for starting convenience
    options = {
        "lr_max_iterations": request.max_iter or 300, 
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": request.tol or 0,
        "lr_weak_convergence_tol": 1e-3,
        "lr_min_additional_nodes": 1,
        "lr_max_additional_nodes": 100,
        "lr_shift": request.shift if request.shift is not None else True, 
        "alpha": request.alpha or 0.0, 
        "lr_primme_batch_size": request.batch_size or 20,
        "lr_primme_tol": 1e-3,
        "lr_primme_max_iterations": 5000,
        "lr_return_S": True  
    }

    if network is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "network not initialized yet. First send a .mat file to /api/."}
        )
    
    logger.info(f"Starting sgclr computation with {network.shape[0]} nodes, fun={request.fun_name}, nnodes={request.nnodes}")
    vip_nodes, vip_stconv, num_eigs, candidates_history = stconvlr(network, request.fun_name or "exp", request.nnodes or 1, options)
    
    # TODO: check default parameters to prevent missing convergence

    return {
        "vip_nodes": vip_nodes.tolist(),
        "vip_stconv": vip_stconv.tolist(),
        "used_eigenpairs": num_eigs, 
        "candidates_history": [c.tolist() for c in candidates_history]
    }

@app.post("/api/sgcgauss")
async def get_sgcgauss(request: GaussSubgraphCentrality):

    if network is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "network not initialized yet. First send a .mat file to /api/."}
        )

    # Gauss quadrature options
    options = {
        "gauss_tol": request.tol or 1e-3, 
        "gauss_max_iterations": request.max_iter or 200,
        "gauss_largest_eigenvalue": leig,
        "alpha": request.alpha or 0.0
    }

    vip_nodes, vip_sgc, info, iters, allsgc = sgcengauss(network, request.fun_name or "exp", request.nnodes or 1, options)

    return {
        "vip_nodes": vip_nodes.tolist(), 
        "vip_sgc": vip_sgc.tolist(), 
        "convergence": "exceeded max iterations number" if info else "satisfied", 
        "matrix vector products": iters.tolist(), 
        "all subgraph centralities": allsgc.tolist()
    }

@app.post("/api/commgauss")
async def get_commgauss(request: GaussCommunicability):
    if network is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "network not initialized yet. First send a .mat file to /api/."}
        )

    # Gauss quadrature options for communicability
    options = {
        "gauss_tol": request.tol or 1e-3, 
        "gauss_max_iterations": request.max_iter or 200,
        "alpha": request.alpha or 0.0
    }

    try: 
        vip_nodes, vip_comm, info, iters, allcomm = commgauss(network, request.i, request.fun_name or "exp", request.nnodes or 1, options)
    except ValueError as e:
        return JSONResponse(
            status_code=400, 
            content={"error": str(e)}
        )

    return {
        "vip_nodes": vip_nodes.tolist(), 
        "vip_comm": vip_comm.tolist(), 
        "convergence": "exceeded max iterations number" if info else "satisfied", 
        "matrix vector products": iters.tolist(), 
        "all communicatibilites": allcomm.tolist()
    }

@app.post("/api/stconvgauss")
async def get_stconvgauss(request: GaussSubgraphCentrality):

    if network is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "network not initialized yet. First send a .mat file to /api/."}
        )

    # Gauss quadrature options for starting convenience
    options = {
        "gauss_tol": request.tol or 1e-3, 
        "gauss_max_iterations": request.max_iter or 200,
        "gauss_largest_eigenvalue": leig,
        "alpha": request.alpha or 0.0
    }

    vip_nodes, vip_stconv, info, iters, allstconv = stconvgauss(network, request.fun_name or "exp", request.nnodes or 1, options)


    return {
        "vip_nodes": vip_nodes.tolist(), 
        "vip_stconv": vip_stconv.tolist(), 
        "convergence": "exceeded max iterations number" if info else "satisfied", 
        "matrix vector products": iters.tolist(), 
        "all subgraph centralities": allstconv.tolist()
    }

@app.post("/api/sgchyb")
async def get_sgchyb(request: HybridSubgraphCentrality):

    if network is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "network not initialized yet. First send a .mat file to /api/."}
        )

    # Hybrid options: low-rank approximation + Gauss quadrature refinement
    # Low-rank options
    lr_options = {
        "lr_max_iterations": request.max_iter or 300, 
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": 1e-3,
        "lr_weak_convergence_tol": 1e-1,
        "lr_nnodes": request.low_rank_nnodes or int(10 * request.nnodes), # estimate of the number of nodes for low rank
        "lr_min_additional_nodes": 5,
        "lr_max_additional_nodes": 100,
        "lr_shift": request.shift if request.shift is not None else True,
        "lr_primme_batch_size": request.batch_size or 20,
        "lr_primme_tol": 1e-5,
        "lr_primme_max_iterations": 5000,
        "lr_return_S": True,
    }
    
    # Gauss options
    gauss_options = {
        "gauss_tol": request.tol or 1e-3,
        "gauss_max_iterations": 200,
        "gauss_largest_eigenvalue": leig,
    }
    
    # Combine options for hybrid method
    options = {**lr_options, **gauss_options, "alpha": request.alpha or 0.0}

    logger = logging.getLogger(__name__)
    logger.info(f"Starting sgchyb computation with {network.shape[0]} nodes, fun={request.fun_name}, nnodes={request.nnodes}")
    try: 
        vip_nodes, vip_sgc, info, iters, allsgc, vip_lr, vipsgc_lr, realN_lr, S_history_lr, convergence = sgcenhyb(network, request.fun_name or "exp", request.nnodes or 1, options)
    except PrimmeError: 
        return JSONResponse(
            status_code=400, 
            content={"error": "maximum number of iterations or matvecs reached, try decreasing batch size."}
    )

    logger.info(f"vipnodes: {vip_nodes}")
    return {
        "vip_nodes": vip_nodes.tolist(),
        "vip_sgc": vip_sgc.tolist(),
        "convergence_gauss": "exceeded max iterations number" if info else "satisfied",
        "convergence_lowrank": convergence,
        "matrix_vector_products": iters.tolist(),
        "all_subgraph_centralities": allsgc.tolist(),
        "vip_lowrank": vip_lr.tolist(),
        "vipsgc_lowrank": vipsgc_lr.tolist(),
        "used_eigenpairs": int(realN_lr),
        "candidates_history": [c.tolist() for c in S_history_lr]
    }

@app.post("/api/commhyb")
async def get_commhyb(request: HybridCommunicability):

    if network is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "network not initialized yet. First send a .mat file to /api/."}
        )

    # Hybrid options: low-rank approximation + Gauss quadrature refinement
    # Low-rank options
    lr_options = {
        "lr_max_iterations": request.max_iter or 300,
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": 1e-3,
        "lr_weak_convergence_tol": 1e-1,
        "lr_nnodes": request.low_rank_nnodes or int(10 * request.nnodes), # estimate of the number of nodes for low rank
        "lr_min_additional_nodes": 5,
        "lr_max_additional_nodes": 100,
        "lr_shift": request.shift if request.shift is not None else True,
        "lr_primme_batch_size": request.batch_size or 20,
        "lr_primme_tol": 1e-5,
        "lr_primme_max_iterations": 5000,
        "lr_return_S": True,
    }
    
    # Gauss options
    gauss_options = {
        "gauss_tol": request.tol or 1e-3,
        "gauss_max_iterations": 200,
    }
    
    # Combine options for hybrid method
    options = {**lr_options, **gauss_options, "alpha": request.alpha or 0.0}
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting commhyb computation with {network.shape[0]} nodes, fun={request.fun_name}, nnodes={request.nnodes}")
    try: 
        vip_nodes, vip_comm, info, iters, allcomm, vip_lr_local, vipcomm_lr_local, realN_lr, S_history_lr, convergence = commhyb(network, request.i, request.fun_name or "exp", request.nnodes or 1, options)
    except PrimmeError: 
        return JSONResponse(
            status_code=400, 
            content={"error": "maximum number of iterations or matvecs reached, try decreasing batch size."}
        )

    return {
        "vip_nodes": vip_nodes.tolist(),
        "vip_comm": vip_comm.tolist(),
        "convergence_gauss": "exceeded max iterations number" if info else "satisfied",
        "convergence_lowrank": convergence,
        "matrix_vector_products": iters.tolist(),
        "all_communicabilities": allcomm.tolist(),
        "vip_lowrank": vip_lr_local.tolist(),
        "vipcomm_lowrank": vipcomm_lr_local.tolist(),
        "used_eigenpairs": int(realN_lr),
        "candidates_history": [c.tolist() for c in S_history_lr]
    }

@app.post("/api/stconvhyb")
async def get_stconvhyb(request: HybridSubgraphCentrality):

    if network is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "network not initialized yet. First send a .mat file to /api/."}
        )

    # Hybrid options: low-rank approximation + Gauss quadrature refinement
    # Low-rank options
    lr_options = {
        "lr_max_iterations": request.max_iter or 300,
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": 1e-3,
        "lr_weak_convergence_tol": 1e-1,
        "lr_nnodes": request.low_rank_nnodes or int(10 * request.nnodes), # estimate of the number of nodes for low rank
        "lr_min_additional_nodes": 5,
        "lr_max_additional_nodes": 100,
        "lr_shift": request.shift if request.shift is not None else True,
        "lr_primme_batch_size": request.batch_size or 20,
        "lr_primme_tol": 1e-5,
        "lr_primme_max_iterations": 5000,
        "lr_return_S": True,
    }
    
    # Gauss options
    gauss_options = {
        "gauss_tol": request.tol or 1e-3,
        "gauss_max_iterations": 200,
        "gauss_largest_eigenvalue": leig,
    }
    
    # Combine options for hybrid method
    options = {**lr_options, **gauss_options, "alpha": request.alpha or 0.0}

    logger = logging.getLogger(__name__)
    logger.info(f"Starting stconvhyb computation with {network.shape[0]} nodes, fun={request.fun_name}, nnodes={request.nnodes}")

    try: 
        vip_nodes, vip_stconv, info, iters, allstconv, vip_lr, vipstconv_lr, realN_lr, S_history_lr, convergence = stconvhyb(network, request.fun_name or "exp", request.nnodes or 1, options)
    except PrimmeError: 
        return JSONResponse(
            status_code=400, 
            content={"error": "maximum number of iterations or matvecs reached, try decreasing batch size."}
    )

    return {
        "vip_nodes": vip_nodes.tolist(),
        "vip_stconv": vip_stconv.tolist(),
        "convergence_gauss": "exceeded max iterations number" if info else "satisfied",
        "convergence_lowrank": convergence,
        "matrix_vector_products": iters.tolist(),
        "all_starting_conveniences": allstconv.tolist(),
        "vip_lowrank": vip_lr.tolist(),
        "vipstconv_lowrank": vipstconv_lr.tolist(),
        "used_eigenpairs": int(realN_lr),
        "candidates_history": [c.tolist() for c in S_history_lr]
    }

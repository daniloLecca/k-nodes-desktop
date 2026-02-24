import io
import numpy as np
import scipy
import asyncio
import generate as gnt
from scipy import sparse
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import eigsh
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from utils import get_clusters, ClusterRequest, ExpRequest, ResRequest, RandomComplexNetworkRequest
from utils import LowRankSubgraphCentrality
from gauss import gauss_exp, gauss_res
from lowrank import sgcenlr
from secrets import token_urlsafe

# Middleware per limitare la dimensione del body
class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_size: int = 100 * 1024 * 1024):  # Default 100 MB
        super().__init__(app)
        self.max_body_size = max_body_size
    
    async def dispatch(self, request: Request, call_next):
        # Controlla la dimensione del content-length se presente nell'header
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_body_size:
            return JSONResponse(
                status_code=413,
                content={"error": f"File too large. Maximum size allowed is {self.max_body_size / (1024 * 1024):.0f} MB"}
            )
        
        response = await call_next(request)
        return response

app = FastAPI()

# Aggiungi il middleware all'applicazione
app.add_middleware(BodySizeLimitMiddleware, max_body_size=100 * 1024 * 1024)  # 100 MB

# TODO: add expiring for this variables, only needed for when it will be deployed
clusters = {}
network: csc_matrix = None # the adjacency matrix
leig: float = 0.0


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

        # convert the sparse matrix in column sparse format if it's not already
        if sparse.issparse(adj):
            adj = adj.tocsc()
            adj.setdiag(0) # all the elements in the diagonal will be equal to 0
            # TODO: check if there were self loops (compare the original diagonal with a 
            # diagonal of zeros)
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
        
        return {
            "filename": file.filename,
            "nodes": int(list(adj.shape)[0]),
            "edges": int(adj.nnz), 
            "clusters": size_of_clusters,
            "numberOfClusters": len(size_of_clusters.keys()), 
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
def get_gauss_exp(request: ExpRequest):
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
        "clusters": clusters
    }

@app.post("/api/sgclr")
async def get_sgclr(request: LowRankSubgraphCentrality):
    import logging
    logger = logging.getLogger(__name__)
    
    options = {
        "sgcmaxn": request.max_iter or 30, 
        "sgcmaxva": 200,  # max eigenvector database
        "sgctoll": request.tol or 1e-3,  # tolerance for approximation loop
        "sgctau": 1e-4, # tolerance for weak convergence
        "sgcminkappa": 5,  # min size of additional nodes in the case of weak convergence
        "sgcmaxkappa": 100,  # max size of additional nodes in the case of weak convergence
        "sgcshift": request.shift if request.shift is not None else True, 
        "alpha": request.alpha or 0.0, 
        "k": request.batch_size or 20,  # batch size for primme
        "tol": 1e-5,  # tolerance for primme
        "primme_maxiter": 5000,  # max number of iterations for primme
        "return_S": True  
    }

    if network is None:
        return JSONResponse(
            status_code=400, 
            content={"error": "network not initialized yet. First send a .mat file to /api/."}
        )
    
    logger.info(f"Starting sgclr computation with {network.shape[0]} nodes, fun={request.fun_name}, nnodes={request.nnodes}")
    vip_nodes, vip_sgc, candidates_history = sgcenlr(network, request.fun_name or "exp", request.nnodes or 1, options)
    
    # TODO: check default parameters to prevent missing convergence

    return {
        "vip_nodes": vip_nodes.tolist(),
        "vip_sgc": vip_sgc.tolist(),
        "candidates_history": [c.tolist() for c in candidates_history]
    }

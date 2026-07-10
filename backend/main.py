import io
import os
import numpy as np
import logging
import argparse
import uvicorn 
import generate as gnt
from scipy import sparse
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import eigsh
from fastapi import FastAPI, File, UploadFile, Request, Header, Depends, HTTPException
from fastapi.responses import StreamingResponse
import matplotlib.pyplot as plt
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi.middleware.cors import CORSMiddleware 

from utils import get_clusters, ClusterRequest, ExpRequest, ResRequest, RandomComplexNetworkRequest
from utils import LowRankSubgraphCentrality, LowRankCommunicability, GaussSubgraphCentrality, GaussCommunicability
from utils import HybridSubgraphCentrality, HybridCommunicability
from utils import extract_complex_network_from_file
from gauss import gauss_exp, gauss_res, sgcengauss, commgauss, stconvgauss
from lowrank import sgcenlr, commlr, stconvlr
from hybrid import sgcenhyb, commhyb, stconvhyb
from layout import entire_network_layout
from primme import PrimmeError
from secrets import token_urlsafe
from time import perf_counter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

NUMBER_OF_LOW_RANK_NODES_ESTIMATE = 10

class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_size: int = 100 * 1024 * 1024):
        super().__init__(app)
        self.max_body_size = max_body_size
    
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_body_size:
            return JSONResponse(
                status_code=413,
                content={"error": f"File too large. Maximum size allowed is {self.max_body_size / (1024 * 1024):.0f} MB"}
            )
        response = await call_next(request)
        return response

app = FastAPI()
app.add_middleware(BodySizeLimitMiddleware, max_body_size=100 * 1024 * 1024)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOCAL_SESSION_STORE = {}

def serialize_candidates_history(candidates_history):
    serialized = []
    for entry in candidates_history:
        if isinstance(entry, tuple) and len(entry) == 4:
            candidate_nodes, lower_bounds, upper_bounds, eigenvalue = entry
            serialized.append({
                "candidate_nodes": np.asarray(candidate_nodes).tolist(),
                "lower_bounds": np.asarray(lower_bounds).tolist(),
                "upper_bounds": np.asarray(upper_bounds).tolist(),
                "eigenvalue": float(eigenvalue),
            })
        else:
            serialized.append({
                "candidate_nodes": np.asarray(entry).tolist(),
            })
    return serialized

def get_network_session(x_network_token: str = Header(...)) -> csc_matrix:
    if not x_network_token:
        raise HTTPException(status_code=400, detail="token is missing")
    
    session_data = LOCAL_SESSION_STORE.get(x_network_token)
    if not session_data:
        raise HTTPException(status_code=404, detail="session expired or not existing.")
    
    return session_data

@app.delete("/api/session")
def delete_network_session(x_network_token: str = Header(...)):
    if not x_network_token:
        raise HTTPException(status_code=400, detail="token is missing")
    deleted = LOCAL_SESSION_STORE.pop(x_network_token, None) is not None
    return {"deleted": deleted, "token": x_network_token}

@app.get("/api/")
def read_root():
    return {"Hello": "World"}

@app.post("/api/")
async def overview(file: UploadFile = File(...)):
    if not (file.filename.endswith('.mat') or file.filename.endswith('.gexf') or file.filename.endswith('.json')):
        return JSONResponse(status_code=400, content={"error": "the file must have .mat, .gexf or .json extension"})
    
    try:
        contents = await file.read()
        contents = io.BytesIO(contents)
        
        if file.filename.endswith('.mat'): format = ".mat"
        elif file.filename.endswith('.json'): format = ".json"
        else: format = ".gexf"

        try: 
            network = extract_complex_network_from_file(contents=contents, format=format)
        except Exception as e: 
            return JSONResponse(status_code=400, content={"error": "file not valid"})

        number_of_self_loops: int = 0
        if sparse.issparse(network):
            network = network.tocsc()
            number_of_self_loops = np.sum(network.diagonal())
            network.setdiag(0)
            network.eliminate_zeros()
        else:
            return JSONResponse(status_code=400, content={"error": "must be a sparse adjacency matrix"})
        
        leig = eigsh(network, k=1, which='LA', return_eigenvectors=False)[0]
        clusters = {}
        token = token_urlsafe(32)
        
        LOCAL_SESSION_STORE[token] = {
            "network": network,
            "leig": leig,
            "clusters": clusters
        }
        
        return {
            "token": token,
            "filename": file.filename,
            "nodes": int(list(network.shape)[0]),
            "edges": int(network.nnz // 2),
            "largest eigenvalue": leig,
            "max value for alpha": float(1 / leig),
            "self loops": int(number_of_self_loops),
            "clusters": clusters,
            "numberOfClusters": len(clusters.keys())
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"error processing the file: {str(e)}"})
    finally:
        await file.close()

@app.post("/api/cluster")
def nodes_of_cluster(request: ClusterRequest, session: dict = Depends(get_network_session)):
    clusters = session["clusters"]
    try:
        cluster_id = int(request.clusterID)
        if cluster_id in clusters:
            return {"clusterID": cluster_id, "nodes": clusters[cluster_id]}
        else:
            return JSONResponse(status_code=404, content={"error": f"Cluster not found"})
    except ValueError:
        return JSONResponse(status_code=400, content={"error": f"clusterID must be an integer"})
    
@app.post("/api/gaussexp")
def get_gauss_exp(request: ExpRequest, session: dict = Depends(get_network_session)):
    network = session["network"]
    leig = session["leig"]
    u = np.zeros(network.shape[0])
    u[request.node] = 1.0
    val, steps = gauss_exp(network, u, leig)
    return {"exp": val, "steps": steps}

@app.post("/api/gaussres")
def get_gauss_res(request: ResRequest, session: dict = Depends(get_network_session)):
    network = session["network"]
    leig = session["leig"]
    try:
        u = np.zeros(network.shape[0])
        u[request.node] = 1.0
        val, steps = gauss_res(network, u, leig, request.alpha)
        return {"res": val}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
@app.post("/api/random")
def get_random_complex_network(request: RandomComplexNetworkRequest): 
    if request.model == "scale_free": 
        network = gnt.generate_scale_free_complex_network(request.nnodes, request.k)
    else:
        network = gnt.generate_small_world_complex_network(request.nnodes, request.k, request.p)

    leig = eigsh(network, k=1, which='LA', return_eigenvectors=False)[0]
    clusters = {}
    token = token_urlsafe(32)
        
    LOCAL_SESSION_STORE[token] = {
        "network": network,
        "leig": leig,
        "clusters": clusters
    }
        
    return {
        "token": token,
        "nodes": int(network.shape[0]),
        "edges": int(network.nnz // 2), 
        "largest eigenvalue": leig,
        "max value for alpha": float(1 / leig),
        "self loops": 0,
        "clusters": clusters,
        "numberOfClusters": len(clusters.keys())
    }

@app.post("/api/plot")
async def get_plot(session: dict = Depends(get_network_session)):
    network = session["network"]
    plt.figure()
    plt.spy(network, precision=0.01, markersize=0.5)
    plt.title("Sparsity pattern of the adjacency matrix")
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")

@app.post("/api/sgcenlr")
async def get_sgclr(request: LowRankSubgraphCentrality, session: dict = Depends(get_network_session)):
    network = session["network"]
    options = {
        "lr_max_iterations": request.max_iter or 300, 
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": request.low_rank_tol or 1e-3,
        "lr_weak_convergence_tol": 1e-1,
        "lr_min_additional_nodes": 1,
        "lr_max_additional_nodes": 100,
        "lr_shift": request.shift if request.shift is not None else True, 
        "alpha": request.alpha or 0.0, 
        "lr_primme_batch_size": request.batch_size or 20,
        "lr_primme_tol": 1e-5,
        "lr_primme_max_iterations": 5000,
        "lr_return_S": True  
    }
    try: 
        t0 = perf_counter()
        vip_nodes, vip_sgc, num_eigs, candidates_history = sgcenlr(network, request.fun_name or "exp", request.nnodes or 1, options)
    except PrimmeError: 
        return JSONResponse(status_code=400, content={"error": "max iterations reached"})
    return {
        "vip_nodes": vip_nodes.tolist(),
        "vip_scores": vip_sgc.tolist(),
        "used_eigenpairs": num_eigs, 
        "elapsed_time": perf_counter() - t0,
        "candidates_history": serialize_candidates_history(candidates_history)
    }

@app.post("/api/commlr")
async def get_commlr(request: LowRankCommunicability, session: dict = Depends(get_network_session)):
    network = session["network"]
    options = {
        "lr_max_iterations": request.max_iter or 300, 
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": request.low_rank_tol or 1e-3,
        "lr_weak_convergence_tol": 1e-1,
        "lr_min_additional_nodes": 1,
        "lr_max_additional_nodes": 100,
        "lr_shift": request.shift if request.shift is not None else True, 
        "alpha": request.alpha or 0.0, 
        "lr_primme_batch_size": request.batch_size or 20,
        "lr_primme_tol": 1e-5,
        "lr_primme_max_iterations": 5000,
        "lr_return_S": True  
    }
    try: 
        t0 = perf_counter()
        vip_nodes, vip_comm, num_eigs, candidates_history = commlr(network, request.i, request.fun_name or "exp", request.nnodes or 1, options)
    except PrimmeError: 
        return JSONResponse(status_code=400, content={"error": "max iterations reached"})
    return {
        "vip_nodes": vip_nodes.tolist(),
        "vip_scores": vip_comm.tolist(),
        "used_eigenpairs": num_eigs, 
        "elapsed_time": perf_counter() - t0,
        "candidates_history": serialize_candidates_history(candidates_history)
    }

@app.post("/api/stconvlr")
async def get_stconvlr(request: LowRankSubgraphCentrality, session: dict = Depends(get_network_session)):
    network = session["network"]
    options = {
        "lr_max_iterations": request.max_iter or 300, 
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": request.low_rank_tol or 1e-3,
        "lr_weak_convergence_tol": 1e-1,
        "lr_min_additional_nodes": 1,
        "lr_max_additional_nodes": 100,
        "lr_shift": request.shift if request.shift is not None else True, 
        "alpha": request.alpha or 0.0, 
        "lr_primme_batch_size": request.batch_size or 20,
        "lr_primme_tol": 1e-5,
        "lr_primme_max_iterations": 5000,
        "lr_return_S": True  
    }
    try: 
        t0 = perf_counter()
        vip_nodes, vip_stconv, num_eigs, candidates_history = stconvlr(network, request.fun_name or "exp", request.nnodes or 1, options)
    except PrimmeError: 
        return JSONResponse(status_code=400, content={"error": "max iterations reached"})
    return {
        "vip_nodes": vip_nodes.tolist(),
        "vip_scores": vip_stconv.tolist(),
        "used_eigenpairs": num_eigs, 
        "elapsed_time": perf_counter() - t0,
        "candidates_history": serialize_candidates_history(candidates_history)
    }

@app.post("/api/sgcengauss")
async def get_sgcgauss(request: GaussSubgraphCentrality, session: dict = Depends(get_network_session)):
    network = session["network"]
    leig = session["leig"]
    options = {
        "gauss_tol": request.gauss_tol or 1e-3, 
        "gauss_max_iterations": request.max_iter or 200,
        "gauss_largest_eigenvalue": leig,
        "alpha": request.alpha or 0.0
    }
    t0 = perf_counter()
    vip_nodes, vip_sgc, info, iters, allsgc = sgcengauss(network, request.fun_name or "exp", request.nnodes or 1, options)
    return {
        "vip_nodes": vip_nodes.tolist(), 
        "vip_scores": vip_sgc.tolist(), 
        "convergence_gauss": "exceeded max iterations number" if info else "satisfied",
        "elapsed_time": perf_counter() - t0, 
        "matrix vector products": iters.tolist(), 
        "all subgraph centralities": allsgc.tolist()
    }

@app.post("/api/commgauss")
async def get_commgauss(request: GaussCommunicability, session: dict = Depends(get_network_session)):
    network = session["network"]
    options = {
        "gauss_tol": request.gauss_tol or 1e-3, 
        "gauss_max_iterations": request.max_iter or 200,
        "alpha": request.alpha or 0.0
    }
    try: 
        t0 = perf_counter()
        vip_nodes, vip_comm, info, iters, allcomm = commgauss(network, request.i, request.fun_name or "exp", request.nnodes or 1, options)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    return {
        "vip_nodes": vip_nodes.tolist(), 
        "vip_scores": vip_comm.tolist(), 
        "convergence_gauss": "exceeded" if info else "satisfied", 
        "elapsed_time": perf_counter() - t0,
        "matrix vector products": iters.tolist(), 
        "all communicatibilites": allcomm.tolist()
    }

@app.post("/api/stconvgauss")
async def get_stconvgauss(request: GaussSubgraphCentrality, session: dict = Depends(get_network_session)):
    network = session["network"]
    leig = session["leig"]
    options = {
        "gauss_tol": request.gauss_tol or 1e-3, 
        "gauss_max_iterations": request.max_iter or 200,
        "gauss_largest_eigenvalue": leig,
        "alpha": request.alpha or 0.0
    }
    t0 = perf_counter()
    vip_nodes, vip_stconv, info, iters, allstconv = stconvgauss(network, request.fun_name or "exp", request.nnodes or 1, options)
    return {
        "vip_nodes": vip_nodes.tolist(), 
        "vip_scores": vip_stconv.tolist(), 
        "convergence_gauss": "exceeded" if info else "satisfied", 
        "elapsed_time": perf_counter() - t0,
        "matrix vector products": iters.tolist(), 
        "all subgraph centralities": allstconv.tolist()
    }

@app.post("/api/sgcenhyb")
async def get_sgchyb(request: HybridSubgraphCentrality, session: dict = Depends(get_network_session)):
    network = session["network"]
    leig = session["leig"]
    lr_options = {
        "lr_max_iterations": request.max_iter or 300, 
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": request.low_rank_tol or 1e-3,
        "lr_weak_convergence_tol": 1e-1,
        "lr_nnodes": request.low_rank_nnodes or int(NUMBER_OF_LOW_RANK_NODES_ESTIMATE * request.nnodes),
        "lr_min_additional_nodes": 5,
        "lr_max_additional_nodes": 100,
        "lr_shift": request.shift if request.shift is not None else True,
        "lr_primme_batch_size": request.batch_size or 20,
        "lr_primme_tol": 1e-5,
        "lr_primme_max_iterations": 5000,
        "lr_return_S": True,
    }
    gauss_options = {"gauss_tol": request.gauss_tol or 1e-3, "gauss_max_iterations": 200, "gauss_largest_eigenvalue": leig}
    options = {**lr_options, **gauss_options, "alpha": request.alpha or 0.0}
    try: 
        t0 = perf_counter()
        vip_nodes, vip_sgc, info, iters, allsgc, vip_lr, vipsgc_lr, realN_lr, S_history_lr, convergence = sgcenhyb(network, request.fun_name or "exp", request.nnodes or 1, options)
    except PrimmeError as e: 
        return JSONResponse(status_code=400, content={"error": "max iterations reached"})
    return {
        "vip_nodes": vip_nodes.tolist(),
        "vip_scores": vip_sgc.tolist(),
        "convergence_gauss": "exceeded" if info else "satisfied",
        "convergence_lowrank": convergence,
        "matrix_vector_products": iters.tolist(),
        "all_subgraph_centralities": allsgc.tolist(),
        "elapsed_time": perf_counter() - t0,
        "vip_lowrank": vip_lr.tolist(),
        "vipsgcen_lowrank": vipsgc_lr.tolist(),
        "used_eigenpairs": int(realN_lr),
        "candidates_history": serialize_candidates_history(S_history_lr)
    }

@app.post("/api/commhyb")
async def get_commhyb(request: HybridCommunicability, session: dict = Depends(get_network_session)):
    network = session["network"]
    lr_options = {
        "lr_max_iterations": request.max_iter or 300, 
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": request.low_rank_tol or 1e-3,
        "lr_weak_convergence_tol": 1e-1,
        "lr_nnodes": request.low_rank_nnodes or int(NUMBER_OF_LOW_RANK_NODES_ESTIMATE * request.nnodes),
        "lr_min_additional_nodes": 5,
        "lr_max_additional_nodes": 100,
        "lr_shift": request.shift if request.shift is not None else True,
        "lr_primme_batch_size": request.batch_size or 20,
        "lr_primme_tol": 1e-5,
        "lr_primme_max_iterations": 5000,
        "lr_return_S": True,
    }
    gauss_options = {"gauss_tol": request.gauss_tol or 1e-3, "gauss_max_iterations": 200}
    options = {**lr_options, **gauss_options, "alpha": request.alpha or 0.0}
    try: 
        t0 = perf_counter()
        vip_nodes, vip_comm, info, iters, allcomm, vip_lr_local, vipcomm_lr_local, realN_lr, S_history_lr, convergence = commhyb(network, request.i, request.fun_name or "exp", request.nnodes or 1, options)
    except Exception as e: 
        return JSONResponse(status_code=400, content={"error": str(e)})
    return {
        "vip_nodes": vip_nodes.tolist(),
        "vip_scores": vip_comm.tolist(),
        "convergence_gauss": "exceeded" if info else "satisfied",
        "convergence_lowrank": convergence,
        "elapsed_time": perf_counter() - t0,
        "matrix_vector_products": iters.tolist(),
        "all_communicabilities": allcomm.tolist(),
        "vip_lowrank": vip_lr_local.tolist(),
        "vipcomm_lowrank": vipcomm_lr_local.tolist(),
        "used_eigenpairs": int(realN_lr),
        "candidates_history": serialize_candidates_history(S_history_lr)
    }

@app.post("/api/stconvhyb")
async def get_stconvhyb(request: HybridSubgraphCentrality, session: dict = Depends(get_network_session)):
    network = session["network"]
    leig = session["leig"]
    lr_options = {
        "lr_max_iterations": request.max_iter or 300, 
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": request.low_rank_tol or 1e-3,
        "lr_weak_convergence_tol": 1e-1,
        "lr_nnodes": request.low_rank_nnodes or int(NUMBER_OF_LOW_RANK_NODES_ESTIMATE * request.nnodes),
        "lr_min_additional_nodes": 5,
        "lr_max_additional_nodes": 100,
        "lr_shift": request.shift if request.shift is not None else True,
        "lr_primme_batch_size": request.batch_size or 20,
        "lr_primme_tol": 1e-5,
        "lr_primme_max_iterations": 5000,
        "lr_return_S": True,
    }
    gauss_options = {"gauss_tol": request.gauss_tol or 1e-3, "gauss_max_iterations": 200, "gauss_largest_eigenvalue": leig}
    options = {**lr_options, **gauss_options, "alpha": request.alpha or 0.0}
    try: 
        t0 = perf_counter()
        vip_nodes, vip_stconv, info, iters, allstconv, vip_lr, vipstconv_lr, realN_lr, S_history_lr, convergence = stconvhyb(network, request.fun_name or "exp", request.nnodes or 1, options)
    except PrimmeError: 
        return JSONResponse(status_code=400, content={"error": "max iterations reached"})
    return {
        "vip_nodes": vip_nodes.tolist(),
        "vip_scores": vip_stconv.tolist(),
        "convergence_gauss": "exceeded" if info else "satisfied",
        "convergence_lowrank": convergence,
        "elapsed_time": perf_counter() - t0,
        "matrix_vector_products": iters.tolist(),
        "all_starting_conveniences": allstconv.tolist(),
        "vip_lowrank": vip_lr.tolist(),
        "vipstconv_lowrank": vipstconv_lr.tolist(),
        "used_eigenpairs": int(realN_lr),
        "candidates_history": serialize_candidates_history(S_history_lr)
    }

@app.post("/api/tiny_network_viz")
async def get_positions_tiny_network(session: dict = Depends(get_network_session)):
    return entire_network_layout(network=session["network"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8123, help="backend server port")
    args = parser.parse_args()
    
    uvicorn.run(app, host="127.0.0.1", port=args.port)
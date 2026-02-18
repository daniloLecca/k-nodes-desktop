import io
import numpy as np
import scipy
from scipy import sparse
from scipy.sparse import csc_matrix
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from utils import get_clusters, ClusterRequest
from gauss import gauss_exp

app = FastAPI()

# TODO: add expiring for this variables, only needed for when it will be deployed
clusters = {}
network: csc_matrix = None # the adjacency matrix


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
    global clusters, network
    
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
            network = adj
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "the variable must be a sparse adjacency matrix"
                }
            )
        
        clusters = get_clusters(adj)
        size_of_clusters = {}

        # for each cluster compute the size of the cluster
        for cluster in clusters.keys():
            size_of_clusters[cluster] = len(clusters[cluster])
        
        return {
            "filename": file.filename,
            "nodes": int(list(adj.shape)[0]),
            "edges": int(adj.size), 
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
def get_gauss_exp():
    if network is None:
        return JSONResponse(status_code=400, content={"error": "network not initialized yet. First send a .mat file to /api/."})

    u = np.zeros(network.shape[0])
    u[0] = 1.0
    val, steps = gauss_exp(network, u)
    return {
        "exp": val
    }
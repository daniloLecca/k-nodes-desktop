import io

import numpy as np
import scipy
from scipy import sparse
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from utils import get_clusters

app = FastAPI()

# TODO: add expiring for this variables
clusters = {}
network = None # the adjacency matrix

@app.get("/api/")
def read_root():
    return {"Hello": "World"}
'''
return a json with this format: 
response = {
    filename: file name,
    nodes: number of nodes,
    edges: number of edges,
    clusters: {
        clusterID1: number of the nodes that compound the cluster
        ...
    },
    numberOfClusters: number of clusters 
}
'''
@app.post("/api/")
async def overview(file: UploadFile = File(...)):
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
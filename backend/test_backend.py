import pytest, scipy
from pathlib import Path
from scipy.sparse import csc_matrix, issparse
from lowrank import sgcenlr, stconvlr, commlr
from gauss import sgcengauss, stconvgauss, commgauss
from hybrid import sgcenhyb, stconvhyb, commhyb


graphs_dir = Path(__file__).parent / 'graphs'
mat_files = [
    "adjacency_22july06.mat", 
    "adjacency_cond-mat-2005.mat", 
    "adjacency_facebook.mat", 
    "adjacency_karate.mat", 
    "adjacency_power.mat", 
    "adjacency_yeast.mat"
]


def retrieve_adj_matrix(file_name: str) -> csc_matrix:
    """
    Returns the adjacency matrix (in column sparse format) given the file name. 
    All the files are from the directory 'graphs/'. 

    :param file_name: name of the file (written as 'file_name.mat')
    """
    graphs_dir = Path(__file__).parent / 'graphs'
    file_path = graphs_dir / file_name
    mat_data = scipy.io.loadmat(str(file_path))
    mat_data = {k: v for k, v in mat_data.items() if not k.startswith('__')}
    _, adj = next(iter(mat_data.items()))
    adj = adj.tocsc()
    return adj

def test_retrieve_adj_matrix():
    """
    Checks if each file contains a sparse matrix.
    """
    
    for file in mat_files:
        net = retrieve_adj_matrix(file_name=file)
        assert issparse(net)

# --- TEST FOR SOME ADJACENCY MATRICES --- #
# For each adjacency matrix is verified if it passes when: 
# 1. nnodes = 1 
# 2. nnodes = 10
# 3. 


def test_adjacency_22july06_low_rank():

    net = retrieve_adj_matrix(mat_files[0])
    leig = 71.61300031264696
    alpha = 0.001

    options_lr = {
        "lr_max_iterations": 300, 
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": 1e-1,
        "lr_weak_convergence_tol": 1e-1,
        "lr_min_additional_nodes": 1,
        "lr_max_additional_nodes": 100,
        "lr_shift":  True, 
        "alpha": alpha, 
        "lr_primme_batch_size": 20,
        "lr_primme_tol": 1e-5,
        "lr_primme_max_iterations": 5000,
        "lr_return_S": True  
    }

    options_gauss = {
        "gauss_tol": 1e-3, 
        "gauss_max_iterations": 200,
        "gauss_largest_eigenvalue": leig,
        "alpha": 0.0
    }

    options_hyb = {**options_lr, **options_gauss}
    

    # --- START ASSERTS --- #
    # subgraph centrality with low rank approximation
    vip, vip_sgc, _, _ = sgcenlr(net, "exp", 1, opts=options_lr)
    assert vip[0] == 3
    assert vip_sgc[0] == pytest.approx(7.53597e29)

    vip, vip_sgc, _, _ = sgcenlr(net, "res", 1, opts=options_lr)
    assert vip[0] == 3
    assert vip_sgc[0] == pytest.approx(0.0643101)

    vip, vip_sgc, _, _ = sgcenlr(net, "exp", 10, opts=options_lr)
    assert vip[6] == 11

    vip, vip_sgc, _, _ = sgcenlr(net, "res", 10, opts=options_lr)
    assert vip[6] == 11


    # communicability with low rank approximation
    vip, vip_sgc, _, _ = commlr(net, 0, "exp", 1, opts=options_lr)
    assert vip[0] == 3
    assert vip_sgc[0] == pytest.approx(3.008916e29)

    vip, vip_sgc, _, _ = commlr(net, 0, "res", 1, opts=options_lr)
    assert vip[0] == 3
    assert vip_sgc[0] == pytest.approx(0.02567735)

    vip, vip_sgc, _, _ = commlr(net, 0, "exp", 10, opts=options_lr)
    assert vip[6] == 11

    vip, vip_sgc, _, _ = commlr(net, 0, "res", 10, opts=options_lr)
    assert vip[6] == 11


    # starting convenience with low rank approximation
    vip, vip_sgc, _, _ = stconvlr(net, "exp", 1, opts=options_lr)
    assert vip[0] == 3
    assert vip_sgc[0] == pytest.approx(1.66314549e32)

    vip, vip_sgc, _, _ = stconvlr(net, "res", 1, opts=options_lr)
    assert vip[0] == 3
    assert vip_sgc[0] == pytest.approx(14.192873)

    vip, vip_sgc, _, _ = stconvlr(net, "exp", 10, opts=options_lr)
    assert vip[6] == 11

    vip, vip_sgc, _, _ = stconvlr(net, "res", 10, opts=options_lr)
    assert vip[6] == 11
    # --- END ASSERTS --- #





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


def test_adjacency_power():
    """
    Unit tests for adjacency_power.mat complex network
    Each unit test is performed for the seek of 1 node. 

    Structure of the unit tests: 
    - Subgraph centrality, "exp", low rank
    - Subgraph centrality, "res", low rank

    - Communicability, "exp", low rank
    - Communicability, "res", low rank

    - Starting convenience, "exp", low rank
    - Starting convenience, "res", low rank

    - Subgraph centrality, "exp", gauss
    - Subgraph centrality, "res", gauss
    
    - Communicability, "exp", gauss
    - Communicability, "res", gauss

    - Starting convenience, "exp", gauss
    - Starting convenience, "res", gauss

    - Subgraph centrality, "exp", hybrid
    - Subgraph centrality, "res", hybrid
    
    - Communicability, "exp", hybrid
    - Communicability, "res", hybrid

    - Starting convenience, "exp", hybrid
    - Starting convenience, "res", hybrid
    """

    net = retrieve_adj_matrix(mat_files[4])
    leig = 7.4830513288472496
    alpha = 0.1

    options_lr = {
        "lr_max_iterations": 10000, 
        "lr_max_eigenvectors": 200,
        "lr_approximation_tol": 1e-5,
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
        "alpha": alpha
    }

    options_hyb = {**options_lr, **options_gauss}
    options_hyb["lr_nnodes"] = 1
    

    # --- START ASSERTS --- #
    # subgraph centrality with low rank approximation
    vip, vip_scores, _, _ = sgcenlr(net, "exp", 1, opts=options_lr)
    assert vip[0] == 4345
    assert vip_scores[0] == pytest.approx(185.7289)

    vip, vip_scores, _, _ = sgcenlr(net, "res", 1, opts=options_lr)
    assert vip[0] == 2553
    assert vip_scores[0] == pytest.approx(1.1547479)

    # communicability with low rank approximation
    vip, vip_scores, _, _ = commlr(net, 0, "exp", 1, opts=options_lr)
    assert vip[0] == 2235
    assert vip_scores[0] == pytest.approx(0.4154895808)

    vip, vip_scores, _, _ = commlr(net, 0, "res", 1, opts=options_lr)
    assert vip[0] == 2235
    assert vip_scores[0] == pytest.approx(0.00918930433)

    # starting convenience with low rank approximation
    vip, vip_scores, _, _ = stconvlr(net, "exp", 1, opts=options_lr)
    assert vip[0] == 4345
    assert vip_scores[0] == pytest.approx(3402.56464011)

    vip, vip_scores, _, _ = stconvlr(net, "res", 1, opts=options_lr)
    assert vip[0] == 2553
    assert vip_scores[0] == pytest.approx(8.49223480)

    vip, vip_scores, _, _, _ = sgcengauss(net, "exp", 1, opts=options_gauss)
    print(vip[0], vip_scores[0])
    assert vip[0] == 4345
    assert vip_scores[0] == pytest.approx(186.60281638)

    vip, vip_scores, _, _, _ = sgcengauss(net, "res", 1, opts=options_gauss)
    print(vip[0], vip_scores[0])
    assert vip[0] == 4345
    assert vip_scores[0] == pytest.approx(1.31786168)

    vip, vip_scores, _, _, _ = commgauss(net, 0, "exp", 1, opts=options_gauss)
    print(vip[0], vip_scores[0])
    assert vip[0] == 0
    assert vip_scores[0] == pytest.approx(3.592502075)

    vip, vip_scores, _, _, _ = commgauss(net, 0, "res", 1, opts=options_gauss)
    print(vip[0], vip_scores[0])
    assert vip[0] == 0
    assert vip_scores[0] == pytest.approx(1.03219718)

    vip, vip_scores, _, _, _ = stconvgauss(net, "exp", 1, opts=options_gauss)
    print(vip[0], vip_scores[0])
    assert vip[0] == 4345
    assert vip_scores[0] == pytest.approx(3391.7560733)

    vip, vip_scores, _, _, _ = stconvgauss(net, "res", 1, opts=options_gauss)
    print(vip[0], vip_scores[0])
    assert vip[0] == 4345
    assert vip_scores[0] == pytest.approx(6.547312769433)

    vip, vip_scores, _, _, _, _, _, _, _, _ = sgcenhyb(net, "exp", 1, opts=options_hyb)
    print(vip[0], vip_scores[0])
    assert vip[0] == 4345
    assert vip_scores[0] == pytest.approx(186.60281638)

    vip, vip_scores, _, _, _, _, _, _, _, _ = sgcenhyb(net, "res", 1, opts=options_hyb)
    print(vip[0], vip_scores[0])
    assert vip[0] == 2553
    assert vip_scores[0] == pytest.approx(1.289192272)

    vip, vip_scores, _, _, _, _, _, _, _, _ = commhyb(net, 0, "exp", 1, opts=options_hyb)
    print(vip[0], vip_scores[0])
    assert vip[0] == 2223
    assert vip_scores[0] == pytest.approx(0.4125254997914487)

    vip, vip_scores, _, _, _, _, _, _, _, _ = commhyb(net, 0, "res", 1, opts=options_hyb)
    print(vip[0], vip_scores[0])
    assert vip[0] == 2223
    assert vip_scores[0] == pytest.approx(0.001226976433)

    vip, vip_scores, _, _, _, _, _, _, _, _ = stconvhyb(net, "exp", 1, opts=options_hyb)
    print(vip[0], vip_scores[0])
    assert vip[0] == 4345
    assert vip_scores[0] == pytest.approx(3391.7560733)

    vip, vip_scores, _, _, _, _, _, _, _, _ = stconvhyb(net, "res", 1, opts=options_hyb)
    print(vip[0], vip_scores[0])
    assert vip[0] == 4345
    assert vip_scores[0] == pytest.approx(6.547312769433)
    # --- END ASSERTS --- #





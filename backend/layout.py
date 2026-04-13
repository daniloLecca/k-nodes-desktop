from fa2 import ForceAtlas2
from fa2.viz import export_layout
from scipy.sparse import csc_matrix
import logging
from time import perf_counter
from datetime import datetime

logger = logging.getLogger(__name__) # for printing logs in dev
logging.basicConfig(level=logging.INFO)

# for basic visualization, only needed when doing the setup for Sigma
def entire_network_layout(network: csc_matrix) -> dict:
    network = network.tocsr()
    iters = 300

    logger.info(f"Layout computation started... {datetime(2026, 4, 12).now()}")

    t0 = perf_counter()
    fa2 = ForceAtlas2(verbose=True)
    positions = fa2.forceatlas2(network, iterations=iters)

    layout = export_layout(G=network, positions=positions, fmt="json")

    # Graphology serialized instance has the following format: 
    nodes = list(map(lambda node: {"key": str(node["id"]), "attributes": {"x": node["x"], "y": node["y"], "size": 3, "label": "Node " + str(node["id"] + 1)}}, layout["nodes"]))
    logger.info("nodes positions have been computed")
    edges = list(map(lambda edge: {"source": str(edge["source"]), "target": str(edge["target"]), "weight": 1, "size": 0.5}, layout["edges"]))
    logger.info("edges positions have been computed")

    logger.info(f"Elapsed time with iterations = {iters}: {perf_counter() - t0}s")
    return {"nodes": nodes, "edges": edges}
from fa2 import ForceAtlas2
from fa2.viz import export_layout
from scipy.sparse import csc_matrix
import logging

logger = logging.getLogger(__name__) # for printing logs in dev
logging.basicConfig(level=logging.INFO)

# for basic visualization, only needed when doing the setup for Sigma
def entire_network_layout(network: csc_matrix) -> dict:
    network = network.tocsr()

    fa2 = ForceAtlas2(verbose=False)
    positions = fa2.forceatlas2(network, iterations=300)

    layout = export_layout(G=network, positions=positions, fmt="json")

    # Graphology serialized instance has the following format: 
    nodes = list(map(lambda node: {"key": str(node["id"]), "attributes": {"x": node["x"], "y": node["y"], "size": 5, "color": "yellow", "label": "Nodo " + str(node["id"] + 1)}}, layout["nodes"]))
    logger.info(nodes)
    edges = list(map(lambda edge: {"source": str(edge["source"]), "target": str(edge["target"]), "weight": 2}, layout["edges"]))

    return {"nodes": nodes, "edges": edges}
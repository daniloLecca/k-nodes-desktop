
# Vipnodes

An online tool for seeking the most important nodes of a network through the computation of centrality measures in undirected, unweighted complex networks.

## Description

This tool offers is born with the intention of making available the tool *VIPNODES* already existing in **MATLAB**.

These are some of the functionalities introduced in this tool:

* Analyze a complex network given the sparse adjacency matrix. Note that at the moment only *.mat* files are accepted
* Visualize the complex network. With **vipnodes** you can take a look at the entire network thanks to a force directed layout, which gives a clean and ordered visualization of the nodes and edges
* Discover the most important nodes of the complex network with some of the most interesting measures, for example:
  * Communicability of a node with entire network
  * Subgraph centrality of a node
  * Starting convenience of a node
* Exploit the most common and performing algorithms to compute these metrics via low rank approximation and Gauss quadrature
* Get statistics of the computation, *i.e.* distribution of the spectrum, bounds for a metric in a certain node and a heatmap of the adjacency matrix

The entire project is made in Vue, with the aid of Sigma.js v2 and Graphology for the visualization of the network, and the backend which processes the complex network is based on FastAPI, a popular and high-performing Python framework for backend development.

## Usage
This project makes use of *Nginx* as a reverse proxy, in order to serve the static Vue files and the API calls whenever required. 

In general is strongly suggested to make the HTTP request to this single endpoint: 
```markdown
localhost:80/
```

In case we need to access the API: 
```markdown
localhost:80/api/
```
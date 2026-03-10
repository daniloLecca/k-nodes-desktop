
# Vipnodes

An online tool for seeking the most important nodes of a network through the computation of centrality measures in undirected, unweighted complex networks.

## Description

This tool offers was created with the intent of making available the tool *VIPNODES*, which was originally developed in **MATLAB**.

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

All the data working data of the web-app is stored with Redis, an high performance in-memory database. Redis stores the data with _key-value_ pairs that are going to be accessible through a token with validity of 2 hours.

Note that the database in this case is not persistent since there is no need to save the network persistently. Future versions may implement a persistent storage if needed.

## Usage
This project makes use of *Nginx* as a reverse proxy, in order to serve the static Vue files and the API calls whenever required. In addition, only the port 80 is exposed making the software safer. At the moment the ports 5173 for frontend and 8000 for backend are avalaible for dev as well, they won't be available once the software is in production.

Generally, is strongly suggested to make the HTTP request to this single endpoint: 
```markdown
localhost:80/
```

In case we need to access the API: 
```markdown
localhost:80/api/
```
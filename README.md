
# K-NODES

![GitHub Release](https://img.shields.io/github/v/release/daniloLecca/k-nodes-desktop) ![GitHub Release Date](https://img.shields.io/github/release-date/daniloLecca/k-nodes-desktop?display_date=published_at)

K-NODES: Network-Oriented Detection and Selection of Key Nodes

Caterina FENU, Danilo LECCA, and Fabio PILI

ETNA Volume XX, Pages yy-zz, year

[link](https://etna.math.kent.edu/url_available_after_acceptance)

DESCRIPTION
-----------

An online and desktop tool for complex network analysis via centrality measures computation.

Some of the key functionalities offered by K-NODES:

* Visualization of the complex network with interactive features, especially useful for topological analysis.
* Upload a network or generate a synthetic one with several models and parameters.
* Compute centrality measures with different algorithms and options.
* Explore, interact and download the results with specific functionalities.

Release: 1.0, November 2026

Programming language: Python

DISCLAIMER
----------
ETNA editors have test run the code, but the responsibility of the correctness
of the code is with the authors. ETNA is not responsible for any problems the
code may cause; see the file License.md for details.

---

## Table of contents

* [Getting started](#getting-started)
  * [Web version](#web-version)
  * [Desktop](#desktop-version)
    * [Windows](#windows)
    * [MacOS](#macos)
    * [Linux](#linux)
* [Description](#description)
* [Usage](#usage)

## Getting started

### Web version

K-NODES is available online with the same functionalities of the desktop version.
You can visit K-NODES at [knodes.unica.it](https://knodes.unica.it).

### Desktop version

Click on [Releases](https://github.com/daniloLecca/k-nodes-desktop/releases) and download the latest version suited for your device.

***

#### Windows

##### Step 1

> [!IMPORTANT]
> Make sure to have installed Microsoft Visual C++ Redistributable.

In order to do this, run the following command in PowerShell:

```powershell
Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | Where-Object { $_.DisplayName -like "*Visual C++*" } | Select-Object DisplayName, DisplayVersion
```

if nothing gets displayed, you can install it at [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170). Once you installed it, restart your device.

##### Step 2

Open *K-NODES Setup 1.0.0.exe*. If a Microsoft security windows opens up, click *More info > Run anyway*.

***

#### MacOS

1. Open *K-NODES-1.0.0-arm64.dmg*
2. Move *K-NODES* to the Applications folder.
3. Eject the mounted disk image.

>[!IMPORTANT]
> Because K-NODES is an open-source project and not notarized through a paid Apple Developer certificate, macOS will
> flag it with a security warning on first launch (e.g., "K-NODES is damaged and can’t be opened" or "Apple cannot
> check it for malicious software").
> You can bypass this warning using either of the methods below.

##### Method 1: Remove the Quarantine Flag

1. Open Terminal (Cmd + Space, type Terminal, and press Enter).
2. Run the following command:

```bash
sudo xattr -cr /Applications/K-NODES.app
```

3. Type your macOS administrator password when prompted (characters will not show while typing) and press Enter.
4. Launch K-NODES normally from your Applications folder or Spotlight.

> [!NOTE]
> Note: If you moved the app to a custom folder instead of /Applications, replace the path above with the actual path
> to the app.

##### Method 2: System Settings Override

1. Try to open K-NODES once from /Applications so macOS logs the launch attempt, then close the warning dialog.
2. Open System Settings (or System Preferences on macOS Monterey and older).
3. Navigate to Privacy & Security.
4. Scroll down to the Security section.
5. You will see a notice: "K-NODES was blocked from use because it is not from an identified developer."
6. Click Open Anyway next to the notice and confirm with your admin password or Touch ID.

***

#### Linux

##### Step 1: Make the AppImage executable

Before running the application, grant execute permissions to the downloaded `.AppImage` file:

```bash

chmod +x K-NODES-1.0.0.AppImage

```

##### Step 2: Ensure Fuse2 is installed

> [!IMPORTANT]
> AppImage files require libfuse2 to mount and run. Many recent Linux distributions
> (such as Ubuntu 22.04 and newer, Debian 12, Fedora) do not include libfuse2 by
> default as they have transitioned to fuse3.

If running the AppImage produces an error related to FUSE (e.g., `dlopen(): error loading libfuse.so.2` or `AppImages require FUSE to run`), install the compatibility package:

* **Ubuntu / Debian / Mint**
  
```bash
sudo apt update
sudo apt install libfuse2
```

* **Fedora**

```bash
sudo dnf install fuse-libs
```

* **Arch Linux / Manjaro**
  
```bash
sudo pacman -S fuse2
```

##### Step 3: Run the application

Double-click K-NODES-1.0.0.AppImage or launch it from the terminal:

```bash
./K-NODES-1.0.0.AppImage
```

> [!TIP]
> If you cannot or do not wish to install `libfuse2`, you can launch the app directly
> by passing the `--appimage-extract-and-run` flag:

```bash
./K-NODES-1.0.0.AppImage --appimage-extract-and-run
```

> [!NOTE]
If the application fails to start due to Chromium/Electron sandbox issues (e.g. running in Docker, over SSH, or under strict user namespaces), you may need to pass the --no-sandbox flag:

```bash
./K-NODES-1.0.0.AppImage --no-sandbox
```

## Description

K-NODES proposes itself as a fast, reliable and accurate alternative for network analysis providing a wide range of options for graph visualization, centrality measures computation and data interpretation.

What differentiates K-NODES from the other tools is its unique architecture. An entirely *Python-driven* stack, with the aid of NumPy, SciPy, Networkx and FastAPI, establishes an excellent solution for performing accurate scientific calculations.

The entire GUI is built on top of Vue.js and employs specific tools and libraries in order to provide great performance and high usability. For example, leveraging [Sigma.js v2](https://www.sigmajs.org/) for network visualization ensures a smooth user experience, capable of handling the visualization of hundreds of thousands of nodes.

The neat separation between *frontend* and *backend* yields the possibility to scale and maintain them independently.

```mermaid
graph LR;
    subgraph Frontend [Frontend]
        Vue.js --> D3.js;
        Vue.js --> Sigma.js-V2;
        Vue.js <--> Electron.js;
    end

    Frontend <-- "Rest API" --> Backend;

    subgraph Backend [Backend]
        FastAPI --> SciPy;
        FastAPI --> NetworkX;
        FastAPI --> PRIMME;
    end

```

## Usage

### Network input and synthetic graph generation

Different file extensions are supported. Precisely, MATLAB `.mat` files, Graphology-compatible `.json` and [GEXF](https://gexf.net) `.gexf` format.

> [!NOTE]
> MATLAB `.mat` file must contain exactly one variable representing the sparse binary adjacency matrix of the network. Non-zero diagonal entries will be mapped to zero as well as the nonpositive entries.

Alternatively, one can generate a synthetic complex network using either the Barabási–Albert, Watts-Strogatz or binomial Erdős–Rényi model, with the possibility to precisely adjust the parameters.

![generation-and-upload](/frontend/public/imgs/random-generation-popup.png)

***

### Visualization and interaction

Topological network analysis is achievable with a dedicated dashboard:

![network visualization](/frontend/public/imgs/network-visualization.png)

Different interactions are supported, i.e. node dragging and degree displaying. The controls on the right support zooming, *fullscreen* mode and vertex search.

***

### Centrality computation

Different centrality measures are supported along with a wide range of options and parameters.

![computation form](/frontend/public/imgs/computation-form.png)

***

### Results diagnostics and exportation

Complete analytics are shown ranging from computation time to algorithm-specific outcomes. The prompted computation parameters are reported for a rapid evaluation of the performed experiment.

![results and exportation](/frontend/public/imgs/results-and-exportation.png)

Exporting the results can be done in three different ways:

* **PDF** format: a complete document which reports computation results and parameters alongside with calculation diagnostics.
* **CSV** format: *tabular-like* file where each row reports a K-node with its  corresponding score, with descending order.
* **JSON** format: a *key-value* representation of the results, particularly useful when using data analysis tools.

> [!TIP]
> Try not including the diagnostic images from the PDF file if the download is taking too long. This often happens if many iterations of the low rank approximation algorithm were needed.

Results diagnostics comprehend a *snapshot* of the adjacency matrix sparsity pattern, evaluated eigenvalues visualization and the *low rank* bounds evaluation overview.

![diagnostics](/frontend/public/imgs/diagnostics-evaluation.png)

> [!TIP]
> Try hovering over the plots to observe additional information.

> ## Tutorial and verification

The following smoke test checks that K-NODES can import a network and
compute a standard centrality index. It is not one of the timed experiments
in the paper. The numerical values below were independently checked from
`arctic.json` after representing the data as a simple, undirected graph.

1. Launch K-NODES using the web application or a desktop installation.
2. Import the supplied Graphology JSON file `arctic.json` using the network
   upload control. 
3. Check that the resulting graph has **1,715 vertices and 6,228 distinct
   edges**. The JSON contains 6,676 edge records; 448 are repeated unordered
   vertex pairs and must not be counted twice in a simple graph. No
   self-loops occur. The graph has seven connected components.
4. Select **Degree centrality (normalized)** and request the five highest
   ranked vertices. For the usual normalization by `n - 1 = 1714`, the
   expected results on the simple graph are:

   | Vertex key | Label | Degree | Normalized degree |
   | --- | --- | ---: | ---: |
   | `53` | Changement Climatique | 212 | 0.123687 |
   | `79` | Climatic Change | 170 | 0.099183 |
   | `65` | Effet De Serre | 143 | 0.083431 |
   | `1` | New York | 142 | 0.082847 |
   | `50` | Rechauffement Climatique | 120 | 0.070012 |

   The unaccented text in the last label is for ASCII compatibility; the
   corresponding label in the JSON includes an accent. Vertex keys and
   numeric values, rather than label spelling, are the primary checks.
5. Export the result in CSV or JSON format
   and check the ranking and scores against the table above.

These values are a reference for the **simple undirected** graph. The
original JSON also contains stored node attributes, including a field
named `nansi-degree`; these attributes need not agree with degrees after
parallel edges have been merged.

## Reproducing the numerical experiments

This section corresponds to the Arctic comparison in the graphical user
interface section, the performance comparison with SoftNet in Section
"Numerical Experiments", and the usability study of the accompanying
manuscript. To reproduce a computation, keep the input network,
centrality definition, parameters, program versions, and vertex indexing
identical. Timings are machine-dependent and are intended for comparison,
not as exact pass/fail outputs.

### A. Arctic network: hybrid method versus Gauss quadrature

**Input.** Use the provided `arctic.json` file (Graphology JSON). The
undirected, unweighted simple graph has 1,715 vertices and 6,228 distinct
edges. 

**Procedure.**

1. Open K-NODES and import `arctic.json`.
2. In the centrality-analysis form, select the index and numerical
   parameters used in the paper's Arctic comparison figure (Fig. 4.4 in the paper).
3. Run the **Hybrid** algorithm and record the ranked vertex keys and
   scores; export the results to CSV or JSON.
4. Without changing the input graph or centrality parameters, switch to
   **Gauss quadrature**, run the computation, and export the results.
5. Compare the rankings and displayed scores, accounting for numerical
   rounding and the selected stopping tolerances. The manuscript reports
   matching rankings and reported scores for these two runs.

**Exact settings to add from the screenshots before submission.** The
LaTeX source references figure files but does not encode their values.
Transcribe the following from the recorded K-NODES run:

| Setting | Value used in Arctic comparison |
| --- | --- |
| Centrality measure | Subgraph Centrality |
| Matrix function (exponential/resolvent) | Exponential |
| Number of highest-ranked vertices | 10 |
| Gauss quadrature tolerance | 1e-9 |
| Spectral/low-rank tolerance and stopping mode | 1e-9 |
| Maximum spectral subspace size / candidate count, if used | 1715 |
| Spectral shift and any remaining nondefault controls | true |


### B. Performance comparison with SoftNet

**Experimental environment used in the manuscript.** The timings were
obtained locally on a MacBook Pro with an Apple M1 processor and 8 GB
RAM. SoftNet was executed in MATLAB R2024b in double precision. The
K-NODES release/build and SoftNet revision must be recorded to permit
precise re-execution.

**Benchmark networks.**

| Network | Vertices | Edges | Source or generation details |
| --- | ---: | ---: | --- |
| `power` | 4,941 | 6,594 | Western United States power grid |
| `collaborations` | 40,421 | 175,692 | Scientific collaboration network |
| `random` | 81,724 | 326,896 | Watts-Strogatz, rewiring probability `0.5` |

**Settings common to all nine method/index combinations.**

- Request the **five highest-ranked vertices** (`m = 5`).
- Use the **matrix exponential**, with **spectral shifting enabled**.
- Use the **default stopping tolerances** of the tested release.
- For **communicability**, use **vertex 1** as the reference vertex.
  Verify that K-NODES and SoftNet refer to the same vertex despite any
  differences in internal indexing.
- Run every method/index/network combination **three times** with each
  application. Report the **median elapsed execution time** in seconds.
- Test three methods: **partial spectral factorization with strong
  convergence**, **hybrid**, and **Gauss quadrature**.
- Test three measures: **subgraph centrality** (`sgcen`),
  **communicability** (`comm`), and **starting convenience** (`stconv`).

**Procedure.** For each benchmark graph, import the same
preprocessed adjacency matrix into K-NODES and SoftNet. Apply the shared
settings above. Run each of the nine method/measure combinations three
times in each program, record individual execution times, and calculate
the median. Compare with Table "Median execution times" in the paper.
Do not include graph creation, UI interaction, or file loading in the
timed interval unless that was also included in the original tests;


The following table reproduces the **reported medians** from the paper;
each entry is `K-NODES / SoftNet` in seconds. These are reference
measurements on the stated machine, not platform-independent numerical
outputs.

| Method | Measure | Power | Collaborations | Random |
| --- | --- | ---: | ---: | ---: |
| Strong convergence | `sgcen` | 0.276 / 12.32 | 1.972 / 6.388 | 6.508 / 1541 |
| Strong convergence | `comm` | 0.277 / 20.52 | 2.043 / 6.942 | 6.038 / 1513 |
| Strong convergence | `stconv` | 0.315 / 14.67 | 2.121 / 7.223 | 6.018 / 1509 |
| Hybrid | `sgcen` | 0.338 / 0.463 | 2.507 / 7.084 | 6.841 / 113.1 |
| Hybrid | `comm` | 0.358 / 0.149 | 2.437 / 7.464 | 8.312 / 85.52 |
| Hybrid | `stconv` | 0.342 / 0.383 | 2.676 / 7.129 | 7.373 / 82.41 |
| Gauss | `sgcen` | 4.019 / 2.493 | 842.3 / 467.5 | 2406 / 729.1 |
| Gauss | `comm` | 8.798 / 3.815 | 1254 / 773.9 | 3952 / 1241 |
| Gauss | `stconv` | 9.079 / 4.111 | 1535 / 691.1 | 4445 / 988.3 |



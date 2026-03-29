import { useComplexNetworkStore } from "@/stores/complexNetwork";
import { useComputationStore } from "@/stores/computationStore";
import router from "@/router";

let computeMeasuresController = null

async function sendFile (uploadedFile) {
    const complexNetworkStore = useComplexNetworkStore()
    let error = ''
    if(!uploadedFile) return;

    const formData = new FormData();
    formData.append('file', uploadedFile);

    try {
      const response = await fetch('/api/', {
      method: 'POST', 
      body: formData
    })

    const payload = await response.json().catch(() => ({}));

    if (response.status === 400) {
      error = payload?.error || payload?.detail || 'request not valid (400).'
      return error
    }

    if (!response.ok) {
      error = payload?.error || payload?.detail || `server error (${response.status}).`
      return error
    }

    const result = payload;
    

    console.log('Upload success: ', result);
    complexNetworkStore.fileName = result["filename"]
    complexNetworkStore.token = result["token"]
    complexNetworkStore.nnodes = result["nodes"]
    complexNetworkStore.edges = result["edges"]
    complexNetworkStore.largestEigenvalue = result["largest eigenvalue"]
    complexNetworkStore.maxAlpha = result["max value for alpha"]
    complexNetworkStore.selfLoops = result["self loops"]
    complexNetworkStore.clusters = result["clusters"]
    
    router.push("/overview");

    } catch (err) {
      error= 'network error, check your Internet connection and retry.'
      console.log(err.message)
    }

    return error
  }


  async function generateRandomNetwork (formData, p) {
    const complexNetworkStore = useComplexNetworkStore()
    let error = ''

    if (formData.model === 'small_world') formData["p"] = p;

    console.log('Random network params:', formData)

    try {
      const response = await fetch('/api/random', {
      method: 'POST', 
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(formData)
    })

    const payload = await response.json().catch(() => ({}));

    if (response.status === 400) {
      error = payload?.error || payload?.detail || 'request not valid (400).'
      return error
    }

    if (!response.ok) {
      error = payload?.error || payload?.detail || `server error (${response.status}).`
      return error
    }

    const result = payload;
    

    console.log('Upload success: ', result);
    complexNetworkStore.fileName = result["filename"]
    complexNetworkStore.token = result["token"]
    complexNetworkStore.nnodes = result["nodes"]
    complexNetworkStore.edges = result["edges"]
    complexNetworkStore.largestEigenvalue = result["largest eigenvalue"]
    complexNetworkStore.maxAlpha = result["max value for alpha"]
    complexNetworkStore.selfLoops = result["self loops"]
    complexNetworkStore.clusters = result["clusters"]
    
    router.push("/overview");

    } catch (err) {
      error= 'network error, check your Internet connection and retry.'
      console.log(err.message)
    }

    return error
  }


  async function computeMeasures(computationData) {
    const complexNetworkStore = useComplexNetworkStore()
    const computationStore = useComputationStore()

    if (computeMeasuresController) {
      computeMeasuresController.abort()
    }
    computeMeasuresController = new AbortController()

    const route = `/api/${computationData["cenIndex"]}${computationData.compMethod}`
    console.log(route)

    let error = ''

    const requestBody = {
      shift: computationData.shift, 
      fun_name: computationData.matFun === 'exponent' ? 'exp' : 'res', 
      nnodes: computationData.numNodes, 
      low_rank_nnodes: computationData.numNodesLR, 
      alpha: computationData.alphaRes, 
      max_iter: computationData.numIterLR, 
      batch_size: computationData.eigenSZ, 
      gauss_tol: computationData.gaussTol, 
      low_rank_tol: computationData.LRTol, 
      i: computationData.nodeComm
    }

    try {
      const response = await fetch(route, {
        method: 'POST', 
        headers: {
          "Content-Type": "application/json", 
          "X-Network-token": complexNetworkStore.token
        },
        body: JSON.stringify(requestBody), 
        signal: computeMeasuresController.signal
      })

      const payload = await response.json().catch(() => ({}));

      if (response.status === 400) {
        error = payload?.error || payload?.detail || 'request not valid (400).'
        return { error, aborted: false }
      }

      if (!response.ok) {
        error = payload?.error || payload?.detail || `server error (${response.status}).`
        return { error, aborted: false }
      }

      const result = payload;

      computationStore.$patch({
        computationData,
        computationResult: result,
      })

      console.log(result)


    } catch (err) {
      if (err?.name === 'AbortError') {
        return { error: '', aborted: true }
      }
      console.log(err)
      error = 'network error, check your Internet connection and retry.'
      return { error, aborted: false }
    } finally {
      computeMeasuresController = null
    }

    return { error, aborted: false }
  }

function cancelComputeMeasures() {
  if (computeMeasuresController) {
    computeMeasuresController.abort()
  }
}

// for basic visualization, only needed when doing the setup for Sigma
async function getEntireNetworkPositions () {

  const complexNetworkStore = useComplexNetworkStore()
  let error = ''

  try {
      const response = await fetch('/api/tiny_network_viz', {
      method: 'POST', 
      headers: {
        "Content-Type": "application/json", 
        "X-Network-token": complexNetworkStore.token
      },
    })

    const payload = await response.json().catch(() => ({}));

    if (response.status === 400) {
      error = payload?.error || payload?.detail || 'request not valid (400).'
      return error
    }

    if (!response.ok) {
      error = payload?.error || payload?.detail || `server error (${response.status}).`
      return error
    }

    const result = payload;
    return result

    } catch (err) {
      error= 'network error, check your Internet connection and retry.'
      console.log(err.message)
    }

}

export {sendFile, generateRandomNetwork, computeMeasures, cancelComputeMeasures, getEntireNetworkPositions}

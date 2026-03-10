import { useComplexNetworkStore } from "@/stores/complexNetwork";
import router from "@/router";

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
export {sendFile, generateRandomNetwork}

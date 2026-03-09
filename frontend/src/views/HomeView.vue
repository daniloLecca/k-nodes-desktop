<script setup>
  import { ref } from 'vue'
  import { useComplexNetworkStore } from '@/stores/complexNetwork'
  import router from '@/router/index'

  const selectedFile = ref(null)
  const error = ref('')

  const complexNetworkStore = useComplexNetworkStore()


  const handleFileUpload = event => {
    selectedFile.value = event.target.files[0]
    error.value = ''
  }

  const uploadFile = async () => {
    if(!selectedFile.value) return;

    const formData = new FormData();
    formData.append('file', selectedFile.value);

    try {
      const response = await fetch('/api/', {
      method: 'POST', 
      body: formData
    })

    const payload = await response.json().catch(() => ({}));

    if (response.status === 400) {
      error.value = payload?.error || payload?.detail || 'request not valid (400).'
      return
    }

    if (!response.ok) {
      error.value = payload?.error || payload?.detail || `server error (${response.status}).`
      return
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
          error.value = 'Errore di rete. Controlla la connessione e riprova.'
          console.log(err.message)
    }

  }
</script>

<template>
  <main>
    <RouterLink to="/"><h1>VIPNODES</h1></RouterLink>
    <input type='file' @change='handleFileUpload' accept=".mat"/>
    <button class="upload-button" @click='uploadFile' v-if="selectedFile">
      <svg class="upload-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 3l-5 5h3v6h4V8h3l-5-5zm-7 13v5h14v-5h-2v3H7v-3H5z" />
      </svg>
      <span>Upload</span>
    </button>
    <p v-if="selectedFile">Selected file: {{ selectedFile.name }}</p>
    <p v-if="error" class="error-message">{{ error }}</p>
  </main>
</template>

<style scoped>
  @import "../assets/base.css";

  

  h1 {
    font-size: 96px;
    font-weight: 600;
  }

  .upload-button {
    background-color: rgb(0, 174, 0);
    border: 0;
    padding: 0.65rem 1.5rem;
    border-radius: 9999px;
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    cursor: pointer;
    transition: transform 0.15s ease, filter 0.2s ease;
  }

  .upload-button span {
    color: var(--vt-c-white-soft);
    font-size: 18px;
    font-weight: 1000;
    font-family: inherit;
  }

  .upload-icon {
    width: 1rem;
    height: 1rem;
    fill: var(--vt-c-white-soft);
  }

  .upload-button:hover {
    filter: brightness(1.07);
    transform: translateY(-1px);
  }

  .upload-button:focus-visible {
    outline: 2px solid #0d7c0d;
    outline-offset: 2px;
  }

  .error-message {
    margin-top: 0.75rem;
    color: #c62828;
    font-weight: 600;
  }
</style>
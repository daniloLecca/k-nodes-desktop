<script setup>
  import { ref, computed } from 'vue'
  import nprogress from 'nprogress'
  import { sendFile, generateRandomNetwork } from '@/utils/apis'
  import InfoSection from '@/components/InfoSection.vue'

  const selectedFile = ref(null)
  const error = ref('')
  const pressedRandomNetworkButton = ref(false)
  const randomNodes = ref(3)
  const randomEdges = ref(2)
  const networkModel = ref('scale_free')
  const rewiringProbability = ref(0.01)
  const vipnodesLogoUrl = new URL('../assets/place-holder-image.png', import.meta.url).href

  const infoSectionsDescriptions = [
    {
      title: "Why VIPNODES?",
      description: "VIPNODES computes the most important nodes of a complex network, therefore the \'VIP\' nodes.", 
      imgURL: (new URL('../assets/place-holder-image.png', import.meta.url).href)
    },
    {
      title: "How do I upload a complex network with VIPNODES?",
      description: "At this very moment, VIPNODES supports only .mat files. The .mat file must contain exactly one variable\
      and is must be a sparse matrix (which represents the adjacency matrix). \nA Column Sparse format is preferable but not mandatory.\
      The complex network must be undirected, therefore the adjacency matrix has to be symmetric. \n\n \
      In addition, you can even generate a random complex network specifying the number of nodes and starting edges. \n \
      Two types of random network generation models are available: \n \
        1. Scale free network: makes use of the Baràbasi-Albert model, which generates the network iteratively adding 1 node each time \
        and wiring it with the others. The wiring probability dependes on the degree of the node which the new added node can be wired to. ", 
      imgURL: (new URL('../assets/place-holder-image.png', import.meta.url).href)
    },
  ]

  const fileInput = ref(null)

  const triggerFileInput = () => {
    fileInput.value.click()
  }

  const handleFileUpload = event => {
    selectedFile.value = event.target.files[0]
    error.value = ''
  }

  const uploadFile = async () => {
    error.value = await sendFile(selectedFile.value)
  }

  const openRandomNetworkPopup = () => {
    pressedRandomNetworkButton.value = true
  }

  const closeRandomNetworkPopup = () => {
    pressedRandomNetworkButton.value = false
  }

  const clampProbability = () => {
    if (rewiringProbability.value > 1) rewiringProbability.value = 0.9999
  }

  const popupValid = computed(() => {
    if (randomNodes.value <= 2) return false
    if (randomEdges.value <= 1) return false
    if (randomNodes.value <= randomEdges.value) return false
    if (networkModel.value === 'small_world' &&
        (rewiringProbability.value <= 0 || rewiringProbability.value > 1)) return false
    return true
  })

  const submitRandomNetworkParams = async () => {

    let formData = {
      nnodes: randomNodes.value,
      k: randomEdges.value,
      model: networkModel.value
    }
    
    nprogress.start()
    error.value = await generateRandomNetwork(formData, rewiringProbability.value)
    nprogress.done()
    closeRandomNetworkPopup()
  }

</script>

<template>
  <main class="home-main">
    <RouterLink to="/"><h1>VIPNODES</h1></RouterLink>
    <h2>VIPNODES is an online tool for computing centrality measures in undirected, unweighted complex networks.</h2>
    <h4>Load a .mat file</h4>
    <input 
      type='file' 
      ref="fileInput" 
      style="display: none" 
      @change='handleFileUpload' 
      accept=".mat"
    />

    <button 
      class="app-button app-button--confirm upload-button" 
      @click="selectedFile ? uploadFile() : triggerFileInput()"
    >
      <svg v-if="!selectedFile" class="button-icon" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 3l-5 5h3v6h4V8h3l-5-5zm-7 13v5h14v-5h-2v3H7v-3H5z" />
      </svg>

      <svg v-if="selectedFile" class="button-icon" viewBox="0 0 24 24" aria-hidden="true"
      stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 2L11 13"></path>
        <path d="M22 2L15 22l-4-9-9-4 20-7z"></path>
      </svg>
      
      <span>{{ selectedFile ? 'Send' : 'Upload' }}</span>
    </button>
    
    <p v-if="selectedFile">
      Selected file: {{ selectedFile.name }}
      <br>
      <a href="#" @click.prevent="selectedFile = null"
       style="font-size: 0.8rem; text-decoration: underline; color: var(--color-tertiary);">
       Change file
      </a>
    </p>

    <h4>or</h4>

    <button class="app-button random-network-button" @click="openRandomNetworkPopup">
      Random network
    </button>

    <p v-if="error" class="error-message">{{ error }}</p>

    <InfoSection
      v-for="item in infoSectionsDescriptions"
      :title=item.title
      :description=item.description
      :imgURL=item.imgURL
      class="info-section"
    ></InfoSection>
  </main>

  <div
    v-if="pressedRandomNetworkButton"
    class="popup-overlay"
    @click="closeRandomNetworkPopup"
  >
    <div class="popup-modal" @click.stop>
      <h2 style="font-size: 22px;">Generate a random network</h2>

      <label for="random-nodes">Number of nodes</label>
      <input
        id="random-nodes"
        v-model.number="randomNodes"
        type="number"
        min="0"
        autofocus
        @keypress.enter="submitRandomNetworkParams"
      />

      <p v-if="randomNodes <= 2" class="input-error">The network must have at least 3 nodes.</p>

      <label for="random-edges">Number of starting edges for each node</label>
      <input
        id="random-edges"
        v-model.number="randomEdges"
        type="number"
        min="0"
        @keypress.enter="submitRandomNetworkParams"
      />
      <p v-if="randomNodes <= randomEdges" class="input-error">Nodes must be greater than edges.</p>
      <p v-if="randomEdges <= 1" class="input-error">The network must have at least 2 edges.</p>

      <p class="radio-group-title">Network model</p>
      <div class="popup-radio-group">
        <label class="radio-option">
          <input v-model="networkModel" type="radio" value="scale_free" />
          <span>Scale free network</span>
        </label>
        <label class="radio-option">
          <input v-model="networkModel" type="radio" value="small_world" />
          <span>Small world network</span>
        </label>
      </div>

      <div v-if="networkModel === 'small_world'">
        <label for="option-probability">Rewiring probability</label>
        <input
          id="option-probability"
          v-model.number="rewiringProbability"
          type="number"
          step="0.01"
          min="0.01"
          max="1"
          @input="clampProbability"
          @keypress.enter="submitRandomNetworkParams"
        />
      </div>

      <div class="popup-actions">
        <button class="app-button app-button--outline--danger" @click="closeRandomNetworkPopup">
          Cancel
        </button>
        <button class="app-button app-button--confirm" @click="submitRandomNetworkParams" :disabled="!popupValid">
          Confirm
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>

  h1 {
    font-size: 96px;
    font-weight: 600;
  }

  h2 {
    width: 80%;
    font-weight: 400;
  }

  h4 {
    font-weight: 200;
  }

  .info-section {
    margin-bottom: 5vh;
  }

  :deep(.info-section article p) {
    text-align: left;
    white-space: pre-line;
  }

  :deep(.info-section img) {
    width: 20%;
  }

  .home-main {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
    align-items: center;
    text-align: center;
    width: 100%;
    margin-top: 20vh;
  }

  .upload-button span {
    font-size: 18px;
    font-weight: 800;
    font-family: inherit;
  }

  .error-message {
    margin-top: 0.75rem;
    color: #c62828;
    font-weight: 600;
  }

  .popup-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 1rem;
  }

  .popup-modal {
    width: min(92vw, 420px);
    background: var(--color-background-soft);
    border: 1px solid var(--color-border);
    border-radius: 1rem;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    padding: 1.2rem;
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
  }

  .popup-modal label {
    font-weight: 500;
  }

  .popup-modal input {
    width: 100%;
    border: 1px solid var(--color-border);
    border-radius: 0.6rem;
    background: var(--color-background);
    color: var(--color-text);
    padding: 0.55rem 0.7rem;
    font-family: inherit;
    font-size: 1rem;
  }

  .radio-group-title {
    font-weight: 500;
    margin-top: 0.2rem;
  }

  .popup-radio-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .radio-option {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 400;
  }

  .radio-option input[type="radio"] {
    width: 1rem;
    height: 1rem;
    accent-color: var(--color-tertiary);
  }

  .input-error {
    color: var(--color-button-danger);
    font-size: 0.85rem;
    font-weight: 500;
    margin-top: -0.3rem;
  }

  .popup-actions {
    margin-top: 0.4rem;
    display: flex;
    justify-content: flex-end;
    gap: 0.6rem;
  }

  .random-network-button {
    margin-bottom: 40vh;
  }

  .app-button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
    pointer-events: none;
  }

  @media (max-width: 768px) {
    h1 {
      font-size: 64px;
    }

    .info-section {
      width: 100%;
    }

    :deep(.info-section article p) {
      text-align: center;
    }

    :deep(.info-section img) {
      width: 100%;
    }
  }


</style>
<script setup>
  import { ref, computed, onMounted, watch } from 'vue'
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
  const theme = ref('')

  nprogress.configure({
            showSpinner: true,
            minimum: 0.08,
            trickleSpeed: 0.05,
            trickleRate: 0.02
        })

  const savedTheme = localStorage.getItem('vipnodes-theme')
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  theme.value = savedTheme || (prefersDark ? 'dark' : 'light')

  // descriptions for info sections
  const infoSectionsDescriptions = computed(() => [
    {
      title: "Why VIPNODES?",
      description: "VIPNODES identifies the most important nodes in a complex network, referred to as 'VIP' nodes. \n\n \
      VIPNODES makes the tool available online, originally developed in MATLAB. Furthermore, this new version introduces \
      various performance optimizations and extends the tool with new features such as network visualization, different export \
      formats and an enhanced statistical visualization. \n\n \
      A desktop version for Windows, Linux and MacOS is available as well. Click the corresponding button for the download. ", 
      imgURL: "./vipnodes-logo.png"
    },
    {
      title: "How do I upload a complex network with VIPNODES?",
      description: "Currently, VIPNODES supports only .mat, .gexf or .json files. The .mat file must contain exactly one variable\
      and it must be a sparse matrix representing the adjacency matrix. The json must follow the Graphology format. \
      The adjacency matrix must be symmetric as the network is undirected. \n\n \
      Alternatively, you can generate a synthetic complex network. \n \
      Three models for random network generation are available: \n \
        1. Scale free network: using Barabási-Albert model, generate the network adding one node at a time and connecting it \
         to the existing ones. The connection probability depends on the degree of the already existing nodes. \n \
        2. Small world network: using the Watts-Strogatz model, generate a lattice with the initial nodes and edges and rewire \
        edges with a certain probability. \n \
        3. Random network: using the Erdős-Rényi model, connect each pair of nodes independently with a probability p.", 
      imgURL: `./imgs/random-network-screenshot-${theme.value}.png`
    },
    {
      title: "What can I do with VIPNODES?",
      description: "VIPNODES identifies the most important nodes of a complex network using some of the most relevant and advanced centrality \
      measures in complex network theory, such as the subgraph centrality, the communicability of a certain node with the rest of the \
      network and the starting convenience.\n Other centralities indices are available, such as Katz centrality, PageRank and closeness. \
       \n\nIn addition, VIPNODES offers a wide choice of options and parameters in order to maximize the results \
      and ensure numerical precision. \n\nUnlike other tools, VIPNODES lets you explore the complex network, with a robust overview of \
      the entire network and lets you interact with its structure. For example, by dragging the nodes or visualizing the VIP nodes.", 
      imgURL: `./imgs/vip-nodes-visualization-${theme.value}.png`
    },
    {
      title: "Which computation methods does VIPNODES implement?",
      description: "Various computation methods are introduced in this tool, ensuring flexibility and versatility. \
      For example, you can directly identify the VIP nodes using Gauss quadrature rules for extreme precision or perform a low rank approximation \
      on the complex network for a rapid analysis. \n\n What makes VIPNODES different is the possibility to identify the most important nodes with a \
      unique two-stage approach referred to as the 'hybrid method', which first performs a low rank approximation in order to quickly determine a larger set of \
      VIP nodes and eventually refines the computation with Gauss type quadrature rules on the few remaining nodes.\n\nThe hybrid method combines \
      efficiency and precision and is usually considered a more convenient approach for most applications. ", 
      imgURL: `./imgs/results-screenshot-${theme.value}.png`
    },
  ]);

  // FILE INPUT HANDLING
  const fileInput = ref(null)

  const triggerFileInput = () => {
    fileInput.value.click()
  }

  const handleFileUpload = event => {
    selectedFile.value = event.target.files[0]
    error.value = ''
  }

  const loadingBarNeeded = file => {
    return (file.name.at(-1) === 't' && file.size >= 102400) || // if the file is .mat and at least 100KB
           (file.name.at(-1) === 'n' && file.size >= 6024000) || // if the file is .json and at least 6MB
           (file.name.at(-1) === 'f' && file.size >= 6024000)  // if the file is .gexf and at least 6MB
  }

  const uploadFile = async () => {
    if (loadingBarNeeded(selectedFile.value)) nprogress.start({showSpinner: false})
    error.value = await sendFile(selectedFile.value)
    if (loadingBarNeeded(selectedFile.value)) nprogress.done()
  }

  const openRandomNetworkPopup = () => {
    pressedRandomNetworkButton.value = true
    if (networkModel.value === 'random_model' && (rewiringProbability.value == null || rewiringProbability.value === 0)) {
      rewiringProbability.value = 0.5
    }
  }

  const closeRandomNetworkPopup = () => {
    pressedRandomNetworkButton.value = false
  }

  const clampProbability = () => {
    if (rewiringProbability.value < 0) rewiringProbability.value = 0
    if (rewiringProbability.value > 1) rewiringProbability.value = 1
  }

  const isRandomNetworkValid = () => {
    if (networkModel.value === 'scale_free') {
      if (randomNodes.value < 2 || randomEdges.value < 1) return false
      return randomEdges.value < randomNodes.value
    }

    if (networkModel.value === 'random_model') {
      if (randomNodes.value < 2) return false
      if (rewiringProbability.value == null || rewiringProbability.value === '') return false
      if (rewiringProbability.value === 0) return false
      return rewiringProbability.value > 0 && rewiringProbability.value <= 1
    }

    if (randomNodes.value < 3) return false
    if (randomEdges.value < 2) return false
    if (randomEdges.value >= randomNodes.value) return false
    if (rewiringProbability.value == null || rewiringProbability.value === '') return false
    return rewiringProbability.value >= 0 && rewiringProbability.value <= 1
  }

  const popupValid = computed(() => {
    return isRandomNetworkValid()
  });

  const handleRandomNetworkEnter = () => {
    if (popupValid.value) submitRandomNetworkParams()
  }

  const submitRandomNetworkParams = async () => {
    if (!popupValid.value) return

    let formData = {
      nnodes: randomNodes.value,
      model: networkModel.value
    }

    if (networkModel.value !== 'random_model') {
      formData.k = randomEdges.value
    }

    nprogress.start()
    error.value = await generateRandomNetwork(formData, rewiringProbability.value)
    nprogress.done()
    closeRandomNetworkPopup()
  }

  watch(networkModel, (nv) => {
    if (nv === 'random_model') {
      if (!rewiringProbability || rewiringProbability.value === 0) rewiringProbability.value = 0.5
      if (randomNodes.value < 2) randomNodes.value = 2
    }
  })

</script>

<template>
  <a 
    href="https://github.com/daniloLecca/vipnodes-desktop" 
    target="_blank" 
    rel="noopener noreferrer"
    class="github-badge"
  >
    <span>Download on Github</span>
    <svg class="github-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
    </svg>
  </a>
  <main class="home-main">
    <RouterLink to="/"><h1>VIPNODES</h1></RouterLink>
    <h2>VIPNODES is an online tool for complex network analysis in undirected, unweighted complex networks.</h2>
    <p v-if="error" class="error-message">{{ error }}</p>
    <h4>Load a .mat, .gexf or .json file</h4>
    <input 
      type='file' 
      ref="fileInput" 
      style="display: none" 
      @change='handleFileUpload' 
      accept=".mat, .gexf, .json"
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

      <div>
        <label for="random-nodes">Number of nodes</label>
        <input
          id="random-nodes"
          v-model.number="randomNodes"
          type="number"
          :min="networkModel === 'scale_free' ? 2 : networkModel === 'small_world' ? 3 : 2"
          autofocus
          @keydown.enter.prevent="handleRandomNetworkEnter"
        />

        <p v-if="networkModel === 'scale_free' ? randomNodes < 2 : networkModel === 'small_world' ? randomNodes < 3 : randomNodes < 2" class="input-error">
          {{ networkModel === 'scale_free' ? 'The scale free network must have at least 2 nodes.' : networkModel === 'small_world' ? 'The small world network must have at least 3 nodes.' : 'The random network must have at least 2 nodes.' }}
        </p>
      </div>

      <div v-if="networkModel !== 'random_model'">
        <label for="random-edges">Number of starting edges for each node</label>
        <input
          id="random-edges"
          v-model.number="randomEdges"
          type="number"
          :min="networkModel === 'scale_free' ? 1 : 2"
          @keydown.enter.prevent="handleRandomNetworkEnter"
        />
        <p v-if="randomEdges >= randomNodes" class="input-error">Number of nodes must be greater than the number of edges</p>
        <p v-if="networkModel === 'scale_free' ? randomEdges < 1 : randomEdges < 2" class="input-error">
          {{ networkModel === 'scale_free' ? 'The scale free network must have at least 1 starting edge.' : 'The small world network must have at least 2 edges.' }}
        </p>
      </div>

      <div v-if="networkModel === 'small_world' || networkModel === 'random_model'">
        <label for="option-probability">{{ networkModel === 'small_world' ? 'Rewiring probability' : 'Connection probability' }}</label>
        <input
          id="option-probability"
          v-model.number="rewiringProbability"
          type="number"
          step="0.01"
          min="0"
          max="1"
          @input="clampProbability"
          @keydown.enter.prevent="handleRandomNetworkEnter"
        />
            <p v-if="(networkModel === 'small_world' || networkModel === 'random_model') && (rewiringProbability == null || rewiringProbability === '')" class="input-error">
              {{ networkModel === 'small_world' ? 'Rewiring probability must be provided.' : 'Connection probability must be provided.' }}
            </p>
            <p v-if="networkModel === 'random_model' && rewiringProbability === 0" class="input-error">Connection probability must be greater than 0.</p>
      </div>

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
        <label class="radio-option">
          <input v-model="networkModel" type="radio" value="random_model" />
          <span>Erdős-Rényi binomial model</span>
        </label>
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
    width: 80%;
  }

  :deep(.info-section article p) {
    text-align: left;
    white-space: pre-line;
  }

  :deep(.info-section img) {
    width: 40%;
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
    color: var(--color-error);
    font-weight: 600;
  }

  .popup-overlay {
    position: fixed;
    inset: 0;
    background: var(--color-overlay);
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
    box-shadow: 0 20px 40px var(--color-shadow-lg);
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
    margin: 0.3rem 0;
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

  .github-badge {
    position: absolute;
    top: 2rem;
    left: 0.5rem;
    z-index: 100;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.45rem 0.85rem;
    font-size: 0.85rem;
    font-weight: 600;
    text-decoration: none;
    color: var(--color-text);
    background: var(--color-background-soft);
    border: 1px solid var(--color-border);
    border-radius: 9999px;
    box-shadow: 0 2px 6px var(--color-shadow, rgba(0, 0, 0, 0.08));
    transition: transform 0.2s ease, border-color 0.2s ease, opacity 0.2s ease;
}

.github-badge:hover {
  transform: translateY(-1px);
  border-color: var(--color-tertiary);
  opacity: 0.9;
}

.github-icon {
  width: 1.15rem;
  height: 1.15rem;
  display: block;
}

@media (max-width: 768px) {
  .github-badge {
    top: 1.75rem;
    left: 0.15rem;
    padding: 0.35rem 0.65rem;
    font-size: 0.75rem;
  }

  .github-icon {
    width: 1rem;
    height: 1rem;
  }
}


</style>
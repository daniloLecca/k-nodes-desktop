<script setup>
    import { ref, computed, watch } from 'vue'
    import { useComplexNetworkStore } from '@/stores/complexNetwork';
    import { useComputationStore } from '@/stores/computationStore';
    import { computeMeasures, cancelComputeMeasures } from '@/utils/apis';
    import router from '@/router';
    import nprogress, { trickle } from 'nprogress';

    const TRICKLE_COEFFICIENT = 10 // used for loading bar progress
    const legacyCentralityMeasures = new Set(['sgcen', 'comm', 'stconv'])
    const nodeCountMeasures = new Set(['degree', 'eigenvector', 'betweenness', 'closeness', 'katz', 'pagerank'])
    const katzMeasure = 'katz'
    const pagerankMeasure = 'pagerank'

    const complexNetworkStore = useComplexNetworkStore()
    const computationStore = useComputationStore()

    const computationMethod = ref("hyb")
    const centralityMeasure = ref("sgcen")
    const matrixFunction = ref("exponent")
    const spectrumShift = ref(true)

    const numberOfNodes = ref(1)
    const numberOfIterationsLowRank = ref(complexNetworkStore.nnodes)
    const numberOfNodesLowRank = ref(computationMethod.value === 'hyb' ? 1 : complexNetworkStore.nnodes)

    const nodeCommunicability = ref(1)
    const gaussTolerance = ref(1e-3)
    const lowRankTolerance = ref(1e-3)
    
    const eigenbatchSize = ref(complexNetworkStore.nnodes > 20 ? 20 : complexNetworkStore.nnodes)
    const alphaForResolvent = ref(0.0)
    const katzAlpha = ref(0)
    const katzBeta = ref(1)
    const eigenvectorMaxIter = ref(1000)
    const katzMaxIter = ref(1000)
    const pagerankMaxIter = ref(1000)
    const eigenvectorTol = ref(1e-6)
    const katzTol = ref(1e-6)
    const pagerankTol = ref(1e-6)
    const pagerankAlpha = ref(0.85)

    const isLegacyCentrality = computed(() => legacyCentralityMeasures.has(centralityMeasure.value))
    const showNodeCount = computed(() => nodeCountMeasures.has(centralityMeasure.value))
    const showKatzInputs = computed(() => centralityMeasure.value === katzMeasure)
    const showPagerankInputs = computed(() => centralityMeasure.value === pagerankMeasure)
    const showLegacyMethodInputs = computed(() => isLegacyCentrality.value)

    const error = ref('')
    const isComputing = ref(false)

    watch(
        [computationMethod, () => complexNetworkStore.nnodes],
        ([method, nnodes]) => {
            if (method === 'lr') {
                numberOfNodesLowRank.value = nnodes
            }
        },
        { immediate: true }
    )

    nprogress.configure({
        showSpinner: false,
        minimum: 0.08,
        trickleSpeed: complexNetworkStore.nnodes / TRICKLE_COEFFICIENT, 
        trickleRate: 0.02
    })

    function cancelRequest () {
        cancelComputeMeasures()
        nprogress.done()
    }

    function handleSubmitOnEnter () {
        if (parametersValid.value) {
            submit()
        }
    }
    
    async function submit () {
        if (isComputing.value) return

        const computationData = isLegacyCentrality.value
            ? {
                compMethod: computationMethod.value,
                cenIndex: centralityMeasure.value,
                matFun: matrixFunction.value,
                numNodes: numberOfNodes.value,
                numIterLR: numberOfIterationsLowRank.value,
                numNodesLR: computationMethod.value === 'lr' ? complexNetworkStore.nnodes : numberOfNodesLowRank.value,
                nodeComm: nodeCommunicability.value - 1, // fix because Python arrays are zero based 
                gaussTol: gaussTolerance.value,
                LRTol: lowRankTolerance.value,
                eigenSZ: eigenbatchSize.value,
                shift: spectrumShift.value,
                alphaRes: alphaForResolvent.value
            }
            : {
                cenIndex: centralityMeasure.value,
                numNodes: numberOfNodes.value,
                ...(centralityMeasure.value === 'eigenvector'
                    ? { maxIter: eigenvectorMaxIter.value, tol: eigenvectorTol.value }
                    : {}),
                ...(showKatzInputs.value
                    ? { alpha: katzAlpha.value, beta: katzBeta.value, maxIter: katzMaxIter.value, tol: katzTol.value }
                    : {}),
                ...(showPagerankInputs.value
                    ? { alpha: pagerankAlpha.value, maxIter: pagerankMaxIter.value, tol: pagerankTol.value }
                    : {})
            }

        isComputing.value = true
        error.value = ''
        nprogress.start()
        nprogress.set(0.15)

        const result = await computeMeasures(computationData)

        nprogress.done()
        isComputing.value = false

        if (result.aborted) {
            return
        }

        error.value = result.error

        // if there is no error in the analysis -> display results
        if (error.value === '')
            router.push('/results')
    }

    // make sure that the parameters are valid, otherwise disable the submit button
    const parametersValid = computed(() => {
        if (numberOfNodes.value > complexNetworkStore.nnodes || numberOfNodes.value <= 0) return false
        if (!isLegacyCentrality.value) {
            if (centralityMeasure.value === 'eigenvector') {
                if (eigenvectorMaxIter.value <= 0) return false
                if (eigenvectorTol.value <= 0) return false
            }

            if (showKatzInputs.value) {
                const alpha = Number(katzAlpha.value)
                if (Number.isNaN(alpha) || alpha <= 0 || alpha >= complexNetworkStore.maxAlpha) return false
                if (katzBeta.value <= 0) return false
                if (katzMaxIter.value <= 0) return false
                if (katzTol.value <= 0) return false
            }

            if (showPagerankInputs.value) {
                if (pagerankAlpha.value <= 0 || pagerankAlpha.value >= 1) return false
                if (pagerankMaxIter.value <= 0) return false
                if (pagerankTol.value <= 0) return false
            }

            return true
        }

        if (numberOfIterationsLowRank.value > complexNetworkStore.nnodes || numberOfIterationsLowRank.value <= 0) return false
        if ((numberOfNodesLowRank.value < numberOfNodes.value) && computationMethod.value !== 'gauss' || numberOfNodesLowRank.value <= 0) return false
        if (eigenbatchSize.value > complexNetworkStore.nnodes || eigenbatchSize.value <= 0) return false
        if (nodeCommunicability.value > complexNetworkStore.nnodes || nodeCommunicability.value <= 0) return false
        if (matrixFunction.value === 'resolvent' && 
            (alphaForResolvent.value === 0 ||
             alphaForResolvent.value >= complexNetworkStore.maxAlpha)) return false
        return true
    })

</script>

<template>
    <main>
        <h2>Compute the centrality measures of the complex network. </h2>
        <h4>The network has {{ complexNetworkStore.nnodes }} nodes and {{ complexNetworkStore.edges }} edges. </h4>
        <h3 style="color: var(--color-button-danger);"> {{ error }}</h3>
        <RouterLink 
            style="border: 1px solid var(--color-border); border-radius: 1rem; padding: 1rem;"
            v-if="
                (Array.isArray(computationStore.computationResult?.vip_nodes)
                ? computationStore.computationResult.vip_nodes
                : []).length > 0
                " to="/results" class="app-link-inline">
                <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true" stroke="currentColor">
                    <path d="M12 19l-7-7 7-7"></path>
                </svg>
                Last computation
        </RouterLink>
        <form @submit.prevent="submit()" @keydown.enter.prevent="handleSubmitOnEnter" class="params-form">
            <label for="numberOfNodes">Number of nodes to identify</label>
            <input type="number" v-model="numberOfNodes" step="1" min="1" :max="complexNetworkStore.nnodes" id="numberOfNodes">
            <p v-if="numberOfNodes > complexNetworkStore.nnodes || numberOfNodes <= 0" class="input-error">The number of nodes to identify must be smaller than the number of nodes</p>

            <div id="dropdownMenus">
                <label for="measure">Centrality measure</label>
                <select name="measure" id="measure" v-model="centralityMeasure">
                    <option value="sgcen" selected="selected">Subgraph centrality</option>
                    <option value="comm">Communicability of node <i>i</i></option>
                    <option value="stconv">Starting convenience</option>
                    <option value="degree">Degree centrality (normalized)</option>
                    <option value="eigenvector">Eigenvector centrality</option>
                    <option value="katz">Katz centrality</option>
                    <option value="pagerank">PageRank centrality</option>
                    <option value="betweenness">Betweenness centrality</option>
                    <option value="closeness">Closeness centrality (normalized)</option>
                </select>

                <template v-if="showLegacyMethodInputs">
                    <label for="algorithm">Computation method</label>
                    <select name="algorithm" id="algorithm" v-model="computationMethod">
                        <option value="hyb" selected="selected">Hybrid method</option>
                        <option value="lr">Low rank approximation</option>
                        <option value="gauss">Gauss quadrature</option>
                    </select>
                </template>
            </div>

            <template v-if="isLegacyCentrality">
                <label for="numberOfIterations" v-if="computationMethod !== 'gauss'">Max number of iterations for low-rank</label>
                <input type="number" v-model="numberOfIterationsLowRank" step="1" min="0" id="numberOfIterations" v-if="computationMethod !== 'gauss'">
                <p v-if="numberOfIterationsLowRank > complexNetworkStore.nnodes" class="input-error">Max number of iterations for low rank must be smaller than the number of nodes</p>
                
                <label for="numberNodesLowRank" v-if="computationMethod === 'hyb'">Number of nodes to filter with low rank</label>
                <input type="number" v-model="numberOfNodesLowRank" step="1" min="0" id="numberNodesLowRank" v-if="computationMethod === 'hyb'">
                <p v-if="(numberOfNodesLowRank < numberOfNodes) && computationMethod !== 'gauss'" class="input-error">Number of nodes for low rank must be equal or greater than the number of nodes to identify</p>

                <div id="radioButtons">
                    <legend>Choose the matrix function</legend>
                    <input type="radio" name="matrixFunction" id="exponent" value="exponent" checked v-model="matrixFunction">
                    <label for="exponent">Exponent</label>
                    <input type="radio" name="matrixFunction" id="resolvent" value="resolvent" v-model="matrixFunction">
                    <label for="resolvent">Resolvent</label>
                    <input type="checkbox" name="spectrumShift" id="spectrumShift" checked v-model="spectrumShift">
                    <label for="spectrumShift">Spectrum shift</label>
                </div>

                <label for="nodeCommunicability" v-if="centralityMeasure === 'comm'">Communicability of node i</label>
                <input type="number" v-model="nodeCommunicability" step="1" min="1" id="nodeCommunicability" v-if="centralityMeasure === 'comm'">
                <p v-if="nodeCommunicability > complexNetworkStore.nnodes" class="input-error">The considered node musth be in [1, {{ complexNetworkStore.nnodes }}]</p>

                <label for="gaussTolerance" v-if="computationMethod !== 'lr'">Tolerance for Gauss quadrature</label>
                <input type="number" v-model="gaussTolerance" value="1e-3" step="1e-15" min="0" max="10" id="gaussTolerance" v-if="computationMethod !== 'lr'">

                <label for="lowRankTolerance" v-if="computationMethod !== 'gauss'">Tolerance for low-rank approximation</label>
                <input type="number" v-model="lowRankTolerance" value="1e-3" step="1e-15" min="0" max="10" id="lowRankTolerance" v-if="computationMethod !== 'gauss'">
                
                <label for="eigenbatchSize" v-if="computationMethod !== 'gauss'">Eigenbatch size</label>
                <input type="number" v-model="eigenbatchSize" step="1" min="0" id="eigenbatchSize" v-if="computationMethod !== 'gauss'">
                <p v-if="eigenbatchSize > complexNetworkStore.nnodes" class="input-error">Eigenbatch size must be smaller than the number of nodes</p>

                <label for="alphaForResolvent" v-if="matrixFunction === 'resolvent'">Alpha for resolvent must be in (0, {{ complexNetworkStore.maxAlpha }})</label>
                <input
                    v-if="matrixFunction === 'resolvent'"
                    type="number"
                    v-model="alphaForResolvent"
                    value="0.0"
                    step="1e-3"
                    min="0"
                    id="alphaForResolvent"
                >
                <p v-if="matrixFunction === 'resolvent' && (alphaForResolvent >= complexNetworkStore.maxAlpha || alphaForResolvent <= 0)" class="input-error">Alpha must be in the interval specified above</p>
            </template>

            <template v-else>
                <template v-if="showKatzInputs">
                    <label for="katzAlpha">Alpha for Katz centrality must be in (0, {{ complexNetworkStore.maxAlpha }})</label>
                    <input
                        type="number"
                        v-model="katzAlpha"
                        step="1e-3"
                        min="0"
                        :max="complexNetworkStore.maxAlpha"
                        id="katzAlpha"
                    >
                    <p v-if="katzAlpha <= 0 || katzAlpha >= complexNetworkStore.maxAlpha" class="input-error">Alpha must be in the interval specified above</p>

                    <label for="katzBeta">Beta for Katz centrality</label>
                    <input
                        type="number"
                        v-model="katzBeta"
                        step="1e-3"
                        min="0"
                        id="katzBeta"
                    >
                    <p v-if="katzBeta <= 0" class="input-error">Beta must be greater than 0</p>

                    <label for="katzMaxIter">Max number of iterations for Katz centrality</label>
                    <input type="number" v-model="katzMaxIter" step="1" min="1" id="katzMaxIter">
                    <p v-if="katzMaxIter <= 0" class="input-error">Max iterations must be greater than 0</p>

                    <label for="katzTol">Tolerance for Katz centrality</label>
                    <input type="number" v-model="katzTol" step="1e-6" min="0" id="katzTol">
                    <p v-if="katzTol <= 0" class="input-error">Tolerance must be greater than 0</p>
                </template>

                <template v-if="centralityMeasure === 'eigenvector'">
                    <label for="eigenvectorMaxIter">Max number of iterations for eigenvector centrality</label>
                    <input type="number" v-model="eigenvectorMaxIter" step="1" min="1" id="eigenvectorMaxIter">
                    <p v-if="eigenvectorMaxIter <= 0" class="input-error">Max iterations must be greater than 0</p>

                    <label for="eigenvectorTol">Tolerance for eigenvector centrality</label>
                    <input type="number" v-model="eigenvectorTol" step="1e-6" min="0" id="eigenvectorTol">
                    <p v-if="eigenvectorTol <= 0" class="input-error">Tolerance must be greater than 0</p>
                </template>

                <template v-if="showPagerankInputs">
                    <label for="pagerankAlpha">Alpha for PageRank must be in (0, 1)</label>
                    <input
                        type="number"
                        v-model="pagerankAlpha"
                        step="1e-3"
                        min="0"
                        max="1"
                        id="pagerankAlpha"
                    >
                    <p v-if="pagerankAlpha <= 0 || pagerankAlpha >= 1" class="input-error">Alpha must be in the interval specified above</p>

                    <label for="pagerankMaxIter">Max number of iterations for PageRank</label>
                    <input type="number" v-model="pagerankMaxIter" step="1" min="1" id="pagerankMaxIter">
                    <p v-if="pagerankMaxIter <= 0" class="input-error">Max iterations must be greater than 0</p>

                    <label for="pagerankTol">Tolerance for PageRank</label>
                    <input type="number" v-model="pagerankTol" step="1e-6" min="0" id="pagerankTol">
                    <p v-if="pagerankTol <= 0" class="input-error">Tolerance must be greater than 0</p>
                </template>
            </template>
            
            <button type="submit" :disabled="!parametersValid">Compute</button>

        </form>

            <div v-if="isComputing" class="popup-overlay">
                <div class="popup-modal" id="popup-modal" role="dialog" aria-modal="true" aria-labelledby="compute-loading-title">
                    <h3 id="compute-loading-title">Computation in progress</h3>
                    <p>Please wait while the server computes your measures.</p>

                    <div class="popup-actions">
                        <button class="app-button app-button--outline--danger" type="button" @click="cancelRequest">
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
    </main>
</template>

<style scoped>

    main {
        width: 100%;
        margin-top: 5vh;
        margin-bottom: 5vh;
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    h2 {
        font-weight: 400;
        text-align: center;
    }

    h4 {
        text-align: center;
    }

    .params-form {
        width: min(70vw, 700px);
        background: var(--color-background-soft);
        border: 1px solid var(--color-border);
        border-radius: 1rem;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        padding: 1.2rem;
        display: flex;
        flex-direction: column;
        gap: 0.7rem;
        margin-top: 3.5vh;
        text-align: left;
    }

    .params-form input, .params-form select {
        width: 100%;
        border: 1px solid var(--color-border);
        border-radius: 0.6rem;
        background: var(--color-background);
        color: var(--color-text);
        padding: 0.55rem 0.7rem;
        font-family: inherit;
        font-size: 1rem;
    }

    #dropdownMenus {
        display: flex;
        flex-direction: row;
        gap: 1.5rem;
        margin: 1rem 0;
    }

    #radioButtons {
        display: flex;
        flex-direction: row;
        flex-wrap: wrap;
        align-items: center;
        column-gap: 0.8rem;
        row-gap: 0.6rem;
    }

    #radioButtons legend {
        width: 100%;
        margin-bottom: 0.2rem;
    }

    #radioButtons input {
        width: min-content;
        align-self: center;
        width: 1rem;
        height: 1rem;
        accent-color: var(--color-tertiary);
    }

    #radioButtons input[type="checkbox"] {
        margin-left: 0;
        width: 1.2rem;
        height: 1.2rem;
    }

    @media (max-width: 900px) {
        .params-form {
            width: 100%;
            max-width: 700px;
        }

        #radioButtons {
            display: grid;
            grid-template-columns: auto 1fr;
            align-items: center;
            column-gap: 0.65rem;
            row-gap: 0.45rem;
        }

        #radioButtons legend {
            grid-column: 1 / -1;
            margin-bottom: 0.35rem;
        }

        #radioButtons input[type="checkbox"] {
            margin-top: 0.45rem;
        }

        #radioButtons label[for="spectrumShift"] {
            margin-top: 0.45rem;
        }

        #dropdownMenus {
            flex-direction: column;
            gap: 0.7rem;
        }
    }

    button {
        width: min-content;
        align-self: center;
    }

    button:disabled {
        opacity: 0.4;
        cursor: not-allowed;
        pointer-events: none;
    }

    .app-link-inline {
        margin-top: 3rem;
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
        width: min(92vw, 440px);
        background: var(--color-background-soft);
        border: 1px solid var(--color-border);
        border-radius: 1rem;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        padding: 1.2rem;
        display: flex;
        flex-direction: column;
        gap: 0.7rem;
    }

    .popup-modal h3 {
        font-weight: 600;
    }

    .popup-actions {
        margin-top: 0.2rem;
        display: flex;
        justify-content: flex-end;
    }

    .input-error {
        color: var(--color-button-danger);
        font-size: 0.85rem;
        font-weight: 500;
        margin-top: -0.3rem;
    }


</style>
<script setup>
    import { ref } from 'vue'
    import { useComplexNetworkStore } from '@/stores/complexNetwork';
    import { useComputationStore } from '@/stores/computationStore';

    const complexNetworkStore = useComplexNetworkStore()
    const computationStore = useComputationStore()

    const computationMethod = ref("hybrid")
    const centralityMeasure = ref("sgcen")
    const matrixFunction = ref("exponent")

</script>

<template>
    <main>
        <h2>Compute the centrality measures of the complex network. </h2>
        <h4>The network has {{ complexNetworkStore.nnodes }} nodes and {{ complexNetworkStore.edges }} edges. </h4>
        <form @submit.prevent="submit" class="params-form">
            <label for="numberOfNodes">Number of nodes to identify</label>
            <input type="number" value="1" step="1" min="1" :max="complexNetworkStore.nnodes" id="numberOfNodes">

            <label for="numberOfIterations">Max number of iterations for low-rank</label>
            <input type="number" value="100" step="1" min="1" :max="complexNetworkStore.nnodes" id="numberOfIterations">
            
            <div id="radioButtons">
                <legend>Choose the matrix function</legend>
                <input type="radio" name="matrixFunction" id="exponent" value="exponent" checked>
                <label for="exponent">Exponent</label>
                <input type="radio" name="matrixFunction" id="resolvent" value="resolvent">
                <label for="resolvent">Resolvent</label>
                <input type="checkbox" name="spectrumShift" id="spectrumShift" checked="">
                <label for="spectrumShift">Spectrum shift</label>
            </div>

            <div id="dropdownMenus">
                <label for="algorithm">Computation method</label>
                <select name="algorithm" id="algorithm">
                    <option value="hybrid" selected="selected">Hybrid method</option>
                    <option value="lr">Low rank approximation</option>
                    <option value="gauss">Gauss quadrature</option>
                </select>

                <label for="measure">Centrality measure</label>
                <select name="measure" id="measure">
                    <option value="sgcen" selected="selected">Subgraph centrality</option>
                    <option value="comm">Communicability of node <i>i</i></option>
                    <option value="stconv">Starting convenience</option>
                </select>
            </div>

            <label for="nodeCommunicability">Communicability of node i</label>
            <input type="number" value="1" step="1" min="1" :max="complexNetworkStore.nnodes" id="nodeCommunicability">

            <label for="gaussTolerance">Tolerance for Gauss quadrature</label>
            <input type="number" value="1e-3" step="1e-15" min="1e-15" max="10" id="gaussTolerance">

            <label for="lowRankTolerance">Tolerance for low-rank approximation</label>
            <input type="number" value="1e-3" step="1e-15" min="1e-15" max="10" id="lowRankTolerance">
            
            <label for="eigenbatchSize">Eigenbatch size</label>
            <input type="number" value="20" step="1" min="1" :max="complexNetworkStore.nnodes" id="eigenbatchSize">

            <label for="alphaForResolvent">Alpha for resolvent must be in (0, {{ complexNetworkStore.maxAlpha }})</label>
            <input type="number" value="0" step="1e-3" min="1e-3" :max="complexNetworkStore.maxAlpha - 1e-3" id="alphaForResolvent">
            
            <button>Compute</button>
            <!-- to add matrix function, spectrum shift toggle 
                 gauss tolerance, low-rank tolerance, eigenbatch, alpha-->

            <!-- to add layout option for: 
                 1. overview/analysis toggle must go under the title if device is mobile
                 2. comp. method/cen. measure inputs must be stacked if device is mobile-->
        </form>
    </main>
</template>

<style scoped>

    main {
        width: 100%;
        margin-top: 5vh;
        margin-bottom: 5vh;
    }

    h2 {
        font-weight: 400;
    }

    .params-form {
        width: 50vw;
        background: var(--color-background-soft);
        border: 1px solid var(--color-border);
        border-radius: 1rem;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        padding: 1.2rem;
        display: flex;
        flex-direction: column;
        gap: 0.7rem;
        margin-top: 3.5vh;
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
        gap: 1.5rem;
    }

    #radioButtons input {
        width: min-content;
        align-self: center;
        width: 1rem;
        height: 1rem;
        accent-color: var(--color-tertiary);
    }

    #radioButtons input[type="checkbox"] {
        margin-left: 10rem;
        width: 1.2rem;
        height: 1.2rem;
    }

    button {
        width: min-content;
        align-self: center;
    }



</style>
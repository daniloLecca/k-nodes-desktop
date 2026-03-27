<script setup>
    import { ref } from 'vue';
    import { useComputationStore } from '@/stores/computationStore';
    import InfoSection from '@/components/InfoSection.vue';
    import html2pdf from 'html2pdf.js';

    const computationStore = useComputationStore()
    const lowRankConvergence = ref('')
    const additionalNodes = ref(0)
    const zoomedSection = ref(null)

    if (computationStore.computationData.compMethod === 'lr') {
        if (computationStore.computationResult.vip_nodes.length === computationStore.computationData.numNodes) {
            lowRankConvergence.value = "Strong convergence"
        } else if (computationStore.computationResult.vip_nodes.length > computationStore.computationData.numNodes + 100) {
            lowRankConvergence.value = "No convergence"
        } else {
            lowRankConvergence.value = "Weak convergence"
            additionalNodes.value = computationStore.computationResult.vip_nodes.length - computationStore.computationData.numNodes
        }
    } else {
        if (computationStore.computationResult.convergence_lowrank === 'no convergence') {
            lowRankConvergence.value = "No convergence"
        } else if (computationStore.computationResult.convergence_lowrank === 'weak convergence') {
            lowRankConvergence.value = "Weak convergence"
            additionalNodes.value = computationStore.computationResult.vip_lowrank.length - computationStore.computationData.numNodesLR
        } else {
            lowRankConvergence.value = "Strong convergence"
        }
    }

    console.log(lowRankConvergence.value)

    function processComputationDataLabels (d) {
        console.log(d)
        let updatedD = {
            "Computation method": d.compMethod === 'gauss' ? 'Gauss quadrature' : (d.compMethod === 'hyb' ? 'Hybrid method' : 'Low rank approximation'), 
            "Centrality measure": d.cenIndex === 'comm' ? 'Communicability' : (d.cenIndex === 'sgcen' ? 'Subgraph centrality' : 'Starting convenience'), 
            "Matrix function": d.matFun === 'exponent' ? 'Exponential' : 'Resolvent', 
            'Spectrum shift': d.shift ? 'True' : 'False', 
            'Number of nodes seeked': d.numNodes,
            'Number of nodes seeked via low rank approximation': d.numNodesLR, 
            'Max number of iterations for low rank approximation': d.numIterLR, 
            'Tolerance for low rank approximation': d.LRTol, 
            'Tolerance for Gauss quadrature': d.gaussTol, 
            'Eigenbatch size': d.eigenSZ
        }

        if (d.cenIndex === 'comm') {
            updatedD["Communicability with node"] = d.nodeComm + 1
        }

        if (d.matFun === 'resolvent') {
            updatedD["Alpha for resolvent"] = d.alphaRes
        }

        return updatedD
    }

    const pdfResults = () => {
        const element = document.getElementsByClassName("container")[0]
        console.log(element)
        const options = {
            filename: 'results.pdf',
            image: {type: 'jpeg', quality: 0.98},
            jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        }

        html2pdf().set(options).from(element).save();
    }

    function toggleSectionZoom(sectionId) {
        zoomedSection.value = zoomedSection.value === sectionId ? null : sectionId
    }

</script>

<template>
    <div class="container">
        <header>
        <h2 v-if="computationStore.computationData.compMethod !== 'gauss'">
            {{ lowRankConvergence }} test was satisfied for low rank
            <p v-if="lowRankConvergence === 'Weak convergence'">
                {{ additionalNodes }} additional nodes have been added. <br>
            </p>
        </h2>
        <h2 v-else>The VIP nodes have been identified successfully!</h2>
        <h3 v-if="computationStore.computationData.compMethod === 'hyb'"> Number of nodes seeked via low rank approximation: {{ computationStore.computationData.numNodesLR }}</h3>   
        <h3 v-if="computationStore.computationData.compMethod === 'hyb'"> Number of nodes identified via low rank approximation: {{ computationStore.computationResult.vip_lowrank.length }}</h3>   
        <h3>Total number of VIP nodes identified: {{ computationStore.computationResult.vip_nodes.length }}</h3>
        <h3>Elapsed time: {{ computationStore.computationResult.elapsed_time }}s</h3>
        <h3 v-if="computationStore.computationData.compMethod !== 'gauss'">Number of used eigenpairs: {{ computationStore.computationResult.used_eigenpairs }}</h3>
        <h3 v-if="computationStore.computationData.compMethod === 'gauss'">Mean of matrix vector products:
             {{ (computationStore.computationResult["matrix vector products"].reduce((sum, num) => sum + num, 0)) / computationStore.computationResult["matrix vector products"].length}}
        </h3>
        <section>
            <h3>Computation parameters: </h3>
            <ul>
                <li v-for="key in Object.keys(processComputationDataLabels(computationStore.computationData))">{{ key }}: {{ (processComputationDataLabels(computationStore.computationData))[key] }}</li>
            </ul>
        </section>
    </header>
    <h2>The following nodes have been identified:</h2>
    <main>
        <div class="results-table-column">
            <h4>VIP nodes: </h4>
            <ul>
                <li v-for="node in computationStore.computationResult.vip_nodes"> Node: {{ node + 1 }} </li>
            </ul>
        </div>

        <div class="results-table-column">
            <h4>VIP scores: </h4>
            <ul>
                <li v-for="score in computationStore.computationResult.vip_scores"> Score: {{ score }} </li>
            </ul>
        </div>

    </main>
    <InfoSection
        class="info-section"
        :class="{ 'info-section--zoomed': zoomedSection === 'scatterplot' }"
        :title="'Scatterplot of the adjacency matrix'"
        :description="'Each blue dot represent an edge'"
        :viz="'scatterplot'"
        :interaction-scale="zoomedSection === 'scatterplot' ? 2 : 1"
        @click="toggleSectionZoom('scatterplot')"
    ></InfoSection>
    <template v-if="computationStore.computationData.compMethod !== 'gauss'">
        <InfoSection
            class="info-section"
            :class="{ 'info-section--zoomed': zoomedSection === 'eigenvalues' }"
            :title="'Used eigenvalues'"
            :description="'Only used eigenvalues are represented'"
            :viz="'eigenvalues'"
            :interaction-scale="zoomedSection === 'eigenvalues' ? 2 : 1"
            @click="toggleSectionZoom('eigenvalues')"
        ></InfoSection>
        <InfoSection
            class="info-section"
            :class="{ 'info-section--zoomed': zoomedSection === 'boundsHistory' }"
            :title="'History of low rank bounds'"
            :description="'All the bounds estimated throughout the computation'"
            :viz="'boundsHistory'"
            :interaction-scale="zoomedSection === 'boundsHistory' ? 2 : 1"
            @click="toggleSectionZoom('boundsHistory')"
        ></InfoSection>
    </template>
    <button @click="pdfResults()" style="margin-top: 10vh;">Download PDF</button>
    </div>
    <footer style="width: max-content; height: 30vh;"></footer>
    

    <!-- maybe show candidates history only with d3 plot -->
</template>

<style scoped>

    .container {
        width: min(70vw, 700px);
        margin: 0 auto;
        align-items: center;
        justify-content: center;
        display: flex;
        flex-direction: column;
    }

    header {
        margin: 5vh 0;
        width: 100%;
    }

    section {
        border: 1px solid var(--color-border);
        border-radius: 1rem;
        margin: 1vh 0;
        padding: 1.2rem;
        margin-top: 5vh;
    }

    h2 {
        margin-top: 5vh;
        margin-bottom: 2vh;
    }

    main {
        margin-top: 5vh;
        display: flex;
        flex-direction: row;
        gap: 4rem;
        justify-content: center;
        background: var(--color-background-soft);
        border: 1px solid var(--color-border);
        border-radius: 1rem;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        width: 100%;
        padding: 0.6rem;
        overflow: hidden;
    }

    .results-table-column {
        text-align: center;
        justify-content: center;
        align-items: center;
        text-align: left;
    }

    .results-table-column h4 {
        text-align: center;
    }

    .info-section {
        width: 100%;
        align-self: flex-start;
        margin-top: 5vh;
        cursor: zoom-in;
        transform-origin: center;
        transition: transform 180ms ease;
    }

    .info-section--zoomed {
        transform: scale(2);
        cursor: zoom-out;
        z-index: 2;
    }

    @media (max-width: 900px) {
        main {
            flex-direction: column;
            gap: 1em;
        }
        
    }

</style>
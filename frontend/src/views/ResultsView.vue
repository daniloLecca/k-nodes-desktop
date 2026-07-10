<script setup>
    import { ref, computed, nextTick } from 'vue';
    import { useComputationStore } from '@/stores/computationStore';
    import { useComplexNetworkStore } from '@/stores/complexNetwork';
    import InfoSection from '@/components/InfoSection.vue';
    import { jsPDF } from "jspdf";
    import html2pdf from 'html2pdf.js';
    import nprogress, { trickle } from 'nprogress';

    const computationStore = useComputationStore()
    const complexNetworkStore = useComplexNetworkStore()
    const lowRankConvergence = ref('')
    const additionalNodes = ref(0)
    const zoomedSection = ref(null)
    const exportOption = ref('pdf')
    const exportImgCB = ref(false) // export images in pdf?
    // if not array -> empty array 
    const vipNodes = computed(() => Array.isArray(computationStore.computationResult?.vip_nodes)
        ? computationStore.computationResult.vip_nodes
        : [])
    const vipScores = computed(() => Array.isArray(computationStore.computationResult?.vip_scores)
        ? computationStore.computationResult.vip_scores
        : [])
    const vipLowrank = computed(() => Array.isArray(computationStore.computationResult?.vip_lowrank)
        ? computationStore.computationResult.vip_lowrank
        : [])
    const matrixVectorProducts = computed(() => {
        if (Array.isArray(computationStore.computationResult?.["matrix vector products"])) {
            return computationStore.computationResult["matrix vector products"]
        }

        if (Array.isArray(computationStore.computationResult?.matrix_vector_products)) {
            return computationStore.computationResult.matrix_vector_products
        }

        return []
    })

    // infer convergence 
    if (computationStore.computationData.compMethod === 'lr') {
        if (vipNodes.value.length === computationStore.computationData.numNodes) {
            lowRankConvergence.value = "Strong convergence"
        } else if (vipNodes.value.length > computationStore.computationData.numNodes + 100) {
            lowRankConvergence.value = "No convergence"
        } else {
            lowRankConvergence.value = "Weak convergence"
            additionalNodes.value = vipNodes.value.length - computationStore.computationData.numNodes
        }
    } else {
        if (computationStore.computationResult.convergence_lowrank === 'no convergence') {
            lowRankConvergence.value = "No convergence"
        } else if (computationStore.computationResult.convergence_lowrank === 'weak convergence') {
            lowRankConvergence.value = "Weak convergence"
            additionalNodes.value = vipLowrank.value.length - computationStore.computationData.numNodesLR
        } else {
            lowRankConvergence.value = "Strong convergence"
        }
    }

    // improvement of labels from computation parameters labels
    function processComputationDataLabels (d) {
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

    async function appendInfoSectionsToPdf(doc, startY) {
        await nextTick()

        const margin = 10
        const pageWidth = doc.internal.pageSize.getWidth()
        const pageHeight = doc.internal.pageSize.getHeight()
        const printableWidth = pageWidth - (margin * 2)
        let y = startY

        const infoSectionBlocks = Array.from(document.querySelectorAll('.info-section'))
        if (infoSectionBlocks.length === 0) {
            return y
        }

        if (y > pageHeight - 20) {
            doc.addPage()
            y = margin
        }

        doc.setFontSize(11)

        for (const block of infoSectionBlocks) {
            const canvas = await html2pdf()
                .set({
                    html2canvas: {
                        scale: 2,
                        backgroundColor: '#ffffff',
                        useCORS: true
                    }
                })
                .from(block)
                .toCanvas()
                .get('canvas')

            if (!canvas) {
                continue
            }

            const imageData = canvas.toDataURL('image/png')
            const imageHeight = (canvas.height * printableWidth) / canvas.width

            if (y + imageHeight > pageHeight - margin) {
                doc.addPage()
                y = margin
            }

            doc.addImage(imageData, 'PNG', margin, y, printableWidth, imageHeight, undefined, 'FAST')
            y += imageHeight + 6
        }

        return y
    }

    async function pdfResults() {
        // Default export is a4 paper, portrait, using millimeters for units
        const doc = new jsPDF();
        let x = 10;
        let y = 3;
        const downShift = () => x += 10;

        doc.text("Computation results for the complex network " + (complexNetworkStore.fileName || ''), y, downShift());
        doc.text(`Nodes: ${complexNetworkStore.nnodes}, edges: ${complexNetworkStore.edges}, self loops: ${complexNetworkStore.selfLoops}.`, y, downShift())

        if (computationStore.computationData.compMethod !== 'gauss') {
            doc.text(`${lowRankConvergence.value} test was satisfied for low rank.`, y, downShift())
            if (lowRankConvergence.value === 'Weak convergence') {
                doc.text(`${additionalNodes.value} additional nodes have been added.`, y, downShift())
            }
        }

        doc.text("The VIP nodes have been identified successfully!", y, downShift())

        if (computationStore.computationData.compMethod === 'hyb') {
            doc.text(`Number of nodes sought via low rank approximation: ${computationStore.computationData.numNodesLR}`, y, downShift())
            doc.text(`Number of nodes identified via low rank approximation: ${vipLowrank.value.length}`, y, downShift())
        }

        doc.text(`Total number of VIP nodes identified: ${vipNodes.value.length}`, y, downShift())
        doc.text(`Elapsed time: ${computationStore.computationResult.elapsed_time}s`, y, downShift())

        if (computationStore.computationData.compMethod !== 'gauss') {
            doc.text(`Number of used eigenpairs: ${computationStore.computationResult.used_eigenpairs}`, y, downShift())
        } else {
            doc.text(`Mean of matrix vector products: ${matrixVectorProducts.value.length > 0 ? (matrixVectorProducts.value.reduce((sum, num) => sum + num, 0)) / matrixVectorProducts.value.length : 0}`, y, downShift())
        }

        Object.keys(processComputationDataLabels(computationStore.computationData)).forEach(key => {
            doc.text(`${key}: ${(processComputationDataLabels(computationStore.computationData))[key]}`, y, downShift())
        })
        
        doc.addPage()
        x = 10
        doc.text("The following nodes have been identified: ", y, downShift())

        for (let i = 0; i < vipNodes.value.length; i++) {
            const vipNode = (vipNodes.value)[i]
            const vipScore = (vipScores.value)[i]
            doc.text(`Node: ${vipNode + 1}, score: ${vipScore}`, y, downShift())
            if (x === 260) { // after this point there is no more space in the page
                doc.addPage()
                x = 10
            }
        }

        if (exportImgCB.value) await appendInfoSectionsToPdf(doc, x + 10)

        doc.save("results.pdf");
    }

    function saveTextFile(content, fileName, mimeType) {
        const blob = new Blob([content], { type: mimeType })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = fileName
        link.click()
        URL.revokeObjectURL(url)
    }

    function jsonResults() {
        const toOneBasedNodes = (nodes) => Array.isArray(nodes)
            ? nodes.map((node) => typeof node === 'number' ? node + 1 : node)
            : []

        const normalizedComputationResult = {
            ...computationStore.computationResult,
            vip_nodes: toOneBasedNodes(computationStore.computationResult?.vip_nodes),
            vip_lowrank: toOneBasedNodes(computationStore.computationResult?.vip_lowrank),
            candidates_history: Array.isArray(computationStore.computationResult?.candidates_history)
                ? computationStore.computationResult.candidates_history.map((entry) => ({
                    ...entry,
                    candidate_nodes: toOneBasedNodes(entry?.candidate_nodes)
                }))
                : computationStore.computationResult?.candidates_history
        }

        const payload = {
            fileName: complexNetworkStore.fileName || '',
            network: {
                nodes: complexNetworkStore.nnodes,
                edges: complexNetworkStore.edges,
                selfLoops: complexNetworkStore.selfLoops
            },
            computationData: computationStore.computationData,
            computationResult: normalizedComputationResult,
            vipNodes: toOneBasedNodes(vipNodes.value),
            vipScores: vipScores.value,
            vipLowrank: toOneBasedNodes(vipLowrank.value)
        }

        saveTextFile(JSON.stringify(payload, null, 2), 'results.json', 'application/json;charset=utf-8')
    }

    function csvResults() {
        const rows = [['Node', 'Score']]

        for (let i = 0; i < vipNodes.value.length; i += 1) {
            const node = vipNodes.value[i] + 1
            const score = vipScores.value[i] ?? ''
            rows.push([node, score])
        }

        const csvContent = rows.map(row => row.join(',')).join('\n')
        saveTextFile(csvContent, 'results.csv', 'text/csv;charset=utf-8')
    }

    async function exportResultsFile() {
        nprogress.configure({
            showSpinner: true,
            minimum: 0.08,
            trickleSpeed: 200, 
            trickleRate: 1
        })
        switch (exportOption.value) {
            case 'pdf':
                nprogress.start()
                await pdfResults()
                nprogress.done()
                break
            case 'csv':
                csvResults()
                break
            case 'json':
                jsonResults()
                break
            default:
                await pdfResults()
                break
        }
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
        <h3 v-if="computationStore.computationData.compMethod === 'hyb'"> Number of nodes sought via low rank approximation: {{ computationStore.computationData.numNodesLR }}</h3>   
        <h3 v-if="computationStore.computationData.compMethod === 'hyb'"> Number of nodes identified via low rank approximation: {{ vipLowrank.length }}</h3>   
        <h3>Total number of VIP nodes identified: {{ vipNodes.length }}</h3>
        <h3>Elapsed time: {{ computationStore.computationResult.elapsed_time }}s</h3>
        <h3 v-if="computationStore.computationData.compMethod !== 'gauss'">Number of eigenpairs used: {{ computationStore.computationResult.used_eigenpairs }}</h3>
        <h3 v-if="computationStore.computationData.compMethod === 'gauss'">Mean of matrix vector products:
               {{ matrixVectorProducts.length > 0 ? (matrixVectorProducts.reduce((sum, num) => sum + num, 0)) / matrixVectorProducts.length : 0 }}
        </h3>
        <section>
            <h3>Computation parameters: </h3>
            <ul>
                <li v-for="key in Object.keys(processComputationDataLabels(computationStore.computationData))">{{ key }}: {{ (processComputationDataLabels(computationStore.computationData))[key] }}</li>
            </ul>
        </section>
        <section class="export-results">
            <h3>Export results</h3>
            <div class="export-results-dropdown">
                <label for="export-formats">Select a format to export the results: </label>
                <select name="export-formats" id="export-formats" v-model="exportOption">
                    <option value="pdf">PDF</option>
                    <option value="csv">CSV</option>
                    <option value="json">JSON</option>
                </select>
            </div>
            <div v-if="exportOption === 'pdf'" class="export-img-cb">
                <input type="checkbox" name="img-pdf" id="img-pdf" v-model="exportImgCB">
                <label for="img-pdf">Include images</label>
            </div>
            <button @click="exportResultsFile()">Download {{ exportOption.toUpperCase() }}</button>
        </section>
    </header>
    <h2>The following nodes have been identified:</h2>
    <main>
        <div class="results-table-column">
            <h4>VIP nodes: </h4>
            <ul>
                <li v-for="node in vipNodes"> Node: {{ node + 1 }} </li>
            </ul>
        </div>

        <div class="results-table-column">
            <h4>VIP scores: </h4>
            <ul>
                <li v-for="score in vipScores"> Score: {{ score }} </li>
            </ul>
        </div>

    </main>
    <InfoSection
        class="info-section"
        :class="{ 'info-section--zoomed': zoomedSection === 'scatterplot' }"
        :title="'Sparsity pattern of the adjacency matrix'"
        :description="'Each blue dot represents an edge of the complex network. \n\n\n\n\nClick to zoom the entire section. '"
        :viz="'scatterplot'"
        :interaction-scale="zoomedSection === 'scatterplot' ? 2 : 1"
        @click="toggleSectionZoom('scatterplot')"
    ></InfoSection>
    <template v-if="computationStore.computationData.compMethod !== 'gauss'">
        <InfoSection
            class="info-section"
            :class="{ 'info-section--zoomed': zoomedSection === 'eigenvalues' }"
            :title="'Used eigenvalues'"
            :description="'Only the eigenvalues used in the computation are shown. For each iteration \
            an eigenvalue is used (x-axis) and corresponding value is plotted in the y-axis. \
            \nHover on the plot to more detailed information. \n\n\n\nClick to zoom the entire section'"
            :viz="'eigenvalues'"
            :interaction-scale="zoomedSection === 'eigenvalues' ? 2 : 1"
            @click="toggleSectionZoom('eigenvalues')"
        ></InfoSection>
        <InfoSection
            class="info-section"
            :class="{ 'info-section--zoomed': zoomedSection === 'boundsHistory' }"
            :title="'History of low rank bounds'"
            :description="'All the bounds estimated throughout the computation. For each node, the lower bound (LB) \
            and upper bound (UB) estimate of the \'score\' throughout each iteration (x-axis) is plotted. \nIf a node is no longer \
            eligible as a VIP node its bounds are no longer displayed. \n\nClick to zoom and hover to interact. '"
            :viz="'boundsHistory'"
            :interaction-scale="zoomedSection === 'boundsHistory' ? 2 : 1"
            @click="toggleSectionZoom('boundsHistory')"
        ></InfoSection>
    </template>

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

    .export-results {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    .export-results-dropdown {
        display: flex;
        flex-direction: row;
        width: 100%;
        margin: 3vh 0;
    }

    .export-results-dropdown select {
        width: 90%;
        border: 1px solid var(--color-border);
        border-radius: 0.6rem;
        background: var(--color-background);
        color: var(--color-text);
        padding: 0.55rem 0.7rem;
        font-family: inherit;
        font-size: 1rem;
    }

    .export-img-cb {
        margin-bottom: 3vh;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .export-img-cb input[type="checkbox"] {
        margin-left: 0;
        width: 1.2rem;
        height: 1.2rem;
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

    :deep(.info-section article p) {
        text-align: left;
        white-space: pre-line;
    }

    @media (max-width: 900px) {
        main {
            flex-direction: column;
            gap: 1em;
        }

        .export-results-dropdown {
            flex-direction: column;
            gap: 3vh;
        }

        .export-results-dropdown select {
            height: 5vh;
        }
        
    }

</style>
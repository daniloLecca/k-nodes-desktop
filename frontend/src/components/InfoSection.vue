<script setup>
    import { ref, onMounted, onBeforeUnmount } from "vue"
    import * as d3 from "d3"
    import { useComplexNetworkStore } from '@/stores/complexNetwork';
    import { useComputationStore } from '@/stores/computationStore';

    const complexNetworkStore = useComplexNetworkStore()
    const computationStore = useComputationStore()

    const props = defineProps({
        title: String,
        description: String, 
        viz: String,
        interactionScale: {
            type: Number,
            default: 1
        }, 
        imgURL: String
    })

    const imageUrl = ref(null)
    const chartContainer = ref(null)
    let resizeObserver = null 

    const usedEigenValues = []
    const bounds = []
    const requiresCandidatesHistory = props.viz === 'eigenvalues' || props.viz === 'boundsHistory'
    const candidatesHistory = computationStore.computationResult?.candidates_history
    
    // bounds is an array like [{"i": 1, "lowerBounds": [0, 1, 2], "upperBounds": [3, 4, 5]}]
    if (requiresCandidatesHistory && candidatesHistory && typeof candidatesHistory === 'object') {
        for (const [key, value] of Object.entries(candidatesHistory)) {
            const iter = parseInt(key) + 1;
            usedEigenValues.push({"i": iter, "eig": value.eigenvalue})
            bounds.push({
                "i": iter,
                "candidateNodes": value.candidate_nodes,
                "lowerBounds": value.lower_bounds,
                "upperBounds": value.upper_bounds
            })
        }
    }

    // loads the scatterplot of the adjacency matrix
    async function loadPlot() {
        const API_BASE = 'http://127.0.0.1:8123'; // <-- Aggiunto per Electron
        
        try {
            const res = await fetch(`${API_BASE}/api/plot`, {
                method: "POST", 
                headers: {
                    "X-Network-token": complexNetworkStore.token
                }
            })

            if (res.ok) {
                const blob = await res.blob()
                imageUrl.value = URL.createObjectURL(blob)
            } else {
                console.error("error API plot")
            }
        } catch (err) {
            console.error("error connecting to /api/plot", err)
        }
    }

    async function loadLineChartEigenvalues() {
        if (!chartContainer.value) {
            return
        }

        const measuredWidth = Math.round(chartContainer.value.getBoundingClientRect().width)
        const outerWidth = measuredWidth > 0 ? measuredWidth : 260
        const outerHeight = outerWidth

        const margin = { top: 12, right: 12, bottom: 28, left: 42 }
        const width = Math.max(10, outerWidth - margin.left - margin.right)
        const height = Math.max( outerHeight - margin.top - margin.bottom)

        const container = d3.select(chartContainer.value)
        container.selectAll("*").remove()

        const svgElement = container
            .append("svg")
            .attr("width", outerWidth)
            .attr("height", outerHeight)
            .attr("viewBox", `0 0 ${outerWidth} ${outerHeight}`);

        // Make the full SVG area interactive for pan/zoom gestures.
        svgElement.append("rect")
            .attr("width", outerWidth)
            .attr("height", outerHeight)
            .attr("fill", "transparent");

        const svg = svgElement
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);

        const plotLayer = svg.append("g");
        let currentTransform = d3.zoomIdentity;

        const x = d3.scaleLinear()
            .domain([0, usedEigenValues.length + 1])
            .nice()
            .range([0, width])


        const y = d3.scaleLinear()
            .domain([0, complexNetworkStore.largestEigenvalue])
            .nice()
            .range([height, 0])

        plotLayer.append("g")
            .attr("transform", `translate(0,${height})`)
            .call(d3.axisBottom(x))

        plotLayer.append("g")
            .call(d3.axisLeft(y))

        const points = usedEigenValues.map(d => [x(d.i), y(d.eig), d.i, d.eig]);

        const circles = plotLayer.selectAll("circle")
            .data(usedEigenValues)
            .enter()
            .append("circle")
            .attr("cx", d => x(d.i))
            .attr("cy", d => y(d.eig))
            .attr("r", 2)
            .attr("fill", "none")
            .attr("stroke", "steelblue") 
            .attr("stroke-width", 0.75);  

        const dot = plotLayer.append("g")
            .attr("display", "none");

        dot.append("circle")
            .attr("stroke", "red")
            .attr("fill", "red")
            .attr("r", 2.5);

        dot.append("text")
            .attr("text-anchor", "middle")
            .attr("fill", "currentColor")
            .attr("y", -8);

        const BASE_POINT_RADIUS = 2;
        const ACTIVE_POINT_RADIUS = 3.5;
        const BASE_HIT_RADIUS = 18;

        function pointerInPlotCoordinates(event) {
            const scale = Math.max(1, props.interactionScale || 1);
            const rect = chartContainer.value.getBoundingClientRect();
            const localX = (event.clientX - rect.left) / scale;
            const localY = (event.clientY - rect.top) / scale;
            return [localX - margin.left, localY - margin.top];
        }

        function formatEigenTooltip(iteration, eigenvalue) {
            const xLabel = Number.isFinite(iteration) ? Number(iteration).toFixed(2) : "-";
            const yLabel = Number.isFinite(eigenvalue) ? Number(eigenvalue).toExponential(3) : "-";
            return `EV ${Math.round(iteration)} (${xLabel}; ${yLabel})`;
        }

        function syncTooltipScale() {
            const zoomK = Math.max(1, currentTransform.k);
            dot.select("circle").attr("r", 2.5 / Math.sqrt(zoomK));
            dot.select("text")
                .attr("y", -8 / Math.sqrt(zoomK))
                .style("font-size", `${Math.max(8, 12 / Math.sqrt(zoomK))}px`);
        }

        function highlightPoint(activeIteration = null) {
            circles
                .attr("r", d => (activeIteration !== null && d.i === activeIteration ? ACTIVE_POINT_RADIUS : BASE_POINT_RADIUS))
                .attr("stroke-width", d => (activeIteration !== null && d.i === activeIteration ? 1.5 : 0.75));
        }

        syncTooltipScale();
        highlightPoint();

        svgElement.call(d3.zoom()
            .extent([[0, 0], [outerWidth, outerHeight]])
            .scaleExtent([1, 8])
            .on("zoom", ({ transform }) => {
                currentTransform = transform;
                plotLayer.attr("transform", transform);
                syncTooltipScale();
            }));

        svgElement
            .on("pointerenter", () => {
                dot.attr("display", null);
            })
            .on("pointermove", pointermoved)
            .on("pointerleave", pointerleft)
            .on("touchstart", event => event.preventDefault());

        function pointermoved(event) {
            const [xm, ym] = pointerInPlotCoordinates(event);
            const [zx, zy] = currentTransform.invert([xm, ym]);
            const hitRadius = BASE_HIT_RADIUS /
                (Math.sqrt(Math.max(currentTransform.k, 1)) * Math.max(1, props.interactionScale || 1));

            const i = d3.leastIndex(points, ([px, py]) => Math.hypot(px - zx, py - zy));
            if (i === -1) return;

            const [px, py, iteration, eigenvalue] = points[i];
            const distance = Math.hypot(px - zx, py - zy);

            if (distance > hitRadius) {
                pointerleft();
                return;
            }

            highlightPoint(iteration);
            dot.attr("display", null);
            dot.attr("transform", `translate(${px},${py})`);
            dot.select("text").text(formatEigenTooltip(iteration, eigenvalue));
        }

        function pointerleft() {
            highlightPoint();
            dot.attr("display", "none");
        }
    }

    async function loadMultipleLineChartBoundsHistory() {
        if (!chartContainer.value) {
            return
        }

        const measuredWidth = Math.round(chartContainer.value.getBoundingClientRect().width)
        const outerWidth = measuredWidth > 0 ? measuredWidth : 260
        const outerHeight = outerWidth

        const margin = { top: 20, right: 20, bottom: 30, left: 40 }
        const width = Math.max(10, outerWidth - margin.left - margin.right)
        const height = Math.max(outerHeight - margin.top - margin.bottom)

        const container = d3.select(chartContainer.value)
        container.selectAll("*").remove()

        const rawData = []
        bounds.forEach(d => {
            const candidateNodes = Array.isArray(d.candidateNodes) ? d.candidateNodes : []
            const lbArray = Array.isArray(d.lowerBounds) ? d.lowerBounds : [d.lowerBounds]
            const ubArray = Array.isArray(d.upperBounds) ? d.upperBounds : [d.upperBounds]

            lbArray.forEach((val, idx) => {
                if (val !== undefined && val !== null) {
                    const candidateNode = Number(candidateNodes[idx])
                    const node = Number.isFinite(candidateNode) ? candidateNode : idx + 1
                    rawData.push({
                        x: d.i,
                        y: val,
                        kind: 'LB',
                        node,
                        seriesKey: `LB ${node}`
                    })
                }
            })
            ubArray.forEach((val, idx) => {
                if (val !== undefined && val !== null) {
                    const candidateNode = Number(candidateNodes[idx])
                    const node = Number.isFinite(candidateNode) ? candidateNode : idx + 1
                    rawData.push({
                        x: d.i,
                        y: val,
                        kind: 'UB',
                        node,
                        seriesKey: `UB ${node}`
                    })
                }
            })
        })

        if (rawData.length === 0) return

        const svgElement = container
            .append("svg")
            .attr("width", outerWidth)
            .attr("height", outerHeight)
            .attr("viewBox", `0 0 ${outerWidth} ${outerHeight}`)
            .attr("style", "max-width: 100%; height: auto; overflow: visible; font: 10px sans-serif;")

        svgElement.append("rect")
            .attr("width", outerWidth)
            .attr("height", outerHeight)
            .attr("fill", "transparent")

        const svg = svgElement
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`)

        const plotLayer = svg.append("g")
        let currentTransform = d3.zoomIdentity

        const x = d3.scaleLinear()
            .domain(d3.extent(rawData, d => d.x)).nice()
            .range([0, width])

        const y = d3.scaleLinear()
            .domain(d3.extent(rawData, d => d.y)).nice()
            .range([height, 0])

        plotLayer.append("g")
            .attr("transform", `translate(0,${height})`)
            .call(d3.axisBottom(x).ticks(width / 80).tickSizeOuter(0))

        plotLayer.append("g")
            .call(d3.axisLeft(y))
            .call(g => g.select(".domain").remove())
            .call(g => g.selectAll(".tick line").clone()
                .attr("x2", width)
                .attr("stroke-opacity", 0.1))
            .call(g => g.append("text")
                .attr("x", -margin.left)
                .attr("y", -10)
                .attr("fill", "currentColor")
                .attr("text-anchor", "start")
                .text("↑ Score"))

        const points = rawData.map(d => [x(d.x), y(d.y), d.seriesKey])
        const groups = d3.rollup(points, v => Object.assign(v, { z: v[0][2] }), d => d[2])
        const seriesList = Array.from(groups.values()).map(series => {
            const sorted = [...series].sort((a, b) => a[0] - b[0])
            sorted.z = series.z
            return sorted
        })

        const getLineColor = seriesName => {
            return String(seriesName).startsWith("LB")
                ? "var(--color-tertiary, #5cb0cf)"
                : "steelblue"
        }

        const line = d3.line()
        const path = plotLayer.append("g")
            .attr("fill", "none")
            .attr("stroke-width", 1.5)
            .attr("stroke-linejoin", "round")
            .attr("stroke-linecap", "round")
            .attr("stroke-opacity", 0.2)
            .selectAll("path")
            .data(seriesList)
            .join("path")
            .attr("stroke", d => getLineColor(d.z))
            .attr("d", line)
            .attr("vector-effect", "non-scaling-stroke")

        const dot = plotLayer.append("g")
            .attr("display", "none")

        dot.append("circle")
            .attr("stroke", "red")
            .attr("fill", "red")
            .attr("r", 2.5)

        dot.append("text")
            .attr("text-anchor", "middle")
            .attr("fill", "currentColor")
            .attr("y", -8)

        const BASE_STROKE_WIDTH = 1.5
        const BASE_HIT_RADIUS = 20

        function pointerInPlotCoordinates(event) {
            const scale = Math.max(1, props.interactionScale || 1)
            const rect = chartContainer.value.getBoundingClientRect()
            const localX = (event.clientX - rect.left) / scale
            const localY = (event.clientY - rect.top) / scale
            return [localX - margin.left, localY - margin.top]
        }

        function projectPointToSegment(px, py, ax, ay, bx, by) {
            const abx = bx - ax
            const aby = by - ay
            const abLenSq = (abx * abx) + (aby * aby)

            if (abLenSq === 0) {
                return { x: ax, y: ay, distSq: (px - ax) ** 2 + (py - ay) ** 2 }
            }

            const t = Math.max(0, Math.min(1, (((px - ax) * abx) + ((py - ay) * aby)) / abLenSq))
            const xProj = ax + (t * abx)
            const yProj = ay + (t * aby)
            return { x: xProj, y: yProj, distSq: (px - xProj) ** 2 + (py - yProj) ** 2 }
        }

        function findNearestSeriesPoint(cursorX, cursorY) {
            let best = null

            for (const series of seriesList) {
                if (!series || series.length === 0) continue

                if (series.length === 1) {
                    const [sx, sy] = series[0]
                    const distSq = (cursorX - sx) ** 2 + (cursorY - sy) ** 2
                    if (!best || distSq < best.distSq) {
                        best = { seriesName: series.z, x: sx, y: sy, distSq }
                    }
                    continue
                }

                for (let j = 0; j < series.length - 1; j += 1) {
                    const [ax, ay] = series[j]
                    const [bx, by] = series[j + 1]
                    const projected = projectPointToSegment(cursorX, cursorY, ax, ay, bx, by)

                    if (!best || projected.distSq < best.distSq) {
                        best = {
                            seriesName: series.z,
                            x: projected.x,
                            y: projected.y,
                            distSq: projected.distSq
                        }
                    }
                }
            }

            return best
        }

        function formatTooltip(seriesName, plotX, plotY) {
            const iteration = x.invert(plotX)
            const score = y.invert(plotY)
            const [boundKind = '', node = '?'] = String(seriesName).split(' ')
            const xLabel = Number.isFinite(iteration) ? iteration.toFixed(2) : '-'
            const yLabel = Number.isFinite(score) ? score.toExponential(3) : '-'
            return `${boundKind} ${parseInt(node) + 1} (${parseInt(xLabel)}; ${yLabel})`
        }

        function applyLineEmphasis(activeSeries = null) {
            const zoomK = Math.max(1, currentTransform.k)
            const fadedOpacity = 0.08
            const defaultOpacity = 0.2
            const activeOpacity = 1
            const defaultWidth = BASE_STROKE_WIDTH
            const activeWidth = Math.min(4.5, BASE_STROKE_WIDTH + Math.log2(zoomK + 1))

            path
                .attr("stroke-opacity", d => {
                    if (!activeSeries) return defaultOpacity
                    return d.z === activeSeries ? activeOpacity : fadedOpacity
                })
                .attr("stroke-width", d => {
                    if (!activeSeries) return defaultWidth
                    return d.z === activeSeries ? activeWidth : defaultWidth
                })

            if (activeSeries) {
                path.filter(d => d.z === activeSeries).raise()
            }
        }

        function syncTooltipScale() {
            const zoomK = Math.max(1, currentTransform.k)
            dot.select("circle").attr("r", 2.5 / Math.sqrt(zoomK))
            dot.select("text")
                .attr("y", -8 / Math.sqrt(zoomK))
                .style("font-size", `${Math.max(8, 12 / Math.sqrt(zoomK))}px`)
        }

        applyLineEmphasis()
        syncTooltipScale()

        svgElement.call(d3.zoom()
            .extent([[0, 0], [outerWidth, outerHeight]])
            .scaleExtent([1, 8])
            .on("zoom", ({ transform }) => {
                currentTransform = transform
                plotLayer.attr("transform", transform)
                syncTooltipScale()
            }))

        svgElement
            .on("pointerenter", pointerentered)
            .on("pointermove", pointermoved)
            .on("pointerleave", pointerleft)
            .on("touchstart", event => event.preventDefault())

        function pointermoved(event) {
            const [xm, ym] = pointerInPlotCoordinates(event)
            const [zx, zy] = currentTransform.invert([xm, ym])
            const hitRadius = BASE_HIT_RADIUS /
                (Math.sqrt(Math.max(currentTransform.k, 1)) * Math.max(1, props.interactionScale || 1))

            const nearest = findNearestSeriesPoint(zx, zy)
            if (!nearest) return

            const distance = Math.sqrt(nearest.distSq)
            if (distance > hitRadius) {
                pointerleft()
                return
            }

            applyLineEmphasis(nearest.seriesName)
            dot.attr("display", null)
            dot.attr("transform", `translate(${nearest.x},${nearest.y})`)
            dot.select("text").text(formatTooltip(nearest.seriesName, nearest.x, nearest.y))
        }

        function pointerentered() {
            dot.attr("display", null)
        }

        function pointerleft() {
            applyLineEmphasis()
            dot.attr("display", "none")
        }
    }

    function stopParentClickWhenZoomed(event) {
        if ((props.interactionScale || 1) > 1) {
            event.stopPropagation()
        }
    }

    onMounted(() => {
        if(props.viz === 'scatterplot') {
            loadPlot()
        } else if (props.viz === 'eigenvalues'){
            loadLineChartEigenvalues()

            if (chartContainer.value) {
                resizeObserver = new ResizeObserver(() => {
                    loadLineChartEigenvalues()
                })

                resizeObserver.observe(chartContainer.value)
            }

        } else if (props.viz === 'boundsHistory') {
            loadMultipleLineChartBoundsHistory()

            if (chartContainer.value) {
                resizeObserver = new ResizeObserver(() => {
                    clearTimeout(resizeTimeout);
                    resizeTimeout = setTimeout(() => {
                        loadMultipleLineChartBoundsHistory();
                    }, 250);
                })
                resizeObserver.observe(chartContainer.value)
            }
        }   
    })

    onBeforeUnmount(() => {
        if (resizeObserver) {
            resizeObserver.disconnect()
            resizeObserver = null
        }
    })
</script>
<template>
    <main>
        <img
            v-if="props.viz === 'scatterplot' && imageUrl"
            :src="imageUrl"
            class="media-box"
            @click.stop="stopParentClickWhenZoomed"
            @pointerdown.stop="stopParentClickWhenZoomed"
            @pointerup.stop="stopParentClickWhenZoomed"
        />
        <div
            v-else-if="props.viz === 'eigenvalues' || props.viz === 'boundsHistory'"
            ref="chartContainer"
            class="media-box chart-box"
            @click.stop="stopParentClickWhenZoomed"
            @pointerdown.stop="stopParentClickWhenZoomed"
            @pointerup.stop="stopParentClickWhenZoomed"
        ></div>
        <img
            v-else-if="props.imgURL"
            :src="props.imgURL"
            class="media-box"
            alt="Info section image"
            @click.stop="stopParentClickWhenZoomed"
            @pointerdown.stop="stopParentClickWhenZoomed"
            @pointerup.stop="stopParentClickWhenZoomed"
        />
        <article>
            <h3>{{ title }}</h3>
            <p>{{ description }}</p>
        </article>
    </main>
</template>

<style scoped>
    
    main {
        background: var(--color-background-soft);
        border: 1px solid var(--color-border);
        border-radius: 1rem;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        width: 100%;
        display: flex;
        justify-content: flex-start;
        align-items: flex-start;
        gap: 0.75rem;
        margin: 0;
        padding: 0.6rem;
        overflow: hidden;
    }

    article {
        flex: 1 1 auto;
        min-width: 0;
        padding: 0 0 0 1rem;
        margin: 0;
        background-color: var(--color-background-soft);
    }

    .media-box {
        display: block;
        flex: 0 0 auto;
        margin: 0;
        width: clamp(240px, 20vw, 300px);
        max-width: 100%;
        cursor: default;
        overflow: hidden;
    }

    img {
        border-radius: 1rem;
        height: auto;
        width: 100%;
    }

    .chart-box {
        aspect-ratio: 1 / 1;
        border: 1px solid var(--color-border);
        border-radius: 1rem;
    }

    @media (max-width: 768px) {
        main {
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        article {
            width: 100%;
            padding: 0;
            text-align: center;
        }

        img {
            margin: 0 auto;
        }
    }
</style>
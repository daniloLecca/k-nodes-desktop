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
        viz: String
    })

    const imageUrl = ref(null)
    const chartContainer = ref(null)
    let resizeObserver = null 

    const usedEigenValues = []
    const bounds = []
    
    // bounds is an array like [{"i": 1, "lowerBounds": [0, 1, 2], "upperBounds": [3, 4, 5]}]
    if (props.viz !== 'scatterplot') {
        for (const [key, value] of Object.entries(computationStore.computationResult.candidates_history)) {
            const iter = parseInt(key) + 1;
            usedEigenValues.push({"i": iter, "eig": value.eigenvalue})
            bounds.push({"i": iter, "lowerBounds": value.lower_bounds, "upperBounds": value.upper_bounds})
        }

        console.log(bounds)
    }

    async function loadPlot() {
        const res = await fetch("/api/plot", {
            method: "POST", 
            headers: {
                "X-Network-token": complexNetworkStore.token
            }
        })

        const blob = await res.blob()
        imageUrl.value = URL.createObjectURL(blob)
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

        const x = d3.scaleLinear()
            .domain([0, usedEigenValues.length])
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

        plotLayer.selectAll("circle")
            .data(usedEigenValues)
            .enter()
            .append("circle")
            .attr("cx", d => x(d.i))
            .attr("cy", d => y(d.eig))
            .attr("r", 2)
            .attr("fill", "none")
            .attr("stroke", "steelblue") 
            .attr("stroke-width", 0.75);  

        svgElement.call(d3.zoom()
            .extent([[0, 0], [outerWidth, outerHeight]])
            .scaleExtent([1, 8])
            .on("zoom", ({ transform }) => {
                plotLayer.attr("transform", transform);
            }));
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
        const height = Math.max( outerHeight - margin.top - margin.bottom)

        const container = d3.select(chartContainer.value)
        container.selectAll("*").remove()

        // transform the bounds array to get an array of "points", where each point is represented by: 
        // x (which node), y (the bound), z (upper bound or lower bound)
        const rawData = [];
        bounds.forEach(d => {
            // ensuring that the array of bounds is an array (i.e. forcing 1.42342 to [1.42342])
            const lbArray = Array.isArray(d.lowerBounds) ? d.lowerBounds : [d.lowerBounds];
            const ubArray = Array.isArray(d.upperBounds) ? d.upperBounds : [d.upperBounds];

            lbArray.forEach((val, idx) => {
                if (val !== undefined && val !== null) {
                    rawData.push({ x: d.i, y: val, z: lbArray.length > 1 ? `Lower Bound ${idx+1}` : 'Lower Bound' });
                }
            });
            ubArray.forEach((val, idx) => {
                if (val !== undefined && val !== null) {
                    rawData.push({ x: d.i, y: val, z: ubArray.length > 1 ? `Upper Bound ${idx+1}` : 'Upper Bound' });
                }
            });
        });

        if (rawData.length === 0) return;


        const svgElement = container
            .append("svg")
            .attr("width", outerWidth)
            .attr("height", outerHeight)
            .attr("viewBox", `0 0 ${outerWidth} ${outerHeight}`)
            .attr("style", "max-width: 100%; height: auto; overflow: visible; font: 10px sans-serif;");

        // rectangle to "catch" the pointer
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
            .domain(d3.extent(rawData, d => d.x))
            .range([0, width]);

        const y = d3.scaleLinear()
            .domain(d3.extent(rawData, d => d.y)).nice()
            .range([height, 0]);

        
        plotLayer.append("g")
            .attr("transform", `translate(0,${height})`)
            .call(d3.axisBottom(x).ticks(width / 80).tickSizeOuter(0));

        
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
                .text("↑ Score"));

        svgElement.call(d3.zoom()
            .extent([[0, 0], [outerWidth, outerHeight]])
            .scaleExtent([1, 8])
            .on("zoom", ({ transform }) => {
                currentTransform = transform;
                plotLayer.attr("transform", transform);
            }));

        // determine the corresponding position in the axis
        const points = rawData.map((d) => [x(d.x), y(d.y), d.z]);
        // each point is mapped with a "group"
        const groups = d3.rollup(points, v => Object.assign(v, {z: v[0][2]}), d => d[2]);

        // color of the path depending on the theme (light or dark)
        const getLineColor = (seriesName) => {
            return seriesName.includes("Lower") 
                ? "var(--color-tertiary, #5cb0cf)" 
                : "steelblue";
        };

        const line = d3.line();
        const path = plotLayer.append("g")
            .attr("fill", "none")
            .attr("stroke-width", 1.5)
            .attr("stroke-linejoin", "round")
            .attr("stroke-linecap", "round")
            .attr("stroke-opacity", 0.2) 
            .selectAll("path")
            .data(groups.values())
            .join("path")
            .attr("stroke", d => getLineColor(d.z)) 
            .attr("d", line);

        
        // "dot" is the tooltip
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

        svgElement
            .on("pointerenter", pointerentered)
            .on("pointermove", pointermoved)
            .on("pointerleave", pointerleft)
            .on("touchstart", event => event.preventDefault());

        function pointermoved(event) {
            const [xm, ym] = d3.pointer(event, svg.node());
            const [zx, zy] = currentTransform.invert([xm, ym]);
            const i = d3.leastIndex(points, ([px, py]) => Math.hypot(px - zx, py - zy));
            if (i === -1) return;
            
            const [px, py, k] = points[i];
            const [tx, ty] = currentTransform.apply([px, py]);
            
            // handling opacity during hover:
            // each path but the underlined one has 20% opacity, the underlined one has 100%
            path.attr("stroke-opacity", d => d.z === k ? 1 : 0.2)
                .filter(d => d.z === k).raise();
            
            dot.attr("transform", `translate(${tx},${ty})`);
            dot.select("text").text(k);
        }

        function pointerentered() {
            // makes sure that opacity is handled individually
            dot.attr("display", null);
        }

        function pointerleft() {
            // when mouse leaves, default opacity is assigned
            path.attr("stroke-opacity", 0.2)
                .style("mix-blend-mode", null); 
            dot.attr("display", "none");
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
        <img v-if="props.viz === 'scatterplot' && imageUrl" :src="imageUrl" class="media-box" />
        <div v-else-if="props.viz === 'eigenvalues' || props.viz === 'boundsHistory'" ref="chartContainer" class="media-box chart-box"></div>
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
    }

    .media-box {
        display: block;
        flex: 0 0 auto;
        margin: 0;
        width: clamp(240px, 20vw, 300px);
        max-width: 100%;
    }

    img {
        border-radius: 1rem;
        height: auto;
        width: 100%;
    }

    .chart-box {
        aspect-ratio: 1 / 1;
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
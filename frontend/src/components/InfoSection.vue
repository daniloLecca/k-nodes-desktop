<script setup>
    import { ref, onMounted } from "vue"
    import { useComplexNetworkStore } from '@/stores/complexNetwork';
    import { useComputationStore } from '@/stores/computationStore';

    const complexNetworkStore = useComplexNetworkStore()
    const computationStore = useComputationStore()

    const props = defineProps({
        title: String,
        description: String, 
        viz: String
    })

    console.log(props)

    const imageUrl = ref(null)

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

    onMounted(() => {
        if(props.viz === 'scatterplot') {
            loadPlot()
        }
    })
</script>
<template>
    <main>
        <img v-if="imageUrl" :src="imageUrl" />
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

    img {
        display: block;
        flex: 0 0 auto;
        margin: 0;
        width: clamp(140px, 15vw, 260px);
        border-radius: 1rem;
        height: auto;
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
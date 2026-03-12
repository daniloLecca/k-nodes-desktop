<script setup>
    import { useComputationStore } from '@/stores/computationStore';

    const computationStore = useComputationStore()
</script>

<template>
    <main>
        <h4>VIP nodes: </h4>
        <ul>
            <li v-for="node in computationStore.vipNodes"> Node: {{ node }} </li>
        </ul>

        <br>

        <h4>VIP scores: </h4>
        <ul>
            <li v-for="score in computationStore.vipScores"> Score: {{ score }} </li>
        </ul>
    </main>
</template>

<style scoped>

    main {
        margin-top: 5vh;
        display: flex;
        flex-direction: row;
        gap: 4rem;
    }

    @media (max-width: 900px) {
        main {
            flex-direction: column;
            gap: 1em;
        }
        
    }

</style>
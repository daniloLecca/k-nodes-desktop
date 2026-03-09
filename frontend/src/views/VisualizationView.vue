<script setup>
    import { useComplexNetworkStore } from '@/stores/complexNetwork';

    const complexNetworkStore = useComplexNetworkStore()
    
</script>

<template>
    <RouterLink to="/"><h1>VIPNODES</h1></RouterLink>
    <h2>{{ complexNetworkStore.fileName }}</h2>
    <p>The network has {{ complexNetworkStore.nnodes }} nodes and {{ complexNetworkStore.edges }} edges. </p>
    <p v-if="complexNetworkStore.selfLoops !== 0">
        The network has {{ complexNetworkStore.selfLoops }} self loop(s). Self loops have been removed.
    </p>
</template>

<style scoped>
    h1 {
    font-size: 56px;
    font-weight: 500;
  }
</style>
<script setup>
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute();
</script>

<template>
  <div class="container">
    <header v-if="route.path === '/overview' || route.path === '/analysis'" class="top-nav">
      
      <div class="nav-left">
        <RouterLink to="/"><h1 class="logo">VIPNODES</h1></RouterLink>
      </div>

      <div class="nav-center">
        <div class="toggle-container">
          <RouterLink to="/overview" class="toggle-tab" active-class="active">Overview</RouterLink>
          <RouterLink to="/analysis" class="toggle-tab" active-class="active">Analysis</RouterLink>
        </div>
      </div>

      <div class="nav-right"></div>
    
    </header>

    <main>
      <RouterView />
    </main>
  </div>
</template>

<style>

.logo {
    font-size: 56px;
    font-weight: 500;
  }

.container {
  width: 100%;
}
/* Stili per l'Header e il Toggle */
.top-nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 1rem;
  background-color: var(--color-background); /* Modifica con il colore del tuo tema */
  border-bottom: 1px solid #eaeaea; 
}

/* Flex: 1 su nav-left e nav-right garantisce che nav-center sia sempre al centro */
.nav-left, .nav-right {
  flex: 1;
}

/* Allinea il titolo a sinistra */
.nav-left {
  display: flex;
  justify-content: flex-start;
}

/* Allinea il container al centro */
.nav-center {
  display: flex;
  justify-content: center;
  flex: 1;
}

/* Contenitore stile "Pillola" per i bottoni */
.toggle-container {
  display: flex;
  background-color: var(--color-tertiary); /* Sfondo del toggle non attivo */
  border-radius: 30px;
  padding: 4px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

/* I bottoni del toggle */
.toggle-tab {
  padding: 8px 20px;
  text-decoration: none;
  color: var(--color-background);
  font-weight: 500;
  border-radius: 26px;
  transition: all 0.5s ease-out;
}

/* Stato attivo del bottone (aggiunto automaticamente da RouterLink) */
.toggle-tab.active {
  background-color: var(--color-background); /* Sfondo bottone attivo */
  color: var(--color-text);
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}
</style>
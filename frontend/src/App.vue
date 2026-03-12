<script setup>
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute();
</script>

<template>
  <div class="container">
    <header v-if="route.path === '/overview' || route.path === '/analysis' || route.path === '/results'" class="top-nav">
      
      <div class="nav-left">
        <RouterLink to="/"><h1 class="logo">VIPNODES</h1></RouterLink>
      </div>

      <div class="nav-center">
        <div class="toggle-container">
          <RouterLink to="/overview" class="toggle-tab app-link-inline" active-class="active">
            <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="12" x2="6" y2="6"/>
              <line x1="12" y1="12" x2="18" y2="6"/>
              <line x1="12" y1="12" x2="6" y2="18"/>
              <line x1="12" y1="12" x2="18" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="6"/>
              <circle cx="12" cy="12" r="1.8" fill="currentColor" stroke="none"/>
              <circle cx="6" cy="6" r="1.4" fill="currentColor" stroke="none"/>
              <circle cx="18" cy="6" r="1.4" fill="currentColor" stroke="none"/>
              <circle cx="6" cy="18" r="1.4" fill="currentColor" stroke="none"/>
              <circle cx="18" cy="18" r="1.4" fill="currentColor" stroke="none"/>
            </svg>
            Overview
          </RouterLink>
          <RouterLink to="/analysis" class="toggle-tab app-link-inline" active-class="active">
            <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 20V10"></path>
              <path d="M10 20V4"></path>
              <path d="M16 20v-6"></path>
              <path d="M22 20V8"></path>
            </svg>
            Analysis
          </RouterLink>
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

.top-nav {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 1rem;
  background-color: var(--color-background); /* Modifica con il colore del tuo tema */
  border-bottom: 1px solid #eaeaea; 
}

.nav-left, .nav-right {
  flex: 1;
}

.nav-left {
  display: flex;
  justify-content: flex-start;
}

.nav-center {
  display: flex;
  justify-content: center;
  flex: 1;
}

.toggle-container {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 4px;
  background-color: var(--color-tertiary); /* Sfondo del toggle non attivo */
  border-radius: 30px;
  padding: 4px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  max-width: 100%;
}

.toggle-tab {
  padding: 8px 20px;
  text-decoration: none;
  color: var(--color-background);
  font-weight: 500;
  border-radius: 26px;
  transition: all 0.5s ease-out;
  white-space: nowrap;
}

.toggle-tab.active {
  background-color: var(--color-background); /* Sfondo bottone attivo */
  color: var(--color-text);
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

@media (max-width: 768px) {
  .top-nav {
    row-gap: 1rem;
    justify-content: center;
  }

  .nav-left {
    flex: 1 1 100%;
    justify-content: center;
  }

  .nav-right {
    display: none;
  }

  .nav-center {
    order: 2;
    flex: 0 1 auto;
    width: 100%;
  }

  .toggle-container {
    width: max-content;
    max-width: 100%;
    flex-wrap: nowrap;
    border-radius: 16px;
  }

  .toggle-tab {
    flex: 0 0 auto;
    text-align: center;
  }

  .logo {
    font-size: 38px;
  }
}
</style>
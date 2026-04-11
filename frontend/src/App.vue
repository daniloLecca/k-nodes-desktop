<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useComputationStore } from './stores/computationStore';

const route = useRoute();
const computationStore = useComputationStore()

const initialTheme = document.documentElement.dataset.theme || 'light'
const theme = ref(initialTheme)

const applyTheme = nextTheme => {
  theme.value = nextTheme
  document.documentElement.dataset.theme = nextTheme
  document.documentElement.style.colorScheme = nextTheme
  localStorage.setItem('vipnodes-theme', nextTheme)
}

const toggleTheme = () => {
  applyTheme(theme.value === 'dark' ? 'light' : 'dark')
}

const themeToggleLabel = computed(() => theme.value === 'dark' ? 'Light mode' : 'Dark mode')

onMounted(() => {
  // the theme is saved in localStorage
  const savedTheme = localStorage.getItem('vipnodes-theme')
  applyTheme(savedTheme || initialTheme)
})
</script>

<template>
  <div class="container">
    <button
      class="app-button app-button--outline theme-toggle"
      type="button"
      :aria-label="themeToggleLabel"
      :aria-pressed="theme === 'dark'"
      @click="toggleTheme"
    >
      <svg v-if="theme === 'dark'" class="button-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="4"></circle>
        <path d="M12 2v2"></path>
        <path d="M12 20v2"></path>
        <path d="M4.93 4.93l1.41 1.41"></path>
        <path d="M17.66 17.66l1.41 1.41"></path>
        <path d="M2 12h2"></path>
        <path d="M20 12h2"></path>
        <path d="M6.34 17.66l-1.41 1.41"></path>
        <path d="M19.07 4.93l-1.41 1.41"></path>
      </svg>
      <svg v-else class="button-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.5 6.5 0 0 0 9.8 9.8Z"></path>
      </svg>
    </button>

    <header v-if="route.path === '/overview' || route.path === '/analysis' || route.path === '/results'" class="top-nav">
      
      <div class="nav-left">
        <RouterLink to="/"><h1 class="logo">VIPNODES</h1></RouterLink>
      </div>

      <div class="nav-center">
        <div class="toggle-container">
          <RouterLink to="/overview" class="toggle-tab app-link-inline" active-class="active">
            <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"
                stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <!-- Edges -->
              <line x1="12" y1="12" x2="5"  y2="6"/>
              <line x1="12" y1="12" x2="19" y2="6"/>
              <line x1="12" y1="12" x2="12" y2="20"/>
              <line x1="12" y1="12" x2="4"  y2="15"/>
              <line x1="12" y1="12" x2="20" y2="15"/>
              <!-- Nodes -->
              <circle cx="12" cy="12" r="3" fill="currentColor" stroke="none"/>
              <circle cx="5"  cy="6"  r="1.6" fill="currentColor" stroke="none"/>
              <circle cx="19" cy="6"  r="1.6" fill="currentColor" stroke="none"/>
              <circle cx="12" cy="20" r="1.6" fill="currentColor" stroke="none"/>
              <circle cx="4"  cy="15" r="1.6" fill="currentColor" stroke="none"/>
              <circle cx="20" cy="15" r="1.6" fill="currentColor" stroke="none"/>
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
          <RouterLink v-if="
                (Array.isArray(computationStore.computationResult?.vip_nodes)
                ? computationStore.computationResult.vip_nodes
                : []).length > 0
                "
                to="/results" class="toggle-tab app-link-inline" active-class="active">
            <svg class="button-icon" viewBox="0 0 24 24" aria-hidden="true"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
            fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="4" cy="6" r="1.5"/>
              <line x1="8" y1="6" x2="20" y2="6"/>
              <circle cx="6" cy="12" r="1.5"/>
              <line x1="10" y1="12" x2="20" y2="12"/>
              <circle cx="8" cy="18" r="1.5"/>
              <line x1="12" y1="18" x2="20" y2="18"/>
            </svg>
            Results
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
  position: relative;
}

.theme-toggle {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 1100;
  background-color: var(--color-background-soft);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  box-shadow: 0 12px 24px var(--color-shadow-sm);
}

.theme-toggle:hover {
  background-color: var(--color-background-mute);
}

.theme-toggle .button-icon {
  fill: none;
  stroke: currentColor;
}

.top-nav {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 1rem;
  background-color: var(--color-background); 
  border-bottom: 1px solid var(--color-border); 
}

.nav-left, .nav-right {
  flex: 1;
}

.nav-left {
  display: flex;
  justify-content: flex-start;
  cursor: pointer;
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
  background-color: var(--color-tertiary); 
  border-radius: 30px;
  padding: 4px;
  box-shadow: 0 20px 40px var(--color-shadow-lg);
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
  background-color: var(--color-background); 
  color: var(--color-text);
  box-shadow: 0 2px 5px var(--color-shadow-sm);
}

@media (max-width: 1302px) {
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
    width: 100%;
    max-width: 100%;
    flex-wrap: nowrap;
    border-radius: 16px;
  }

  .toggle-tab {
    flex: 1 1 0;
    min-width: 0;
    text-align: center;
    justify-content: center;
    padding-inline: 0.6rem;
  }

  .logo {
    font-size: 38px;
  }

  .theme-toggle {
    top: 1rem;
    right: 0.15rem;
    padding-inline: 1rem;
  }
}
</style>
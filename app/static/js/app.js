/**
 * Gateway Admin UI - JavaScript Application
 */

// API Base URL (internal endpoints)
const API_BASE = '/internal';

// State
let apiKeys = [];
let systemStatus = {};
let currentKeyToDeactivate = null;
let newlyCreatedKey = null;

// ============================================
// Initialization
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize navigation
    initNavigation();

    // Initialize event listeners
    initEventListeners();

    // Load initial data
    loadApiKeys();
});

// ============================================
// Navigation
// ============================================

function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const section = link.dataset.section;
            switchSection(section);
        });
    });

    // Handle hash navigation
    if (window.location.hash) {
        const section = window.location.hash.replace('#', '');
        switchSection(section);
    }
}

function switchSection(section) {
    // Update nav links
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.toggle('active', link.dataset.section === section);
    });

    // Update sections
    document.querySelectorAll('.section-content').forEach(el => {
        el.classList.add('hidden');
    });

    const sectionEl = document.getElementById(`section-${section}`);
    if (sectionEl) {
        sectionEl.classList.remove('hidden');
    }

    // Update page title
    const titles = {
        'keys': 'API Keys',
        'status': 'System Status'
    };
    document.getElementById('page-title').textContent = titles[section] || 'API Keys';

    // Load section-specific data
    if (section === 'status') {
        loadSystemStatus();
    }

    // Update URL hash
    window.location.hash = section;
}

// ============================================
// Event Listeners
// ============================================

function initEventListeners() {
    // Create key button
    document.getElementById('create-key-btn').addEventListener('click', () => {
        openModal('create-modal');
    });

    // Create key form
    document.getElementById('create-key-form').addEventListener('submit', handleCreateKey);

    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', () => {
        loadApiKeys();
        showToast('Refreshed');
    });

    // Search input
    document.getElementById('search-input').addEventListener('input', filterKeys);

    // Status filter
    document.getElementById('filter-status').addEventListener('change', filterKeys);
}

// ============================================
// API Calls
// ============================================

async function loadApiKeys() {
    showLoading(true);

    try {
        const response = await fetch(`${API_BASE}/list-api-keys`);
        if (!response.ok) throw new Error('Failed to load API keys');

        const data = await response.json();
        // API returns { keys: { "key_prefix": {...}, ... } }
        // Convert to array format with key_prefix added
        if (data.keys && typeof data.keys === 'object') {
            apiKeys = Object.entries(data.keys).map(([keyPrefix, keyData]) => ({
                ...keyData,
                key_prefix: keyPrefix
            }));
        } else if (Array.isArray(data.api_keys)) {
            apiKeys = data.api_keys;
        } else {
            apiKeys = [];
        }
        renderApiKeys();
    } catch (error) {
        console.error('Error loading API keys:', error);
        showToast('Failed to load API keys', 'error');
    } finally {
        showLoading(false);
    }
}

async function createApiKey(formData) {
    try {
        const response = await fetch(`${API_BASE}/generate-api-key`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        if (!response.ok) throw new Error('Failed to create API key');

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error creating API key:', error);
        throw error;
    }
}

async function deactivateApiKey(apiKey) {
    try {
        const response = await fetch(`${API_BASE}/deactivate-api-key`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey })
        });

        if (!response.ok) throw new Error('Failed to deactivate API key');

        return await response.json();
    } catch (error) {
        console.error('Error deactivating API key:', error);
        throw error;
    }
}

async function loadSystemStatus() {
    try {
        const [statusRes, configRes] = await Promise.all([
            fetch(`${API_BASE}/status`),
            fetch(`${API_BASE}/config`)
        ]);

        const status = await statusRes.json();
        const config = await configRes.json();

        renderSystemStatus(status, config);
    } catch (error) {
        console.error('Error loading system status:', error);
        showToast('Failed to load system status', 'error');
    }
}

// ============================================
// Rendering
// ============================================

function renderApiKeys() {
    const tbody = document.getElementById('keys-table-body');
    const emptyState = document.getElementById('empty-state');

    // Apply filters
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const statusFilter = document.getElementById('filter-status').value;

    let filteredKeys = apiKeys.filter(key => {
        const matchesSearch = key.name.toLowerCase().includes(searchTerm) ||
            key.service.toLowerCase().includes(searchTerm);
        const matchesStatus = statusFilter === 'all' ||
            (statusFilter === 'active' && key.is_active) ||
            (statusFilter === 'inactive' && !key.is_active);
        return matchesSearch && matchesStatus;
    });

    if (filteredKeys.length === 0) {
        tbody.innerHTML = '';
        emptyState.classList.remove('hidden');
        return;
    }

    emptyState.classList.add('hidden');

    tbody.innerHTML = filteredKeys.map(key => `
    <tr class="group">
      <td class="px-6 py-4">
        <div class="font-medium text-slate-800">${escapeHtml(key.name)}</div>
        <div class="text-xs text-slate-400 font-mono">${maskKey(key.key_prefix || key.api_key || '')}</div>
      </td>
      <td class="px-6 py-4">
        <span class="text-sm text-slate-600">${escapeHtml(key.service)}</span>
      </td>
      <td class="px-6 py-4">
        ${(key.permissions || []).map(p => `<span class="permission-tag">${escapeHtml(p)}</span>`).join('')}
      </td>
      <td class="px-6 py-4">
        <span class="badge ${key.is_active ? 'badge-active' : 'badge-inactive'}">
          ${key.is_active ? 'Active' : 'Inactive'}
        </span>
      </td>
      <td class="px-6 py-4">
        <span class="text-sm text-slate-600">${formatNumber(key.usage_count || 0)}</span>
      </td>
      <td class="px-6 py-4">
        <span class="text-sm text-slate-500">${formatDate(key.created_at)}</span>
      </td>
      <td class="px-6 py-4 text-right">
        ${key.is_active ? `
          <button onclick="showDeactivateModal('${escapeHtml(key.key_prefix || key.api_key)}', '${escapeHtml(key.name)}')" 
                  class="text-sm text-red-600 hover:text-red-700 font-medium opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
            Deactivate
          </button>
        ` : `
          <span class="text-xs text-slate-400">Deactivated</span>
        `}
      </td>
    </tr>
  `).join('');
}

function renderSystemStatus(status, config) {
    // Update stats
    const totalKeys = apiKeys.length;
    const activeKeys = apiKeys.filter(k => k.is_active).length;
    const totalRequests = apiKeys.reduce((sum, k) => sum + (k.usage_count || 0), 0);

    document.getElementById('stat-total').textContent = totalKeys;
    document.getElementById('stat-active').textContent = activeKeys;
    document.getElementById('stat-requests').textContent = formatNumber(totalRequests);

    // Database status
    const dbStatus = status.database_connected !== false ? 'Connected' : 'Disconnected';
    const dbEl = document.getElementById('stat-db');
    dbEl.textContent = dbStatus;
    dbEl.className = status.database_connected !== false
        ? 'text-2xl font-semibold text-green-600'
        : 'text-2xl font-semibold text-red-600';

    // System config
    const configEl = document.getElementById('system-config');
    const configItems = [
        { label: 'Backend', value: config.backend || 'PostgreSQL' },
        { label: 'Environment', value: config.environment || 'production' },
        { label: 'Version', value: config.version || '1.0' },
        { label: 'Client IP', value: status.client_ip || 'Unknown' },
    ];

    configEl.innerHTML = configItems.map(item => `
    <div class="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
      <span class="text-sm text-slate-500">${item.label}</span>
      <span class="text-sm font-medium text-slate-800">${item.value}</span>
    </div>
  `).join('');
}

// ============================================
// Event Handlers
// ============================================

async function handleCreateKey(e) {
    e.preventDefault();

    const formData = new FormData(e.target);
    const permissions = formData.getAll('permissions');

    const data = {
        name: formData.get('name'),
        service: formData.get('service'),
        permissions: permissions.length > 0 ? permissions : ['read']
    };

    try {
        const result = await createApiKey(data);
        newlyCreatedKey = result.api_key;

        // Close create modal and show success
        closeModal('create-modal');
        document.getElementById('new-key-value').textContent = newlyCreatedKey;
        openModal('success-modal');

        // Reset form and reload keys
        e.target.reset();
        loadApiKeys();
    } catch (error) {
        showToast('Failed to create API key', 'error');
    }
}

function showDeactivateModal(apiKey, name) {
    currentKeyToDeactivate = apiKey;
    document.getElementById('deactivate-key-name').textContent = name;
    openModal('deactivate-modal');
}

async function confirmDeactivate() {
    if (!currentKeyToDeactivate) return;

    try {
        await deactivateApiKey(currentKeyToDeactivate);
        closeModal('deactivate-modal');
        showToast('API key deactivated');
        loadApiKeys();
    } catch (error) {
        showToast('Failed to deactivate API key', 'error');
    } finally {
        currentKeyToDeactivate = null;
    }
}

function copyKey() {
    if (newlyCreatedKey) {
        navigator.clipboard.writeText(newlyCreatedKey).then(() => {
            showToast('Copied to clipboard!');
        });
    }
}

function filterKeys() {
    renderApiKeys();
}

// ============================================
// Modal Helpers
// ============================================

function openModal(modalId) {
    document.getElementById(modalId).classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
    document.body.style.overflow = '';
}

// ============================================
// UI Helpers
// ============================================

function showLoading(show) {
    const loadingState = document.getElementById('loading-state');
    const tableBody = document.getElementById('keys-table-body');

    if (show) {
        loadingState.classList.remove('hidden');
        tableBody.innerHTML = '';
    } else {
        loadingState.classList.add('hidden');
    }
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const messageEl = document.getElementById('toast-message');

    messageEl.textContent = message;
    toast.classList.remove('hidden');

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// ============================================
// Utility Functions
// ============================================

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function maskKey(key) {
    if (!key) return '••••••••';
    if (key.length <= 8) return key + '••••••••';
    return key.substring(0, 8) + '••••••••';
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

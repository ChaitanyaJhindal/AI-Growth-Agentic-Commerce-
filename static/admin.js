// =====================================================================
// AURA EXECUTIVE ATELIER — Admin Intelligence Portal Logic
// =====================================================================

const API_BASE = "";
let allOrders = [];
let allUsers = [];
let adminMetrics = null;

// DOM References
const liveClock = document.getElementById("live-clock");
const refreshDataBtn = document.getElementById("refresh-data-btn");
const exportOrdersBtn = document.getElementById("export-orders-btn");

// KPI Elements
const kpiGrossVolume = document.getElementById("kpi-gross-volume");
const kpiTotalOrders = document.getElementById("kpi-total-orders");
const kpiTotalUsers = document.getElementById("kpi-total-users");
const kpiAvgOrder = document.getElementById("kpi-avg-order");

// Tabs & Panes
const tabButtons = document.querySelectorAll(".admin-tab");
const tabPanes = document.querySelectorAll(".tab-pane");
const tabOrdersCount = document.getElementById("tab-orders-count");
const tabUsersCount = document.getElementById("tab-users-count");

// Orders Table
const orderSearchInput = document.getElementById("order-search-input");
const orderStatusFilter = document.getElementById("order-status-filter");
const ordersTableBody = document.getElementById("orders-table-body");

// Patrons Table & Analytics
const patronsTableBody = document.getElementById("patrons-table-body");
const categoryBarsList = document.getElementById("category-bars-list");

// Abandoned Cart & WhatsApp Automation Elements
const tabAbandonedCount = document.getElementById("tab-abandoned-count");
const kpiAbandonedCount = document.getElementById("kpi-abandoned-count");
const kpiAbandonedVal = document.getElementById("kpi-abandoned-val");
const kpiReachableCount = document.getElementById("kpi-reachable-count");
const kpiQueueTotal = document.getElementById("kpi-queue-total");
const triggerCartCampaignBtn = document.getElementById("trigger-cart-campaign-btn");
const campaignExecLog = document.getElementById("campaign-exec-log");
const abandonedTableBody = document.getElementById("abandoned-table-body");

// Inspector Modal
const orderInspectorModal = document.getElementById("order-inspector-modal");
const inspectorCloseBtn = document.getElementById("inspector-close-btn");
const inspectorOrderId = document.getElementById("inspector-order-id");
const inspectorOrderMeta = document.getElementById("inspector-order-meta");
const inspectorPayId = document.getElementById("inspector-pay-id");
const inspectorPayStatus = document.getElementById("inspector-pay-status");
const inspectorItemsList = document.getElementById("inspector-items-list");
const inspectorTotalAmount = document.getElementById("inspector-total-amount");

// Safe fallback images
const FALLBACK_IMAGES = [
  "https://images.unsplash.com/photo-1549298916-b41d501d3772?q=80&w=300&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?q=80&w=300&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?q=80&w=300&auto=format&fit=crop"
];

function getSafeImageUrl(url, index = 0) {
  if (url && url.startsWith("http")) return url;
  return FALLBACK_IMAGES[index % FALLBACK_IMAGES.length];
}

// =====================================================================
// INITIALIZATION
// =====================================================================

document.addEventListener("DOMContentLoaded", () => {
  startLiveClock();
  loadAllAdminData();
  loadAbandonedCartData();
  setupEventListeners();
});

function startLiveClock() {
  function update() {
    const now = new Date();
    liveClock.textContent = now.toUTCString().replace("GMT", "UTC");
  }
  update();
  setInterval(update, 1000);
}

function setupEventListeners() {
  refreshDataBtn.addEventListener("click", () => {
    refreshDataBtn.innerHTML = "Syncing...";
    Promise.all([loadAllAdminData(), loadAbandonedCartData()]).then(() => {
      refreshDataBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg> Sync`;
    });
  });

  exportOrdersBtn.addEventListener("click", exportOrdersAsJSON);

  if (triggerCartCampaignBtn) {
    triggerCartCampaignBtn.addEventListener("click", executeAbandonedCartRecoveryCampaign);
  }

  // Tab Switching
  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      tabButtons.forEach(b => b.classList.remove("active"));
      tabPanes.forEach(p => {
        p.classList.remove("active");
        p.style.display = "none";
      });

      btn.classList.add("active");
      const activePane = document.getElementById(targetTab);
      if (activePane) {
        activePane.classList.add("active");
        activePane.style.display = "block";
      }
    });
  });

  // Search & Filter Listeners
  orderSearchInput.addEventListener("input", filterAndRenderOrders);
  orderStatusFilter.addEventListener("change", filterAndRenderOrders);

  // Inspector Modal Close
  inspectorCloseBtn.addEventListener("click", () => {
    orderInspectorModal.style.display = "none";
  });
}

// =====================================================================
// DATA FETCHING
// =====================================================================

async function loadAllAdminData() {
  try {
    const [overviewRes, ordersRes, usersRes] = await Promise.all([
      fetch(`${API_BASE}/api/admin/overview`),
      fetch(`${API_BASE}/api/admin/orders`),
      fetch(`${API_BASE}/api/admin/users`)
    ]);

    const overviewData = await overviewRes.json();
    const ordersData = await ordersRes.json();
    const usersData = await usersRes.json();

    if (overviewData.success) {
      adminMetrics = overviewData.metrics;
      renderKPIs(adminMetrics);
      renderCategoryAnalytics(adminMetrics.category_breakdown || {});
    }

    if (ordersData.success) {
      allOrders = ordersData.orders || [];
      tabOrdersCount.textContent = allOrders.length;
      filterAndRenderOrders();
    }

    if (usersData.success) {
      allUsers = usersData.users || [];
      tabUsersCount.textContent = allUsers.length;
      renderPatronsTable(allUsers);
    }
  } catch (err) {
    console.error("Error loading admin atelier data:", err);
  }
}

async function loadAbandonedCartData() {
  try {
    const res = await fetch(`${API_BASE}/api/automation/abandoned-cart-stats`);
    if (!res.ok) return;
    const data = await res.json();
    if (!data.success || !data.stats) return;

    const stats = data.stats;
    if (tabAbandonedCount) tabAbandonedCount.textContent = stats.abandoned_carts_count || 0;
    if (kpiAbandonedCount) kpiAbandonedCount.textContent = stats.abandoned_carts_count || 0;
    if (kpiAbandonedVal) kpiAbandonedVal.textContent = `$${(stats.abandoned_total_value || 0).toFixed(2)}`;
    if (kpiReachableCount) kpiReachableCount.textContent = stats.reachable_via_whatsapp || 0;
    if (kpiQueueTotal) kpiQueueTotal.textContent = (stats.queue && stats.queue.total) || 0;

    renderAbandonedCartsTable(stats.active_users || []);
  } catch (e) {
    console.error("Error loading abandoned cart stats:", e);
  }
}

// =====================================================================
// RENDER METHODS
// =====================================================================

function renderKPIs(metrics) {
  kpiGrossVolume.textContent = `$${(metrics.gross_volume || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
  kpiTotalOrders.textContent = metrics.total_orders || 0;
  kpiTotalUsers.textContent = metrics.total_users || 0;
  kpiAvgOrder.textContent = `$${(metrics.average_order_value || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
}

function filterAndRenderOrders() {
  const query = (orderSearchInput.value || "").trim().toLowerCase();
  const statusFilter = orderStatusFilter.value;

  const filtered = allOrders.filter(order => {
    const matchesQuery = (
      (order.order_id || "").toLowerCase().includes(query) ||
      (order.payment_id || "").toLowerCase().includes(query) ||
      (order.user_email || "").toLowerCase().includes(query) ||
      (order.user_name || "").toLowerCase().includes(query)
    );

    let matchesStatus = true;
    if (statusFilter === "PAID") {
      matchesStatus = (order.status || "").toLowerCase().includes("paid");
    } else if (statusFilter === "IN TRANSIT") {
      matchesStatus = (order.status || "").toLowerCase().includes("transit");
    } else if (statusFilter === "DELIVERED") {
      matchesStatus = (order.status || "").toLowerCase().includes("delivered");
    }

    return matchesQuery && matchesStatus;
  });

  renderOrdersTable(filtered);
}

function renderOrdersTable(orders) {
  if (orders.length === 0) {
    ordersTableBody.innerHTML = `
      <tr>
        <td colspan="8" class="table-loading-cell">No acquisitions matching the specified filters.</td>
      </tr>
    `;
    return;
  }

  ordersTableBody.innerHTML = "";
  orders.forEach(order => {
    const tr = document.createElement("tr");
    
    const formattedDate = order.created_at ? new Date(order.created_at).toLocaleDateString("en-US", {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
    }) : "-";

    const itemsCount = (order.items || []).length;
    const isPaid = (order.status || "").toLowerCase().includes("paid");
    const isTransit = (order.status || "").toLowerCase().includes("transit");
    const isDelivered = (order.status || "").toLowerCase().includes("delivered");

    let statusClass = "status-paid";
    if (isTransit) statusClass = "status-transit";
    if (isDelivered) statusClass = "status-delivered";

    tr.innerHTML = `
      <td><strong style="color: #ffffff;">${order.order_id}</strong></td>
      <td>
        <div class="patron-cell">
          <span class="patron-name">${order.user_name || 'Patron'}</span>
          <span class="patron-email">${order.user_email || ''}</span>
        </div>
      </td>
      <td style="color: var(--text-muted); font-size: 0.8rem;">${formattedDate}</td>
      <td>${itemsCount} piece${itemsCount === 1 ? '' : 's'}</td>
      <td><strong style="color: var(--accent-gold);">$${(order.total_amount || 0).toFixed(2)}</strong></td>
      <td><code style="color: var(--text-secondary); font-size: 0.75rem;">${order.payment_id || 'Direct'}</code></td>
      <td>
        <select class="status-dropdown" data-order-id="${order.order_id}">
          <option value="Paid (Razorpay)" ${isPaid ? 'selected' : ''}>Paid (Razorpay)</option>
          <option value="In Transit" ${isTransit ? 'selected' : ''}>In Transit</option>
          <option value="Delivered" ${isDelivered ? 'selected' : ''}>Delivered</option>
        </select>
      </td>
      <td>
        <button class="btn-inspect" data-order-id="${order.order_id}">Inspect</button>
      </td>
    `;

    // Status change listener
    const select = tr.querySelector(".status-dropdown");
    select.addEventListener("change", (e) => {
      updateOrderStatus(order.order_id, e.target.value);
    });

    // Inspect listener
    tr.querySelector(".btn-inspect").addEventListener("click", () => {
      inspectOrder(order);
    });

    ordersTableBody.appendChild(tr);
  });
}

function renderPatronsTable(users) {
  if (users.length === 0) {
    patronsTableBody.innerHTML = `
      <tr>
        <td colspan="7" class="table-loading-cell">No registered patrons in MongoDB directory.</td>
      </tr>
    `;
    return;
  }

  patronsTableBody.innerHTML = "";
  users.forEach(u => {
    const tr = document.createElement("tr");
    const regDate = u.created_at ? new Date(u.created_at).toLocaleDateString("en-US", {
      year: "numeric", month: "short", day: "numeric"
    }) : "Recent";

    tr.innerHTML = `
      <td><strong style="color: #ffffff;">${u.name}</strong></td>
      <td style="color: var(--text-secondary);">${u.email}</td>
      <td><code style="color: var(--accent-gold); font-size: 0.8rem;">${u.phone || 'Not Linked'}</code></td>
      <td style="color: var(--text-muted);">${regDate}</td>
      <td>${u.wardrobe_count || 0} pieces saved</td>
      <td><strong>${u.orders_count || 0} orders</strong></td>
      <td><strong style="color: var(--accent-gold);">$${(u.total_spent || 0).toFixed(2)}</strong></td>
    `;
    patronsTableBody.appendChild(tr);
  });
}

function renderAbandonedCartsTable(users) {
  if (!abandonedTableBody) return;
  if (!users || users.length === 0) {
    abandonedTableBody.innerHTML = `
      <tr>
        <td colspan="7" class="table-loading-cell">No active abandoned carts found in MongoDB right now.</td>
      </tr>
    `;
    return;
  }

  abandonedTableBody.innerHTML = "";
  users.forEach(u => {
    const tr = document.createElement("tr");
    const lastCampaign = u.last_campaign_sent_at ? new Date(u.last_campaign_sent_at).toLocaleTimeString("en-US", {
      hour: "2-digit", minute: "2-digit"
    }) : "Never";

    tr.innerHTML = `
      <td><strong style="color: #ffffff;">${u.name || 'Patron'}</strong></td>
      <td style="color: var(--text-secondary); font-size: 0.82rem;">${u.email}</td>
      <td><code style="color: var(--accent-gold); font-size: 0.8rem;">${u.phone || 'No Phone (Fallback Test)'}</code></td>
      <td>${u.cart_items_count} piece${u.cart_items_count === 1 ? '' : 's'}</td>
      <td><strong style="color: var(--accent-gold);">$${(u.cart_total_value || 0).toFixed(2)}</strong></td>
      <td style="color: var(--text-muted); font-size: 0.8rem;">${lastCampaign}</td>
      <td>
        <button class="btn-inspect send-single-cart-btn" data-email="${u.email}" data-phone="${u.phone || ''}" style="background: rgba(197, 160, 89, 0.15); border-color: rgba(197, 160, 89, 0.4); color: var(--accent-gold);">
          ⚡ Message
        </button>
      </td>
    `;

    tr.querySelector(".send-single-cart-btn").addEventListener("click", () => {
      executeSingleUserRecovery(u.email, u.phone);
    });

    abandonedTableBody.appendChild(tr);
  });
}

async function executeAbandonedCartRecoveryCampaign() {
  if (!triggerCartCampaignBtn) return;

  triggerCartCampaignBtn.disabled = true;
  triggerCartCampaignBtn.innerHTML = `<span>⏳</span> Synthesizing & Enqueueing...`;

  if (campaignExecLog) {
    campaignExecLog.style.display = "block";
    campaignExecLog.innerHTML = `[${new Date().toLocaleTimeString()}] 🚀 Initiating Abandoned Cart AI Re-Engagement Pipeline...\n`;
    campaignExecLog.innerHTML += `[${new Date().toLocaleTimeString()}] 🔍 Querying MongoDB users with active bags...\n`;
  }

  try {
    const res = await fetch(`${API_BASE}/api/automation/abandoned-cart-campaign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        coupon_code: "AURA20",
        tone: "witty_hinglish",
        cooldown_hours: 0.05, // low cooldown for admin test
        max_users: 20
      })
    });

    const data = await res.json();
    if (campaignExecLog) {
      if (data.success) {
        campaignExecLog.innerHTML += `[${new Date().toLocaleTimeString()}] ✅ ${data.message}\n`;
        campaignExecLog.innerHTML += `[${new Date().toLocaleTimeString()}] 📦 Processed: ${data.processed_count} patrons | Enqueued: ${data.enqueued_count} messages | Skipped: ${data.skipped_count}\n`;
        if (data.details && data.details.length > 0) {
          data.details.forEach(d => {
            campaignExecLog.innerHTML += `  ✦ [${d.email} -> ${d.phone}] ${d.status}: "${(d.preview || '').slice(0, 60)}..."\n`;
          });
        }
      } else {
        campaignExecLog.innerHTML += `[${new Date().toLocaleTimeString()}] ❌ Execution notice: ${data.detail || data.error}\n`;
      }
    }

    loadAbandonedCartData();
  } catch (err) {
    if (campaignExecLog) {
      campaignExecLog.innerHTML += `[${new Date().toLocaleTimeString()}] ❌ Network error: ${err.message}\n`;
    }
  } finally {
    triggerCartCampaignBtn.disabled = false;
    triggerCartCampaignBtn.innerHTML = `<span>🚀</span> Launch AI WhatsApp Recovery Campaign`;
  }
}

async function executeSingleUserRecovery(email, phone) {
  if (!confirm(`Generate personalized WhatsApp message for ${email}?`)) return;

  try {
    const res = await fetch(`${API_BASE}/api/automation/abandoned-cart-campaign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        coupon_code: "AURA20",
        tone: "witty_hinglish",
        override_phone: phone || "+919876543210",
        cooldown_hours: 0.0,
        max_users: 1
      })
    });
    const data = await res.json();
    alert(`Success: ${data.message || 'Message enqueued to MongoDB queue'}`);
    loadAbandonedCartData();
  } catch (e) {
    alert(`Error: ${e.message}`);
  }
}

function renderCategoryAnalytics(categories) {
  const keys = Object.keys(categories);
  if (keys.length === 0) {
    categoryBarsList.innerHTML = `<div class="table-loading-cell">No categorical acquisitions recorded yet.</div>`;
    return;
  }

  const maxVal = Math.max(...Object.values(categories), 1);
  categoryBarsList.innerHTML = "";

  keys.forEach(cat => {
    const count = categories[cat];
    const percentage = Math.round((count / maxVal) * 100);

    const row = document.createElement("div");
    row.className = "category-bar-row";
    row.innerHTML = `
      <div class="category-bar-meta">
        <span style="font-weight: 500; color: #ffffff;">${cat}</span>
        <span style="color: var(--accent-gold);">${count} piece${count === 1 ? '' : 's'}</span>
      </div>
      <div class="bar-track">
        <div class="bar-fill" style="width: ${percentage}%;"></div>
      </div>
    `;
    categoryBarsList.appendChild(row);
  });
}

// =====================================================================
// ORDER STATUS UPDATE & INSPECTION
// =====================================================================

async function updateOrderStatus(orderId, newStatus) {
  try {
    const res = await fetch(`${API_BASE}/api/admin/orders/update-status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ order_id: orderId, status: newStatus })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      alert("Failed to update status: " + (data.detail || "Error"));
      return;
    }

    // Update in local cache
    const target = allOrders.find(o => o.order_id === orderId);
    if (target) target.status = newStatus;
  } catch (e) {
    alert("Network error updating status: " + e.message);
  }
}

function inspectOrder(order) {
  inspectorOrderId.textContent = order.order_id;
  const dateStr = order.created_at ? new Date(order.created_at).toLocaleString("en-US") : "-";
  inspectorOrderMeta.innerHTML = `Patron: <strong style="color:#ffffff;">${order.user_name || 'Member'}</strong> (${order.user_email}) &bull; ${dateStr}`;
  inspectorPayId.textContent = order.payment_id || "Direct Verified";
  inspectorPayStatus.textContent = order.status || "Paid";
  inspectorTotalAmount.textContent = `$${(order.total_amount || 0).toFixed(2)}`;

  inspectorItemsList.innerHTML = "";
  (order.items || []).forEach((item, idx) => {
    const row = document.createElement("div");
    row.className = "inspector-item-row";
    row.innerHTML = `
      <img src="${getSafeImageUrl(item.image_url, idx)}" class="inspector-item-img" alt="${item.name}"/>
      <div class="inspector-item-details">
        <div class="inspector-item-name">${item.name}</div>
        <div class="inspector-item-brand">${item.brand || 'Studio Collection'} &bull; ${item.article_type || 'Piece'}</div>
      </div>
      <div class="inspector-item-price">$${(item.price || 0).toFixed(2)}</div>
    `;
    inspectorItemsList.appendChild(row);
  });

  orderInspectorModal.style.display = "flex";
}

function exportOrdersAsJSON() {
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(allOrders, null, 2));
  const downloadAnchor = document.createElement("a");
  downloadAnchor.setAttribute("href", dataStr);
  downloadAnchor.setAttribute("download", `AURA_Orders_Export_${new Date().toISOString().slice(0, 10)}.json`);
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
}

// =====================================================================
// AURA — AI Fashion Concierge Client Application
// =====================================================================

const API_BASE = "";
let currentThreadId = localStorage.getItem("aura_thread_id") || generateUUID();
localStorage.setItem("aura_thread_id", currentThreadId);

let wardrobeItems = JSON.parse(localStorage.getItem("aura_wardrobe") || "[]");
let bagItems = JSON.parse(localStorage.getItem("aura_bag") || "[]");
let activeEnsembleProducts = [];

function generateUUID() {
  return "aura-" + Math.random().toString(36).substring(2, 9);
}

// Fallback high-fashion images if external catalog URL fails
const FALLBACK_IMAGES = [
  "https://images.unsplash.com/photo-1549298916-b41d501d3772?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1591047139829-d91aecb6caea?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1523275335684-37898b6baf30?q=80&w=800&auto=format&fit=crop",
  "https://images.unsplash.com/photo-1584917865442-de89df76afd3?q=80&w=800&auto=format&fit=crop"
];

function getSafeImageUrl(url, index = 0) {
  if (url && url.startsWith("http")) return url;
  return FALLBACK_IMAGES[index % FALLBACK_IMAGES.length];
}

// =====================================================================
// DOM Elements
// =====================================================================

const queryInput = document.getElementById("query-input");
const submitBtn = document.getElementById("submit-btn");
const voiceBtn = document.getElementById("voice-btn");
const suggestionChips = document.querySelectorAll(".suggestion-chips .chip");
const processingCard = document.getElementById("ai-processing-card");
const processingTitle = document.getElementById("processing-title");
const clarificationCard = document.getElementById("clarification-card");
const clarifyQuestionText = document.getElementById("clarification-question-text");
const clarifyOptions = document.getElementById("clarification-options");
const clarifyInput = document.getElementById("clarify-input");
const clarifySubmitBtn = document.getElementById("clarify-submit-btn");
const resultsSection = document.getElementById("results-section");
const productsGrid = document.getElementById("products-grid");
const editorialHome = document.getElementById("editorial-home");
const editorialGrid = document.getElementById("editorial-grid");
const interpretationHeadline = document.getElementById("interpretation-headline");
const interpretationSub = document.getElementById("interpretation-sub");
const activeFiltersRow = document.getElementById("active-filters-row");
const validationText = document.getElementById("validation-text");

// Outfit Modal & Drawers
const outfitModal = document.getElementById("outfit-modal");
const modalCloseBtn = document.getElementById("modal-close-btn");
const anchorItemPanel = document.getElementById("anchor-item-panel");
const ensembleCardsList = document.getElementById("ensemble-cards-list");
const stylistInsightText = document.getElementById("stylist-insight-text");
const ensembleTotalPrice = document.getElementById("ensemble-total-price");
const buyCompleteLookBtn = document.getElementById("buy-complete-look-btn");

const bagDrawer = document.getElementById("bag-drawer");
const bagCloseBtn = document.getElementById("bag-close-btn");
const openBagBtn = document.getElementById("open-bag-btn");
const bagCount = document.getElementById("bag-count");
const drawerBagCount = document.getElementById("drawer-bag-count");
const bagItemsList = document.getElementById("bag-items-list");
const bagSubtotal = document.getElementById("bag-subtotal");

const wardrobeDrawer = document.getElementById("wardrobe-drawer");
const wardrobeCloseBtn = document.getElementById("wardrobe-close-btn");
const tabWardrobe = document.getElementById("tab-wardrobe");
const wardrobeCount = document.getElementById("wardrobe-count");
const drawerWardrobeCount = document.getElementById("drawer-wardrobe-count");
const wardrobeItemsList = document.getElementById("wardrobe-items-list");

// =====================================================================
// Initialize App
// =====================================================================

document.addEventListener("DOMContentLoaded", () => {
  updateBagUI();
  updateWardrobeUI();
  loadTrendingCurations();
  setupEventListeners();
});

function setupEventListeners() {
  submitBtn.addEventListener("click", () => executeQuery(queryInput.value));
  queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") executeQuery(queryInput.value);
  });

  // Suggestion Chips
  suggestionChips.forEach(chip => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      queryInput.value = prompt;
      executeQuery(prompt);
    });
  });

  // Clarification reply
  clarifySubmitBtn.addEventListener("click", () => {
    if (clarifyInput.value.trim()) {
      executeClarification(clarifyInput.value.trim());
    }
  });

  clarifyInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && clarifyInput.value.trim()) {
      executeClarification(clarifyInput.value.trim());
    }
  });

  // Drawers & Modals
  openBagBtn.addEventListener("click", () => bagDrawer.style.display = "flex");
  bagCloseBtn.addEventListener("click", () => bagDrawer.style.display = "none");
  tabWardrobe.addEventListener("click", () => wardrobeDrawer.style.display = "flex");
  wardrobeCloseBtn.addEventListener("click", () => wardrobeDrawer.style.display = "none");
  modalCloseBtn.addEventListener("click", () => outfitModal.style.display = "none");

  // Buy complete look
  buyCompleteLookBtn.addEventListener("click", () => {
    activeEnsembleProducts.forEach(prod => addToBag(prod));
    outfitModal.style.display = "none";
    bagDrawer.style.display = "flex";
  });

  // Voice Affordance
  voiceBtn.addEventListener("click", () => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.onstart = () => {
        voiceBtn.style.color = "var(--accent-amber)";
        queryInput.placeholder = "Listening to your request...";
      };
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        queryInput.value = transcript;
        executeQuery(transcript);
      };
      recognition.onend = () => {
        voiceBtn.style.color = "var(--text-secondary)";
      };
      recognition.start();
    } else {
      alert("Speech recognition is not supported in this browser.");
    }
  });
}

// =====================================================================
// AI Agent Chat Execution
// =====================================================================

async function executeQuery(message) {
  if (!message || !message.trim()) return;

  // Show processing animation
  processingCard.style.display = "block";
  clarificationCard.style.display = "none";
  resultsSection.style.display = "none";
  editorialHome.style.display = "none";
  animateProcessingSteps();

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message.trim(),
        thread_id: currentThreadId
      })
    });

    const data = await res.json();
    processingCard.style.display = "none";

    if (data.needs_clarification && data.clarification_question) {
      // Display Clarification Card
      displayClarification(data.clarification_question);
    } else {
      // Display Search Results
      displaySearchResults(data);
    }
  } catch (err) {
    console.error("Error executing query:", err);
    processingCard.style.display = "none";
    alert("Connection error. Please ensure the FastAPI backend is running.");
  }
}

async function executeClarification(answer) {
  processingCard.style.display = "block";
  clarificationCard.style.display = "none";
  animateProcessingSteps();

  try {
    const res = await fetch(`${API_BASE}/api/clarify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        thread_id: currentThreadId,
        answer: answer
      })
    });

    const data = await res.json();
    processingCard.style.display = "none";

    if (data.needs_clarification && data.clarification_question) {
      displayClarification(data.clarification_question);
    } else {
      displaySearchResults(data);
    }
  } catch (err) {
    console.error("Error on clarification:", err);
    processingCard.style.display = "none";
  }
}

function animateProcessingSteps() {
  const steps = ["step-1", "step-2", "step-3", "step-4", "step-5"];
  steps.forEach((id, idx) => {
    const el = document.getElementById(id);
    if (el) {
      el.className = "step";
      setTimeout(() => {
        el.className = "step active";
        if (idx > 0) document.getElementById(steps[idx - 1]).className = "step done";
      }, idx * 600);
    }
  });
}

function displayClarification(question) {
  clarificationCard.style.display = "flex";
  clarifyQuestionText.textContent = question;
  clarifyInput.value = "";

  // Dynamic sample options based on question
  clarifyOptions.innerHTML = "";
  let sampleChoices = [];
  if (question.toLowerCase().includes("budget")) {
    sampleChoices = ["Under $50", "$50 to $100", "$100 to $200", "No budget limit"];
  } else if (question.toLowerCase().includes("men") || question.toLowerCase().includes("women")) {
    sampleChoices = ["Men's collection", "Women's collection", "Unisex"];
  } else {
    sampleChoices = ["Everyday wear", "Formal & Dinner", "Sport & Fitness", "Minimalist"];
  }

  sampleChoices.forEach(choice => {
    const pill = document.createElement("button");
    pill.className = "clarify-pill";
    pill.textContent = choice;
    pill.addEventListener("click", () => executeClarification(choice));
    clarifyOptions.appendChild(pill);
  });
}

// =====================================================================
// Search Results Rendering
// =====================================================================

function displaySearchResults(data) {
  resultsSection.style.display = "block";
  productsGrid.innerHTML = "";
  activeFiltersRow.innerHTML = "";

  const products = data.search_results || [];
  interpretationHeadline.textContent = `${products.length} Curated Matches for "${data.current_query || 'your search'}"`;

  // Validation details
  const val = data.validation_result || {};
  if (val.validated) {
    validationText.textContent = "Validated by AI Concierge";
    validationText.parentElement.style.backgroundColor = "#F0FDF4";
  } else {
    validationText.textContent = "Refined automatically";
  }

  // Render active filters
  const filters = data.filters || {};
  for (const [key, val] of Object.entries(filters)) {
    if (val && typeof val !== "object") {
      const tag = document.createElement("div");
      tag.className = "filter-tag";
      tag.innerHTML = `<span>${key}: <strong>${val}</strong></span>`;
      activeFiltersRow.appendChild(tag);
    } else if (val && typeof val === "object") {
      if (val["$lte"]) {
        const tag = document.createElement("div");
        tag.className = "filter-tag";
        tag.innerHTML = `<span>Price ≤ <strong>$${val["$lte"]}</strong></span>`;
        activeFiltersRow.appendChild(tag);
      }
    }
  }

  if (products.length === 0) {
    productsGrid.innerHTML = `<p class="empty-msg" style="grid-column: 1/-1; padding: 2rem 0;">No exact matches found. Try broadening your criteria or asking for another aesthetic.</p>`;
    return;
  }

  // Render Product Cards
  products.forEach((prod, index) => {
    const card = document.createElement("div");
    card.className = "product-card";

    const badgeLabel = index === 0 ? "Stylist Top Pick" : (prod.rating >= 4.3 ? "Highly Rated" : "Curated");

    card.innerHTML = `
      <div class="card-image-wrap">
        <img src="${getSafeImageUrl(prod.image_url, index)}" alt="${prod.name}" onerror="this.src='${FALLBACK_IMAGES[index % FALLBACK_IMAGES.length]}'"/>
        <span class="card-badge">${badgeLabel}</span>
        <button class="card-save-btn" title="Save to Wardrobe">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="${isSaved(prod.product_id) ? '#B87A44' : 'none'}" stroke="${isSaved(prod.product_id) ? '#B87A44' : 'currentColor'}" stroke-width="2">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
          </svg>
        </button>
      </div>
      <div class="card-body">
        <div class="card-meta">
          <span class="card-brand">${prod.brand || 'Luxury Studio'}</span>
          <span class="card-rating">${prod.rating ? prod.rating.toFixed(1) + ' ★' : ''}</span>
        </div>
        <h3 class="card-title">${prod.name}</h3>
        <div class="card-footer">
          <span class="card-price">$${prod.price ? prod.price.toFixed(2) : '48.00'}</span>
          <button class="explore-outfit-btn">Complete Look</button>
        </div>
      </div>
    `;

    // Save toggle
    const saveBtn = card.querySelector(".card-save-btn");
    saveBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleWardrobe(prod);
      displaySearchResults(data);
    });

    // Open Complete Look Outfit Studio
    const outfitBtn = card.querySelector(".explore-outfit-btn");
    outfitBtn.addEventListener("click", () => openOutfitStudio(prod, data.upsell_results));

    productsGrid.appendChild(card);
  });
}

// =====================================================================
// Outfit Studio Modal ("Complete The Look")
// =====================================================================

async function openOutfitStudio(anchorProduct, existingUpsells = []) {
  outfitModal.style.display = "flex";
  activeEnsembleProducts = [anchorProduct];

  // Render left anchor panel
  anchorItemPanel.innerHTML = `
    <span class="kicker">ANCHOR PIECE</span>
    <img src="${getSafeImageUrl(anchorProduct.image_url, 0)}" class="anchor-image" alt="${anchorProduct.name}"/>
    <div class="card-brand">${anchorProduct.brand || 'AURA Studio'}</div>
    <h3 style="font-size: 1.15rem; font-weight: 500; margin: 0.25rem 0 0.5rem;">${anchorProduct.name}</h3>
    <div style="font-size: 1.25rem; font-weight: 600; margin-bottom: 0.75rem;">$${anchorProduct.price ? anchorProduct.price.toFixed(2) : '88.00'}</div>
    <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;">${anchorProduct.gender || 'Unisex'} · ${anchorProduct.base_color || 'Neutral'} · ${anchorProduct.article_type || 'Piece'}</p>
  `;

  // Fetch complementary outfit if not preloaded
  let pairings = existingUpsells;
  if (!pairings || pairings.length === 0) {
    stylistInsightText.textContent = "Curating harmonious complementary outfit...";
    ensembleCardsList.innerHTML = "<p>Loading outfit pairings...</p>";
    try {
      const res = await fetch(`${API_BASE}/api/outfit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: anchorProduct.product_id })
      });
      const data = await res.json();
      pairings = data.outfit_pairings || [];
    } catch (e) {
      console.error(e);
      pairings = [];
    }
  }

  // Render complementary pieces
  ensembleCardsList.innerHTML = "";
  let total = anchorProduct.price || 88.00;

  if (pairings && pairings.length > 0) {
    const topPairing = pairings[0];
    stylistInsightText.textContent = topPairing.stylist_note || topPairing.compatibility_reason || "Selected for optimal tonal balance and silhouette harmony.";

    pairings.forEach((item, idx) => {
      activeEnsembleProducts.push(item);
      total += (item.price || 45.00);

      const pieceCard = document.createElement("div");
      pieceCard.className = "ensemble-piece-card";
      pieceCard.innerHTML = `
        <img src="${getSafeImageUrl(item.image_url, idx + 1)}" class="ensemble-piece-img" alt="${item.name}"/>
        <div style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-secondary);">${item.article_type || 'Complementary'}</div>
        <div class="ensemble-piece-name">${item.name}</div>
        <div class="ensemble-piece-price">$${item.price ? item.price.toFixed(2) : '35.00'}</div>
      `;
      ensembleCardsList.appendChild(pieceCard);
    });
  } else {
    stylistInsightText.textContent = "A clean neutral silhouette that pairs seamlessly with minimalist denim and linen tailoring.";
  }

  ensembleTotalPrice.textContent = `$${total.toFixed(2)}`;
}

// =====================================================================
// Wardrobe & Bag State Management
// =====================================================================

function isSaved(productId) {
  return wardrobeItems.some(item => item.product_id === productId);
}

function toggleWardrobe(product) {
  if (isSaved(product.product_id)) {
    wardrobeItems = wardrobeItems.filter(item => item.product_id !== product.product_id);
  } else {
    wardrobeItems.push(product);
  }
  localStorage.setItem("aura_wardrobe", JSON.stringify(wardrobeItems));
  updateWardrobeUI();
}

function updateWardrobeUI() {
  wardrobeCount.textContent = wardrobeItems.length;
  drawerWardrobeCount.textContent = wardrobeItems.length;

  if (wardrobeItems.length === 0) {
    wardrobeItemsList.innerHTML = `<p class="empty-msg">No items saved to your wardrobe yet. Click the bookmark icon on any piece to save it.</p>`;
    return;
  }

  wardrobeItemsList.innerHTML = "";
  wardrobeItems.forEach(item => {
    const row = document.createElement("div");
    row.className = "cart-item-row";
    row.innerHTML = `
      <img src="${getSafeImageUrl(item.image_url)}" class="cart-item-img" alt="${item.name}"/>
      <div style="flex: 1;">
        <div style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-secondary);">${item.brand || 'Studio'}</div>
        <div style="font-weight: 500; font-size: 0.9rem;">${item.name}</div>
        <div style="font-weight: 600; margin-top: 0.25rem;">$${item.price ? item.price.toFixed(2) : '0.00'}</div>
      </div>
      <button class="btn-primary" style="padding: 0.4rem 0.75rem; font-size: 0.75rem;">Add to Bag</button>
    `;
    row.querySelector("button").addEventListener("click", () => addToBag(item));
    wardrobeItemsList.appendChild(row);
  });
}

function addToBag(product) {
  bagItems.push(product);
  localStorage.setItem("aura_bag", JSON.stringify(bagItems));
  updateBagUI();
}

function removeFromBag(index) {
  bagItems.splice(index, 1);
  localStorage.setItem("aura_bag", JSON.stringify(bagItems));
  updateBagUI();
}

function updateBagUI() {
  bagCount.textContent = bagItems.length;
  drawerBagCount.textContent = bagItems.length;

  if (bagItems.length === 0) {
    bagItemsList.innerHTML = `<p class="empty-msg">Your shopping bag is currently empty.</p>`;
    bagSubtotal.textContent = "$0.00";
    return;
  }

  bagItemsList.innerHTML = "";
  let total = 0;

  bagItems.forEach((item, index) => {
    total += (item.price || 0);
    const row = document.createElement("div");
    row.className = "cart-item-row";
    row.innerHTML = `
      <img src="${getSafeImageUrl(item.image_url, index)}" class="cart-item-img" alt="${item.name}"/>
      <div style="flex: 1;">
        <div style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-secondary);">${item.brand || 'Studio'}</div>
        <div style="font-weight: 500; font-size: 0.9rem;">${item.name}</div>
        <div style="font-weight: 600; margin-top: 0.25rem;">$${item.price ? item.price.toFixed(2) : '0.00'}</div>
      </div>
      <button style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:1.2rem;" title="Remove">&times;</button>
    `;
    row.querySelector("button").addEventListener("click", () => removeFromBag(index));
    bagItemsList.appendChild(row);
  });

  bagSubtotal.textContent = `$${total.toFixed(2)}`;
}

// =====================================================================
// Load Initial Editorial Trending Curations
// =====================================================================

async function loadTrendingCurations() {
  try {
    const res = await fetch(`${API_BASE}/api/trending`);
    const data = await res.json();
    const curations = data.curations || [];

    editorialGrid.innerHTML = "";
    curations.slice(0, 6).forEach((prod, index) => {
      const card = document.createElement("div");
      card.className = "product-card";
      card.innerHTML = `
        <div class="card-image-wrap">
          <img src="${getSafeImageUrl(prod.image_url, index)}" alt="${prod.name}" onerror="this.src='${FALLBACK_IMAGES[index % FALLBACK_IMAGES.length]}'"/>
          <span class="card-badge">Editorial Pick</span>
        </div>
        <div class="card-body">
          <div class="card-meta">
            <span class="card-brand">${prod.brand || 'Studio'}</span>
            <span class="card-rating">${prod.rating ? prod.rating.toFixed(1) + ' ★' : ''}</span>
          </div>
          <h3 class="card-title">${prod.name}</h3>
          <div class="card-footer">
            <span class="card-price">$${prod.price ? prod.price.toFixed(2) : '55.00'}</span>
            <button class="explore-outfit-btn">Complete Look</button>
          </div>
        </div>
      `;

      card.querySelector(".explore-outfit-btn").addEventListener("click", () => openOutfitStudio(prod));
      editorialGrid.appendChild(card);
    });
  } catch (err) {
    console.log("Notice: Starting up backend server for editorial loading...");
  }
}

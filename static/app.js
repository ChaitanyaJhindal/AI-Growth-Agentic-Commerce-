// =====================================================================
// AURA — AI Fashion Concierge Client Application
// =====================================================================

const API_BASE = "";
let currentThreadId = localStorage.getItem("aura_thread_id") || generateUUID();
localStorage.setItem("aura_thread_id", currentThreadId);

let currentUser = JSON.parse(localStorage.getItem("aura_user") || "null");
let wardrobeItems = JSON.parse(localStorage.getItem("aura_wardrobe") || "[]");
let bagItems = JSON.parse(localStorage.getItem("aura_bag") || "[]");
let activeEnsembleProducts = [];
let pendingCheckout = false;

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
const checkoutBtn = document.getElementById("checkout-btn");

const wardrobeDrawer = document.getElementById("wardrobe-drawer");
const wardrobeCloseBtn = document.getElementById("wardrobe-close-btn");
const tabWardrobe = document.getElementById("tab-wardrobe");
const wardrobeCount = document.getElementById("wardrobe-count");
const drawerWardrobeCount = document.getElementById("drawer-wardrobe-count");
const wardrobeItemsList = document.getElementById("wardrobe-items-list");

// Auth Elements
const authBtn = document.getElementById("auth-btn");
const authUserName = document.getElementById("auth-user-name");
const userDropdown = document.getElementById("user-dropdown");
const dropdownUserEmail = document.getElementById("dropdown-user-email");
const logoutBtn = document.getElementById("logout-btn");

const authModal = document.getElementById("auth-modal");
const authCloseBtn = document.getElementById("auth-close-btn");
const authModalTitle = document.getElementById("auth-modal-title");
const tabLoginBtn = document.getElementById("tab-login-btn");
const tabSignupBtn = document.getElementById("tab-signup-btn");
const loginForm = document.getElementById("login-form");
const signupForm = document.getElementById("signup-form");
const loginEmail = document.getElementById("login-email");
const loginPassword = document.getElementById("login-password");
const loginError = document.getElementById("login-error");
const signupName = document.getElementById("signup-name");
const signupEmail = document.getElementById("signup-email");
const signupPassword = document.getElementById("signup-password");
const signupError = document.getElementById("signup-error");
const authSkipBtn = document.getElementById("auth-skip-btn");

// Order Confirmation Modal Elements
const orderSuccessModal = document.getElementById("order-success-modal");
const orderSuccessCloseBtn = document.getElementById("order-success-close-btn");
const orderDoneBtn = document.getElementById("order-done-btn");
const orderRefId = document.getElementById("order-ref-id");
const orderRefTotal = document.getElementById("order-ref-total");

// Customer Maison Profile Modal Elements
const profileModal = document.getElementById("profile-modal");
const profileCloseBtn = document.getElementById("profile-close-btn");
const navProfileBtn = document.getElementById("nav-profile-btn");
const profileDisplayName = document.getElementById("profile-display-name");
const profileDisplayEmail = document.getElementById("profile-display-email");
const profileAvatarLetter = document.getElementById("profile-avatar-letter");
const profileStatWardrobe = document.getElementById("profile-stat-wardrobe");
const profileStatOrders = document.getElementById("profile-stat-orders");
const profileStatSpend = document.getElementById("profile-stat-spend");
const profileOrdersCountBadge = document.getElementById("profile-orders-count-badge");
const profileOrdersList = document.getElementById("profile-orders-list");

// =====================================================================
// Initialize App
// =====================================================================

document.addEventListener("DOMContentLoaded", () => {
  updateAuthUI();
  updateBagUI();
  updateWardrobeUI();
  loadTrendingCurations();
  setupEventListeners();
  initDynamicPlaceholderAgent();
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

  // Checkout Button (Login Gate)
  if (checkoutBtn) {
    checkoutBtn.addEventListener("click", handleCheckoutClick);
  }

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

  // Auth Event Handlers
  authBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (currentUser) {
      userDropdown.style.display = userDropdown.style.display === "none" ? "block" : "none";
    } else {
      openAuthModal("login");
    }
  });

  document.addEventListener("click", () => {
    if (userDropdown) userDropdown.style.display = "none";
  });

  logoutBtn.addEventListener("click", () => {
    logoutUser();
  });

  authCloseBtn.addEventListener("click", () => {
    authModal.style.display = "none";
    pendingCheckout = false;
  });

  if (authSkipBtn) {
    authSkipBtn.addEventListener("click", () => {
      authModal.style.display = "none";
      pendingCheckout = false;
    });
  }

  tabLoginBtn.addEventListener("click", () => switchAuthTab("login"));
  tabSignupBtn.addEventListener("click", () => switchAuthTab("signup"));

  loginForm.addEventListener("submit", handleLoginSubmit);
  signupForm.addEventListener("submit", handleSignupSubmit);

  // Order Success Modal Close
  if (orderSuccessCloseBtn) {
    orderSuccessCloseBtn.addEventListener("click", () => orderSuccessModal.style.display = "none");
  }
  if (orderDoneBtn) {
    orderDoneBtn.addEventListener("click", () => orderSuccessModal.style.display = "none");
  }

  // Customer Profile & Orders Modal Handlers
  if (navProfileBtn) {
    navProfileBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      if (userDropdown) userDropdown.style.display = "none";
      openProfileModal();
    });
  }
  if (profileCloseBtn) {
    profileCloseBtn.addEventListener("click", () => {
      profileModal.style.display = "none";
    });
  }
}

async function openProfileModal() {
  if (!currentUser || !currentUser.email) {
    openAuthModal("login");
    return;
  }

  profileModal.style.display = "flex";
  profileDisplayName.textContent = currentUser.name || "Member";
  profileDisplayEmail.textContent = currentUser.email || "";
  profileAvatarLetter.textContent = (currentUser.name || "M").charAt(0).toUpperCase();
  profileStatWardrobe.textContent = wardrobeItems.length;

  try {
    const res = await fetch(`${API_BASE}/api/user/orders?email=${encodeURIComponent(currentUser.email)}`);
    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || "Failed to load order history");
    }

    const orders = data.orders || [];
    profileStatOrders.textContent = orders.length;

    let lifetimeSpend = 0;
    orders.forEach(o => lifetimeSpend += (o.total_amount || 0));
    profileStatSpend.textContent = `$${lifetimeSpend.toFixed(2)}`;
    profileOrdersCountBadge.textContent = `${orders.length} Acquisition${orders.length === 1 ? '' : 's'}`;

    renderProfileOrders(orders);
  } catch (err) {
    console.error("Error loading user profile orders:", err);
    profileOrdersList.innerHTML = `<div class="empty-orders-state"><p>Could not retrieve historical orders at this time.</p></div>`;
  }
}

function renderProfileOrders(orders) {
  if (!orders || orders.length === 0) {
    profileOrdersList.innerHTML = `
      <div class="empty-orders-state">
        <p style="font-size: 1rem; color: #ffffff; margin-bottom: 0.25rem;">No historical orders yet</p>
        <p style="font-size: 0.8rem; color: #71717a;">Your bespoke acquisitions and capsule orders will be archived here once placed.</p>
      </div>
    `;
    return;
  }

  profileOrdersList.innerHTML = "";
  orders.forEach(order => {
    const orderDate = order.created_at ? new Date(order.created_at).toLocaleDateString("en-US", {
      year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit"
    }) : "Recent Order";

    const card = document.createElement("div");
    card.className = "order-history-card";

    let itemsHtml = "";
    (order.items || []).forEach((item, idx) => {
      itemsHtml += `
        <div class="order-item-chip">
          <img src="${getSafeImageUrl(item.image_url, idx)}" class="order-item-thumb" alt="${item.name}"/>
          <div class="order-item-info">
            <span class="order-item-name">${item.name}</span>
            <span class="order-item-price">$${item.price ? item.price.toFixed(2) : '0.00'}</span>
          </div>
        </div>
      `;
    });

    card.innerHTML = `
      <div class="order-card-header">
        <div class="order-ref-group">
          <span class="order-ref-title">${order.order_id}</span>
          <span class="order-meta-sub">${orderDate} &bull; Razorpay ID: <code style="color:var(--accent-gold);">${order.payment_id || 'Direct'}</code></span>
        </div>
        <span class="order-status-pill">${order.status || 'Paid (Razorpay)'}</span>
      </div>
      <div class="order-items-grid">
        ${itemsHtml}
      </div>
      <div class="order-card-footer">
        <span>Complimentary Express Delivery</span>
        <span>Total Paid: <strong>$${(order.total_amount || 0).toFixed(2)}</strong></span>
      </div>
    `;

    profileOrdersList.appendChild(card);
  });
}

// =====================================================================
// User Authentication Logic
// =====================================================================

function updateAuthUI() {
  if (currentUser) {
    authUserName.textContent = currentUser.name || "Member";
    dropdownUserEmail.textContent = currentUser.email || "";
  } else {
    authUserName.textContent = "Sign In";
    dropdownUserEmail.textContent = "";
  }
}

function openAuthModal(mode = "login", isForCheckout = false) {
  authModal.style.display = "flex";
  pendingCheckout = isForCheckout;
  switchAuthTab(mode);
  if (isForCheckout) {
    authModalTitle.textContent = "Sign In to Place Order";
  }
}

function switchAuthTab(mode) {
  if (mode === "login") {
    tabLoginBtn.classList.add("active");
    tabSignupBtn.classList.remove("active");
    loginForm.style.display = "flex";
    signupForm.style.display = "none";
    authModalTitle.textContent = pendingCheckout ? "Sign In to Place Order" : "Welcome Back";
    loginError.style.display = "none";
  } else {
    tabSignupBtn.classList.add("active");
    tabLoginBtn.classList.remove("active");
    signupForm.style.display = "flex";
    loginForm.style.display = "none";
    authModalTitle.textContent = pendingCheckout ? "Create Account to Place Order" : "Join AURA";
    signupError.style.display = "none";
  }
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  loginError.style.display = "none";
  const submitBtn = document.getElementById("login-submit-btn");
  submitBtn.disabled = true;
  submitBtn.textContent = "Signing In...";

  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: loginEmail.value.trim(),
        password: loginPassword.value
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || "Invalid email or password.");
    }

    // Save logged-in user
    currentUser = data.user;
    localStorage.setItem("aura_user", JSON.stringify(currentUser));

    // Merge saved wardrobe and bag from MongoDB
    if (data.user.wardrobe && data.user.wardrobe.length > 0) {
      wardrobeItems = data.user.wardrobe;
      localStorage.setItem("aura_wardrobe", JSON.stringify(wardrobeItems));
    }
    if (data.user.bag && data.user.bag.length > 0) {
      bagItems = data.user.bag;
      localStorage.setItem("aura_bag", JSON.stringify(bagItems));
    }

    updateAuthUI();
    updateBagUI();
    updateWardrobeUI();
    authModal.style.display = "none";
    loginForm.reset();

    // If user triggered login from checkout, proceed immediately
    if (pendingCheckout) {
      pendingCheckout = false;
      executeOrderCheckout();
    }
  } catch (err) {
    loginError.textContent = err.message;
    loginError.style.display = "block";
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Sign In";
  }
}

async function handleSignupSubmit(e) {
  e.preventDefault();
  signupError.style.display = "none";
  const submitBtn = document.getElementById("signup-submit-btn");
  submitBtn.disabled = true;
  submitBtn.textContent = "Creating Account...";

  try {
    const res = await fetch(`${API_BASE}/api/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: signupName.value.trim(),
        email: signupEmail.value.trim(),
        password: signupPassword.value
      })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      throw new Error(data.detail || data.error || "Sign up failed.");
    }

    currentUser = data.user;
    localStorage.setItem("aura_user", JSON.stringify(currentUser));

    syncUserDataWithMongo();

    updateAuthUI();
    updateBagUI();
    updateWardrobeUI();
    authModal.style.display = "none";
    signupForm.reset();

    // If user triggered sign up from checkout, proceed immediately
    if (pendingCheckout) {
      pendingCheckout = false;
      executeOrderCheckout();
    }
  } catch (err) {
    signupError.textContent = err.message;
    signupError.style.display = "block";
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Create Account";
  }
}

function logoutUser() {
  currentUser = null;
  localStorage.removeItem("aura_user");
  userDropdown.style.display = "none";
  updateAuthUI();
}

async function syncUserDataWithMongo() {
  if (!currentUser || !currentUser.email) return;
  try {
    await fetch(`${API_BASE}/api/user/sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: currentUser.email,
        wardrobe: wardrobeItems,
        bag: bagItems
      })
    });
  } catch (err) {
    console.log("Notice on syncing user collections to MongoDB:", err);
  }
}

// =====================================================================
// Checkout & Order Placement Logic (Auth Protected)
// =====================================================================

function handleCheckoutClick() {
  if (bagItems.length === 0) {
    alert("Your shopping bag is empty. Please add items to proceed with checkout.");
    return;
  }

  // If user is guest/not logged in, prompt Auth Modal with checkout context
  if (!currentUser) {
    openAuthModal("login", true);
    return;
  }

  executeOrderCheckout();
}

async function executeOrderCheckout() {
  if (bagItems.length === 0) return;

  let total = 0;
  bagItems.forEach(i => total += (i.price || 0));

  checkoutBtn.disabled = true;
  checkoutBtn.textContent = "Initiating Payment...";

  try {
    // 1. Create Razorpay Order on Backend
    const orderRes = await fetch(`${API_BASE}/api/create-order`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        amount: total,
        currency: "INR",
        receipt: `rcpt_${Date.now().toString(36)}`
      })
    });

    const orderData = await orderRes.json();
    if (!orderRes.ok || !orderData.order_id) {
      throw new Error(orderData.detail || "Failed to initialize payment gateway.");
    }

    // 2. Open Razorpay Standard Checkout Modal
    const options = {
      key: orderData.key_id,
      amount: orderData.amount,
      currency: orderData.currency || "INR",
      name: "AURA Luxury Fashion",
      description: "Curated Fashion Capsule Order",
      image: "https://images.unsplash.com/photo-1549298916-b41d501d3772?q=80&w=200&auto=format&fit=crop",
      order_id: orderData.order_id,
      handler: async function (response) {
        checkoutBtn.textContent = "Verifying Payment...";
        
        try {
          // 3. Verify Payment Signature on Backend
          const verifyRes = await fetch(`${API_BASE}/api/verify-payment`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              email: currentUser.email,
              items: bagItems,
              total: total
            })
          });

          const verifyData = await verifyRes.json();
          if (!verifyRes.ok || !verifyData.success) {
            throw new Error(verifyData.detail || "Payment signature verification failed.");
          }

          // Payment successfully verified & recorded in MongoDB
          bagItems = [];
          localStorage.setItem("aura_bag", JSON.stringify(bagItems));
          updateBagUI();

          bagDrawer.style.display = "none";
          if (orderRefId) {
            orderRefId.innerHTML = `${verifyData.order_id || 'ORD-AURA-2026'} <br><small style="color:var(--text-secondary);font-size:0.75rem;">(Razorpay ID: ${response.razorpay_payment_id})</small>`;
          }
          if (orderRefTotal) orderRefTotal.textContent = `$${total.toFixed(2)}`;
          if (orderSuccessModal) orderSuccessModal.style.display = "flex";
        } catch (vErr) {
          alert(`Verification Error: ${vErr.message}`);
        } finally {
          checkoutBtn.disabled = false;
          checkoutBtn.textContent = "Proceed to Checkout";
        }
      },
      prefill: {
        name: currentUser.name || "Customer",
        email: currentUser.email || "",
        contact: "9999999999"
      },
      notes: {
        customer_email: currentUser.email,
        item_count: bagItems.length.toString()
      },
      theme: {
        color: "#c5a059" // AURA signature luxury gold accent
      },
      modal: {
        ondismiss: function () {
          console.log("Razorpay checkout modal dismissed by user");
          checkoutBtn.disabled = false;
          checkoutBtn.textContent = "Proceed to Checkout";
        }
      }
    };

    const rzp = new Razorpay(options);

    rzp.on('payment.failed', function (response) {
      alert(`Payment Failed: ${response.error.description} (Reason: ${response.error.reason})`);
      checkoutBtn.disabled = false;
      checkoutBtn.textContent = "Proceed to Checkout";
    });

    rzp.open();
  } catch (err) {
    alert(`Checkout Error: ${err.message}`);
    checkoutBtn.disabled = false;
    checkoutBtn.textContent = "Proceed to Checkout";
  }
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
    handleAgentResponse(data);
  } catch (err) {
    console.error("API error:", err);
    processingCard.style.display = "none";
    alert("Connection error. Please ensure the server is running on http://127.0.0.1:8000");
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
    handleAgentResponse(data);
  } catch (err) {
    console.error("Clarification error:", err);
    processingCard.style.display = "none";
  }
}

function handleAgentResponse(data) {
  processingCard.style.display = "none";

  if (data.needs_clarification && data.clarification_question) {
    showClarificationCard(data.clarification_question);
    return;
  }

  // Render search results & upsells
  renderResults(data);
}

function animateProcessingSteps() {
  const steps = ["step-1", "step-2", "step-3", "step-4", "step-5"];
  steps.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.className = "step";
  });

  steps.forEach((id, index) => {
    setTimeout(() => {
      const el = document.getElementById(id);
      if (el) el.className = "step active";
    }, index * 300);
  });
}

function showClarificationCard(question) {
  clarificationQuestionText.textContent = question;
  clarificationCard.style.display = "flex";
  clarifyInput.value = "";
  clarifyInput.focus();

  // Setup pill buttons
  clarifyOptions.querySelectorAll(".clarify-pill").forEach(pill => {
    pill.onclick = () => {
      const ans = pill.getAttribute("data-answer");
      executeClarification(ans);
    };
  });
}

function renderResults(data) {
  const products = data.search_results || [];
  resultsSection.style.display = "block";
  editorialHome.style.display = "none";

  // Update headline & validation
  interpretationHeadline.textContent = `${products.length} Curated Selections Found`;
  
  const valRes = data.validation_result || {};
  if (valRes.explanation) {
    validationText.textContent = valRes.explanation;
  } else {
    validationText.textContent = "Verified by AI Concierge";
  }

  // Active filter pills
  renderFilterPills(data.filters || {});

  // Product cards
  productsGrid.innerHTML = "";
  if (products.length === 0) {
    productsGrid.innerHTML = `
      <div class="empty-state">
        <h3>No matching catalog pieces found</h3>
        <p>Try refining your inquiry or removing some constraint filters above.</p>
      </div>
    `;
    return;
  }

  products.forEach((prod, index) => {
    const card = document.createElement("div");
    card.className = "product-card";
    card.innerHTML = `
      <div class="card-image-wrap">
        <img src="${getSafeImageUrl(prod.image_url, index)}" alt="${prod.name}" onerror="this.src='${FALLBACK_IMAGES[index % FALLBACK_IMAGES.length]}'"/>
        <button class="save-bookmark-btn ${isSaved(prod.product_id) ? 'active' : ''}" title="Save to Wardrobe">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="${isSaved(prod.product_id) ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
          </svg>
        </button>
      </div>
      <div class="card-body">
        <div class="card-meta">
          <span class="card-brand">${prod.brand || 'Studio'}</span>
          <span class="card-rating">${prod.rating ? prod.rating.toFixed(1) + ' ★' : ''}</span>
        </div>
        <h3 class="card-title">${prod.name}</h3>
        <div class="card-footer">
          <span class="card-price">$${prod.price ? prod.price.toFixed(2) : '45.00'}</span>
          <button class="explore-outfit-btn">Complete Look</button>
        </div>
      </div>
    `;

    // Attach bookmark toggle
    const bookmarkBtn = card.querySelector(".save-bookmark-btn");
    bookmarkBtn.addEventListener("click", () => {
      toggleWardrobe(prod);
      bookmarkBtn.classList.toggle("active");
      const svg = bookmarkBtn.querySelector("svg");
      svg.setAttribute("fill", isSaved(prod.product_id) ? "currentColor" : "none");
    });

    // Attach outfit studio open
    card.querySelector(".explore-outfit-btn").addEventListener("click", () => {
      openOutfitStudio(prod);
    });

    productsGrid.appendChild(card);
  });
}

function renderFilterPills(filters) {
  activeFiltersRow.innerHTML = "";
  if (!filters || Object.keys(filters).length === 0) return;

  for (const [key, val] of Object.entries(filters)) {
    if (!val) continue;
    let label = `${key}: ${JSON.stringify(val)}`;
    if (key === "price" && typeof val === "object") {
      if (val.$lte) label = `Under $${val.$lte}`;
      else if (val.$gte) label = `Above $${val.$gte}`;
    } else if (typeof val === "string") {
      label = val;
    }

    const pill = document.createElement("div");
    pill.className = "filter-tag";
    pill.innerHTML = `
      <span>${label}</span>
      <button class="remove-btn" title="Remove constraint">&times;</button>
    `;
    pill.querySelector(".remove-btn").addEventListener("click", () => {
      pill.remove();
      executeQuery(`Show results without ${label}`);
    });
    activeFiltersRow.appendChild(pill);
  }
}

// =====================================================================
// Outfit Studio Modal ("Complete The Look")
// =====================================================================

async function openOutfitStudio(selectedProduct) {
  outfitModal.style.display = "flex";
  activeEnsembleProducts = [selectedProduct];

  // Render Anchor item on Left
  const safeImg = getSafeImageUrl(selectedProduct.image_url);
  anchorItemPanel.innerHTML = `
    <div class="anchor-badge">Anchor Piece</div>
    <img src="${safeImg}" class="anchor-img" alt="${selectedProduct.name}" onerror="this.onerror=null;this.src='${FALLBACK_IMAGES[0]}'"/>
    <div style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-secondary); margin-top: 0.75rem;">${selectedProduct.brand || 'Studio'}</div>
    <div class="anchor-name">${selectedProduct.name}</div>
    <div class="anchor-price">$${selectedProduct.price ? selectedProduct.price.toFixed(2) : '55.00'}</div>
    <button class="btn-primary" style="margin-top: 1rem; width: 100%;" id="add-anchor-btn">Add Piece Only</button>
  `;

  document.getElementById("add-anchor-btn").addEventListener("click", () => {
    addToBag(selectedProduct);
    outfitModal.style.display = "none";
    bagDrawer.style.display = "flex";
  });

  // Always re-run the dynamic AI Fashion Stylist Upsell Agent specifically for this clicked product
  stylistInsightText.textContent = `Curating bespoke complementary pieces and tonal harmony for ${selectedProduct.name}...`;
  ensembleCardsList.innerHTML = `<div style="color: var(--text-secondary); font-size: 0.85rem; padding: 1.5rem; text-align: center;">✦ AI Stylist is composing dynamic outfit pairings...</div>`;
  ensembleTotalPrice.textContent = `$${(selectedProduct.price || 55.00).toFixed(2)}`;

  let pairings = [];
  try {
    const res = await fetch(`${API_BASE}/api/outfit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_id: selectedProduct.product_id })
    });
    const data = await res.json();
    pairings = data.outfit_pairings || [];
  } catch (e) {
    console.error("Error generating outfit pairings:", e);
    pairings = [];
  }

  renderEnsembleItems(selectedProduct, pairings);
}

function renderEnsembleItems(selectedProduct, pairings) {
  ensembleCardsList.innerHTML = "";
  let total = selectedProduct.price || 55.00;

  if (pairings && pairings.length > 0) {
    const firstTip = pairings[0].stylist_note || pairings[0].compatibility_reason;
    stylistInsightText.textContent = firstTip || "Pairs impeccably with seasonal essentials for an elevated tonal look.";

    pairings.forEach((item, idx) => {
      activeEnsembleProducts.push(item);
      total += (item.price || 45.00);

      const pieceCard = document.createElement("div");
      pieceCard.className = "ensemble-piece-card";
      pieceCard.innerHTML = `
        <img src="${getSafeImageUrl(item.image_url, idx + 1)}" class="ensemble-piece-img" alt="${item.name}" onerror="this.onerror=null;this.src='${FALLBACK_IMAGES[(idx + 1) % FALLBACK_IMAGES.length]}'"/>
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
  syncUserDataWithMongo();
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
  syncUserDataWithMongo();
}

function removeFromBag(index) {
  bagItems.splice(index, 1);
  localStorage.setItem("aura_bag", JSON.stringify(bagItems));
  updateBagUI();
  syncUserDataWithMongo();
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

// =====================================================================
// Gen-Z Dynamic Streaming Placeholder Agent (openai/gpt-oss-20b)
// =====================================================================

const DEFAULT_GENZ_PROMPTS_CLIENT = [
  "main character energy, black oversized tailored blazer...",
  "clean girl aesthetic linen button-down for Sunday brunch...",
  "drop a vibe for a late night rooftop fit under $90...",
  "coastal granddaughter mood, breezy white sundress...",
  "stealth wealth minimal white leather sneakers on a budget...",
  "y2k vintage chronograph watch for the ultimate wrist flex...",
  "gym rat chic, breathable dry-fit compression tee under $40...",
  "quiet luxury cashmere knit sweater for evening dinner...",
  "blokecore retro jersey drip paired with relaxed denim...",
  "streetwear essentials, matte black cargo trousers under $60...",
  "old money aesthetic polo shirt in rich navy blue...",
  "dark academia tailored trousers with structured leather belt..."
];

let placeholderPool = [...DEFAULT_GENZ_PROMPTS_CLIENT];
let placeholderIndex = 0;
let isUserTypingOrFocused = false;
let currentTypewriterTimeout = null;

async function fetchFreshPlaceholderBatch() {
  try {
    const res = await fetch(`${API_BASE}/api/placeholder/batch?count=6`);
    if (res.ok) {
      const data = await res.json();
      if (data.prompts && data.prompts.length > 0) {
        placeholderPool.push(...data.prompts);
      }
    }
  } catch (e) {
    // Resilient client fallback
  }
}

async function getNextGenzPrompt() {
  try {
    const res = await fetch(`${API_BASE}/api/placeholder/next`);
    if (res.ok) {
      const data = await res.json();
      if (data.prompt) return data.prompt;
    }
  } catch (e) {}

  const prompt = placeholderPool[placeholderIndex % placeholderPool.length];
  placeholderIndex++;
  return prompt;
}

function initDynamicPlaceholderAgent() {
  const inputEl = document.getElementById("query-input");
  if (!inputEl) return;

  inputEl.addEventListener("focus", () => {
    isUserTypingOrFocused = true;
    if (currentTypewriterTimeout) clearTimeout(currentTypewriterTimeout);
    inputEl.placeholder = "Describe any outfit, aesthetic, brand, or occasion...";
  });

  inputEl.addEventListener("blur", () => {
    isUserTypingOrFocused = false;
    if (!inputEl.value.trim()) {
      if (currentTypewriterTimeout) clearTimeout(currentTypewriterTimeout);
      runPlaceholderCycle();
    }
  });

  inputEl.addEventListener("input", () => {
    if (inputEl.value && inputEl.value.trim()) {
      isUserTypingOrFocused = true;
      if (currentTypewriterTimeout) clearTimeout(currentTypewriterTimeout);
    }
  });

  // Pre-fetch fresh creative prompts from openai/gpt-oss-20b
  fetchFreshPlaceholderBatch();

  // Start the 10-second streaming cycle
  runPlaceholderCycle();
}

async function runPlaceholderCycle() {
  const inputEl = document.getElementById("query-input");
  if (!inputEl) return;
  if (isUserTypingOrFocused || (inputEl.value && inputEl.value.trim())) return;

  const targetPrompt = await getNextGenzPrompt();
  const prefix = "e.g., '";
  const suffix = "'";
  const fullText = `${prefix}${targetPrompt}${suffix}`;

  let currentLength = prefix.length;
  inputEl.placeholder = prefix;

  // Step 1: Sequential Typewriter (Token/Character streaming appearance)
  function typeChar() {
    if (isUserTypingOrFocused || (inputEl.value && inputEl.value.trim())) return;

    if (currentLength <= fullText.length) {
      inputEl.placeholder = fullText.slice(0, currentLength);
      currentLength++;
      currentTypewriterTimeout = setTimeout(typeChar, 28); // Silky ~28ms streaming speed
    } else {
      // Step 2: Stay displayed for 3.5 seconds (as requested for styling & reading)
      currentTypewriterTimeout = setTimeout(eraseChar, 3500);
    }
  }

  // Step 3: Sequential Erase (Disappear line-wise / character-wise)
  function eraseChar() {
    if (isUserTypingOrFocused || (inputEl.value && inputEl.value.trim())) return;

    if (currentLength >= prefix.length) {
      inputEl.placeholder = fullText.slice(0, currentLength);
      currentLength--;
      currentTypewriterTimeout = setTimeout(eraseChar, 14); // Fast ~14ms erase
    } else {
      // Step 4: Pause briefly and launch next Gen-Z prompt (~10s total cycle)
      currentTypewriterTimeout = setTimeout(runPlaceholderCycle, 800);
    }
  }

  typeChar();
}


/**
 * KHOJ — The Uncharted
 * Official Frontend Application Engine (Vanilla JavaScript)
 * Communicates with FastAPI Python Backend
 */

// Application State
const state = {
  currentQuery: "",
  currentDestination: "",
  currentCategory: "all",
  currentBudget: "all",
  currentSort: "relevance",
  places: [],
  systemHealth: null,
  activePlaceDetail: null,
  categories: [],
  isLoading: false,
};

// DOM Element References
const elements = {
  searchForm: document.getElementById("searchForm"),
  destinationInput: document.getElementById("destinationInput"),
  queryInput: document.getElementById("queryInput"),
  categorySelect: document.getElementById("categorySelect"),
  budgetSelect: document.getElementById("budgetSelect"),
  sortSelect: document.getElementById("sortSelect"),
  categoriesList: document.getElementById("categoriesList"),
  resultsGrid: document.getElementById("resultsGrid"),
  resultsSummary: document.getElementById("resultsSummary"),
  summaryText: document.getElementById("summaryText"),
  summarySourceBadge: document.getElementById("summarySourceBadge"),
  loadingState: document.getElementById("loadingState"),
  emptyState: document.getElementById("emptyState"),
  statusPill: document.getElementById("statusPill"),
  statusDot: document.getElementById("statusDot"),
  statusText: document.getElementById("statusText"),
  
  // Modals
  placeModal: document.getElementById("placeModal"),
  scoreModal: document.getElementById("scoreModal"),
  contributeModal: document.getElementById("contributeModal"),
  feedbackModal: document.getElementById("feedbackModal"),
  diagnosticsModal: document.getElementById("diagnosticsModal"),
  
  // Forms
  contributeForm: document.getElementById("contributeForm"),
  feedbackForm: document.getElementById("feedbackForm"),
  
  // Toast Container
  toastContainer: document.getElementById("toastContainer"),
};

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  fetchHealthStatus();
  fetchCategories();
  executeSearch(); // Initial load of benchmark discoveries
});

// Event Listeners Setup
function initEventListeners() {
  // Search Form Submit
  if (elements.searchForm) {
    elements.searchForm.addEventListener("submit", (e) => {
      e.preventDefault();
      state.currentDestination = elements.destinationInput.value.trim();
      state.currentQuery = elements.queryInput.value.trim();
      state.currentCategory = elements.categorySelect.value;
      state.currentBudget = elements.budgetSelect.value;
      executeSearch();
    });
  }

  // Sort Dropdown
  if (elements.sortSelect) {
    elements.sortSelect.addEventListener("change", (e) => {
      state.currentSort = e.target.value;
      sortAndRenderPlaces();
    });
  }

  // Quick Chips
  document.querySelectorAll(".chip-btn").forEach((chip) => {
    chip.addEventListener("click", () => {
      const dest = chip.getAttribute("data-dest") || "";
      const query = chip.getAttribute("data-query") || "";
      const cat = chip.getAttribute("data-cat") || "all";
      
      elements.destinationInput.value = dest;
      elements.queryInput.value = query;
      elements.categorySelect.value = cat;
      
      state.currentDestination = dest;
      state.currentQuery = query;
      state.currentCategory = cat;
      executeSearch();
      
      // Scroll to results
      const resultsSection = document.getElementById("resultsSection");
      if (resultsSection) {
        resultsSection.scrollIntoView({ behavior: "smooth" });
      }
    });
  });

  // Modal Closers
  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      closeAllModals();
    });
  });

  // Close modal on background click
  document.querySelectorAll(".modal-overlay").forEach((modal) => {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        closeAllModals();
      }
    });
  });

  // Status Pill Click -> Opens Diagnostics Modal
  if (elements.statusPill) {
    elements.statusPill.addEventListener("click", () => {
      openDiagnosticsModal();
    });
  }

  // Contribute CTA Buttons
  document.querySelectorAll("[data-open-contribute]").forEach((btn) => {
    btn.addEventListener("click", () => {
      openContributeModal();
    });
  });

  // Contribute Form Submit
  if (elements.contributeForm) {
    elements.contributeForm.addEventListener("submit", handleContributeSubmit);
  }

  // Feedback Form Submit
  if (elements.feedbackForm) {
    elements.feedbackForm.addEventListener("submit", handleFeedbackSubmit);
  }

  // Escape key closes modals
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeAllModals();
    }
  });
}

// --------------------------------------------------------------------------
// API Client Functions
// --------------------------------------------------------------------------

/**
 * Checks system health & TinyFish operational status.
 */
async function fetchHealthStatus() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) throw new Error("Health check degraded");
    const data = await res.json();
    state.systemHealth = data;
    updateStatusPill(data);
  } catch (err) {
    console.warn("Health check error:", err);
    updateStatusPill({
      status: "offline",
      tinyfish_configured: false,
      tinyfish_mode: "offline"
    });
  }
}

/**
 * Updates header status indicator pill.
 */
function updateStatusPill(health) {
  if (!elements.statusPill) return;
  
  if (health.tinyfish_configured) {
    elements.statusDot.className = "status-dot active";
    elements.statusText.textContent = "TinyFish Live Web Active";
    elements.statusPill.title = "Connected to TinyFish AI crawler platform";
  } else {
    elements.statusDot.className = "status-dot";
    elements.statusText.textContent = "Knowledge Archive Mode";
    elements.statusPill.title = "Operating in verified local archive mode (TINYFISH_API_KEY pending)";
  }
}

/**
 * Fetches standard taxonomy categories and counts.
 */
async function fetchCategories() {
  try {
    const res = await fetch("/api/discovery/categories");
    if (!res.ok) throw new Error("Failed to load categories");
    const data = await res.json();
    state.categories = data.categories || [];
    renderCategoriesBar(state.categories);
  } catch (err) {
    console.error("Categories fetch error:", err);
  }
}

/**
 * Renders category navigation pills bar.
 */
function renderCategoriesBar(categories) {
  if (!elements.categoriesList) return;
  
  let html = `
    <button class="cat-pill ${state.currentCategory === 'all' ? 'active' : ''}" data-cat="all">
      🧭 All Discoveries
    </button>
  `;

  categories.forEach((cat) => {
    const isActive = state.currentCategory === cat.id ? "active" : "";
    html += `
      <button class="cat-pill ${isActive}" data-cat="${cat.id}">
        ${getCategoryIcon(cat.id)} ${cat.title}
        <span class="count-badge">${cat.count}</span>
      </button>
    `;
  });

  elements.categoriesList.innerHTML = html;

  // Add click listeners to category pills
  elements.categoriesList.querySelectorAll(".cat-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      const selectedCat = pill.getAttribute("data-cat");
      state.currentCategory = selectedCat;
      if (elements.categorySelect) {
        elements.categorySelect.value = selectedCat;
      }
      
      // Update active pill UI
      elements.categoriesList.querySelectorAll(".cat-pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      
      executeSearch();
    });
  });
}

/**
 * Core Search and Retrieval: Calls FastAPI backend.
 */
async function executeSearch() {
  setLoading(true);

  try {
    const payload = {
      query: state.currentQuery,
      destination: state.currentDestination,
      category: state.currentCategory !== "all" ? state.currentCategory : null,
      budget: state.currentBudget !== "all" ? state.currentBudget : null
    };

    // Use POST /api/search with fallback to GET /api/search
    const res = await fetch("/api/search", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      throw new Error(`Search failed with status ${res.status}`);
    }

    const data = await res.json();
    state.places = data.results || [];

    // Render results
    renderResultsSummary(data);
    sortAndRenderPlaces();

  } catch (err) {
    console.error("Search execution error:", err);
    showToast("Search failed: " + err.message, "error");
    if (elements.resultsGrid) {
      elements.resultsGrid.innerHTML = `
        <div class="empty-state" style="grid-column: 1 / -1;">
          <div class="empty-icon">⚠️</div>
          <h3>Unable to complete search</h3>
          <p>${err.message}. Please check your connection to the FastAPI server.</p>
        </div>
      `;
    }
  } finally {
    setLoading(false);
  }
}

/**
 * Updates search summary bar with query metrics and TinyFish metadata.
 */
function renderResultsSummary(data) {
  if (!elements.resultsSummary) return;

  const total = data.total_results || 0;
  const liveCount = data.live_retrieved_count || 0;
  const places = data.results || [];
  const communityCount = places.filter(p => p.source_type === "community_verified").length;
  const archiveCount = places.filter(p => p.source_type !== "community_verified" && p.source_type !== "live_tinyfish").length;
  const tfStatus = data.tinyfish_status || {};

  let queryLabel = "All Discoveries";
  if (data.destination && data.query) {
    queryLabel = `"${data.query}" in ${data.destination}`;
  } else if (data.destination) {
    queryLabel = `Places around ${data.destination}`;
  } else if (data.query) {
    queryLabel = `Query matching "${data.query}"`;
  }

  elements.summaryText.innerHTML = `Found <strong>${total}</strong> discoveries for <span style="color: var(--color-forest-teal);">${queryLabel}</span>`;

  let badgesHtml = "";
  if (liveCount > 0) {
    badgesHtml += `
      <span class="badge-source-live">
        <span class="status-dot active"></span>
        ${liveCount} Live TinyFish Scrapes
      </span>
    `;
  }
  if (communityCount > 0) {
    badgesHtml += `
      <span class="badge-source-community" style="background: #E8F5E9; color: #1B5E20; border: 1px solid #A5D6A7; font-size: 11px; padding: 3px 10px; border-radius: 9999px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">
        🌱 ${communityCount} Community Discoveries
      </span>
    `;
  }
  if (archiveCount > 0) {
    badgesHtml += `
      <span class="badge-source-archive">
        🏛️ ${archiveCount} Curated Records
      </span>
    `;
  }
  if (liveCount === 0 && tfStatus.is_configured === false) {
    badgesHtml += `<span style="font-size: 11px; color: #8F601C; background: #FEF3C7; padding: 2px 8px; border-radius: 9999px;">TinyFish key pending</span>`;
  }

  elements.summarySourceBadge.innerHTML = badgesHtml;
}

/**
 * Sorts state.places according to state.currentSort and renders cards.
 */
function sortAndRenderPlaces() {
  if (!elements.resultsGrid) return;

  if (state.places.length === 0) {
    elements.resultsGrid.style.display = "none";
    if (elements.emptyState) elements.emptyState.style.display = "block";
    return;
  }

  if (elements.emptyState) elements.emptyState.style.display = "none";
  elements.resultsGrid.style.display = "grid";

  // Sort places
  const sorted = [...state.places];
  if (state.currentSort === "relevance") {
    sorted.sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
  } else if (state.currentSort === "upvotes") {
    sorted.sort((a, b) => (b.upvotes || 0) - (a.upvotes || 0));
  } else if (state.currentSort === "completeness") {
    sorted.sort((a, b) => (b.score_breakdown?.information_completeness || 0) - (a.score_breakdown?.information_completeness || 0));
  } else if (state.currentSort === "freshness") {
    sorted.sort((a, b) => (b.score_breakdown?.source_freshness || 0) - (a.score_breakdown?.source_freshness || 0));
  }

  elements.resultsGrid.innerHTML = sorted.map((place) => createPlaceCardHTML(place)).join("");

  // Attach card event listeners
  attachCardListeners();
}

/**
 * Generates HTML for an individual discovery place card.
 */
function createPlaceCardHTML(place) {
  const claimBadge = getClaimBadge(place.claim_type);
  const sourceBadge = getSourceBadge(place.source_type);
  const practicalTips = Array.isArray(place.practical_tips) ? place.practical_tips : [];
  const missingFlags = Array.isArray(place.missing_fields_flag) ? place.missing_fields_flag : [];
  
  // Format formatted timestamp
  const retrievedTime = place.retrieved_at ? formatTimeAgo(place.retrieved_at) : "Recently";

  return `
    <article class="place-card" data-place-id="${place.id}">
      <header class="place-card-header">
        <div class="place-badges-row">
          <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
            <span class="cat-badge">${getCategoryName(place.category)}</span>
            ${sourceBadge}
          </div>
          ${claimBadge}
        </div>
        <h3 class="place-title">${escapeHTML(place.name)}</h3>
        <div class="place-destination">
          <span>📍</span>
          <span>${escapeHTML(place.destination)}</span>
          <span style="margin: 0 4px;">•</span>
          <span style="text-transform: capitalize; font-weight: 500;">${getBudgetLabel(place.budget_tier)}</span>
        </div>
      </header>

      <div class="place-card-body">
        <p class="place-description">${escapeHTML(place.short_description)}</p>

        <div class="why-explore-box">
          <strong>Why It's Worth Exploring</strong>
          ${escapeHTML(truncateText(place.detailed_story, 160))}
        </div>

        ${practicalTips.length > 0 ? `
          <div class="practical-preview">
            <ul class="tips-preview-list">
              ${practicalTips.slice(0, 2).map(tip => `<li>${escapeHTML(tip)}</li>`).join("")}
            </ul>
          </div>
        ` : ''}

        ${missingFlags.length > 0 ? `
          <div class="missing-fields-box">
            <span class="title">⚠️ Notice:</span>
            <span>${escapeHTML(missingFlags[0])}</span>
          </div>
        ` : ''}
      </div>

      <footer class="place-card-footer">
        <div class="source-info">
          ${place.source_url ? `
            <a href="${escapeHTML(place.source_url)}" target="_blank" rel="noopener noreferrer" class="source-link" title="${escapeHTML(place.source_title || place.source_url)}">
              🔗 ${escapeHTML(place.source_title || 'Public Source')}
            </a>
          ` : `
            <span class="source-link" style="color: #7E908D;">Archive Source</span>
          `}
          <span class="source-time">Checked ${retrievedTime}</span>
        </div>

        <div class="card-actions">
          <button class="score-badge" data-action="view-score" data-place-id="${place.id}" title="Click to view rule-based scoring calculation">
            ⚡ ${place.relevance_score || 0} pts
          </button>
          
          <button class="btn-upvote" data-action="upvote" data-place-id="${place.id}">
            ▲ <span class="upvote-count">${place.upvotes || 0}</span>
          </button>

          <button class="btn-view-story" data-action="view-story" data-place-id="${place.id}">
            Explore Story
          </button>
        </div>
      </footer>
    </article>
  `;
}

/**
 * Attaches click handlers to place card buttons.
 */
function attachCardListeners() {
  // View Story / Place Details Modal
  document.querySelectorAll("[data-action='view-story']").forEach((btn) => {
    btn.addEventListener("click", () => {
      const placeId = parseInt(btn.getAttribute("data-place-id"), 10);
      openPlaceDetailModal(placeId);
    });
  });

  // Upvote Button
  document.querySelectorAll("[data-action='upvote']").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const placeId = parseInt(btn.getAttribute("data-place-id"), 10);
      await handleUpvote(placeId, btn);
    });
  });

  // Score Breakdown Button
  document.querySelectorAll("[data-action='view-score']").forEach((btn) => {
    btn.addEventListener("click", () => {
      const placeId = parseInt(btn.getAttribute("data-place-id"), 10);
      openScoreModal(placeId);
    });
  });
}

/**
 * Upvotes a place using the backend API.
 */
async function handleUpvote(placeId, btnElement) {
  if (btnElement.classList.contains("voted")) {
    showToast("You have already upvoted this discovery.", "info");
    return;
  }

  try {
    const res = await fetch(`/api/places/${placeId}/upvote`, {
      method: "POST"
    });
    if (!res.ok) throw new Error("Upvote failed");
    const data = await res.json();
    
    // Update local state and button text
    btnElement.classList.add("voted");
    const countSpan = btnElement.querySelector(".upvote-count");
    if (countSpan) {
      countSpan.textContent = data.upvotes;
    }
    
    // Update place in state
    const place = state.places.find(p => p.id === placeId);
    if (place) place.upvotes = data.upvotes;
    
    showToast("Helpful discovery upvoted! Thank you.", "success");
  } catch (err) {
    console.error("Upvote error:", err);
    showToast("Unable to record upvote right now.", "error");
  }
}

// --------------------------------------------------------------------------
// Modals Handling
// --------------------------------------------------------------------------

/**
 * Opens Place Details Modal (Feature 4).
 */
function openPlaceDetailModal(placeId) {
  const place = state.places.find(p => p.id === placeId);
  if (!place) return;

  state.activePlaceDetail = place;

  const titleEl = document.getElementById("modalPlaceTitle");
  const destEl = document.getElementById("modalPlaceDest");
  const storyEl = document.getElementById("modalPlaceStory");
  const claimNoticeEl = document.getElementById("modalClaimNotice");
  const tipsListEl = document.getElementById("modalTipsList");
  const missingBoxEl = document.getElementById("modalMissingBox");
  const sourceLinkEl = document.getElementById("modalSourceLink");
  const modalUpvoteBtn = document.getElementById("modalUpvoteBtn");
  const modalFeedbackTrigger = document.getElementById("modalFeedbackTrigger");

  const sourceBadge = getSourceBadge(place.source_type);

  if (titleEl) titleEl.textContent = place.name;
  if (destEl) destEl.innerHTML = `📍 ${escapeHTML(place.destination)} • <span>Category: ${getCategoryName(place.category)}</span> • <span>${sourceBadge}</span> • <span>Budget: ${place.budget_tier}</span>`;
  if (storyEl) storyEl.textContent = place.detailed_story;

  // Claim notice
  if (claimNoticeEl) {
    if (place.claim_type === "documented_history") {
      claimNoticeEl.innerHTML = `
        <div style="background: #EDF4FF; border-left: 4px solid #1D4ED8; padding: 10px 14px; border-radius: 4px; font-size: 13px; color: #1E40AF;">
          <strong>🏛️ Documented Historical Record:</strong> Supported by archaeological documentation, state gazetteers, or historical records.
        </div>
      `;
    } else if (place.claim_type === "folklore_oral_tradition") {
      claimNoticeEl.innerHTML = `
        <div style="background: #FEF3C7; border-left: 4px solid #D97706; padding: 10px 14px; border-radius: 4px; font-size: 13px; color: #92400E;">
          <strong>📜 Cultural Folklore & Oral Tradition:</strong> Rooted in local myths and oral tales passed down through generations.
        </div>
      `;
    } else {
      claimNoticeEl.innerHTML = `
        <div style="background: #F3E8FF; border-left: 4px solid #9333EA; padding: 10px 14px; border-radius: 4px; font-size: 13px; color: #6B21A8;">
          <strong>👥 Living Community Experience:</strong> Shared directly by local travellers and community residents.
        </div>
      `;
    }
  }

  // Tips list
  if (tipsListEl) {
    const tips = Array.isArray(place.practical_tips) ? place.practical_tips : [];
    if (tips.length > 0) {
      tipsListEl.innerHTML = tips.map(tip => `<li>💡 ${escapeHTML(tip)}</li>`).join("");
    } else {
      tipsListEl.innerHTML = `<li style="color: #7E908D;">No specific tips submitted yet. Share yours below!</li>`;
    }
  }

  // Missing fields flags
  if (missingBoxEl) {
    const flags = Array.isArray(place.missing_fields_flag) ? place.missing_fields_flag : [];
    if (flags.length > 0) {
      missingBoxEl.style.display = "block";
      missingBoxEl.innerHTML = `
        <div class="missing-fields-box">
          <span class="title">⚠️ Missing / Unverified Details Notice:</span>
          <p style="margin-top: 4px; font-size: 12px;">KHOJ transparently flags unverified data rather than fabricating details:</p>
          <ul style="margin-left: 18px; margin-top: 4px;">
            ${flags.map(f => `<li>${escapeHTML(f)}</li>`).join("")}
          </ul>
        </div>
      `;
    } else {
      missingBoxEl.style.display = "none";
    }
  }

  // Source link
  if (sourceLinkEl) {
    if (place.source_url) {
      sourceLinkEl.innerHTML = `
        <strong>Source Reference:</strong> 
        <a href="${escapeHTML(place.source_url)}" target="_blank" rel="noopener noreferrer" style="color: var(--color-forest-teal); font-weight: 600;">
          ${escapeHTML(place.source_title || place.source_url)} ↗
        </a>
        <div style="font-size: 11px; color: #7E908D; margin-top: 2px;">
          Retrieved / Checked: ${new Date(place.retrieved_at).toLocaleString()} via ${place.source_type}
        </div>
      `;
    } else {
      sourceLinkEl.innerHTML = `
        <strong>Source Reference:</strong> Verified Community Heritage Archive
      `;
    }
  }

  // Modal Upvote button
  if (modalUpvoteBtn) {
    modalUpvoteBtn.innerHTML = `▲ Upvote (${place.upvotes || 0})`;
    modalUpvoteBtn.onclick = async () => {
      await handleUpvote(place.id, modalUpvoteBtn);
    };
  }

  // Trigger feedback
  if (modalFeedbackTrigger) {
    modalFeedbackTrigger.onclick = () => {
      closeAllModals();
      openFeedbackModal(place.id, place.name);
    };
  }

  openModal(elements.placeModal);
}

/**
 * Opens Transparent Scoring Breakdown Modal.
 */
function openScoreModal(placeId) {
  const place = state.places.find(p => p.id === placeId);
  if (!place || !place.score_breakdown) return;

  const titleEl = document.getElementById("scoreModalTitle");
  const contentEl = document.getElementById("scoreModalContent");

  if (titleEl) {
    titleEl.textContent = `Ranking Breakdown: ${place.name}`;
  }

  const breakdown = place.score_breakdown;

  if (contentEl) {
    contentEl.innerHTML = `
      <p style="font-size: 13px; color: var(--color-charcoal-light); margin-bottom: 16px;">
        KHOJ uses transparent, explainable Python rule-based scoring (0-100 pts) rather than opaque black-box estimates:
      </p>

      <table class="score-breakdown-table">
        <thead>
          <tr>
            <th>Evaluation Factor</th>
            <th>Max Weight</th>
            <th>Awarded Points</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Search Query Relevance</strong><br><span style="font-size: 11px; color: #7E908D;">Token matches in name, destination & story</span></td>
            <td>35 pts</td>
            <td><strong>+${breakdown.query_relevance} pts</strong></td>
          </tr>
          <tr>
            <td><strong>Category Alignment</strong><br><span style="font-size: 11px; color: #7E908D;">Requested travel interest match</span></td>
            <td>25 pts</td>
            <td><strong>+${breakdown.category_match} pts</strong></td>
          </tr>
          <tr>
            <td><strong>Information Completeness</strong><br><span style="font-size: 11px; color: #7E908D;">Practical tips, rich context, verified source link</span></td>
            <td>20 pts</td>
            <td><strong>+${breakdown.information_completeness} pts</strong></td>
          </tr>
          <tr>
            <td><strong>Source Freshness & Credibility</strong><br><span style="font-size: 11px; color: #7E908D;">Live TinyFish scrape or recently verified archive</span></td>
            <td>15 pts</td>
            <td><strong>+${breakdown.source_freshness} pts</strong></td>
          </tr>
          <tr>
            <td><strong>Budget Alignment</strong><br><span style="font-size: 11px; color: #7E908D;">Filter preference match</span></td>
            <td>5 pts</td>
            <td><strong>+${breakdown.budget_match} pts</strong></td>
          </tr>
          <tr style="background: var(--color-sage-light); font-weight: bold;">
            <td>Total Explainable Score</td>
            <td>100 pts</td>
            <td><strong style="color: var(--color-forest-teal); font-size: 16px;">${breakdown.total_score} pts</strong></td>
          </tr>
        </tbody>
      </table>

      <div style="margin-top: 18px; padding: 12px; background: var(--color-ivory); border-radius: var(--radius-sm); font-size: 12px; color: var(--color-forest-teal);">
        <strong>Score Summary Explanation:</strong><br>
        ${escapeHTML(breakdown.explanation || 'Calculated based on search parameters and verified source attributes.')}
      </div>
    `;
  }

  openModal(elements.scoreModal);
}

/**
 * Opens Community Contribution Modal (Feature 5).
 */
function openContributeModal() {
  if (elements.contributeForm) {
    elements.contributeForm.reset();
  }
  openModal(elements.contributeModal);
}

/**
 * Handles Community Contribution Submission.
 */
async function handleContributeSubmit(e) {
  e.preventDefault();
  
  const placeName = document.getElementById("contribPlaceName").value.trim();
  const destination = document.getElementById("contribDestination").value.trim();
  const category = document.getElementById("contribCategory").value;
  const contribType = document.getElementById("contribType").value;
  const details = document.getElementById("contribDetails").value.trim();
  const tips = document.getElementById("contribTips").value.trim();
  const sourceRef = document.getElementById("contribSource").value.trim();
  const contributorName = document.getElementById("contribName").value.trim();

  if (details.length < 15) {
    showToast("Please provide at least 15 characters describing the place or story.", "error");
    return;
  }

  const payload = {
    place_name: placeName,
    destination: destination,
    category: category,
    contribution_type: contribType,
    details: details,
    practical_tips: tips,
    source_reference: sourceRef,
    contributor_name: contributorName || "Anonymous Explorer"
  };

  try {
    const res = await fetch("/api/contributions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      let errMsg = "Submission rejected by server";
      try {
        const errJson = await res.json();
        if (errJson && errJson.detail) errMsg = errJson.detail;
      } catch (_) {}
      throw new Error(errMsg);
    }

    const data = await res.json();

    closeAllModals();
    showToast(`Discovery "${placeName}" saved to KHOJ knowledge base!`, "success");

    // Reset contribution form
    if (elements.contributeForm) {
      elements.contributeForm.reset();
    }

    // Reset search filters so the newly saved discovery is immediately visible
    if (elements.destinationInput) elements.destinationInput.value = "";
    if (elements.queryInput) elements.queryInput.value = "";
    if (elements.categorySelect) elements.categorySelect.value = "all";
    if (elements.budgetSelect) elements.budgetSelect.value = "all";
    state.currentDestination = "";
    state.currentQuery = "";
    state.currentCategory = "all";
    state.currentBudget = "all";

    // Refresh discoveries directly from persistent backend
    await executeSearch();

    // Scroll to results to view the newly saved discovery
    const resultsSection = document.getElementById("resultsSection");
    if (resultsSection) {
      resultsSection.scrollIntoView({ behavior: "smooth" });
    }

  } catch (err) {
    console.error("Contribution error:", err);
    showToast(err.message, "error");
  }
}

/**
 * Opens Feedback / Correction Modal (Feature 6).
 */
function openFeedbackModal(placeId = null, placeName = "") {
  if (elements.feedbackForm) {
    elements.feedbackForm.reset();
    document.getElementById("feedbackPlaceId").value = placeId || "";
    document.getElementById("feedbackPlaceName").value = placeName || "";
  }
  openModal(elements.feedbackModal);
}

/**
 * Handles Feedback / Inaccuracy Report Submission.
 */
async function handleFeedbackSubmit(e) {
  e.preventDefault();

  const placeIdRaw = document.getElementById("feedbackPlaceId").value;
  const placeName = document.getElementById("feedbackPlaceName").value.trim();
  const reportType = document.getElementById("feedbackType").value;
  const notes = document.getElementById("feedbackNotes").value.trim();

  if (!placeName || notes.length < 5) {
    showToast("Please provide the place name and detailed feedback.", "error");
    return;
  }

  const payload = {
    place_id: placeIdRaw ? parseInt(placeIdRaw, 10) : null,
    place_name: placeName,
    report_type: reportType,
    notes: notes
  };

  try {
    const res = await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error("Feedback submission error");
    const data = await res.json();

    closeAllModals();
    showToast(`Feedback report #${data.id} recorded. Our editors will verify it.`, "success");
  } catch (err) {
    console.error("Feedback error:", err);
    showToast("Unable to submit feedback: " + err.message, "error");
  }
}

/**
 * Opens System Diagnostics Modal.
 */
function openDiagnosticsModal() {
  const contentEl = document.getElementById("diagnosticsContent");
  if (!contentEl) return;

  const h = state.systemHealth || {};
  const db = h.database || {};

  contentEl.innerHTML = `
    <div style="font-size: 13px; display: flex; flex-direction: column; gap: 14px;">
      <div style="padding: 12px; background: var(--color-ivory); border-radius: var(--radius-sm); border-left: 3px solid var(--color-forest-teal);">
        <h4 style="color: var(--color-forest-teal); margin-bottom: 4px;">KHOJ Engine & Stack</h4>
        <div><strong>Application:</strong> ${h.app_name || 'KHOJ — The Uncharted'} v${h.version || '1.0.0'}</div>
        <div><strong>Backend:</strong> Python + FastAPI (Asynchronous REST API)</div>
        <div><strong>Frontend:</strong> HTML5 + CSS3 + Vanilla JavaScript (Framework-free)</div>
        <div><strong>Status:</strong> <span style="color: ${h.status === 'healthy' ? '#0E6245' : '#D97706'}; font-weight: 700;">${h.status || 'Active'}</span></div>
      </div>

      <div style="padding: 12px; background: var(--color-ivory); border-radius: var(--radius-sm); border-left: 3px solid #D97706;">
        <h4 style="color: #B45309; margin-bottom: 4px;">TinyFish Web Intelligence Integration</h4>
        <div><strong>Status:</strong> ${h.tinyfish_configured ? '<span style="color: #0E6245; font-weight: 700;">Configured & Ready</span>' : '<span style="color: #92400E; font-weight: 700;">Curated Knowledge Archive Mode (API Key Pending)</span>'}</div>
        <div><strong>Mode:</strong> ${h.tinyfish_mode || 'curated_archive_fallback'}</div>
        <div style="font-size: 12px; color: var(--color-charcoal-light); margin-top: 4px;">
          To activate live web crawling, obtain an API key from <a href="https://agent.tinyfish.ai/api-keys" target="_blank" style="color: var(--color-forest-teal); text-decoration: underline;">agent.tinyfish.ai</a> and set <code>TINYFISH_API_KEY=...</code> in <code>backend/.env</code>.
        </div>
      </div>

      <div style="padding: 12px; background: var(--color-ivory); border-radius: var(--radius-sm); border-left: 3px solid #1D4ED8;">
        <h4 style="color: #1D4ED8; margin-bottom: 4px;">Persistent Storage Health</h4>
        <div><strong>Database Engine:</strong> ${db.engine || 'SQLite'} (Persistent Storage)</div>
        <div><strong>Total Curated Places:</strong> ${db.places_count || 0}</div>
        <div><strong>Community Submissions:</strong> ${db.contributions_count || 0}</div>
        <div><strong>Feedback & Corrections:</strong> ${db.feedback_count || 0}</div>
      </div>
    </div>
  `;

  openModal(elements.diagnosticsModal);
}

function openModal(modalEl) {
  if (modalEl) modalEl.classList.add("open");
  document.body.style.overflow = "hidden";
}

function closeAllModals() {
  document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("open"));
  document.body.style.overflow = "";
}

// --------------------------------------------------------------------------
// UI Helpers
// --------------------------------------------------------------------------

function setLoading(isLoading) {
  state.isLoading = isLoading;
  if (elements.loadingState) {
    elements.loadingState.style.display = isLoading ? "block" : "none";
  }
  if (elements.resultsGrid && isLoading) {
    elements.resultsGrid.style.display = "none";
  }
}

function getCategoryIcon(catId) {
  const icons = {
    culture_history: "🏛️",
    local_food: "🍲",
    markets_shopping: "🛍️",
    nature_scenic: "🌲",
    local_experiences: "🏮"
  };
  return icons[catId] || "📍";
}

function getCategoryName(catId) {
  const names = {
    culture_history: "Culture & History",
    local_food: "Local Food",
    markets_shopping: "Markets & Crafts",
    nature_scenic: "Nature & Scenic",
    local_experiences: "Living Heritage"
  };
  return names[catId] || catId;
}

function getBudgetLabel(budgetTier) {
  const labels = {
    free: "Free Entry",
    budget: "Budget Friendly",
    moderate: "Moderate Budget",
    splurge: "Splurge"
  };
  return labels[budgetTier] || "Moderate Budget";
}

function getClaimBadge(claimType) {
  if (claimType === "documented_history") {
    return `<span class="claim-badge claim-documented" title="Supported by archaeological or archival documentation">🛡️ Documented History</span>`;
  } else if (claimType === "folklore_oral_tradition") {
    return `<span class="claim-badge claim-folklore" title="Local folklore and sacred oral traditions">📜 Cultural Lore</span>`;
  }
  return `<span class="claim-badge claim-community" title="Shared by community travellers & local residents">👥 Community Experience</span>`;
}

function getSourceBadge(sourceType) {
  if (sourceType === "live_tinyfish") {
    return `<span class="badge-source-live"><span class="status-dot active"></span> Live TinyFish</span>`;
  } else if (sourceType === "community_verified") {
    return `<span class="badge-source-community" style="background: #E8F5E9; color: #1B5E20; border: 1px solid #A5D6A7; font-size: 11px; padding: 2px 8px; border-radius: 9999px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">🌱 Community Discovery</span>`;
  }
  return `<span class="badge-source-archive">🏛️ Verified Archive</span>`;
}

function truncateText(str, maxLen = 140) {
  if (!str) return "";
  if (str.length <= maxLen) return str;
  return str.substring(0, maxLen).trim() + "…";
}

function formatTimeAgo(isoString) {
  try {
    const diffMs = Date.now() - new Date(isoString).getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours < 1) return "just now";
    if (diffHours === 1) return "1 hour ago";
    if (diffHours < 24) return `${diffHours} hours ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return "yesterday";
    return `${diffDays} days ago`;
  } catch (e) {
    return "recently";
  }
}

function escapeHTML(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function showToast(message, type = "info") {
  if (!elements.toastContainer) return;

  const toast = document.createElement("div");
  toast.className = "toast";
  if (type === "error") {
    toast.style.borderLeftColor = "#EF4444";
  } else if (type === "success") {
    toast.style.borderLeftColor = "#10B981";
  }

  const icon = type === "error" ? "❌" : type === "success" ? "✅" : "ℹ️";
  toast.innerHTML = `<span>${icon}</span><span>${escapeHTML(message)}</span>`;

  elements.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(50px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, 4000);
}

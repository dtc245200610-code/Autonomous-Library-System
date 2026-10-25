/**
 * ATHENA SMARTLIB - CLIENT APPLICATION CONTROLLER
 * Handles interactive SPA views, live queries, REST API communication,
 * Chart.js analytics, and real-time modal operations.
 */

// Global State
const state = {
  currentView: 'books', // 'books' | 'ledger' | 'patrons'
  books: [],
  categories: [],
  patrons: [],
  borrowings: [],
  stats: null,
  activeCategory: null,
  availableOnly: false,
  searchQuery: '',
  charts: {
    category: null
  }
};

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', () => {
  initEventListeners();
  loadInitialData();
  // Poll stats and health every 30s
  setInterval(refreshStatsAndHealth, 30000);
});

function initEventListeners() {
  // Search input debounce
  const searchInput = document.getElementById('searchInput');
  let debounceTimeout = null;
  searchInput.addEventListener('input', (e) => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      state.searchQuery = e.target.value.trim();
      renderCurrentView();
    }, 250);
  });

  // Available only checkbox
  const availableToggle = document.getElementById('availableOnlyToggle');
  availableToggle.addEventListener('change', (e) => {
    state.availableOnly = e.target.checked;
    loadBooks();
  });

  // View navigation tabs
  document.querySelectorAll('.view-tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
      document.querySelectorAll('.view-tab').forEach(t => t.classList.remove('active'));
      const targetTab = e.currentTarget;
      targetTab.classList.add('active');
      state.currentView = targetTab.dataset.view;
      switchView(state.currentView);
    });
  });

  // Form Submissions
  document.getElementById('formAddBook').addEventListener('submit', handleAddBookSubmit);
  document.getElementById('formAddPatron').addEventListener('submit', handleAddPatronSubmit);
  document.getElementById('formBorrow').addEventListener('submit', handleBorrowSubmit);
}

// ======================== DATA LOADING ========================

async function loadInitialData() {
  await Promise.all([
    loadCategories(),
    loadBooks(),
    loadPatrons(),
    loadBorrowings(),
    refreshStatsAndHealth()
  ]);
  renderCategoryPills();
}

async function refreshStatsAndHealth() {
  try {
    const res = await fetch('/api/stats');
    const json = await res.json();
    if (json.success) {
      state.stats = json.data;
      updateKpis(json.data);
      renderCategoryChart(json.data.categories);
    }

    const healthRes = await fetch('/api/health');
    const healthJson = await healthRes.json();
    const healthStatusText = document.getElementById('dbHealthStatus');
    if (healthJson.status === 'healthy') {
      healthStatusText.innerHTML = '<span class="status-dot pulse"></span> PostgreSQL Active';
    } else {
      healthStatusText.innerHTML = '<span class="status-dot" style="background:#f43f5e;box-shadow:0 0 8px #f43f5e;"></span> DB Disconnected';
    }
  } catch (err) {
    console.error('Failed to refresh stats:', err);
  }
}

async function loadCategories() {
  try {
    const res = await fetch('/api/categories');
    const json = await res.json();
    if (json.success) {
      state.categories = json.data;
      populateCategorySelects();
    }
  } catch (err) {
    console.error('Error loading categories:', err);
  }
}

async function loadBooks() {
  try {
    let url = `/api/books?available=${state.availableOnly}`;
    if (state.activeCategory) url += `&category_id=${state.activeCategory}`;
    if (state.searchQuery) url += `&q=${encodeURIComponent(state.searchQuery)}`;
    
    const res = await fetch(url);
    const json = await res.json();
    if (json.success) {
      state.books = json.data;
      if (state.currentView === 'books') renderBooksGrid();
      populateBookSelect();
    }
  } catch (err) {
    console.error('Error loading books:', err);
  }
}

async function loadPatrons() {
  try {
    const res = await fetch('/api/patrons');
    const json = await res.json();
    if (json.success) {
      state.patrons = json.data;
      if (state.currentView === 'patrons') renderPatronsGrid();
      populatePatronSelect();
    }
  } catch (err) {
    console.error('Error loading patrons:', err);
  }
}

async function loadBorrowings() {
  try {
    const res = await fetch('/api/borrowings');
    const json = await res.json();
    if (json.success) {
      state.borrowings = json.data;
      if (state.currentView === 'ledger') renderBorrowingsLedger();
    }
  } catch (err) {
    console.error('Error loading borrowings:', err);
  }
}

// ======================== VIEW RENDERING ========================

function switchView(viewName) {
  document.getElementById('booksViewSection').style.display = (viewName === 'books') ? 'block' : 'none';
  document.getElementById('ledgerViewSection').style.display = (viewName === 'ledger') ? 'block' : 'none';
  document.getElementById('patronsViewSection').style.display = (viewName === 'patrons') ? 'block' : 'none';

  if (viewName === 'books') renderBooksGrid();
  if (viewName === 'ledger') renderBorrowingsLedger();
  if (viewName === 'patrons') renderPatronsGrid();
}

function renderCurrentView() {
  if (state.currentView === 'books') loadBooks();
  else if (state.currentView === 'ledger') renderBorrowingsLedger();
  else if (state.currentView === 'patrons') renderPatronsGrid();
}

function updateKpis(stats) {
  document.getElementById('kpiTotalBooks').textContent = stats.total_titles || 0;
  document.getElementById('kpiTotalCopiesSub').textContent = `${stats.available_copies || 0} bản sẵn sàng mượn / ${stats.total_copies || 0} tổng bản`;
  
  document.getElementById('kpiActiveLoans').textContent = stats.active_borrowings || 0;
  document.getElementById('kpiOverdueLoans').textContent = stats.overdue_borrowings || 0;
  document.getElementById('kpiTotalPatrons').textContent = stats.total_patrons || 0;
}

function renderCategoryPills() {
  const container = document.getElementById('categoryPills');
  let html = `<button class="pill-btn ${state.activeCategory === null ? 'active' : ''}" onclick="selectCategory(null)">Tất Cả Thể Loại</button>`;
  
  state.categories.forEach(cat => {
    const isActive = state.activeCategory === cat.id;
    html += `
      <button class="pill-btn ${isActive ? 'active' : ''}" onclick="selectCategory(${cat.id})">
        <i class="fa-solid ${cat.icon || 'fa-tag'}" style="color:${cat.badge_color}"></i> ${cat.name}
      </button>
    `;
  });
  container.innerHTML = html;
}

window.selectCategory = function(catId) {
  state.activeCategory = catId;
  renderCategoryPills();
  loadBooks();
};

function renderBooksGrid() {
  const container = document.getElementById('booksGridContainer');
  if (state.books.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; color: #64748b;">
        <i class="fa-solid fa-book-open" style="font-size: 40px; margin-bottom: 12px; color: #334155;"></i>
        <h4 style="color:#94a3b8; font-size:16px;">Không tìm thấy cuốn sách nào phù hợp</h4>
        <p style="font-size:13px;">Hãy thử tìm từ khóa khác hoặc bỏ chọn bộ lọc có sẵn.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = state.books.map(book => {
    const available = book.available_copies;
    const total = book.total_copies;
    const percent = Math.round((available / total) * 100);
    const meterClass = percent > 50 ? 'high' : (percent > 0 ? 'medium' : 'empty');
    const isOutOfStock = available <= 0;

    return `
      <div class="book-card">
        <div class="book-cover-header ${book.cover_theme || 'gradient-indigo'}">
          <span class="book-category-badge">
            <i class="fa-solid ${book.category_icon || 'fa-bookmark'}"></i> ${book.category_name || 'Tài liệu'}
          </span>
          <span class="book-shelf-badge">
            <i class="fa-solid fa-location-dot"></i> ${book.shelf_location}
          </span>
        </div>
        <div class="book-body">
          <h3 class="book-title" title="${book.title}">${book.title}</h3>
          <div class="book-author">
            <i class="fa-solid fa-feather-pointed"></i> <span>${book.author}</span>
          </div>
          <div class="book-isbn-row">
            <span>ISBN: ${book.isbn}</span>
            <span>NXB ${book.publish_year || 2024}</span>
          </div>
          <p class="book-summary">${book.summary || 'Tài liệu chuyên khảo được bảo quản và phân phối tại Thư viện Athena.'}</p>
          
          <div class="stock-meter-wrap">
            <div class="stock-meter-labels">
              <span style="color:#94a3b8;">Trữ lượng kho</span>
              <span style="color:${isOutOfStock ? '#f43f5e' : '#38bdf8'}; font-family:var(--font-mono);">${available}/${total} cuốn</span>
            </div>
            <div class="stock-meter-bar">
              <div class="stock-fill ${meterClass}" style="width: ${percent}%;"></div>
            </div>
          </div>

          <div class="book-footer-actions">
            <button class="btn-card-borrow" ${isOutOfStock ? 'disabled' : ''} onclick="openBorrowModalForBook(${book.id})">
              <i class="fa-solid ${isOutOfStock ? 'fa-ban' : 'fa-bolt'}"></i>
              ${isOutOfStock ? 'Đã Hết Bản Sao' : '⚡ Mượn Sách Nhanh'}
            </button>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderBorrowingsLedger() {
  const container = document.getElementById('ledgerTableBody');
  let list = state.borrowings;
  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    list = list.filter(b => 
      b.book_title.toLowerCase().includes(q) || 
      b.patron_name.toLowerCase().includes(q) || 
      b.borrow_code.toLowerCase().includes(q)
    );
  }

  if (list.length === 0) {
    container.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 40px; color: #64748b;">Không có phiếu mượn nào được ghi nhận.</td></tr>`;
    return;
  }

  container.innerHTML = list.map(item => {
    let statusBadge = '';
    const status = item.computed_status || item.status;
    if (status === 'BORROWED') {
      statusBadge = `<span class="badge-status badge-borrowed"><i class="fa-solid fa-clock"></i> Đang Mượn</span>`;
    } else if (status === 'OVERDUE') {
      statusBadge = `<span class="badge-status badge-overdue"><i class="fa-solid fa-triangle-exclamation"></i> Quá Hạn</span>`;
    } else {
      statusBadge = `<span class="badge-status badge-returned"><i class="fa-solid fa-circle-check"></i> Đã Trả</span>`;
    }

    const fineFormatted = Number(item.fine_amount) > 0 
      ? `<span style="color:#fb7185; font-weight:700;">${Number(item.fine_amount).toLocaleString('vi-VN')} đ</span>` 
      : `<span style="color:#64748b;">0 đ</span>`;

    return `
      <tr>
        <td style="font-family:var(--font-mono); color:#38bdf8; font-weight:600;">${item.borrow_code}</td>
        <td>
          <div style="font-weight:600; color:#ffffff;">${item.book_title}</div>
          <div style="font-size:11px; color:#64748b;">ISBN: ${item.isbn} | ${item.shelf_location}</div>
        </td>
        <td>
          <div style="font-weight:600; color:#e2e8f0;">${item.patron_name}</div>
          <div style="font-size:11px; color:#64748b;">Mã thẻ: ${item.card_number}</div>
        </td>
        <td style="font-family:var(--font-mono); font-size:12px;">${formatDate(item.borrow_date)}</td>
        <td style="font-family:var(--font-mono); font-size:12px;">${formatDate(item.due_date)}</td>
        <td>${statusBadge}</td>
        <td>${fineFormatted}</td>
        <td>
          ${status !== 'RETURNED' ? `
            <button class="btn-action-return" onclick="handleReturnBook(${item.id})">
              <i class="fa-solid fa-arrow-rotate-left"></i> Trả Sách
            </button>
          ` : `<span style="color:#64748b; font-size:12px;"><i class="fa-solid fa-check"></i> Hoàn tất</span>`}
        </td>
      </tr>
    `;
  }).join('');
}

function renderPatronsGrid() {
  const container = document.getElementById('patronsGridContainer');
  let list = state.patrons;
  if (state.searchQuery) {
    const q = state.searchQuery.toLowerCase();
    list = list.filter(p => p.full_name.toLowerCase().includes(q) || p.card_number.toLowerCase().includes(q) || p.email.toLowerCase().includes(q));
  }

  if (list.length === 0) {
    container.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding:40px; color:#64748b;">Không có độc giả nào.</div>`;
    return;
  }

  container.innerHTML = list.map(p => `
    <div class="patron-card">
      <div class="patron-top">
        <div class="patron-avatar">${p.full_name.charAt(0)}</div>
        <div class="patron-info">
          <h4>${p.full_name}</h4>
          <span class="patron-card-no"><i class="fa-solid fa-id-card"></i> ${p.card_number}</span>
        </div>
      </div>
      <div class="patron-meta">
        <div><i class="fa-solid fa-graduation-cap" style="width:16px; color:#38bdf8;"></i> ${p.patron_type} - ${p.department}</div>
        <div><i class="fa-solid fa-envelope" style="width:16px; color:#818cf8;"></i> ${p.email}</div>
        <div><i class="fa-solid fa-phone" style="width:16px; color:#34d399;"></i> ${p.phone || 'Chưa cập nhật'}</div>
        <div style="display:flex; justify-content:space-between; margin-top:4px; font-weight:600;">
          <span style="color:#94a3b8;">Đang mượn:</span>
          <span style="color:#38bdf8;">${p.current_borrowed_count || 0} / ${p.max_borrow_limit} cuốn</span>
        </div>
      </div>
    </div>
  `).join('');
}

// ======================== CHARTS ========================

function renderCategoryChart(categories) {
  if (!categories || categories.length === 0) return;
  const ctx = document.getElementById('categoryDoughnutChart');
  if (!ctx) return;

  const labels = categories.map(c => c.name);
  const data = categories.map(c => c.book_count);
  const colors = categories.map(c => c.badge_color || '#38bdf8');

  if (state.charts.category) {
    state.charts.category.destroy();
  }

  state.charts.category = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: '#0f172a'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#94a3b8',
            font: { family: 'Plus Jakarta Sans', size: 11 },
            boxWidth: 12
          }
        }
      },
      cutout: '68%'
    }
  });
}

// ======================== MODAL & ACTIONS ========================

function populateCategorySelects() {
  const select = document.getElementById('newBookCategory');
  if (!select) return;
  select.innerHTML = state.categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
}

function populateBookSelect() {
  const select = document.getElementById('borrowBookSelect');
  if (!select) return;
  select.innerHTML = state.books.map(b => `
    <option value="${b.id}" ${b.available_copies <= 0 ? 'disabled' : ''}>
      ${b.title} (Còn sẵn: ${b.available_copies}/${b.total_copies})
    </option>
  `).join('');
}

function populatePatronSelect() {
  const select = document.getElementById('borrowPatronSelect');
  if (!select) return;
  select.innerHTML = state.patrons.map(p => `
    <option value="${p.id}">
      ${p.full_name} (${p.card_number} - ${p.patron_type})
    </option>
  `).join('');
}

window.openModal = function(modalId) {
  document.getElementById(modalId).classList.add('active');
};

window.closeModal = function(modalId) {
  document.getElementById(modalId).classList.remove('active');
};

window.openBorrowModalForBook = function(bookId) {
  const select = document.getElementById('borrowBookSelect');
  if (select) select.value = bookId;
  openModal('modalBorrow');
};

async function handleAddBookSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const payload = {
    isbn: form.isbn.value.trim(),
    title: form.title.value.trim(),
    author: form.author.value.trim(),
    category_id: parseInt(form.category_id.value),
    shelf_location: form.shelf_location.value.trim(),
    total_copies: parseInt(form.total_copies.value) || 1,
    cover_theme: form.cover_theme.value,
    summary: form.summary.value.trim()
  };

  try {
    const res = await fetch('/api/books', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.success) {
      showToast('Thêm sách mới thành công!', 'success');
      form.reset();
      closeModal('modalAddBook');
      await Promise.all([loadBooks(), refreshStatsAndHealth()]);
    } else {
      showToast(json.error || 'Lỗi khi thêm sách', 'error');
    }
  } catch (err) {
    showToast('Lỗi mạng khi thêm sách', 'error');
  }
}

async function handleAddPatronSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const payload = {
    card_number: form.card_number.value.trim(),
    full_name: form.full_name.value.trim(),
    email: form.email.value.trim(),
    phone: form.phone.value.trim(),
    department: form.department.value.trim(),
    patron_type: form.patron_type.value
  };

  try {
    const res = await fetch('/api/patrons', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.success) {
      showToast('Đăng ký độc giả mới thành công!', 'success');
      form.reset();
      closeModal('modalAddPatron');
      await Promise.all([loadPatrons(), refreshStatsAndHealth()]);
    } else {
      showToast(json.error || 'Lỗi đăng ký độc giả', 'error');
    }
  } catch (err) {
    showToast('Lỗi mạng khi đăng ký độc giả', 'error');
  }
}

async function handleBorrowSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const payload = {
    book_id: parseInt(form.book_id.value),
    patron_id: parseInt(form.patron_id.value),
    days: parseInt(form.days.value) || 14,
    notes: form.notes.value.trim()
  };

  try {
    const res = await fetch('/api/borrowings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await res.json();
    if (json.success) {
      showToast(json.message, 'success');
      form.reset();
      closeModal('modalBorrow');
      await Promise.all([loadBooks(), loadBorrowings(), loadPatrons(), refreshStatsAndHealth()]);
    } else {
      showToast(json.error || 'Lỗi khi lập phiếu mượn', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối khi lập phiếu mượn', 'error');
  }
}

window.handleReturnBook = async function(borrowingId) {
  if (!confirm('Xác nhận trả cuốn sách này vào kho?')) return;
  try {
    const res = await fetch(`/api/borrowings/${borrowingId}/return`, {
      method: 'POST'
    });
    const json = await res.json();
    if (json.success) {
      showToast(json.message, 'success');
      await Promise.all([loadBooks(), loadBorrowings(), loadPatrons(), refreshStatsAndHealth()]);
    } else {
      showToast(json.error || 'Lỗi khi trả sách', 'error');
    }
  } catch (err) {
    showToast('Lỗi kết nối khi trả sách', 'error');
  }
};

// ======================== HELPERS ========================

function formatDate(isoStr) {
  if (!isoStr) return '-';
  const d = new Date(isoStr);
  return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

function showToast(message, type = 'success') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <i class="fa-solid ${type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation'}" style="color:${type === 'success' ? '#10b981' : '#f43f5e'};"></i>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

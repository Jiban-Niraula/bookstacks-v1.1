// The inline guard script in index.html's <head> already redirects to
// /login.html if there's no token at all — this confirms the token is
// still actually valid server-side, and fills in the nav with who's logged in.

const userDisplayEl = document.getElementById('user-display');
const userRoleEl = document.getElementById('user-role');
const userAvatarEl = document.getElementById('user-avatar');

function renderUser(user) {
  userDisplayEl.textContent = user.username;
  userRoleEl.textContent = roleLabel(user.role);
  userAvatarEl.textContent = user.username.slice(0, 1);
  // "Add a title" and the delete button are catalog-management actions --
  // gate them on the books:create/books:delete permissions (granted to
  // Super Admin and Librarian) rather than a single hardcoded role name,
  // so this stays correct if roles are added or changed later.
  document.body.classList.toggle('can-add-books', hasPermission(user.role, 'books:create'));
  document.body.classList.toggle('can-delete-books', hasPermission(user.role, 'books:delete'));
  document.body.classList.toggle('can-view-members', hasPermission(user.role, 'members:read'));
}

// ---------- Books ----------

const bookRowsEl = document.getElementById('book-rows');
const emptyStateEl = document.getElementById('empty-state');
const catalogCountEl = document.getElementById('catalog-count');
const rowTemplate = document.getElementById('row-template');
const addForm = document.getElementById('add-form');
const addError = document.getElementById('add-error');
const searchInputEl = document.getElementById('search-input');

let searchTimer = null;

async function fetchBooks(query) {
  const url = query ? `/api/books/search?q=${encodeURIComponent(query)}` : '/api/books';
  const res = await fetch(url);
  return res.json();
}

async function fetchStats() {
  const res = await fetch('/api/stats');
  return res.json();
}

function renderStats(stats) {
  document.getElementById('stat-titles').textContent = stats.totalTitles ?? '–';
  document.getElementById('stat-copies').textContent = stats.totalCopies ?? '–';
  document.getElementById('stat-available').textContent = stats.totalAvailable ?? '–';
  document.getElementById('stat-borrowed').textContent = stats.totalBorrowed ?? '–';
  document.getElementById('stat-overdue').textContent = stats.totalOverdue ?? '–';
}

function renderBooks(books) {
  bookRowsEl.innerHTML = '';
  catalogCountEl.textContent = `${books.length} title${books.length === 1 ? '' : 's'}`;

  if (books.length === 0) {
    emptyStateEl.hidden = false;
    return;
  }
  emptyStateEl.hidden = true;

  books.forEach((book) => {
    const node = rowTemplate.content.cloneNode(true);
    const available = book.availableCopies > 0;

    node.querySelector('.col-title').textContent = book.title;
    node.querySelector('.col-author').textContent = book.author;
    node.querySelector('.col-genre').textContent = book.genre || 'General';
    node.querySelector('.col-copies').textContent =
      `${book.availableCopies} / ${book.totalCopies}`;

    const badge = node.querySelector('.badge');
    badge.textContent = available ? 'Available' : 'Borrowed out';
    badge.classList.add(available ? 'badge--available' : 'badge--borrowed');

    const errorRow = node.querySelector('.row-error-tr');
    const errorCell = node.querySelector('.row-error');

    node.querySelector('.btn-borrow').addEventListener('click', () =>
      handleLoanAction(book.id, 'borrow', errorRow, errorCell)
    );
    node.querySelector('.btn-return').addEventListener('click', () =>
      handleLoanAction(book.id, 'return', errorRow, errorCell)
    );
    node.querySelector('.btn-delete').addEventListener('click', () =>
      handleDelete(book.id, book.title, errorRow, errorCell)
    );

    bookRowsEl.appendChild(node);
  });
}

async function handleLoanAction(id, action, errorRow, errorCell) {
  errorRow.classList.remove('visible');
  errorCell.textContent = '';
  try {
    const res = await authFetch(`/api/books/${id}/${action}`, { method: 'POST' });
    const data = await res.json();
    if (!res.ok) {
      errorCell.textContent = data.error || 'Something went wrong.';
      errorRow.classList.add('visible');
      return;
    }
    await loadApp();
  } catch (err) {
    errorCell.textContent = 'Could not reach the server.';
    errorRow.classList.add('visible');
  }
}

async function handleDelete(id, title, errorRow, errorCell) {
  if (!confirm(`Remove "${title}" from the catalog?`)) return;
  errorRow.classList.remove('visible');
  errorCell.textContent = '';
  try {
    const res = await authFetch(`/api/books/${id}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) {
      errorCell.textContent = data.error || 'Could not delete this book.';
      errorRow.classList.add('visible');
      return;
    }
    await loadApp();
  } catch (err) {
    errorCell.textContent = 'Could not reach the server.';
    errorRow.classList.add('visible');
  }
}

addForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  addError.textContent = '';

  const formData = new FormData(addForm);
  const payload = {
    title: formData.get('title').trim(),
    author: formData.get('author').trim(),
    genre: formData.get('genre').trim() || 'General',
    copies: Number(formData.get('copies')) || 1,
  };

  try {
    const res = await authFetch('/api/books', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      addError.textContent = data.error || 'Could not add that book.';
      return;
    }
    addForm.reset();
    addForm.copies.value = 1;
    await loadApp();
  } catch (err) {
    addError.textContent = 'Could not reach the server.';
  }
});

searchInputEl.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadBooksAndStats, 250);
});

// ---------- My loans ----------

function renderMyLoans(loans) {
  const listEl = document.getElementById('my-loans-list');
  const emptyEl = document.getElementById('my-loans-empty');
  listEl.innerHTML = '';

  const active = loans.filter((l) => !l.returnedAt);
  if (active.length === 0) {
    emptyEl.hidden = false;
    return;
  }
  emptyEl.hidden = true;

  active.forEach((loan) => {
    const row = document.createElement('div');
    row.className = `loan-row${loan.overdue ? ' loan-row--overdue' : ''}`;

    const titleSpan = document.createElement('span');
    titleSpan.className = 'loan-title';
    titleSpan.textContent = loan.bookTitle || 'Unknown title';

    const dueSpan = document.createElement('span');
    dueSpan.className = 'loan-due';
    const dueDate = new Date(loan.dueAt).toLocaleDateString();
    dueSpan.textContent = loan.overdue ? `Overdue — was due ${dueDate}` : `Due ${dueDate}`;

    const returnBtn = document.createElement('button');
    returnBtn.type = 'button';
    returnBtn.textContent = 'Return';
    returnBtn.addEventListener('click', async () => {
      await authFetch(`/api/books/${loan.bookId}/return`, { method: 'POST' });
      await loadApp();
    });

    row.append(titleSpan, dueSpan, returnBtn);
    listEl.appendChild(row);
  });
}

async function loadMyLoans() {
  try {
    const res = await authFetch('/api/my/loans');
    if (res.ok) {
      renderMyLoans(await res.json());
    }
  } catch (err) {
    // non-fatal — leave the panel as-is
  }
}

// ---------- Orchestration ----------

async function loadBooksAndStats() {
  const query = searchInputEl.value.trim();
  try {
    const [books, stats] = await Promise.all([fetchBooks(query), fetchStats()]);
    renderBooks(books);
    renderStats(stats);
  } catch (err) {
    bookRowsEl.innerHTML = '';
    emptyStateEl.hidden = false;
    emptyStateEl.textContent = 'Could not load books. Is the backend running?';
  }
}

async function loadApp() {
  await loadBooksAndStats();
  await loadMyLoans();
}

async function init() {
  try {
    const res = await authFetch('/api/auth/me');
    if (!res.ok) return; // authFetch already redirects to /login.html on 401
    const user = await res.json();
    setSession(getToken(), user);
    renderUser(user);
    await loadApp();
  } catch (err) {
    // Backend unreachable — show the shell with an inline error rather
    // than bouncing a possibly-valid session back to the login page.
    emptyStateEl.hidden = false;
    emptyStateEl.textContent = 'Could not reach the server.';
  }
}

init();

// Members page — list/search patrons, add new ones, and (for staff who
// can process circulation) issue or return books against a member's
// account. Mirrors dashboard.js's structure/patterns for consistency.

const memberRowsEl = document.getElementById('member-rows');
const memberEmptyStateEl = document.getElementById('member-empty-state');
const memberCountEl = document.getElementById('member-count');
const memberRowTemplate = document.getElementById('member-row-template');
const memberSearchEl = document.getElementById('member-search');
const memberAddForm = document.getElementById('member-add-form');
const memberAddError = document.getElementById('member-add-error');

let currentRole = null;
let searchTimer = null;
let openMemberId = null; // which row's detail panel is currently expanded

function renderUser(user) {
  currentRole = user.role;
  document.getElementById('user-display').textContent = user.username;
  document.getElementById('user-role').textContent = roleLabel(user.role);
  document.getElementById('user-avatar').textContent = user.username.slice(0, 1);
  document.body.classList.toggle('can-add-members', hasPermission(user.role, 'members:create'));
  document.body.classList.toggle('can-delete-members', hasPermission(user.role, 'members:delete'));
  document.body.classList.toggle(
    'can-process-circulation',
    hasPermission(user.role, 'circulation:issue') || hasPermission(user.role, 'circulation:return')
  );
  document.body.classList.toggle('can-view-members', hasPermission(user.role, 'members:read'));
}

async function fetchMembers(query) {
  const url = query ? `/api/members?q=${encodeURIComponent(query)}` : '/api/members';
  const res = await authFetch(url);
  return res.json();
}

async function fetchMemberDetail(memberId) {
  const res = await authFetch(`/api/members/${memberId}`);
  return res.json();
}

async function fetchAvailableBooks() {
  const res = await authFetch('/api/books');
  const books = await res.json();
  return books.filter((b) => b.availableCopies > 0);
}

function renderMembers(members) {
  memberRowsEl.innerHTML = '';
  memberCountEl.textContent = `${members.length} member${members.length === 1 ? '' : 's'}`;

  if (members.length === 0) {
    memberEmptyStateEl.hidden = false;
    return;
  }
  memberEmptyStateEl.hidden = true;

  members.forEach((member) => {
    const node = memberRowTemplate.content.cloneNode(true);
    const row = node.querySelector('.member-row');
    row.dataset.memberId = member.id;

    node.querySelector('.col-membership-number').textContent = member.membershipNumber;
    node.querySelector('.col-full-name').textContent = member.fullName;
    node.querySelector('.col-contact').textContent =
      [member.phone, member.email].filter(Boolean).join(' · ') || '—';
    node.querySelector('.col-active-loans').textContent = member.activeLoans;

    const badge = node.querySelector('.badge');
    badge.textContent = member.status;
    badge.classList.add(`badge--${member.status}`);

    node.querySelector('.btn-view-member').addEventListener('click', () =>
      toggleMemberDetail(member.id)
    );
    node.querySelector('.btn-archive-member').addEventListener('click', () =>
      handleArchiveMember(member.id, member.fullName)
    );

    memberRowsEl.appendChild(node);
  });
}

async function toggleMemberDetail(memberId) {
  const detailTr = memberRowsEl.querySelector(
    `.member-row[data-member-id="${memberId}"] + .member-detail-tr`
  );
  if (!detailTr) return;

  const alreadyOpen = detailTr.classList.contains('visible');
  // Close any other open row first — one detail panel open at a time keeps
  // the table from getting overwhelming.
  memberRowsEl.querySelectorAll('.member-detail-tr.visible').forEach((tr) => tr.classList.remove('visible'));
  openMemberId = null;

  if (alreadyOpen) return;

  detailTr.classList.add('visible');
  openMemberId = memberId;
  await renderMemberDetail(memberId, detailTr);
}

async function renderMemberDetail(memberId, detailTr) {
  const loansEl = detailTr.querySelector('.member-detail__loans');
  const noLoansEl = detailTr.querySelector('.member-detail__no-loans');
  const selectEl = detailTr.querySelector('.member-detail__book-select');
  const issueBtn = detailTr.querySelector('.member-detail__issue-btn');
  const errorEl = detailTr.querySelector('.member-detail__error');

  loansEl.innerHTML = '';
  errorEl.textContent = '';

  const [detail, books] = await Promise.all([
    fetchMemberDetail(memberId),
    hasPermission(currentRole, 'circulation:issue') ? fetchAvailableBooks() : Promise.resolve([]),
  ]);

  const activeLoans = detail.loans.filter((l) => !l.returnedAt);
  if (activeLoans.length === 0) {
    noLoansEl.style.display = 'block';
  } else {
    noLoansEl.style.display = 'none';
    activeLoans.forEach((loan) => {
      const row = document.createElement('div');
      row.className = `loan-row${loan.overdue ? ' loan-row--overdue' : ''}`;

      const titleSpan = document.createElement('span');
      titleSpan.className = 'loan-title';
      titleSpan.textContent = loan.bookTitle || 'Unknown title';

      const dueSpan = document.createElement('span');
      dueSpan.className = 'loan-due';
      const dueDate = new Date(loan.dueAt).toLocaleDateString();
      dueSpan.textContent = loan.overdue ? `Overdue — was due ${dueDate}` : `Due ${dueDate}`;

      row.append(titleSpan, dueSpan);

      if (hasPermission(currentRole, 'circulation:return')) {
        const returnBtn = document.createElement('button');
        returnBtn.type = 'button';
        returnBtn.textContent = 'Return';
        returnBtn.addEventListener('click', async () => {
          errorEl.textContent = '';
          try {
            const res = await authFetch(`/api/circulation/return/${loan.id}`, { method: 'POST' });
            const data = await res.json();
            if (!res.ok) {
              errorEl.textContent = data.error || 'Could not process the return.';
              return;
            }
            await renderMemberDetail(memberId, detailTr);
            await loadMembers();
          } catch (err) {
            errorEl.textContent = 'Could not reach the server.';
          }
        });
        row.append(returnBtn);
      }

      loansEl.appendChild(row);
    });
  }

  // Issue-book control (only rendered functional if circulation:issue is granted)
  selectEl.innerHTML = '';
  if (books.length === 0) {
    const opt = document.createElement('option');
    opt.textContent = 'No available copies to issue';
    opt.disabled = true;
    selectEl.appendChild(opt);
    issueBtn.disabled = true;
  } else {
    books.forEach((book) => {
      const opt = document.createElement('option');
      opt.value = book.id;
      opt.textContent = `${book.title} — ${book.availableCopies} available`;
      selectEl.appendChild(opt);
    });
    issueBtn.disabled = false;
  }

  issueBtn.onclick = async () => {
    errorEl.textContent = '';
    const bookId = Number(selectEl.value);
    if (!bookId) return;
    try {
      const res = await authFetch('/api/circulation/issue', {
        method: 'POST',
        body: JSON.stringify({ bookId, memberId }),
      });
      const data = await res.json();
      if (!res.ok) {
        errorEl.textContent = data.error || 'Could not issue that book.';
        return;
      }
      await renderMemberDetail(memberId, detailTr);
      await loadMembers();
    } catch (err) {
      errorEl.textContent = 'Could not reach the server.';
    }
  };
}

async function handleArchiveMember(memberId, fullName) {
  if (!confirm(`Archive "${fullName}"'s membership? Their loan history is kept.`)) return;
  try {
    const res = await authFetch(`/api/members/${memberId}`, { method: 'DELETE' });
    const data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Could not archive this member.');
      return;
    }
    await loadMembers();
  } catch (err) {
    alert('Could not reach the server.');
  }
}

memberAddForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  memberAddError.textContent = '';

  const formData = new FormData(memberAddForm);
  const payload = {
    membershipNumber: formData.get('membershipNumber').trim(),
    fullName: formData.get('fullName').trim(),
    phone: formData.get('phone').trim(),
    email: formData.get('email').trim(),
  };

  try {
    const res = await authFetch('/api/members', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      memberAddError.textContent = data.error || 'Could not add that member.';
      return;
    }
    memberAddForm.reset();
    await loadMembers();
  } catch (err) {
    memberAddError.textContent = 'Could not reach the server.';
  }
});

memberSearchEl.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadMembers, 250);
});

async function loadMembers() {
  const query = memberSearchEl.value.trim();
  try {
    const members = await fetchMembers(query);
    renderMembers(members);
  } catch (err) {
    memberRowsEl.innerHTML = '';
    memberEmptyStateEl.hidden = false;
    memberEmptyStateEl.textContent = 'Could not load members. Is the backend running?';
  }
}

async function init() {
  try {
    const res = await authFetch('/api/auth/me');
    if (!res.ok) return; // authFetch already redirects to /login.html on 401
    const user = await res.json();
    renderUser(user);

    if (!hasPermission(user.role, 'members:read')) {
      // Not authorized for this page at all -- send them back to the
      // dashboard rather than showing an empty/broken Members screen.
      window.location.replace('/index.html');
      return;
    }

    await loadMembers();
  } catch (err) {
    memberEmptyStateEl.hidden = false;
    memberEmptyStateEl.textContent = 'Could not reach the server.';
  }
}

init();

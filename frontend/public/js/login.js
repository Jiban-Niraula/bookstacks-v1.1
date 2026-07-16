const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const loginSubmit = document.getElementById('login-submit');

loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  loginError.textContent = '';
  loginSubmit.disabled = true;
  loginSubmit.textContent = 'Logging in…';

  const formData = new FormData(loginForm);

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: formData.get('username').trim(),
        password: formData.get('password'),
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      loginError.textContent = data.error || 'Login failed.';
      return;
    }

    setSession(data.token, data.user);
    window.location.href = '/index.html';
  } catch (err) {
    loginError.textContent = 'Could not reach the server.';
  } finally {
    loginSubmit.disabled = false;
    loginSubmit.textContent = 'Log in';
  }
});

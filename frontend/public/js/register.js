const registerForm = document.getElementById('register-form');
const registerError = document.getElementById('register-error');
const registerSubmit = document.getElementById('register-submit');

registerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  registerError.textContent = '';
  registerSubmit.disabled = true;
  registerSubmit.textContent = 'Creating account…';

  const formData = new FormData(registerForm);

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: formData.get('username').trim(),
        email: formData.get('email').trim(),
        password: formData.get('password'),
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      registerError.textContent = data.error || 'Could not create account.';
      return;
    }

    setSession(data.token, data.user);
    window.location.href = '/index.html';
  } catch (err) {
    registerError.textContent = 'Could not reach the server.';
  } finally {
    registerSubmit.disabled = false;
    registerSubmit.textContent = 'Create account';
  }
});

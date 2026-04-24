const auth = document.getElementById('auth');
const dashboard = document.getElementById('dashboard');

function showAuth(mode) {
  auth.classList.remove('hidden');
  auth.innerHTML = `
    <h3>${mode === 'signup' ? 'Create your account' : 'Welcome back'}</h3>
    <input id="email" type="email" placeholder="you@example.com" />
    <input id="password" type="password" placeholder="password" />
    <button onclick="submitAuth('${mode}')">${mode === 'signup' ? 'Sign up' : 'Log in'}</button>
  `;
}

async function submitAuth(mode) {
  const email = document.getElementById('email').value;
  const password = document.getElementById('password').value;
  const res = await fetch(`/api/auth/${mode}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    alert('Auth failed.');
    return;
  }
  const data = await res.json();
  localStorage.setItem('pds_user', JSON.stringify(data));
  auth.classList.add('hidden');
  dashboard.classList.remove('hidden');
}

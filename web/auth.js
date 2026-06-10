// ============================================================
// Book2Vision — Hardcoded Auth Module (Demo Only)
// ============================================================

const DEMO_USER = {
    email: 'ttest@example.com',
    password: '000',
    full_name: 'Demo User'
};

// ============================================================
// SESSION HELPERS
// ============================================================

/**
 * Get current session (local)
 */
async function getSession() {
    const session = localStorage.getItem('b2v_session');
    return session ? JSON.parse(session) : null;
}

/**
 * Get current user (local)
 */
async function getUser() {
    const session = await getSession();
    return session?.user || null;
}

/**
 * Get the JWT access token (mock)
 */
async function getAccessToken() {
    return 'demo-token';
}

// ============================================================
// AUTH GUARD — redirect to login if not signed in
// ============================================================

async function requireAuth() {
    const session = await getSession();
    if (!session) {
        // Only redirect if NOT already on login or signup
        const path = window.location.pathname;
        if (!path.includes('login.html') && !path.includes('signup.html')) {
            window.location.href = 'login.html';
        }
        return null;
    }
    return session;
}

// ============================================================
// SIGN OUT
// ============================================================

async function signOut() {
    localStorage.removeItem('b2v_session');
    window.location.href = 'login.html';
}

// ============================================================
// EMAIL AUTH
// ============================================================

async function signInAsGuest() {
    const session = {
        user: {
            email: 'guest@book2vision.com',
            id: 'guest-id-' + Date.now(),
            user_metadata: { full_name: 'Guest User' }
        },
        access_token: 'guest-token'
    };
    localStorage.setItem('b2v_session', JSON.stringify(session));
    window.location.href = 'index.html';
}

async function signInWithEmail(email, password) {
    if (email === DEMO_USER.email && password === DEMO_USER.password) {
        const session = {
            user: {
                email: DEMO_USER.email,
                id: 'demo-id',
                user_metadata: { full_name: DEMO_USER.full_name }
            },
            access_token: 'demo-token'
        };
        localStorage.setItem('b2v_session', JSON.stringify(session));
        return { data: session, error: null };
    } else {
        throw new Error('Invalid credentials. Hint: ttest@example.com / 000');
    }
}

async function signUpWithEmail(email, password, fullName) {
    // Mock user and session for demo
    const session = {
        user: {
            email: email,
            id: 'new-id-' + Date.now(),
            user_metadata: { full_name: fullName }
        },
        access_token: 'demo-token-' + Date.now()
    };
    localStorage.setItem('b2v_session', JSON.stringify(session));
    return { data: session, error: null };
}

async function signInWithOAuth(provider) {
    showAuthError('Social login is disabled in beta version.');
}

async function resetPassword(email) {
    showAuthError('Password reset is disabled in demo mode.');
}

// ============================================================
// NAVBAR USER AVATAR
// ============================================================

async function injectNavUser() {
    const user = await getUser();
    const navLinks = document.querySelector('.nav-links');
    if (!navLinks || !user) return;

    const existing = document.getElementById('nav-user-menu');
    if (existing) existing.remove();

    const displayName = user.user_metadata?.full_name || user.email.split('@')[0];
    const initials = displayName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);

    const userMenu = document.createElement('div');
    userMenu.id = 'nav-user-menu';
    userMenu.style.cssText = `
        display: flex; align-items: center; gap: 0.6rem;
        position: relative; margin-left: 1.5rem; cursor: pointer;
    `;

    userMenu.innerHTML = `
        <div id="user-avatar-btn" style="
            width: 36px; height: 36px; border-radius: 50%;
            background: linear-gradient(135deg, #7F5AF0, #6246EA);
            display: flex; align-items: center; justify-content: center;
            font-size: 0.75rem; font-weight: 700; color: white;
            border: 2px solid rgba(255,255,255,0.15);
            box-shadow: 0 0 12px rgba(127,90,240,0.4);
            transition: all 0.2s ease;
        ">
            ${initials}
        </div>
        <div id="user-dropdown" style="
            display: none; position: absolute; top: calc(100% + 10px); right: 0;
            min-width: 220px; background: rgba(16,16,20,0.97);
            backdrop-filter: blur(24px); border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px; padding: 0.5rem; box-shadow: 0 16px 40px rgba(0,0,0,0.6);
            z-index: 9999;
        ">
            <div style="padding: 0.75rem 1rem 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.06);">
                <div style="font-weight: 600; font-size: 0.9rem; color: #fff;">${displayName}</div>
                <div style="font-size: 0.75rem; color: #94A1B2; margin-top: 2px;">${user.email}</div>
            </div>
            <button onclick="signOut()" style="
                display: flex; align-items: center; gap: 0.6rem;
                width: 100%; padding: 0.65rem 1rem; margin-top: 0.25rem;
                background: transparent; border: none; color: #EF4565;
                font-family: 'Outfit', sans-serif; font-size: 0.85rem;
                font-weight: 500; cursor: pointer; border-radius: 10px;
                transition: background 0.2s; text-align: left;
            " onmouseover="this.style.background='rgba(239,69,101,0.1)'" onmouseout="this.style.background='transparent'">
                <span>↩</span> Sign Out
            </button>
        </div>
    `;

    navLinks.appendChild(userMenu);

    document.getElementById('user-avatar-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        const dd = document.getElementById('user-dropdown');
        dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
    });

    document.addEventListener('click', () => {
        const dd = document.getElementById('user-dropdown');
        if (dd) dd.style.display = 'none';
    });
}

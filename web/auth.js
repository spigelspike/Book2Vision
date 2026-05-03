// ============================================================
// Book2Vision — Supabase Auth Module
// ============================================================

const SUPABASE_URL = 'https://gkhbmchvfcxpwealrlpe.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_shya8s5ClUJZvWFNclYTGw_yXWfnieV';

// Initialize Supabase client
const { createClient } = supabase;
const supabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// ============================================================
// SESSION HELPERS
// ============================================================

/**
 * Get current session (async)
 */
async function getSession() {
    const { data, error } = await supabaseClient.auth.getSession();
    return data?.session || null;
}

/**
 * Get current user (async)
 */
async function getUser() {
    // TEMPORARILY DISABLED FOR TESTING
    return { email: 'test@example.com', id: '123', user_metadata: { full_name: 'Test User' } };
    
    // const session = await getSession();
    // return session?.user || null;
}

/**
 * Get the JWT access token for API calls
 */
async function getAccessToken() {
    const session = await getSession();
    return session?.access_token || null;
}

// ============================================================
// AUTH GUARD — redirect to login if not signed in
// ============================================================

async function requireAuth() {
    // TEMPORARILY DISABLED FOR TESTING
    return { user: { email: 'test@example.com', id: '123' } };
    
    // const session = await getSession();
    // if (!session) {
    //     window.location.href = 'login.html';
    //     return null;
    // }
    // return session;
}

// ============================================================
// SIGN OUT
// ============================================================

async function signOut() {
    await supabaseClient.auth.signOut();
    window.location.href = 'login.html';
}

// ============================================================
// OAUTH — Google / GitHub
// ============================================================

async function signInWithOAuth(provider) {
    const { error } = await supabaseClient.auth.signInWithOAuth({
        provider: provider,
        options: {
            redirectTo: window.location.origin + '/index.html'
        }
    });
    if (error) {
        console.error('OAuth error:', error.message);
        throw error;
    }
}

// ============================================================
// EMAIL AUTH
// ============================================================

async function signInWithEmail(email, password) {
    const { data, error } = await supabaseClient.auth.signInWithPassword({ email, password });
    if (error) throw error;
    return data;
}

async function signUpWithEmail(email, password, fullName) {
    const { data, error } = await supabaseClient.auth.signUp({
        email,
        password,
        options: {
            data: { full_name: fullName }
        }
    });
    if (error) throw error;
    return data;
}

async function resetPassword(email) {
    const { error } = await supabaseClient.auth.resetPasswordForEmail(email, {
        redirectTo: window.location.origin + '/login.html'
    });
    if (error) throw error;
}

// ============================================================
// NAVBAR USER AVATAR (inject into any page with .nav-links)
// ============================================================

async function injectNavUser() {
    const user = await getUser();
    const navLinks = document.querySelector('.nav-links');
    if (!navLinks || !user) return;

    // Remove any existing auth button to avoid duplicates
    const existing = document.getElementById('nav-user-menu');
    if (existing) existing.remove();

    const avatarUrl = user.user_metadata?.avatar_url || null;
    const displayName = user.user_metadata?.full_name
        || user.user_metadata?.name
        || user.email?.split('@')[0]
        || 'User';

    const initials = displayName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);

    const userMenu = document.createElement('div');
    userMenu.id = 'nav-user-menu';
    userMenu.style.cssText = `
        display: flex;
        align-items: center;
        gap: 0.6rem;
        position: relative;
        margin-left: 1.5rem;
        cursor: pointer;
    `;

    userMenu.innerHTML = `
        <div id="user-avatar-btn" style="
            width: 36px; height: 36px; border-radius: 50%;
            background: linear-gradient(135deg, #7F5AF0, #6246EA);
            display: flex; align-items: center; justify-content: center;
            font-size: 0.75rem; font-weight: 700; color: white;
            border: 2px solid rgba(255,255,255,0.15);
            overflow: hidden; cursor: pointer;
            box-shadow: 0 0 12px rgba(127,90,240,0.4);
            transition: all 0.2s ease;
        ">
            ${avatarUrl
            ? `<img src="${avatarUrl}" style="width:100%;height:100%;object-fit:cover;" onerror="this.style.display='none'">`
            : initials
        }
        </div>
        <div id="user-dropdown" style="
            display: none;
            position: absolute;
            top: calc(100% + 10px);
            right: 0;
            min-width: 220px;
            background: rgba(16,16,20,0.97);
            backdrop-filter: blur(24px);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 0.5rem;
            box-shadow: 0 16px 40px rgba(0,0,0,0.6);
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
                transition: background 0.2s;
                text-align: left;
            " onmouseover="this.style.background='rgba(239,69,101,0.1)'" onmouseout="this.style.background='transparent'">
                <span>↩</span> Sign Out
            </button>
        </div>
    `;

    navLinks.appendChild(userMenu);

    // Toggle dropdown
    document.getElementById('user-avatar-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        const dd = document.getElementById('user-dropdown');
        dd.style.display = dd.style.display === 'none' ? 'block' : 'none';
    });

    // Close on outside click
    document.addEventListener('click', () => {
        const dd = document.getElementById('user-dropdown');
        if (dd) dd.style.display = 'none';
    });
}

// ============================================================
// AUTH STATE LISTENER — handle OAuth callback redirect
// ============================================================

supabaseClient.auth.onAuthStateChange((event, session) => {
    if (event === 'SIGNED_IN' && session) {
        // If on login or signup page after OAuth redirect, go to app
        const currentPage = window.location.pathname;
        if (currentPage.includes('login.html') || currentPage.includes('signup.html')) {
            window.location.href = 'index.html';
        }
    }
});

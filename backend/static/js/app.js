(function () {
  const root = document.documentElement;

  window.toggleDarkMode = function () {
    root.classList.toggle('dark');
    localStorage.setItem('theme', root.classList.contains('dark') ? 'dark' : 'light');
    updateDarkModeIcons();
  };

  function updateDarkModeIcons() {
    /* Icons are CSS-driven in base.html; no emoji toggle needed */
  }

  window.showToast = function (message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
  };

  window.renderMarkdown = function (text) {
    if (!text) return '';
    if (typeof marked !== 'undefined') {
      return marked.parse(text, { breaks: true });
    }
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');
  };

  window.typeText = function (element, text, speed = 12) {
    return new Promise((resolve) => {
      let i = 0;
      element.textContent = '';
      const timer = setInterval(() => {
        element.textContent += text.charAt(i);
        i += 1;
        if (i >= text.length) {
          clearInterval(timer);
          resolve();
        }
      }, speed);
    });
  };

  window.copyToClipboard = async function (text) {
    try {
      await navigator.clipboard.writeText(text);
      showToast('Copied to clipboard', 'success');
    } catch {
      showToast('Copy failed', 'error');
    }
  };

  window.deleteResume = async function (resumeId, cardEl) {
    if (!resumeId || !confirm('Delete this resume analysis?')) return;
    try {
      const headers = typeof csrfHeaders === 'function' ? csrfHeaders() : {};
      const res = await fetch(`/resume/${resumeId}`, { method: 'DELETE', headers });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        showToast(data.error || 'Delete failed', 'error');
        return;
      }
      if (cardEl) {
        cardEl.remove();
      } else {
        window.location.reload();
      }
      showToast('Resume deleted', 'success');
    } catch {
      showToast('Delete failed', 'error');
    }
  };

  document.addEventListener('DOMContentLoaded', () => {
    const menuBtn = document.getElementById('mobile-menu-btn');
    const menu = document.getElementById('mobile-menu');
    if (menuBtn && menu) {
      menuBtn.addEventListener('click', () => menu.classList.toggle('hidden'));
    }
    document.querySelectorAll('.dark-mode-toggle').forEach((btn) => {
      btn.addEventListener('click', toggleDarkMode);
    });
    document.addEventListener('click', (event) => {
      const btn = event.target.closest('.delete-resume-btn');
      if (!btn) return;
      deleteResume(btn.dataset.resumeId, btn.closest('[data-resume-card]'));
    });
    
    // Dynamic Header on Scroll
    const siteHeader = document.getElementById('site-header');
    const headerCard = document.getElementById('header-card');
    const headerInner = document.getElementById('header-inner');
    
    if (siteHeader && headerCard && headerInner) {
      window.addEventListener('scroll', () => {
        if (window.scrollY > 20) {
          siteHeader.classList.remove('pt-4');
          siteHeader.classList.add('pt-2');
          
          headerCard.classList.remove('shadow-sm', 'bg-white/70', 'dark:bg-gray-900/70', 'border-gray-200/50', 'dark:border-gray-700/50', 'rounded-2xl');
          headerCard.classList.add('shadow-md', 'bg-white/90', 'dark:bg-gray-900/90', 'border-gray-200', 'dark:border-gray-700', 'rounded-b-2xl', 'rounded-t-none');
          
          headerInner.classList.remove('h-16');
          headerInner.classList.add('h-14');
        } else {
          siteHeader.classList.add('pt-4');
          siteHeader.classList.remove('pt-2');
          
          headerCard.classList.add('shadow-sm', 'bg-white/70', 'dark:bg-gray-900/70', 'border-gray-200/50', 'dark:border-gray-700/50', 'rounded-2xl');
          headerCard.classList.remove('shadow-md', 'bg-white/90', 'dark:bg-gray-900/90', 'border-gray-200', 'dark:border-gray-700', 'rounded-b-2xl', 'rounded-t-none');
          
          headerInner.classList.add('h-16');
          headerInner.classList.remove('h-14');
        }
      });
    }

    updateDarkModeIcons();
  });
})();

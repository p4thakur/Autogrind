// ── Lazy load gallery cards ──────────────────────────────────────────────────
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add('visible');
      observer.unobserve(e.target);
    }
  });
}, { threshold: 0.1 });

document.querySelectorAll('.card').forEach(c => observer.observe(c));


// ── Animated stat counters ────────────────────────────────────────────────────
function animateCounter(el) {
  const target = parseInt(el.dataset.target, 10);
  const duration = 1400;
  const start = performance.now();
  (function step(now) {
    const t = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(ease * target).toLocaleString();
    if (t < 1) requestAnimationFrame(step);
  })(start);
}

const statsObserver = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.querySelectorAll('.stat-num').forEach(animateCounter);
      statsObserver.unobserve(e.target);
    }
  });
}, { threshold: 0.5 });

const statsEl = document.querySelector('.stats');
if (statsEl) statsObserver.observe(statsEl);


// ── Lightbox ──────────────────────────────────────────────────────────────────
const lb       = document.getElementById('lightbox');
const lbImg    = document.getElementById('lb-img');
const lbCap    = document.getElementById('lb-caption');
const lbLikes  = document.getElementById('lb-likes');
const lbClose  = document.getElementById('lb-close');
const lbPrev   = document.getElementById('lb-prev');
const lbNext   = document.getElementById('lb-next');

const cards = Array.from(document.querySelectorAll('.card'));
let current = 0;

function openLightbox(idx) {
  current = idx;
  const card = cards[idx];
  lbImg.src       = card.dataset.img;
  lbCap.textContent   = card.dataset.caption;
  lbLikes.textContent = '♥ ' + card.dataset.likes;
  lb.hidden = false;
  document.body.style.overflow = 'hidden';
  lbClose.focus();
}

function closeLightbox() {
  lb.hidden = true;
  document.body.style.overflow = '';
}

cards.forEach((card, idx) => {
  card.addEventListener('click', (e) => {
    // Don't intercept the Instagram link click
    if (e.target.closest('a.card-link')) return;
    openLightbox(idx);
  });
  // Also open lightbox when clicking the image directly (prevent navigation)
  const link = card.querySelector('a.card-link');
  if (link) {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      openLightbox(idx);
    });
  }
});

lbClose.addEventListener('click', closeLightbox);
lb.addEventListener('click', (e) => { if (e.target === lb) closeLightbox(); });

lbPrev.addEventListener('click', () => openLightbox((current - 1 + cards.length) % cards.length));
lbNext.addEventListener('click', () => openLightbox((current + 1) % cards.length));

document.addEventListener('keydown', (e) => {
  if (lb.hidden) return;
  if (e.key === 'Escape')      closeLightbox();
  if (e.key === 'ArrowLeft')   openLightbox((current - 1 + cards.length) % cards.length);
  if (e.key === 'ArrowRight')  openLightbox((current + 1) % cards.length);
});

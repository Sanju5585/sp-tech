/* SP-Tech Software Solution – Main JS */
(function () {
  'use strict';

  /* ── Navbar scroll class ── */
  const navbar = document.getElementById('mainNavbar');
  if (navbar) {
    const onScroll = () => navbar.classList.toggle('scrolled', window.scrollY > 30);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  /* ── Intersection-observer fade-in ── */
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('fade-in-up');
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });

    document.querySelectorAll(
      '.pcard, .why-card, .tcard, .blog-card, .team-card, .timeline-item, .contact-info-card, .stats-bar-item'
    ).forEach(el => io.observe(el));
  }

  /* ── Auto-dismiss alerts after 5 s ── */
  document.querySelectorAll('.alert').forEach(alert => {
    setTimeout(() => {
      const a = bootstrap.Alert.getOrCreateInstance(alert);
      if (a) a.close();
    }, 5000);
  });

})();


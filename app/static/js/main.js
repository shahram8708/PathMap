/* PathMap Client Interactions */
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';
const signupUrl = document.body?.dataset.signupUrl || '/auth/signup';
const pricingUrl = document.body?.dataset.pricingUrl || '/pricing';
const dashboardUrl = document.body?.dataset.dashboardUrl || '/dashboard';
const isPremium = document.body?.dataset.isPremium === 'true';
window.csrfToken = csrfToken;

document.addEventListener('DOMContentLoaded', () => {
  // Navbar shadow on scroll
  const navbar = document.querySelector('.navbar-pathmap');
  const toggleNavbarShadow = () => {
    if (!navbar) return;
    if (window.scrollY > 10) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  };
  toggleNavbarShadow();
  window.addEventListener('scroll', toggleNavbarShadow);

  // Flash auto-dismiss
  document.querySelectorAll('.alert.auto-dismiss').forEach((alert) => {
    setTimeout(() => {
      alert.classList.add('fade');
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert.close();
    }, 5000);
  });

  // Smooth scroll for hash links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', (e) => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // Close mobile navbar when link clicked
  const navbarMain = document.getElementById('navbarMain');
  if (navbarMain) {
    navbarMain.querySelectorAll('a.nav-link').forEach((link) => {
      link.addEventListener('click', () => {
        const collapse = new bootstrap.Collapse(navbarMain, { toggle: false });
        if (navbarMain.classList.contains('show')) {
          collapse.hide();
        }
      });
    });
  }

  // Hero quick-start redirect
  const heroForm = document.getElementById('hero-role-form');
  if (heroForm) {
    heroForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = document.getElementById('hero-role-input');
      const value = input?.value?.trim();
      const roleParam = encodeURIComponent(value || 'career pivot');
      window.location.href = `${signupUrl}?role=${roleParam}`;
    });
  }

  // Contact form character counter
  const messageField = document.getElementById('contact-message');
  const messageCounter = document.getElementById('message-counter');
  if (messageField && messageCounter) {
    const updateCount = () => {
      messageCounter.textContent = `${messageField.value.length}/2000 characters`;
    };
    messageField.addEventListener('input', updateCount);
    updateCount();
  }

  // Intersection Observer animations
  const animated = document.querySelectorAll('.animate-on-scroll');
  if (animated.length > 0) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.2 });
    animated.forEach((el) => observer.observe(el));
  }

  // Blog tag filter
  const tagPills = document.querySelectorAll('[data-tag-filter]');
  const blogCards = document.querySelectorAll('[data-blog-card]');
  if (tagPills.length) {
    tagPills.forEach((pill) => {
      pill.addEventListener('click', () => {
        const tag = pill.dataset.tagFilter;
        tagPills.forEach((p) => p.classList.remove('active'));
        pill.classList.add('active');
        blogCards.forEach((card) => {
          const tags = card.dataset.tags?.toLowerCase() || '';
          if (tag === 'all' || tags.includes(tag.toLowerCase())) {
            card.classList.remove('d-none');
          } else {
            card.classList.add('d-none');
          }
        });
      });
    });
  }

  // Testimonial carousel (simple rotate)
  const testimonialContainer = document.querySelector('[data-testimonial-carousel]');
  if (testimonialContainer) {
    const cards = testimonialContainer.querySelectorAll('.testimonial-card');
    const prevBtn = testimonialContainer.querySelector('[data-carousel-prev]');
    const nextBtn = testimonialContainer.querySelector('[data-carousel-next]');
    let start = 0;
    const visibleCount = 3;
    const render = () => {
      cards.forEach((card, idx) => {
        card.classList.toggle('d-none', !(idx >= start && idx < start + visibleCount));
      });
    };
    if (cards.length > visibleCount) {
      render();
      const shift = (dir) => {
        start = (start + dir + cards.length) % cards.length;
        if (start > cards.length - visibleCount) start = cards.length - visibleCount;
        render();
      };
      prevBtn?.addEventListener('click', () => shift(-1));
      nextBtn?.addEventListener('click', () => shift(1));
      setInterval(() => shift(1), 6000);
    }
  }

  setDashboardGreeting();

  const assessmentRing = document.getElementById('assessment-ring');
  if (assessmentRing) {
    const pct = parseFloat(assessmentRing.dataset.percentage || '0');
    renderAssessmentRing(pct);
  }

  initOnboardingCardSelectors();
  initRoleSearch();

  initAuthPasswordFields();

  initSidebarSubmenus();

  const yearsSlider = document.getElementById('years-experience-slider');
  if (yearsSlider) {
    const updateLabel = () => updateYearsExperienceLabel(yearsSlider);
    yearsSlider.addEventListener('input', updateLabel);
    updateLabel();
  }

  initAIDashboardWidget();
  initRoadmapTaskCheck();

  initBreadcrumbOverflow();
});

function initSidebarSubmenus() {
  const toggles = document.querySelectorAll('[data-submenu-toggle]');
  toggles.forEach((toggle) => {
    const targetId = toggle.dataset.submenuToggle;
    const target = document.getElementById(targetId);
    if (!target) return;

    const openIfActive = () => {
      const hasActiveChild = !!target.querySelector('.active');
      if (hasActiveChild) {
        target.classList.add('show');
        toggle.setAttribute('aria-expanded', 'true');
      }
    };

    toggle.addEventListener('click', (e) => {
      e.preventDefault();
      const isOpen = target.classList.contains('show');
      target.classList.toggle('show', !isOpen);
      toggle.setAttribute('aria-expanded', (!isOpen).toString());
    });

    openIfActive();
  });
}

function initBreadcrumbOverflow() {
  const bars = document.querySelectorAll('[data-breadcrumb-bar]');
  bars.forEach((bar) => {
    const nav = bar.querySelector('.breadcrumb-nav');
    if (!nav) return;
    const maybeCollapse = () => {
      const links = nav.querySelectorAll('.breadcrumb-link');
      if (links.length <= 3) return;
      const containerWidth = bar.clientWidth;
      const navWidth = nav.scrollWidth;
      const overflow = navWidth - containerWidth;
      if (overflow > 40) {
        links.forEach((link, idx) => {
          if (idx === 0 || idx === links.length - 1) return;
          link.classList.add('d-none');
        });
        const sep = document.createElement('span');
        sep.textContent = '…';
        sep.className = 'breadcrumb-sep';
        nav.insertBefore(sep, links[links.length - 1]);
      }
    };
    maybeCollapse();
    window.addEventListener('resize', () => {
      nav.querySelectorAll('.d-none').forEach((el) => el.classList.remove('d-none'));
      nav.querySelectorAll('.breadcrumb-sep').forEach((el) => { if (el.textContent === '…') el.remove(); });
      maybeCollapse();
    });
  });
}

function initAuthPasswordFields() {
  const toggleButtons = document.querySelectorAll('[data-toggle-password]');
  toggleButtons.forEach((btn) => {
    const targetId = btn.dataset.togglePassword;
    const input = document.getElementById(targetId);
    if (!input) return;

    btn.addEventListener('click', () => {
      const showing = input.type === 'text';
      input.type = showing ? 'password' : 'text';
      const icon = btn.querySelector('i');
      if (icon) {
        icon.classList.toggle('bi-eye', showing);
        icon.classList.toggle('bi-eye-slash', !showing);
      }
      btn.setAttribute('aria-pressed', (!showing).toString());
    });
  });

  const strengthInputs = document.querySelectorAll('input[data-strength]');
  const calcStrength = (value) => {
    let score = 0;
    if (value.length >= 8) score += 1;
    if (value.length >= 12) score += 1;
    if (/[A-Z]/.test(value)) score += 1;
    if (/\d/.test(value)) score += 1;
    if (/[^A-Za-z0-9]/.test(value)) score += 1;
    return Math.min(100, Math.round((score / 5) * 100));
  };

  const applyStrength = (bar, value) => {
    const percent = calcStrength(value);
    bar.style.width = `${percent}%`;
    if (percent < 40) {
      bar.style.background = 'linear-gradient(90deg, #E74C3C, #C0392B)';
    } else if (percent < 70) {
      bar.style.background = 'linear-gradient(90deg, #F1C40F, #F39C12)';
    } else {
      bar.style.background = 'linear-gradient(90deg, #2ECC71, #27AE60)';
    }
  };

  strengthInputs.forEach((input) => {
    const barId = input.dataset.strength;
    const bar = document.getElementById(barId);
    if (!bar) return;
    const update = () => applyStrength(bar, input.value || '');
    input.addEventListener('input', update);
    update();
  });
}

// Razorpay checkout helpers
async function startCheckout(plan) {
  if (typeof USER_AUTHENTICATED !== 'undefined' && !USER_AUTHENTICATED) {
    window.location.href = `${signupUrl}?next=${pricingUrl}`;
    return;
  }

  try {
    const response = await fetch('/payment/create-subscription', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ plan_type: plan })
    });

    if (response.status === 401) {
      window.location.href = `${signupUrl}?next=${pricingUrl}`;
      return;
    }

    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error || 'Unable to start checkout.');
    }
    const options = {
      key: data.key || (typeof RAZORPAY_KEY_ID !== 'undefined' ? RAZORPAY_KEY_ID : ''),
      subscription_id: data.subscription_id,
      name: 'PathMap Premium',
      description: `PathMap ${plan === 'annual' ? 'Annual' : 'Monthly'} Plan`,
      currency: 'INR',
      handler: async function (responseObj) {
        await fetch('/payment/verify-subscription', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            razorpay_payment_id: responseObj.razorpay_payment_id,
            razorpay_signature: responseObj.razorpay_signature,
            razorpay_subscription_id: responseObj.razorpay_subscription_id
          })
        });
        window.location.href = dashboardUrl;
      },
      theme: { color: '#1A5276' },
      modal: {
        ondismiss: () => {
          console.info('Checkout closed');
        }
      }
    };
    const rzp = new Razorpay(options);
    rzp.open();
  } catch (error) {
    console.error('Checkout failed', error);
    alert('Unable to start checkout right now. Please try again.');
  }
}

window.initiateMonthlyCheckout = () => startCheckout('monthly');
window.initiateAnnualCheckout = () => startCheckout('annual');

// Dashboard assessment ring
function renderAssessmentRing(targetPercentage) {
  const ring = document.getElementById('assessment-ring');
  if (!ring) return;
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const progressCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  progressCircle.setAttribute('cx', '70');
  progressCircle.setAttribute('cy', '70');
  progressCircle.setAttribute('r', radius.toString());
  progressCircle.setAttribute('stroke', '#1A5276');
  progressCircle.setAttribute('stroke-width', '12');
  progressCircle.setAttribute('fill', 'none');
  progressCircle.setAttribute('stroke-linecap', 'round');
  progressCircle.setAttribute('stroke-dasharray', circumference.toString());
  progressCircle.setAttribute('stroke-dashoffset', circumference.toString());
  ring.appendChild(progressCircle);

  let start = null;
  const duration = 1200;
  const animate = (timestamp) => {
    if (!start) start = timestamp;
    const progress = Math.min((timestamp - start) / duration, 1);
    const current = progress * targetPercentage;
    const offset = circumference - (current / 100) * circumference;
    progressCircle.setAttribute('stroke-dashoffset', offset.toString());
    if (progress < 1) requestAnimationFrame(animate);
  };
  requestAnimationFrame(animate);
}

// Onboarding selectors
function initOnboardingCardSelectors() {
  const cards = document.querySelectorAll('.onboarding-option-card-group');
  if (!cards.length) return;
  const applyInitialState = () => {
    cards.forEach((card) => {
      const inputName = card.dataset.input;
      const multi = card.dataset.multi === 'true';
      const hiddenInput = document.getElementById(inputName);
      if (!hiddenInput) return;
      const values = (hiddenInput.value || '').split(',').filter(Boolean);
      if ((multi && values.includes(card.dataset.value)) || (!multi && hiddenInput.value === card.dataset.value)) {
        card.classList.add('selected');
      }
    });
  };

  cards.forEach((card) => {
    card.addEventListener('click', () => {
      const inputName = card.dataset.input;
      const multi = card.dataset.multi === 'true';
      const value = card.dataset.value;
      const hiddenInput = document.getElementById(inputName);
      if (!hiddenInput) return;
      if (multi) {
        const existing = hiddenInput.value ? hiddenInput.value.split(',').filter(Boolean) : [];
        const exists = existing.includes(value);
        const updated = exists ? existing.filter((v) => v !== value) : [...existing, value];
        hiddenInput.value = updated.join(',');
        card.classList.toggle('selected', !exists);
      } else {
        cards.forEach((c) => { if (c.dataset.input === inputName) c.classList.remove('selected'); });
        card.classList.add('selected');
        hiddenInput.value = value;
      }
    });
  });
  applyInitialState();
}

// Role search
function initRoleSearch() {
  const searchInput = document.getElementById('role-search');
  const roleItems = document.querySelectorAll('.role-list-item');
  const countLabel = document.getElementById('role-search-count');
  const continueBtn = document.getElementById('role-continue-btn');
  const hiddenRoleId = document.getElementById('current_role_id');
  if (!searchInput || !roleItems.length) return;

  const updateCount = () => {
    const query = searchInput.value.toLowerCase();
    let visible = 0;
    roleItems.forEach((item) => {
      const title = item.dataset.roleTitle.toLowerCase();
      const category = item.dataset.roleCategory.toLowerCase();
      const match = title.includes(query) || category.includes(query);
      item.classList.toggle('d-none', !match);
      if (match) visible += 1;
    });
    if (countLabel) countLabel.textContent = `${visible} roles match your search`;
  };
  searchInput.addEventListener('input', updateCount);
  updateCount();

  roleItems.forEach((item) => {
    item.addEventListener('click', () => {
      roleItems.forEach((btn) => btn.classList.remove('active'));
      item.classList.add('active');
      const checkIcon = item.querySelector('.bi-check-circle-fill');
      document.querySelectorAll('.role-list-item .bi-check-circle-fill').forEach((icon) => icon.classList.add('d-none'));
      if (checkIcon) checkIcon.classList.remove('d-none');
      if (hiddenRoleId) hiddenRoleId.value = item.dataset.roleId;
      if (continueBtn) continueBtn.disabled = false;
    });
  });

  if (hiddenRoleId && hiddenRoleId.value) {
    const preset = Array.from(roleItems).find((item) => item.dataset.roleId === hiddenRoleId.value);
    if (preset) {
      preset.classList.add('active');
      preset.querySelector('.bi-check-circle-fill')?.classList.remove('d-none');
      if (continueBtn) continueBtn.disabled = false;
    }
  }
}

function updateYearsExperienceLabel(slider) {
  const label = document.getElementById('years-experience-label');
  if (!slider || !label) return;
  const val = parseInt(slider.value, 10);
  if (val === 0) label.textContent = 'Less than 1 year';
  else if (val >= 30) label.textContent = '30+ years';
  else label.textContent = `${val} years`;
}

// AI insight widget
function initAIDashboardWidget() {
  const sendBtn = document.getElementById('ai-send-btn');
  const input = document.getElementById('ai-question-input');
  const loading = document.querySelector('.ai-widget-loading');
  const responseBox = document.querySelector('.ai-widget-response');
  const premiumOverlay = document.getElementById('ai-premium-overlay');
  if (!sendBtn || !input) return;

  const storageKey = 'pathmap_ai_questions_today';
  const today = new Date().toISOString().slice(0, 10);

  const getCount = () => {
    try {
      const stored = JSON.parse(localStorage.getItem(storageKey) || '{}');
      return stored.date === today ? stored.count : 0;
    } catch (e) { return 0; }
  };

  const setCount = (count) => {
    localStorage.setItem(storageKey, JSON.stringify({ date: today, count }));
  };

  sendBtn.addEventListener('click', async () => {
    const question = input.value.trim();
    if (!question) return;
    if (!isPremium && getCount() >= 3) {
      if (premiumOverlay) premiumOverlay.classList.remove('d-none');
      return;
    }
    loading?.classList.remove('d-none');
    responseBox?.classList.add('d-none');
    try {
      const res = await fetch('/dashboard/ai-insight', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ question })
      });
      const data = await res.json();
      if (data && data.answer) {
        if (responseBox) {
          const renderer = typeof marked !== 'undefined' ? marked.parse : (val) => val;
          responseBox.innerHTML = renderer(data.answer);
          responseBox.classList.remove('d-none');
        }
        setCount(getCount() + 1);
        if (!isPremium && getCount() >= 3 && premiumOverlay) premiumOverlay.classList.remove('d-none');
      }
    } catch (err) {
      if (responseBox) {
        responseBox.textContent = "I'm unable to answer right now. Please try again shortly.";
        responseBox.classList.remove('d-none');
      }
    } finally {
      loading?.classList.add('d-none');
    }
  });
}

// Greeting updater
function setDashboardGreeting() {
  const el = document.getElementById('dashboard-greeting-time');
  if (!el) return;
  const hour = new Date().getHours();
  let label = 'day';
  if (hour >= 5 && hour <= 11) label = 'morning';
  else if (hour >= 12 && hour <= 17) label = 'afternoon';
  else if (hour >= 18 && hour <= 21) label = 'evening';
  else label = 'night';
  el.textContent = label;
}

// Roadmap task check (placeholder for future AJAX)
function initRoadmapTaskCheck() {
  const checkboxes = document.querySelectorAll('.roadmap-task-checkbox');
  if (!checkboxes.length) return;
  checkboxes.forEach((box) => {
    box.addEventListener('change', async () => {
      const taskId = box.dataset.taskId;
      const roadmapId = box.dataset.roadmapId;
      if (!taskId || !roadmapId) return;
      try {
        await fetch('/progress/task-toggle', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({ task_id: taskId, roadmap_id: roadmapId, completed: box.checked })
        });
        const label = box.closest('.roadmap-task-item');
        if (label) label.classList.toggle('text-decoration-line-through', box.checked);
      } catch (e) {
        box.checked = !box.checked;
      }
    });
  });
}

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(null, args), delay);
  };
}

// Subscription checkout (monthly/annual) with Razorpay
async function initSubscriptionCheckout(event) {
  event.preventDefault();
  const trigger = event.currentTarget;
  const planType = trigger.dataset.plan;
  const keyId = trigger.dataset.razorpayKey;
  const userEmail = trigger.dataset.userEmail;
  const userName = trigger.dataset.userName || '';
  const isAuthed = document.body?.dataset.userAuthenticated === 'true' || typeof USER_AUTHENTICATED !== 'undefined' && USER_AUTHENTICATED;
  if (!isAuthed) {
    window.location.href = `${signupUrl}?next=${pricingUrl}`;
    return;
  }
  try {
    const res = await fetch('/payment/create-subscription', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ plan_type: planType })
    });
    const data = await res.json();
    if (!data.success) {
      throw new Error(data.error || 'Unable to start checkout.');
    }
    const rzp = new Razorpay({
      key: data.key || keyId || '',
      subscription_id: data.subscription_id,
      name: 'PathMap Premium',
      description: planType === 'annual' ? 'Premium Annual (₹11,999/year)' : 'Premium Monthly (₹1,499/month)',
      prefill: { email: userEmail, name: userName },
      handler: async function (responseObj) {
        try {
          const verifyRes = await fetch('/payment/verify-subscription', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
              razorpay_payment_id: responseObj.razorpay_payment_id,
              razorpay_subscription_id: responseObj.razorpay_subscription_id,
              razorpay_signature: responseObj.razorpay_signature
            })
          });
          const verifyData = await verifyRes.json();
          if (verifyData.success) {
            window.location.href = verifyData.redirect_url || dashboardUrl;
          } else {
            alert(verifyData.error || 'Payment verification failed.');
          }
        } catch (err) {
          alert('Payment verification failed. Please contact support@pathmap.in.');
        }
      },
      theme: { color: '#1A5276' },
      modal: { ondismiss: () => { /* user closed */ } }
    });
    rzp.open();
  } catch (error) {
    console.error(error);
    alert(error.message || 'Unable to start checkout right now. Please try again.');
  }
}

// Settings tab persistence via URL hash
document.addEventListener('DOMContentLoaded', () => {
  const tabLinks = document.querySelectorAll('#settingsTabs button[data-bs-toggle="tab"]');
  const activateFromHash = () => {
    const hash = window.location.hash.replace('#', '');
    if (!hash) return;
    const targetBtn = Array.from(tabLinks).find((btn) => btn.dataset.bsTarget === `#${hash}`);
    if (targetBtn) {
      const tab = new bootstrap.Tab(targetBtn);
      tab.show();
    }
  };
  tabLinks.forEach((btn) => {
    btn.addEventListener('shown.bs.tab', () => {
      const target = btn.dataset.bsTarget?.replace('#', '') || '';
      if (target) window.history.replaceState(null, '', `#${target}`);
    });
  });
  activateFromHash();
});

// GDPR deletion confirmation with countdown
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('gdpr-delete-form');
  if (!form) return;
  form.addEventListener('submit', (e) => {
    const input = form.querySelector('input[name="confirmation_text"]');
    if (!input || input.value !== 'DELETE') {
      e.preventDefault();
      input?.classList.add('is-invalid');
      return;
    }
    e.preventDefault();
    let countdown = 5;
    const modalId = 'gdprConfirmModal';
    let modalEl = document.getElementById(modalId);
    if (!modalEl) {
      modalEl = document.createElement('div');
      modalEl.className = 'modal fade';
      modalEl.id = modalId;
      modalEl.innerHTML = `
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title text-danger">Confirm Permanent Deletion</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
              <p>This action is permanent and irreversible. All your PathMap data will be deleted.</p>
              <p class="fw-bold mb-0">Proceeding in <span id="gdpr-countdown">5</span> seconds...</p>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
              <button type="button" class="btn btn-danger" id="gdpr-confirm-btn" disabled>Yes, Delete Everything</button>
            </div>
          </div>
        </div>`;
      document.body.appendChild(modalEl);
    }
    const bsModal = new bootstrap.Modal(modalEl);
    const countdownEl = modalEl.querySelector('#gdpr-countdown');
    const confirmBtn = modalEl.querySelector('#gdpr-confirm-btn');
    confirmBtn.disabled = true;
    countdown = 5;
    countdownEl.textContent = countdown;
    const timer = setInterval(() => {
      countdown -= 1;
      countdownEl.textContent = countdown;
      if (countdown <= 0) {
        clearInterval(timer);
        confirmBtn.disabled = false;
      }
    }, 1000);
    confirmBtn.onclick = () => {
      confirmBtn.disabled = true;
      form.submit();
    };
    bsModal.show();
  });
});

// Feasibility radar chart
function initFeasibilityRadarChart(breakdownData) {
  const ctx = document.getElementById('feasibilityRadar');
  if (!ctx) return;
  const labels = ['Skill Gap', 'Time Feasibility', 'Financial Feasibility', 'Historical Success', 'Resource Availability'];
  const scores = [
    breakdownData.skill_gap.score,
    breakdownData.time_feasibility.score,
    breakdownData.financial_feasibility.score,
    breakdownData.historical_success.score,
    breakdownData.resource_availability.score
  ];
  window.radarChart = new Chart(ctx, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        label: 'Feasibility',
        data: scores,
        backgroundColor: 'rgba(26,82,118,0.2)',
        borderColor: '#1A5276',
        borderWidth: 2,
        pointBackgroundColor: '#2E86C1'
      }]
    },
    options: {
      responsive: true,
      scales: { r: { suggestedMin: 0, suggestedMax: 1, ticks: { stepSize: 0.2 } } },
      plugins: { legend: { display: false } },
      animation: { duration: 800 }
    }
  });
}

// Feasibility what-if sliders
function initFeasibilityWhatIf(analysisId) {
  const container = document.getElementById('whatif-container');
  if (!container) return;
  const endpoint = container.dataset.whatifUrl;
  const timelineInput = document.getElementById('whatifTimeline');
  const hoursInput = document.getElementById('whatifHours');
  const incomeInput = document.getElementById('whatifIncome');
  const scoreNumber = document.getElementById('feasibilityScoreNumber');

  const updateCards = (breakdown) => {
    Object.keys(breakdown).forEach((key) => {
      const card = document.querySelector(`[data-dimension="${key}"]`);
      if (!card) return;
      const valueEl = card.querySelector('.dimension-score');
      const bar = card.querySelector('.dimension-progress');
      if (valueEl) valueEl.textContent = `${Math.round(breakdown[key].score * 100)}%`;
      if (bar) bar.style.width = `${Math.round(breakdown[key].score * 100)}%`;
    });
  };

  const fetchUpdate = async () => {
    try {
      const payload = {
        timeline_months: parseInt(timelineInput.value, 10),
        hours_per_week: parseInt(hoursInput.value, 10),
        income_floor: parseFloat(incomeInput.value)
      };
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error || 'Unable to recalculate');
      const breakdown = data.breakdown;
      if (window.radarChart) {
        window.radarChart.data.datasets[0].data = [
          breakdown.skill_gap.score,
          breakdown.time_feasibility.score,
          breakdown.financial_feasibility.score,
          breakdown.historical_success.score,
          breakdown.resource_availability.score
        ];
        window.radarChart.update();
      }
      updateCards(breakdown);
      if (scoreNumber) {
        scoreNumber.textContent = data.composite_score;
        scoreNumber.classList.add('whatif-result-update');
        setTimeout(() => scoreNumber.classList.remove('whatif-result-update'), 600);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const debounced = debounce(fetchUpdate, 800);
  [timelineInput, hoursInput, incomeInput].forEach((input) => {
    if (input) input.addEventListener('input', debounced);
  });
}

// Progress heatmap
function renderHeatmap(heatmapData, containerId) {
  const container = document.getElementById(containerId);
  if (!container || !heatmapData) return;
  container.innerHTML = '';

  const startDate = new Date();
  startDate.setDate(startDate.getDate() - 363);

  const monthLabels = document.createElement('div');
  monthLabels.className = 'heatmap-month-labels';
  container.appendChild(monthLabels);

  const grid = document.createElement('div');
  grid.className = 'heatmap-grid';
  container.appendChild(grid);

  let lastMonth = null;
  for (let i = 0; i < 52; i += 1) {
    const weekStart = new Date(startDate);
    weekStart.setDate(startDate.getDate() + i * 7);
    const month = weekStart.toLocaleString('default', { month: 'short' });
    if (month !== lastMonth) {
      const label = document.createElement('span');
      label.textContent = month;
      monthLabels.appendChild(label);
      lastMonth = month;
    } else {
      const spacer = document.createElement('span');
      spacer.textContent = ' ';
      monthLabels.appendChild(spacer);
    }
  }

  for (let dayIndex = 0; dayIndex < 364; dayIndex += 1) {
    const current = new Date(startDate);
    current.setDate(startDate.getDate() + dayIndex);
    const iso = current.toISOString().slice(0, 10);
    const level = heatmapData[iso] ?? 0;
    const cell = document.createElement('div');
    cell.className = `heatmap-cell level-${level}`;
    const levelLabel = ['No activity', 'Check-in logged', 'Active week', 'High activity week'][level] || 'No activity';
    cell.title = `${iso} · ${levelLabel}`;
    grid.appendChild(cell);
  }
}

// Mood selector
function initMoodSelector(existingMood) {
  const cards = document.querySelectorAll('.mood-emoji-card');
  const hidden = document.getElementById('mood_rating');
  if (!cards.length || !hidden) return;

  const selectMood = (value) => {
    cards.forEach((card) => {
      card.classList.remove('selected-1', 'selected-2', 'selected-3', 'selected-4', 'selected-5');
      if (parseInt(card.dataset.mood, 10) === value) {
        card.classList.add(`selected-${value}`);
      }
    });
    hidden.value = value;
  };

  cards.forEach((card) => {
    card.addEventListener('click', () => {
      const value = parseInt(card.dataset.mood, 10);
      selectMood(value);
    });
  });

  if (existingMood) {
    selectMood(parseInt(existingMood, 10));
  }
}

// Journey filter interactions
function initJourneyFilter() {
  const form = document.getElementById('journey-filter-form');
  if (!form) return;
  const clearBtn = document.getElementById('journey-filter-clear');
  const overlay = document.getElementById('journey-filter-loading');

  form.addEventListener('submit', () => {
    if (overlay) overlay.classList.remove('d-none');
  });

  if (clearBtn) {
    clearBtn.addEventListener('click', (e) => {
      e.preventDefault();
      form.querySelectorAll('input, select').forEach((input) => {
        if (input.type === 'radio') {
          if (input.defaultChecked) input.checked = true;
          else input.checked = false;
        } else {
          input.value = '';
        }
      });
      form.submit();
    });
  }

  document.querySelectorAll('[data-locked-journey]').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      if (btn.dataset.lockedJourney === 'true') {
        e.preventDefault();
      }
    });
  });
}

// Journal search filter
function initJourneySearchFilter() {
  const input = document.getElementById('journal-search');
  if (!input) return;
  const entries = document.querySelectorAll('.journal-entry-card');
  input.addEventListener('input', () => {
    const query = input.value.toLowerCase();
    entries.forEach((card) => {
      const text = card.dataset.reflectionText?.toLowerCase() || '';
      card.classList.toggle('d-none', !text.includes(query));
    });
  });
}

// Task counter
function initCheckInTaskCounter() {
  const checkboxes = document.querySelectorAll('.task-checkbox-custom');
  if (!checkboxes.length) return;
  const counter = document.getElementById('task-selected-count');
  const successMsg = document.getElementById('task-all-complete');

  const update = () => {
    const checked = Array.from(checkboxes).filter((c) => c.checked).length;
    if (counter) counter.textContent = `${checked} task${checked === 1 ? '' : 's'} selected`;
    if (successMsg) successMsg.classList.toggle('d-none', checked !== checkboxes.length || checkboxes.length === 0);
  };

  checkboxes.forEach((box) => box.addEventListener('change', update));
  update();
}

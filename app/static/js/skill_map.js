const skillMapState = { data: null, adjustUrl: null, analysisId: null };
const skillMapCsrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

function debounce(fn, delay) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(null, args), delay);
  };
}

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'position-fixed top-0 end-0 m-3 alert alert-warning shadow';
  toast.style.zIndex = '1080';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('fade');
    setTimeout(() => toast.remove(), 300);
  }, 2200);
}

function renderSkillZones(data) {
  const directContainer = document.getElementById('direct-zone');
  const partialContainer = document.getElementById('partial-zone');
  const gapContainer = document.getElementById('gap-zone');
  if (!directContainer || !partialContainer || !gapContainer) return;
  directContainer.innerHTML = '';
  partialContainer.innerHTML = '';
  gapContainer.innerHTML = '';

  const createBadge = (skill, type) => {
    const badge = document.createElement('span');
    badge.className = `skill-badge-${type}`;
    badge.setAttribute('data-bs-toggle', 'tooltip');
    badge.title = `Your proficiency: ${skill.confidence_label} · Importance: ${skill.importance_label}`;
    badge.textContent = skill.skill_name;
    const importance = document.createElement('span');
    importance.className = 'badge bg-light border text-uppercase';
    importance.style.fontSize = '11px';
    importance.textContent = skill.importance_label[0];
    badge.appendChild(importance);
    return badge;
  };

  (data.direct_skills || []).forEach((skill) => {
    directContainer.appendChild(createBadge(skill, 'direct'));
  });

  (data.partial_skills || []).forEach((skill) => {
    const badge = createBadge(skill, 'partial');
    if (skill.adjacent_skill_used) {
      const via = document.createElement('small');
      via.className = 'text-muted';
      via.textContent = ` via ${skill.adjacent_skill_used}`;
      badge.appendChild(via);
    }
    partialContainer.appendChild(badge);
  });

  (data.gap_skills || []).forEach((skill) => {
    const badgeWrap = document.createElement('div');
    badgeWrap.style.display = 'flex';
    badgeWrap.style.flexDirection = 'column';
    badgeWrap.style.gap = '6px';
    const badge = createBadge(skill, 'gap');
    badge.dataset.skillName = skill.skill_name;
    badgeWrap.appendChild(badge);

    const resourcePanel = document.createElement('div');
    resourcePanel.className = 'skill-resource-panel d-none';
    if (skill.learning_resources && skill.learning_resources.length) {
      skill.learning_resources.forEach((res) => {
        const card = document.createElement('div');
        card.className = 'resource-mini-card mb-2';
        card.innerHTML = `
          <div class="fw-bold">${res.title}</div>
          <div class="small text-muted">${res.provider} · ${res.format || 'Resource'} · ${res.cost_tier || ''}</div>
          <div class="small">Est. ${res.estimated_hours || 0} hours · Rating ${res.quality_rating || ''}</div>
          <a class="btn btn-sm btn-outline-primary mt-1" href="${res.url}" target="_blank" rel="noopener">Open resource →</a>
        `;
        resourcePanel.appendChild(card);
      });
    } else {
      resourcePanel.innerHTML = '<div class="small text-muted">No resources added yet.</div>';
    }
    badgeWrap.appendChild(resourcePanel);
    gapContainer.appendChild(badgeWrap);
  });

  // Only wire tooltips if Bootstrap JS is present to avoid runtime errors that block rendering
  if (window.bootstrap && typeof bootstrap.Tooltip === 'function') {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach((tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl));
  }
  initGapSkillExpansion();
  updateSegmentedBar();
}

function updateSegmentedBar() {
  const bar = document.getElementById('skills-segmented-bar');
  if (!bar || !skillMapState.data) return;
  const total = (skillMapState.data.total_skills_required || 1);
  const d = (skillMapState.data.direct_count || 0) / total * 100;
  const p = (skillMapState.data.partial_count || 0) / total * 100;
  const g = Math.max(0, 100 - d - p);
  bar.style.setProperty('--direct-pct', `${d}%`);
  bar.style.setProperty('--partial-pct', `${p}%`);
  bar.querySelector('.segment-direct').style.width = `${d}%`;
  bar.querySelector('.segment-partial').style.width = `${p}%`;
  bar.querySelector('.segment-gap').style.width = `${g}%`;
}

function animateValue(el, endValue, suffix = '', duration = 400) {
  if (!el) return;
  const startValue = parseFloat(el.dataset.currentValue || el.textContent) || 0;
  const startTime = performance.now();
  const step = (now) => {
    const progress = Math.min((now - startTime) / duration, 1);
    const current = startValue + (endValue - startValue) * progress;
    el.textContent = `${current.toFixed(1)}${suffix}`;
    el.dataset.currentValue = current;
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function updateSummaryStats(data) {
  const transferEl = document.getElementById('summary-transfer');
  const gapEl = document.getElementById('summary-gap');
  const hoursEl = document.getElementById('summary-hours');
  const feasEl = document.getElementById('summary-feasibility');
  animateValue(transferEl, data.transfer_score || 0, '%');
  animateValue(gapEl, data.gap_score || 0, '%');
  animateValue(hoursEl, data.estimated_learning_hours || 0, 'h');
  animateValue(feasEl, data.feasibility_score || 0, '');
}

function animateSkillBadgeTransition(skillName, newZone) {
  const zones = {
    direct: document.getElementById('direct-zone'),
    partial: document.getElementById('partial-zone'),
    gap: document.getElementById('gap-zone')
  };
  const target = zones[newZone];
  if (!target) return;
  target.classList.add('whatif-result-update');
  setTimeout(() => target.classList.remove('whatif-result-update'), 500);
}

function initSkillAdjustmentSliders() {
  const sliders = document.querySelectorAll('[data-skill-slider]');
  if (!sliders.length) return;
  const adjustUrl = document.getElementById('skill-adjustment-panel')?.dataset.adjustUrl;
  skillMapState.adjustUrl = adjustUrl;
  const debouncedUpdate = debounce(async (slider) => {
    const payload = { skill_name: slider.dataset.skillName, new_rating: slider.value };
    const previous = slider.dataset.lastValue || slider.defaultValue;
    try {
      const res = await fetch(adjustUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': skillMapCsrfToken
        },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error || 'Update failed');
      slider.dataset.lastValue = slider.value;
      skillMapState.data = { ...skillMapState.data, ...data, feasibility_score: data.feasibility_score };
      renderSkillZones(skillMapState.data);
      updateSummaryStats({
        transfer_score: data.transfer_score,
        gap_score: data.gap_score,
        estimated_learning_hours: data.estimated_learning_hours,
        feasibility_score: data.feasibility_score,
        direct_skills: data.direct_skills,
        partial_skills: data.partial_skills,
        gap_skills: data.gap_skills,
        direct_count: data.direct_skills.length,
        partial_count: data.partial_skills.length,
        gap_count: data.gap_skills.length,
        total_skills_required: skillMapState.data.total_skills_required
      });
      let newZone = 'gap';
      if ((data.direct_skills || []).some((s) => s.skill_name === slider.dataset.skillName)) newZone = 'direct';
      else if ((data.partial_skills || []).some((s) => s.skill_name === slider.dataset.skillName)) newZone = 'partial';
      animateSkillBadgeTransition(slider.dataset.skillName, newZone);
    } catch (err) {
      slider.value = previous;
      showToast('Update failed — please try again');
    }
  }, 600);

  sliders.forEach((slider) => {
    slider.dataset.lastValue = slider.value;
    slider.addEventListener('input', () => debouncedUpdate(slider));
  });

  const resetBtn = document.getElementById('reset-ratings-btn');
  if (resetBtn && adjustUrl) {
    resetBtn.addEventListener('click', async () => {
      try {
        const res = await fetch(adjustUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': skillMapCsrfToken
          },
          body: JSON.stringify({ reset: true })
        });
        const data = await res.json();
        if (!data.success) throw new Error(data.error || 'Unable to reset');
        document.querySelectorAll('[data-skill-slider]').forEach((slider) => {
          const match = data.direct_skills.find((s) => s.skill_name === slider.dataset.skillName) ||
            data.partial_skills.find((s) => s.skill_name === slider.dataset.skillName) ||
            data.gap_skills.find((s) => s.skill_name === slider.dataset.skillName);
          slider.value = match ? match.user_confidence : 0;
        });
        skillMapState.data = { ...skillMapState.data, ...data, feasibility_score: data.feasibility_score };
        renderSkillZones(skillMapState.data);
        updateSummaryStats({
          transfer_score: data.transfer_score,
          gap_score: data.gap_score,
          estimated_learning_hours: data.estimated_learning_hours,
          feasibility_score: data.feasibility_score,
          direct_skills: data.direct_skills,
          partial_skills: data.partial_skills,
          gap_skills: data.gap_skills,
          direct_count: data.direct_skills.length,
          partial_count: data.partial_skills.length,
          gap_count: data.gap_skills.length,
          total_skills_required: skillMapState.data.total_skills_required
        });
      } catch (err) {
        showToast('Update failed — please try again');
      }
    });
  }
}

function initGapSkillExpansion() {
  const gapBadges = document.querySelectorAll('.skill-badge-gap');
  gapBadges.forEach((badge) => {
    badge.addEventListener('click', () => {
      document.querySelectorAll('.skill-resource-panel').forEach((panel) => {
        if (panel !== badge.nextElementSibling) {
          panel.classList.add('d-none');
          panel.parentElement?.querySelector('.skill-badge-gap')?.classList.remove('expanded');
        }
      });
      const panel = badge.nextElementSibling;
      if (panel) {
        panel.classList.toggle('d-none');
        badge.classList.toggle('expanded');
      }
    });
  });
}

function initSkillMap(initialData) {
  // Default counts if API omitted them to keep segmented bar happy
  const filled = {
    direct_count: (initialData.direct_skills || []).length,
    partial_count: (initialData.partial_skills || []).length,
    gap_count: (initialData.gap_skills || []).length,
    total_skills_required: initialData.total_skills_required || ((initialData.direct_skills || []).length + (initialData.partial_skills || []).length + (initialData.gap_skills || []).length) || 1,
    ...initialData
  };
  skillMapState.data = filled;
  renderSkillZones(filled);
  updateSummaryStats(filled);
}

function loadMarketInsights(analysisId) {
  const panel = document.getElementById('market-insights-content');
  const button = document.getElementById('load-market-btn');
  const endpoint = button?.dataset.marketUrl;
  if (!panel || !endpoint) return;
  const cacheKey = `pathmap_insights_${analysisId}`;
  const cached = localStorage.getItem(cacheKey);
  if (cached) {
    try {
      const parsed = JSON.parse(cached);
      const now = Date.now();
      if (now - parsed.ts < 24 * 60 * 60 * 1000) {
        const renderer = typeof marked !== 'undefined' ? marked.parse : (val) => val;
        panel.innerHTML = renderer(parsed.text || '');
        panel.classList.add('markdown-content');
        button.classList.add('d-none');
        return;
      }
    } catch (e) { /* ignore */ }
  }
  button.disabled = true;
  button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
  fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': skillMapCsrfToken }
  })
    .then((res) => res.json())
    .then((data) => {
      const renderer = typeof marked !== 'undefined' ? marked.parse : (val) => val;
      if (data.success) {
        panel.innerHTML = renderer(data.insights || '');
        panel.classList.add('markdown-content');
        localStorage.setItem(cacheKey, JSON.stringify({ ts: Date.now(), text: data.insights || '' }));
      } else {
        panel.textContent = data.insights || 'Market insights are temporarily unavailable. Please try again.';
      }
    })
    .catch(() => {
      panel.textContent = 'Market insights are temporarily unavailable. Please try again.';
    })
    .finally(() => {
      button.classList.add('d-none');
    });
}

function initCompareCheckboxes() {
  const checkboxes = document.querySelectorAll('.compare-checkbox');
  const submitBtn = document.getElementById('compare-submit');
  const compareUrl = submitBtn?.dataset.compareUrl;
  if (!checkboxes.length || !submitBtn || !compareUrl) return;
  let selected = [];
  const updateState = () => {
    submitBtn.disabled = selected.length < 2 || selected.length > 3;
  };
  checkboxes.forEach((box) => {
    box.addEventListener('change', () => {
      const id = box.dataset.analysisId;
      if (box.checked) {
        if (selected.length >= 3) {
          box.checked = false;
          showToast('Maximum 3 paths for comparison');
          return;
        }
        selected.push(id);
      } else {
        selected = selected.filter((x) => x !== id);
      }
      updateState();
    });
  });
  submitBtn.addEventListener('click', () => {
    if (selected.length >= 2 && selected.length <= 3) {
      const url = `${compareUrl}?analysis_ids=${selected.join(',')}`;
      window.location.href = url;
    }
  });
  updateState();
}

window.initSkillMap = initSkillMap;
window.initSkillAdjustmentSliders = initSkillAdjustmentSliders;
window.animateSkillBadgeTransition = animateSkillBadgeTransition;
window.updateSummaryStats = updateSummaryStats;
window.initGapSkillExpansion = initGapSkillExpansion;
window.loadMarketInsights = loadMarketInsights;
window.initCompareCheckboxes = initCompareCheckboxes;

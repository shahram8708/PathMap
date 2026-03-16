const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]') ? document.querySelector('meta[name="csrf-token"]').content : '';

function debounce(func, wait = 600) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}

function showSavedToast(message = 'Progress saved') {
  let container = document.getElementById('autosave-toast');
  if (!container) {
    container = document.createElement('div');
    container.id = 'autosave-toast';
    container.style.position = 'fixed';
    container.style.bottom = '16px';
    container.style.right = '16px';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = 'toast align-items-center text-bg-success border-0 show';
  toast.role = 'alert';
  toast.style.minWidth = '200px';
  toast.innerHTML = `<div class="d-flex"><div class="toast-body">${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button></div>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 2000);
}

function assessmentAutosave(module, data) {
  return fetch('/assessment/autosave', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': CSRF_TOKEN
    },
    body: JSON.stringify({ module, data })
  })
    .then((response) => response.ok ? response.json() : Promise.reject())
    .then(() => showSavedToast())
    .catch(() => {});
}

function initValuesModule(existingData = {}) {
  const cards = Array.from(document.querySelectorAll('.value-card-slide'));
  if (!cards.length) return;
  const sliderContainer = document.getElementById('values-slider-container');
  if (!sliderContainer) return;
  const answers = (existingData.ratings) ? { ...existingData.ratings } : {};
  let currentIndex = 0;
  const submitBtn = document.getElementById('values-submit-btn');
  const dots = document.querySelectorAll('#values-progress-dots .progress-dot');
  const counter = document.getElementById('values-progress-counter');

  const updateUI = () => {
    cards.forEach((card, idx) => {
      card.style.display = idx === currentIndex ? 'block' : 'none';
      const key = card.dataset.valueKey;
      const selectedValue = answers[key];
      card.querySelectorAll('.value-btn').forEach((btn) => {
        btn.classList.toggle('selected', parseInt(btn.dataset.choice, 10) === parseInt(selectedValue, 10));
      });
      const prevBtn = card.querySelector('.prev-value-btn');
      const nextBtn = card.querySelector('.next-value-btn');
      if (prevBtn) prevBtn.disabled = currentIndex === 0;
      if (nextBtn) nextBtn.disabled = !answers[key];
    });
    dots.forEach((dot) => {
      const key = dot.dataset.valueKey;
      dot.classList.remove('answered', 'current', 'unanswered');
      if (answers[key]) {
        dot.classList.add('answered');
      } else {
        dot.classList.add('unanswered');
      }
    });
    if (dots[currentIndex]) {
      dots[currentIndex].classList.add('current');
    }
    if (counter) {
      counter.textContent = `Question ${currentIndex + 1} of ${cards.length}`;
    }
    const answeredCount = Object.keys(answers).length;
    if (submitBtn) submitBtn.disabled = answeredCount < cards.length;
  };

  const saveAnswer = (key, value) => {
    answers[key] = parseInt(value, 10);
    const hiddenInput = document.getElementById(`${key}-input`);
    if (hiddenInput) hiddenInput.value = value;
    assessmentAutosave('values', { ratings: answers });
    updateUI();
  };

  sliderContainer.addEventListener('click', (event) => {
    const target = event.target;
    if (target.classList.contains('value-btn')) {
      const key = target.dataset.valueKey;
      const choice = target.dataset.choice;
      saveAnswer(key, choice);
    }
    if (target.classList.contains('next-value-btn')) {
      const card = target.closest('.value-card-slide');
      const key = card.dataset.valueKey;
      if (!answers[key]) return;
      currentIndex = Math.min(currentIndex + 1, cards.length - 1);
      updateUI();
    }
    if (target.classList.contains('prev-value-btn')) {
      currentIndex = Math.max(currentIndex - 1, 0);
      updateUI();
    }
  });

  // Prefill existing data
  Object.entries(answers).forEach(([key, value]) => {
    const hiddenInput = document.getElementById(`${key}-input`);
    if (hiddenInput) hiddenInput.value = value;
  });

  updateUI();
}

function interpretSlider(value, leftDesc, rightDesc, leftLabel, rightLabel) {
  const intVal = parseInt(value, 10);
  if (intVal <= 2) return leftDesc;
  if (intVal === 3) return `Slightly ${leftLabel}`;
  if (intVal === 4) return 'Balanced between both';
  if (intVal === 5) return `Slightly ${rightLabel}`;
  return rightDesc;
}

function initWorkstyleModule(existingData = {}) {
  const dimCards = Array.from(document.querySelectorAll('.dimension-group-card'));
  if (!dimCards.length) return;
  const responses = existingData.responses ? { ...existingData.responses } : {};
  let currentDim = 0;
  const dots = document.querySelectorAll('#workstyle-dots .progress-dot');
  const submitBtn = document.getElementById('workstyle-submit-btn');
  const counter = document.getElementById('workstyle-progress-counter');
  const debouncedSave = debounce(() => assessmentAutosave('workstyle', { responses }), 800);

  const updateDots = () => {
    dots.forEach((dot, idx) => {
      dot.classList.remove('answered', 'current', 'unanswered');
      const dim = dot.dataset.dimension;
      const answeredCount = dimCards[idx].querySelectorAll('.workstyle-slider').length;
      const filled = Array.from(dimCards[idx].querySelectorAll('.workstyle-slider')).every((slider) => responses[slider.name]);
      if (filled) dot.classList.add('answered');
      else dot.classList.add('unanswered');
      if (idx === currentDim) dot.classList.add('current');
    });
  };

  const updateSubmit = () => {
    const answered = Object.keys(responses).length;
    if (submitBtn) submitBtn.disabled = answered < 12;
    if (counter) counter.textContent = `Question ${Math.min(answered + 1, 12)} of 12`;
  };

  const showDimension = (index) => {
    dimCards.forEach((card, idx) => {
      card.style.display = idx === index ? 'block' : 'none';
    });
    currentDim = index;
    updateDots();
  };

  dimCards.forEach((card) => {
    card.querySelectorAll('.workstyle-slider').forEach((slider) => {
      const interp = document.getElementById(`${slider.name}-interpretation`);
      const leftDesc = slider.dataset.leftDesc;
      const rightDesc = slider.dataset.rightDesc;
      const labelContainer = slider.closest('[data-question-id]').querySelector('.workstyle-slider-labels');
      const leftLabel = labelContainer.querySelector('div:first-child').textContent.trim();
      const rightLabel = labelContainer.querySelector('div:last-child').textContent.trim();
      if (interp) interp.textContent = interpretSlider(slider.value, leftDesc, rightDesc, leftLabel, rightLabel);
      slider.addEventListener('input', (e) => {
        const val = e.target.value;
        responses[slider.name] = parseInt(val, 10);
        if (interp) interp.textContent = interpretSlider(val, leftDesc, rightDesc, leftLabel, rightLabel);
        debouncedSave();
        updateDots();
        updateSubmit();
      });
    });
  });

  document.getElementById('workstyle-form').addEventListener('click', (event) => {
    if (event.target.classList.contains('workstyle-next')) {
      event.preventDefault();
      showDimension(Math.min(currentDim + 1, dimCards.length - 1));
    }
    if (event.target.classList.contains('workstyle-prev')) {
      event.preventDefault();
      showDimension(Math.max(currentDim - 1, 0));
    }
  });

  // Prefill responses
  Object.entries(responses).forEach(([key, value]) => {
    const slider = document.querySelector(`input[name="${key}"]`);
    if (slider) slider.value = value;
  });

  updateDots();
  updateSubmit();
}

function initSkillsModule(existingData = {}) {
  const rows = Array.from(document.querySelectorAll('.skill-row'));
  if (!rows.length) return;
  const totalSkills = rows.length;
  const counter = document.getElementById('skills-progress-counter');
  const submitBtn = document.getElementById('skills-submit-btn');
  const tabBadges = document.querySelectorAll('.skills-tab-badge');
  const ratings = { ...existingData };
  const debouncedSave = debounce(() => assessmentAutosave('skills', { ratings }), 600);

  const updateCounts = () => {
    let answered = 0;
    const categoryCounts = {};
    rows.forEach((row) => {
      const key = row.dataset.skillKey;
      const category = row.dataset.category;
      if (ratings[key] !== undefined && ratings[key] !== '') answered += 1;
      if (!categoryCounts[category]) categoryCounts[category] = { answered: 0, total: 0 };
      categoryCounts[category].total += 1;
      if (ratings[key] !== undefined && ratings[key] !== '') categoryCounts[category].answered += 1;
    });
    tabBadges.forEach((badge) => {
      const category = badge.dataset.category;
      const info = categoryCounts[category] || { answered: 0, total: 5 };
      badge.textContent = `${info.answered}/${info.total}`;
    });
    if (counter) counter.textContent = `${answered} of ${totalSkills} skills rated`;
    if (submitBtn) submitBtn.disabled = answered < totalSkills;
  };

  rows.forEach((row) => {
    const key = row.dataset.skillKey;
    const buttons = row.querySelectorAll('.skill-rating-btn');
    const hidden = document.getElementById(`${key}-input`);
    const selected = ratings[key];
    if (selected !== undefined) {
      buttons.forEach((btn) => btn.classList.toggle('selected', parseInt(btn.dataset.value, 10) === parseInt(selected, 10)));
    }
    row.addEventListener('click', (event) => {
      if (!event.target.classList.contains('skill-rating-btn')) return;
      const value = event.target.dataset.value;
      buttons.forEach((btn) => btn.classList.remove('selected'));
      event.target.classList.add('selected');
      ratings[key] = parseInt(value, 10);
      if (hidden) hidden.value = value;
      updateCounts();
      debouncedSave();
    });
  });

  updateCounts();
}

function initConstraintsModule(existingData = {}) {
  const presets = document.querySelectorAll('.constraint-preset-btn');
  const incomeInput = document.getElementById('income_floor');
  const hoursSlider = document.getElementById('hours_per_week');
  const hoursLabel = document.getElementById('hours-value-label');
  const hoursFeedback = document.getElementById('hours-feedback-text');
  const timelineCards = document.querySelectorAll('.timeline-option-card');
  const timelineInput = document.getElementById('timeline_months');
  const geoCards = document.querySelectorAll('.geo-option-card');
  const geoInput = document.getElementById('geographic_flexibility');
  const form = document.getElementById('constraints-form');
  if (!form) return;

  const updateHoursFeedback = (value) => {
    if (!hoursFeedback) return;
    hoursFeedback.className = 'hours-feedback';
    const val = parseInt(value, 10);
    if (val < 5) {
      hoursFeedback.classList.add('low');
      hoursFeedback.textContent = 'Very limited — your roadmap will focus on high-leverage activities only';
    } else if (val < 10) {
      hoursFeedback.classList.add('moderate');
      hoursFeedback.textContent = 'Moderate — achievable in 12-18 months with consistency';
    } else if (val < 20) {
      hoursFeedback.classList.add('good');
      hoursFeedback.textContent = 'Good — a well-paced 9-12 month plan is realistic';
    } else {
      hoursFeedback.classList.add('high');
      hoursFeedback.textContent = 'Intensive — you could complete a pivot in 6-9 months';
    }
  };

  const saveConstraints = debounce(() => {
    const payload = {
      income_floor: incomeInput ? incomeInput.value : '',
      hours_per_week: hoursSlider ? hoursSlider.value : '',
      timeline_months: timelineInput ? timelineInput.value : '',
      geographic_flexibility: geoInput ? geoInput.value : ''
    };
    assessmentAutosave('constraints', payload);
  }, 500);

  presets.forEach((btn) => {
    btn.addEventListener('click', () => {
      presets.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      if (incomeInput) incomeInput.value = btn.dataset.value;
      saveConstraints();
    });
  });

  if (hoursSlider) {
    const val = hoursSlider.value || 10;
    if (hoursLabel) hoursLabel.textContent = `${val} hrs`;
    updateHoursFeedback(val);
    hoursSlider.addEventListener('input', (e) => {
      const value = e.target.value;
      if (hoursLabel) hoursLabel.textContent = `${value} hrs`;
      updateHoursFeedback(value);
      saveConstraints();
    });
  }

  timelineCards.forEach((card) => {
    card.addEventListener('click', () => {
      timelineCards.forEach((c) => c.classList.remove('selected'));
      card.classList.add('selected');
      if (timelineInput) timelineInput.value = card.dataset.value;
      saveConstraints();
    });
  });

  geoCards.forEach((card) => {
    card.addEventListener('click', () => {
      geoCards.forEach((c) => c.classList.remove('selected'));
      card.classList.add('selected');
      if (geoInput) geoInput.value = card.dataset.value;
      saveConstraints();
    });
  });

  // Prefill selections
  if (existingData.income_floor && incomeInput) incomeInput.value = existingData.income_floor;
  if (existingData.hours_per_week && hoursSlider) {
    hoursSlider.value = existingData.hours_per_week;
    if (hoursLabel) hoursLabel.textContent = `${existingData.hours_per_week} hrs`;
    updateHoursFeedback(existingData.hours_per_week);
  }
  if (existingData.timeline_months && timelineInput) {
    timelineInput.value = existingData.timeline_months;
    timelineCards.forEach((card) => {
      if (parseInt(card.dataset.value, 10) === parseInt(existingData.timeline_months, 10)) {
        card.classList.add('selected');
      }
    });
  }
  if (existingData.geographic_flexibility && geoInput) {
    geoInput.value = existingData.geographic_flexibility;
    geoCards.forEach((card) => {
      if (card.dataset.value === existingData.geographic_flexibility) card.classList.add('selected');
    });
  }
}

function initVisionModule() {
  const form = document.getElementById('vision-form');
  if (!form) return;
  const counters = document.querySelectorAll('.vision-char-counter');
  const loadingOverlay = document.getElementById('vision-loading-overlay');
  const submitBtn = document.getElementById('vision-submit-btn');
  const getValues = () => ({
    vision_day: form.querySelector('textarea[name="vision_day"]').value,
    vision_impact: form.querySelector('textarea[name="vision_impact"]').value,
    vision_regret: form.querySelector('textarea[name="vision_regret"]').value
  });

  const updateCounter = (textarea) => {
    const counter = Array.from(counters).find((c) => c.dataset.target === textarea.name);
    if (!counter) return;
    const length = textarea.value.length;
    counter.textContent = `${length} / 1500 characters`;
    counter.classList.toggle('warning', length > 1300);
  };

  counters.forEach((counter) => {
    const target = counter.dataset.target;
    const textarea = form.querySelector(`textarea[name="${target}"]`);
    if (textarea) {
      updateCounter(textarea);
      textarea.addEventListener('input', () => updateCounter(textarea));
      textarea.addEventListener('blur', debounce(() => assessmentAutosave('vision', getValues()), 400));
    }
  });

  form.addEventListener('submit', () => {
    if (loadingOverlay) loadingOverlay.classList.remove('d-none');
    if (submitBtn) submitBtn.disabled = true;
  });
}

function initResultsRadarChart(chartData = {}) {
  const canvas = document.getElementById('skillsRadarChart');
  if (!canvas || !window.Chart) return;
  const labels = Object.keys(chartData);
  const dataValues = Object.values(chartData);
  const ctx = canvas.getContext('2d');
  new Chart(ctx, {
    type: 'radar',
    data: {
      labels,
      datasets: [{
        label: 'Skill Confidence',
        data: dataValues,
        backgroundColor: 'rgba(46,134,193,0.2)',
        borderColor: '#2E86C1',
        borderWidth: 2,
        pointBackgroundColor: '#1A5276'
      }]
    },
    options: {
      responsive: true,
      scales: {
        r: {
          suggestedMin: 0,
          suggestedMax: 4,
          ticks: { stepSize: 1 }
        }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

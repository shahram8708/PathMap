// Booking checkout helper for session marketplace pages
(function() {
  function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || '';
  }

  function initBookingPayment(config) {
    const payBtn = document.getElementById('book-session-btn');
    const notesForm = document.getElementById('booking-notes-form');
    if (!payBtn || !notesForm || !config || !config.create_order_url || !config.verify_url) return;

    const notesField = notesForm.querySelector('[name="notes_from_booker"]');
    const originalLabel = payBtn.textContent;
    const statusBox = document.createElement('div');
    statusBox.className = 'text-danger small mt-2 d-none';
    payBtn.insertAdjacentElement('afterend', statusBox);

    const setLoading = (state) => {
      payBtn.disabled = state;
      payBtn.classList.toggle('disabled', state);
      payBtn.textContent = state ? 'Processing...' : originalLabel;
    };

    const showMessage = (text, kind = 'error') => {
      if (!text) {
        statusBox.classList.add('d-none');
        return;
      }
      statusBox.textContent = text;
      statusBox.classList.remove('d-none', 'text-danger', 'text-success');
      statusBox.classList.add(kind === 'success' ? 'text-success' : 'text-danger');
    };

    payBtn.addEventListener('click', async (evt) => {
      evt.preventDefault();
      if (typeof Razorpay === 'undefined') {
        showMessage('Payment gateway unavailable. Please refresh and try again.');
        return;
      }
      setLoading(true);
      showMessage('');

      try {
        const resp = await fetch(config.create_order_url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({ notes_from_booker: notesField?.value || '' })
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) {
          throw new Error(data.error || 'Unable to create order right now.');
        }

        const rzp = new Razorpay({
          key: data.key || '',
          amount: data.amount,
          currency: data.currency || 'INR',
          name: 'PathMap',
          description: data.description || `Shadow Session with ${config.provider_name || ''}`,
          order_id: data.order_id,
          prefill: { email: config.user_email || '', name: config.user_name || '' },
          theme: { color: '#1A5276' },
          modal: {
            ondismiss: function() {
              setLoading(false);
              showMessage('Payment cancelled. Your booking has not been confirmed.');
            }
          },
          handler: async function(response) {
            showMessage('Verifying payment...', 'success');
            try {
              const verifyResp = await fetch(config.verify_url, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                  razorpay_payment_id: response.razorpay_payment_id,
                  razorpay_order_id: response.razorpay_order_id,
                  razorpay_signature: response.razorpay_signature,
                  booking_id: data.booking_id
                })
              });
              const verifyData = await verifyResp.json();
              if (verifyData.success) {
                const redirectUrl = verifyData.redirect_url || '/sessions/my-bookings';
                window.location.href = redirectUrl;
                return;
              }
              throw new Error(verifyData.error || 'Payment verification failed.');
            } catch (err) {
              showMessage(err.message || 'Payment verification failed.');
              setLoading(false);
            }
          }
        });

        rzp.open();
      } catch (err) {
        showMessage(err.message || 'Unable to start payment. Please try again.');
        setLoading(false);
      }
    });
  }

  function initRatingStarsInput() {
    const container = document.getElementById('rating-stars');
    if (!container) return;
    const stars = Array.from(container.querySelectorAll('.star-input'));
    const inputs = Array.from(container.querySelectorAll('input[type="radio"]'));

    const setRating = (value) => {
      stars.forEach((star) => {
        const starValue = parseInt(star.dataset.value, 10);
        star.classList.toggle('opacity-25', !(value && starValue <= value));
      });
      inputs.forEach((input) => {
        input.checked = parseInt(input.value, 10) === value;
      });
    };

    const current = container.querySelector('input:checked');
    setRating(current ? parseInt(current.value, 10) : 0);

    stars.forEach((star) => {
      const value = parseInt(star.dataset.value, 10);
      star.addEventListener('mouseenter', () => setRating(value));
      star.addEventListener('focus', () => setRating(value));
      star.addEventListener('click', () => setRating(value));
      star.addEventListener('mouseleave', () => {
        const checked = container.querySelector('input:checked');
        setRating(checked ? parseInt(checked.value, 10) : 0);
      });
      star.addEventListener('keyup', (evt) => {
        if (evt.key === 'Enter' || evt.key === ' ') {
          setRating(value);
        }
      });
    });
  }

  function initBookmarkToggle() {
    const buttons = document.querySelectorAll('.resource-bookmark-btn');
    if (!buttons.length) return;

    const updateButtonState = (btn, bookmarked) => {
      btn.classList.toggle('bookmarked', bookmarked);
      const icon = btn.querySelector('i');
      if (icon) {
        icon.classList.toggle('bi-bookmark-fill', bookmarked);
        icon.classList.toggle('bi-bookmark', !bookmarked);
      } else if (!bookmarked) {
        const listItem = btn.closest('.list-group-item');
        if (listItem) listItem.remove();
      }
    };

    buttons.forEach((btn) => {
      btn.addEventListener('click', async (evt) => {
        evt.preventDefault();
        const resourceId = btn.dataset.resourceId;
        if (!resourceId) return;
        btn.disabled = true;
        try {
          const resp = await fetch(`/resources/bookmark/${resourceId}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({})
          });
          const data = await resp.json().catch(() => ({}));
          if (resp.status === 403 && data.limit_reached) {
            alert(data.message || 'Bookmark limit reached on your plan.');
            return;
          }
          if (!resp.ok || !data.success) {
            throw new Error(data.error || 'Unable to update bookmark.');
          }
          updateButtonState(btn, data.bookmarked);
        } catch (err) {
          console.error('Bookmark toggle failed', err);
        } finally {
          btn.disabled = false;
        }
      });
    });
  }

  function initResourceSearch() {
    const input = document.getElementById('resource-search-input');
    const results = document.getElementById('resource-search-results');
    if (!input || !results) return;

    let debounceTimer = null;
    let currentAbort = null;

    const hideResults = () => {
      results.classList.add('d-none');
      results.innerHTML = '';
    };

    const renderResults = (items) => {
      if (!items.length) {
        results.innerHTML = '<div class="list-group-item text-muted small">No matches found</div>';
        results.classList.remove('d-none');
        return;
      }
      results.innerHTML = items.map((item) => `
        <a class="list-group-item list-group-item-action" href="${item.url}">
          <div class="fw-semibold">${item.skill_name}</div>
          <div class="small text-muted">${item.resource_title} · ${item.provider} · ${item.format} · ${item.cost_tier}</div>
        </a>
      `).join('');
      results.classList.remove('d-none');
    };

    const runSearch = async (term) => {
      if (currentAbort) currentAbort.abort();
      currentAbort = new AbortController();
      try {
        const resp = await fetch(`/resources/search?q=${encodeURIComponent(term)}`, { signal: currentAbort.signal });
        if (!resp.ok) throw new Error('Search failed');
        const data = await resp.json();
        if (input.value.trim().toLowerCase() !== term.toLowerCase()) return;
        renderResults(Array.isArray(data) ? data : []);
      } catch (err) {
        if (err.name === 'AbortError') return;
        console.error('Resource search failed', err);
      }
    };

    input.addEventListener('input', () => {
      const term = input.value.trim();
      clearTimeout(debounceTimer);
      if (term.length < 2) {
        hideResults();
        return;
      }
      debounceTimer = setTimeout(() => runSearch(term), 250);
    });

    input.addEventListener('focus', () => {
      if (results.children.length) {
        results.classList.remove('d-none');
      }
    });

    document.addEventListener('click', (evt) => {
      if (!results.contains(evt.target) && evt.target !== input) {
        hideResults();
      }
    });

    input.addEventListener('keydown', (evt) => {
      if (evt.key === 'Escape') hideResults();
    });
  }

  window.initBookingPayment = initBookingPayment;
  window.initRatingStarsInput = initRatingStarsInput;
  window.initBookmarkToggle = initBookmarkToggle;
  window.initResourceSearch = initResourceSearch;
})();

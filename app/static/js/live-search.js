(() => {
  const forms = document.querySelectorAll('form[data-live-search]');
  if (!forms.length) return;

  const debounce = (fn, delay) => {
    let timerId;
    return (...args) => {
      window.clearTimeout(timerId);
      timerId = window.setTimeout(() => fn.apply(null, args), delay);
    };
  };

  forms.forEach((form) => {
    const input = form.querySelector('input[name="q"]');
    const targetSelector = form.dataset.resultsTarget;
    if (!input || !targetSelector) {
      return;
    }
    const resultsElement = document.querySelector(targetSelector);
    if (!resultsElement) {
      return;
    }

    const minLength = parseInt(form.dataset.minLength || '0', 10);
    const debounceDelay = parseInt(form.dataset.debounce || '350', 10);
    let lastValue = input.value.trim();
    let controller = null;

    const buildUrl = () => {
      const formAction = form.getAttribute('action') || window.location.pathname;
      const url = new URL(formAction, window.location.origin);
      const formData = new FormData(form);
      formData.forEach((value, key) => {
        url.searchParams.set(key, value);
      });
      return url;
    };

    const requestResults = (force = false) => {
      const currentValue = input.value.trim();
      if (!force && currentValue === lastValue && controller === null) {
        return;
      }
      const meetsLength = currentValue.length === 0 || currentValue.length >= minLength;
      if (!meetsLength && !force) {
        return;
      }
      lastValue = currentValue;

      if (controller) {
        controller.abort();
      }
      controller = new AbortController();

      const url = buildUrl();
      fetch(url, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        signal: controller.signal,
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          return response.text();
        })
        .then((html) => {
          resultsElement.innerHTML = html;
        })
        .catch((error) => {
          if (error.name !== 'AbortError') {
            console.error('Live search error:', error);
          }
        })
        .finally(() => {
          controller = null;
        });
    };

    const debouncedRequest = debounce(requestResults, debounceDelay);

    input.addEventListener('input', () => {
      debouncedRequest();
    });

    form.addEventListener('submit', (event) => {
      const currentValue = input.value.trim();
      const meetsLength = currentValue.length === 0 || currentValue.length >= minLength;
      if (!meetsLength) {
        return;
      }
      event.preventDefault();
      requestResults(true);
    });
  });
})();

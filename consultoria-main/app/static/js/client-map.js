(function () {
  function parseLatLng(value) {
    if (!value) {
      return null;
    }
    const decoded = decodeURIComponent(value);
    const match = decoded.match(/(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)/);
    if (!match) {
      return null;
    }
    return {
      lat: parseFloat(match[1]),
      lng: parseFloat(match[2]),
    };
  }

  function formatCoord(num) {
    return Number.parseFloat(num).toFixed(6);
  }

  function initClientMap(mapId) {
    const mapEl = document.getElementById(mapId);
    if (!mapEl || typeof L === 'undefined') {
      return;
    }

    const editable = mapEl.dataset.editable === 'true';
    const defaultLat = parseFloat(mapEl.dataset.defaultLat || '-25.2867');
    const defaultLng = parseFloat(mapEl.dataset.defaultLng || '-57.6459');
    const initialLink =
      mapEl.dataset.initialLink ||
      (mapEl.dataset.linkTarget
        ? document.querySelector(mapEl.dataset.linkTarget)?.value
        : '');
    const parsedInitial = parseLatLng(initialLink);

    const startLat = parsedInitial ? parsedInitial.lat : defaultLat;
    const startLng = parsedInitial ? parsedInitial.lng : defaultLng;
    const startZoom = parsedInitial
      ? 15
      : parseInt(mapEl.dataset.initialZoom || '12', 10);

    const map = L.map(mapEl).setView([startLat, startLng], startZoom);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    let marker = null;
    const linkInput = mapEl.dataset.linkTarget
      ? document.querySelector(mapEl.dataset.linkTarget)
      : null;
    const coordsOutput = mapEl.dataset.coordTarget
      ? document.querySelector(mapEl.dataset.coordTarget)
      : null;
    const searchInput = mapEl.dataset.searchInput
      ? document.querySelector(mapEl.dataset.searchInput)
      : null;
    const searchButton = mapEl.dataset.searchButton
      ? document.querySelector(mapEl.dataset.searchButton)
      : null;
    const searchResults = mapEl.dataset.searchResults
      ? document.querySelector(mapEl.dataset.searchResults)
      : null;
    let searchAbort = null;

    function placeMarker(lat, lng, updateView) {
      const latNum = Number.parseFloat(lat);
      const lngNum = Number.parseFloat(lng);
      if (!Number.isFinite(latNum) || !Number.isFinite(lngNum)) {
        return;
      }
      if (!marker) {
        marker = L.marker([latNum, lngNum]).addTo(map);
      } else {
        marker.setLatLng([latNum, lngNum]);
      }
      if (updateView) {
        map.setView([latNum, lngNum], 15);
      }
      if (coordsOutput) {
        coordsOutput.textContent = `${formatCoord(latNum)}, ${formatCoord(
          lngNum,
        )}`;
      }
      if (linkInput) {
        linkInput.value = `https://www.google.com/maps?q=${formatCoord(
          latNum,
        )},${formatCoord(lngNum)}`;
      }
    }

    function clearSearchResults() {
      if (searchResults) {
        searchResults.innerHTML = '';
        searchResults.hidden = true;
      }
    }

    function appendInfoResult(message) {
      if (!searchResults) {
        return;
      }
      const info = document.createElement('div');
      info.className = 'list-group-item list-group-item-action disabled text-muted small';
      info.textContent = message;
      searchResults.append(info);
      searchResults.hidden = false;
    }

    function populateSearchResults(features) {
      if (!searchResults) {
        return;
      }
      clearSearchResults();
      if (!features.length) {
        appendInfoResult('No se encontraron resultados.');
        return;
      }
      features.forEach((item) => {
        const entry = document.createElement('button');
        entry.type = 'button';
        entry.className = 'list-group-item list-group-item-action';
        entry.textContent = item.display_name || 'Ubicación';
        entry.addEventListener('click', () => {
          placeMarker(item.lat, item.lon, true);
          if (searchInput) {
            searchInput.value = item.display_name || '';
          }
          clearSearchResults();
        });
        searchResults.append(entry);
      });
      searchResults.hidden = false;
    }

    async function executeSearch(query) {
      if (!query || !searchResults) {
        return;
      }
      const sanitized = query.trim();
      if (!sanitized) {
        return;
      }
      if (searchAbort) {
        searchAbort.abort();
      }
      const controller = new AbortController();
      searchAbort = controller;
      clearSearchResults();
      appendInfoResult('Buscando resultados…');
      try {
        const url = `https://nominatim.openstreetmap.org/search?format=json&addressdetails=0&limit=6&q=${encodeURIComponent(
          sanitized,
        )}`;
        const response = await fetch(url, {
          headers: { Accept: 'application/json' },
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`Error ${response.status}`);
        }
        const data = await response.json();
        if (controller.signal.aborted) {
          return;
        }
        populateSearchResults(Array.isArray(data) ? data : []);
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        clearSearchResults();
        appendInfoResult('No pudimos completar la búsqueda. Intenta nuevamente.');
        console.error('Map search error:', error);
      } finally {
        if (searchAbort === controller) {
          searchAbort = null;
        }
      }
    }

    if (parsedInitial) {
      placeMarker(parsedInitial.lat, parsedInitial.lng, false);
    }

    if (editable) {
      map.on('click', (event) => {
        placeMarker(event.latlng.lat, event.latlng.lng, true);
      });

      if (linkInput) {
        linkInput.addEventListener('change', () => {
          const parsed = parseLatLng(linkInput.value);
          if (parsed) {
            placeMarker(parsed.lat, parsed.lng, true);
          }
        });
      }

      if (searchInput && searchButton && searchResults) {
        const triggerSearch = () => executeSearch(searchInput.value);
        searchButton.addEventListener('click', triggerSearch);
        searchInput.addEventListener('keydown', (event) => {
          if (event.key === 'Enter') {
            event.preventDefault();
            triggerSearch();
          }
        });
        document.addEventListener('click', (event) => {
          if (
            searchResults &&
            !searchResults.contains(event.target) &&
            event.target !== searchInput &&
            event.target !== searchButton
          ) {
            clearSearchResults();
          }
        });
      }
    }
  }

  window.initClientMap = initClientMap;

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-client-map="true"]').forEach((el) => {
      initClientMap(el.id);
    });
  });
})();

(function(){
  function $(sel, root){ return (root||document).querySelector(sel); }
  function $all(sel, root){ return Array.from((root||document).querySelectorAll(sel)); }

  let posponerModal, finalizarModal, alertasModal;
  let posponerModalInstance, finalizarModalInstance, alertasModalInstance;

  function initModals(){
    const pm = $('#modalPosponer');
    const fm = $('#modalFinalizar');
    const am = $('#modalAlertas');
    if (pm && window.bootstrap) posponerModalInstance = bootstrap.Modal.getOrCreateInstance(pm);
    if (fm && window.bootstrap) finalizarModalInstance = bootstrap.Modal.getOrCreateInstance(fm);
    if (am && window.bootstrap) alertasModalInstance = bootstrap.Modal.getOrCreateInstance(am);
    posponerModal = pm; finalizarModal = fm; alertasModal = am;
  }

  async function postJSON(url, data){
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data||{})
    });
    const json = await res.json().catch(()=>({ ok:false, error:'Respuesta inválida' }));
    if (!res.ok || json.ok === false) throw new Error(json.error || 'Error de red');
    return json;
  }

  function onPosponerClick(ev){
    const btn = ev.currentTarget;
    const id = btn.getAttribute('data-proyecto-id');
    if (!id || !posponerModal) return;
    $('#posponer-proyecto-id').value = id;
    $('#posponer-motivo').value = '';
    $('#posponer-dias').value = '7';
    posponerModalInstance && posponerModalInstance.show();
  }
  
  function onFinalizarClick(ev){
    const btn = ev.currentTarget;
    const id = btn.getAttribute('data-proyecto-id');
    if (!id || !finalizarModal) return;
    $('#finalizar-proyecto-id').value = id;
    $('#finalizar-motivo').value = '';
    finalizarModalInstance && finalizarModalInstance.show();
  }

  async function confirmarPosponer(){
    const id = $('#posponer-proyecto-id').value;
    const motivo = $('#posponer-motivo').value;
    const dias = parseInt($('#posponer-dias').value, 10) || 7;
    try{
      await postJSON(`/proyectos/${id}/alerta/posponer`, { motivo, dias });
      posponerModalInstance && posponerModalInstance.hide();
      // Recargar para ocultar la fila en el dashboard
      window.location.reload();
    }catch(err){
      alert(err.message || 'No se pudo posponer');
    }
  }

  async function confirmarFinalizar(){
    const id = $('#finalizar-proyecto-id').value;
    const motivo = $('#finalizar-motivo').value;
    try{
      await postJSON(`/proyectos/${id}/alerta/finalizar`, { motivo });
      finalizarModalInstance && finalizarModalInstance.hide();
      window.location.reload();
    }catch(err){
      alert(err.message || 'No se pudo finalizar');
    }
  }

  async function cargarAlertas(){
    try{
      const res = await fetch('/proyectos/alertas');
      const data = await res.json();
      if (!data || data.ok === false) throw new Error(data.error || 'No se pudieron cargar las alertas');

      const snoozedTbody = $('#tabla-snoozed tbody');
      const finTbody = $('#tabla-finalizadas tbody');
      if (snoozedTbody) snoozedTbody.innerHTML = '';
      if (finTbody) finTbody.innerHTML = '';

      (data.snoozed || []).forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${escapeHtml(projectName(item))}</td>
          <td>${escapeHtml(item.cliente || '')}</td>
          <td>${formatDate(item.snoozed_until)}</td>
          <td class="text-end">
            <button class="btn btn-sm btn-outline-primary js-restaurar" data-id="${item.id_proyecto}">
              <i class="bi bi-arrow-counterclockwise"></i>
            </button>
          </td>`;
        snoozedTbody && snoozedTbody.appendChild(tr);
      });

      (data.finalized || []).forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${escapeHtml(projectName(item))}</td>
          <td>${escapeHtml(item.cliente || '')}</td>
          <td>${formatDate(item.finalized_at)}</td>
          <td class="text-end">
            <button class="btn btn-sm btn-outline-primary js-restaurar" data-id="${item.id_proyecto}">
              <i class="bi bi-arrow-counterclockwise"></i>
            </button>
          </td>`;
        finTbody && finTbody.appendChild(tr);
      });

      $all('.js-restaurar', alertasModal).forEach(btn => {
        btn.addEventListener('click', async (e) => {
          const id = e.currentTarget.getAttribute('data-id');
          try{
            await postJSON(`/proyectos/${id}/alerta/restaurar`, {});
            await cargarAlertas();
            // Si estamos en dashboard, recargar para mostrarlo otra vez
            if (location.pathname === '/' || location.pathname.includes('/dashboard')) {
              window.location.reload();
            }
          }catch(err){ alert(err.message || 'No se pudo restaurar'); }
        });
      });

    }catch(err){
      console.error(err);
      alert('Error al cargar alertas');
    }
  }

  function projectName(item){
    return item.nombre || `${item.institucion||''} ${item.ano||''}`.trim();
  }

  function formatDate(iso){
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleDateString('es-PY');
  }

  function escapeHtml(str){
    return (str||'').replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[s]));
  }

  function initButtons(){
    $all('.js-posponer-alerta').forEach(btn => btn.addEventListener('click', onPosponerClick));
    $all('.js-finalizar-alerta').forEach(btn => btn.addEventListener('click', onFinalizarClick));
    const btnAlertas = $('#btn-alertas');
    if (btnAlertas && alertasModalInstance){
      btnAlertas.addEventListener('click', async () => {
        alertasModalInstance.show();
        await cargarAlertas();
      });
    }
    const confirmPosponer = $('#btn-confirmar-posponer');
    const confirmFinalizar = $('#btn-confirmar-finalizar');
    if (confirmPosponer) confirmPosponer.addEventListener('click', confirmarPosponer);
    if (confirmFinalizar) confirmFinalizar.addEventListener('click', confirmarFinalizar);
  }

  document.addEventListener('DOMContentLoaded', function(){
    initModals();
    initButtons();
  });
})();

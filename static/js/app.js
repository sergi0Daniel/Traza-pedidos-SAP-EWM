const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const state = { orders: [], currentOrder: null, alerts: [], page: 'dashboard', aiAction: 'report' };

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
function formatDate(value) {
  if (!value) return 'Sin fecha';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return escapeHtml(value);
  return new Intl.DateTimeFormat('es-CO', {dateStyle:'short', timeStyle:'short'}).format(date);
}
function minutesSince(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return Math.max(0, Math.floor((Date.now() - date.getTime()) / 60000));
}
function formatMinutes(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'No disponible';
  const mins = Math.max(0, Number(value));
  const hours = Math.floor(mins / 60);
  const rest = mins % 60;
  return hours ? `${hours} h ${String(rest).padStart(2,'0')} min` : `${rest} min`;
}
function stageMinutes(order) {
  return order.elapsed_minutes ?? minutesSince(order.stage_started_at);
}
function statusClass(status) {
  const text = String(status || '').toLowerCase();
  if (text.includes('demora') || text.includes('retras')) return 'danger';
  if (text.includes('listo') || text.includes('despach') || text.includes('confirm')) return 'success';
  if (text.includes('proceso') || text.includes('empaque') || text.includes('picking') || text.includes('cargue')) return 'warning';
  return 'neutral';
}
function statusBadge(status) {
  return `<span class="status-badge ${statusClass(status)}">${escapeHtml(status || 'No informado')}</span>`;
}
async function api(url, options = {}) {
  const response = await fetch(url, options);
  let data;
  try { data = await response.json(); } catch { throw new Error(`Respuesta no válida del servidor (${response.status}).`); }
  if (!response.ok) throw new Error(data.error || data.message || `Error ${response.status}`);
  return data;
}
function toast(message) {
  const el = $('#toast');
  el.textContent = message;
  el.classList.add('show');
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => el.classList.remove('show'), 3500);
}
function navigate(page) {
  state.page = page;
  $$('.page').forEach(el => el.classList.toggle('active', el.id === `page-${page}`));
  $$('.nav-item').forEach(el => el.classList.toggle('active', el.dataset.page === page));
  const active = $(`.nav-item[data-page="${page}"]`);
  $('#breadcrumbCurrent').textContent = active ? active.textContent.trim() : 'Detalle del pedido';
  $('#sidebar').classList.remove('open');
  window.scrollTo({top:0, behavior:'smooth'});
}
function setMode(mode, warning) {
  const isLive = mode === 'SAP EWM';
  $('#modePill').innerHTML = `<span class="status-dot ${isLive ? 'live' : ''}"></span><span>${isLive ? 'Consulta SAP EWM' : 'Datos de demostración'}</span>`;
  $('#sidebarDot').classList.toggle('live', isLive);
  $('#sidebarMode').textContent = isLive ? 'Fuente: SAP EWM' : 'Modo demostración';
  $('#footerDataMode').textContent = isLive ? 'Fuente: SAP EWM' : 'Entorno de demostración';
  $('#demoBanner').classList.toggle('hidden', isLive);
  if (isLive) {
    $('#demoBanner').innerHTML = `<span>✓</span><div><strong>Consulta de SAP EWM</strong><p>${escapeHtml(warning || 'La información procede del servicio configurado. Verifica su fecha de actualización.')}</p></div>`;
  } else {
    $('#demoBanner').innerHTML = `<span>ⓘ</span><div><strong>Vista de demostración</strong><p>${escapeHtml(warning || 'Los pedidos y las cifras que aparecen son ilustrativos. La conexión real con SAP EWM está pendiente de configuración y autorización.')}</p></div>`;
  }
}
function renderStageBreakdown(counts, total) {
  const entries = Object.entries(counts || {}).filter(([, count]) => Number(count) > 0);
  if (!entries.length) {
    $('#stageBreakdown').innerHTML = '<div class="empty-state">No hay pedidos para mostrar.</div>';
    return;
  }
  $('#stageBreakdown').innerHTML = entries.map(([name, count]) => {
    const pct = total ? Math.round((count / total) * 100) : 0;
    return `<div class="stage-row"><span class="stage-label">${escapeHtml(name)}</span><div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div><span class="stage-value">${count}</span></div>`;
  }).join('');
}
function renderOrdersTable(orders, targetId, withDelivery = true) {
  const target = $(`#${targetId}`);
  if (!orders.length) {
    target.innerHTML = `<tr><td colspan="${withDelivery ? 7 : 6}" class="table-empty">No se encontraron pedidos con esos criterios.</td></tr>`;
    return;
  }
  target.innerHTML = orders.map(order => {
    const elapsed = stageMinutes(order);
    const alert = state.alerts.find(a => a.order_id === order.order_id);
    const currentStatus = alert ? 'Con demora' : order.status;
    return `<tr>
      <td><strong>${escapeHtml(order.order_id)}</strong></td>
      ${withDelivery ? `<td>${escapeHtml(order.delivery_id || 'No disponible')}</td>` : ''}
      <td>${escapeHtml(order.stage || 'Sin etapa confirmada')}</td>
      <td>${escapeHtml(order.location || 'Sin ubicación informada')}</td>
      <td>${formatMinutes(elapsed)}</td>
      <td>${statusBadge(currentStatus)}</td>
      <td><button class="table-action view-order" data-order="${escapeHtml(order.order_id)}">Ver detalle →</button></td>
    </tr>`;
  }).join('');
}
function renderAttention() {
  const target = $('#attentionList');
  if (!state.alerts.length) {
    target.innerHTML = '<div class="empty-state">No hay pedidos que superen los límites configurados.</div>';
    return;
  }
  target.innerHTML = state.alerts.slice(0, 4).map(alert => `<div class="attention-item"><div><strong>${escapeHtml(alert.order_id)} · ${escapeHtml(alert.stage)}</strong><small>${escapeHtml(alert.location)}</small></div><span class="time-pill">+ ${formatMinutes(alert.overdue_minutes)}</span></div>`).join('');
}
async function loadDashboard() {
  try {
    const [summary, ordersData, alertsData] = await Promise.all([api('/api/summary'), api('/api/orders'), api('/api/alerts')]);
    state.orders = ordersData.orders || [];
    state.alerts = alertsData.alerts || [];
    setMode(summary.data_mode, summary.warning);
    $('#metricActive').textContent = summary.active_orders ?? '—';
    $('#metricShipped').textContent = summary.shipped_orders ?? '—';
    $('#metricDelayed').textContent = alertsData.configured ? (summary.delayed_orders ?? 0) : '—';
    $('#metricLoading').textContent = summary.loading_orders ?? '—';
    renderStageBreakdown(summary.stage_counts, summary.total_orders);
    renderAttention();
    renderOrdersTable(state.orders.slice(0, 5), 'recentOrders', false);
    $('#navAlertCount').textContent = alertsData.configured ? state.alerts.length : '—';
    await loadConnectionStatus();
    await loadAIStatus();
  } catch (error) {
    toast(`No se pudo cargar el resumen: ${error.message}`);
  }
}
async function loadOrders() {
  const query = $('#orderSearch').value.trim();
  const stage = $('#stageFilter').value;
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (stage) params.set('stage', stage);
  try {
    const data = await api(`/api/orders?${params.toString()}`);
    state.orders = data.orders || [];
    $('#ordersCount').textContent = `${data.total} pedido(s) · Fuente: ${data.mode}`;
    renderOrdersTable(state.orders, 'ordersTable', true);
  } catch (error) {
    $('#ordersTable').innerHTML = `<tr><td colspan="7" class="table-empty">${escapeHtml(error.message)}</td></tr>`;
  }
}
function progressIndex(stage) {
  const stages = ['Pedido registrado', 'Picking', 'Empaque', 'Zona de despacho', 'Puerta de embarque', 'Cargue', 'Salida'];
  const normalized = String(stage || '').toLowerCase();
  if (normalized.includes('despachado') || normalized.includes('salida')) return 6;
  if (normalized.includes('cargue')) return 5;
  if (normalized.includes('puerta')) return 4;
  if (normalized.includes('despacho')) return 3;
  if (normalized.includes('empaque')) return 2;
  if (normalized.includes('picking')) return 1;
  return 0;
}
function renderDetail(order) {
  state.currentOrder = order;
  $('#detailTitle').textContent = `Pedido ${order.order_id}`;
  $('#detailSubtitle').textContent = `Documento de entrega: ${order.delivery_id || 'No informado'} · Creación: ${formatDate(order.created_at)}`;
  const alert = order.alert;
  $('#detailStatus').className = `status-badge ${alert ? 'danger' : statusClass(order.status)}`;
  $('#detailStatus').textContent = alert ? 'Con demora' : (order.status || 'Estado no informado');
  const stages = ['Pedido registrado', 'Picking', 'Empaque', 'Zona de despacho', 'Puerta de embarque', 'Cargue', 'Salida'];
  const currentIndex = progressIndex(order.stage);
  const steps = stages.map((stage, index) => {
    const stateClass = index < currentIndex ? 'done' : index === currentIndex ? 'current' : '';
    const event = (order.events || []).find(e => String(e.stage || '').toLowerCase().includes(stage.toLowerCase().split(' ')[0]));
    return `<div class="progress-step ${stateClass}"><div class="progress-dot"></div><strong>${escapeHtml(stage)}</strong><small>${event ? formatDate(event.event_time) : (index === currentIndex ? 'Etapa actual' : 'Pendiente / sin evento')}</small></div>`;
  }).join('');
  const items = (order.items || []).map(item => `<tr><td><strong>${escapeHtml(item.reference)}</strong></td><td>${escapeHtml(item.description || 'Sin descripción')}</td><td>${escapeHtml(item.quantity ?? '—')} ${escapeHtml(item.unit || '')}</td></tr>`).join('') || '<tr><td colspan="3" class="table-empty">No hay detalle de productos disponible.</td></tr>';
  const hus = (order.handling_units || []).map(hu => `<tr><td><strong>${escapeHtml(hu.hu_id || 'No informado')}</strong></td><td>${escapeHtml(hu.contents || 'Contenido no informado')}</td><td>${escapeHtml(hu.location || 'Sin ubicación')}</td><td>${statusBadge(hu.status || 'No informado')}</td></tr>`).join('') || '<tr><td colspan="4" class="table-empty">No hay unidades de manipulación disponibles.</td></tr>';
  const events = [...(order.events || [])].sort((a,b) => new Date(b.event_time || 0) - new Date(a.event_time || 0));
  const eventRows = events.map(event => `<div class="event-row"><div class="event-time">${formatDate(event.event_time)}</div><div class="event-body"><strong>${escapeHtml(event.event || 'Evento sin descripción')}</strong><small>${escapeHtml(event.stage || 'Etapa no informada')} · ${escapeHtml(event.location || 'Ubicación no informada')} · ${escapeHtml(event.status || 'Estado no informado')}</small></div></div>`).join('') || '<div class="table-empty">No hay eventos disponibles.</div>';
  $('#detailContent').innerHTML = `
    <div class="detail-grid">
      <div class="detail-stat"><span>Fecha de creación</span><strong>${formatDate(order.created_at)}</strong></div>
      <div class="detail-stat"><span>Productos / referencias</span><strong>${(order.items || []).length}</strong></div>
      <div class="detail-stat"><span>Unidades de manipulación</span><strong>${(order.handling_units || []).length} HU</strong></div>
      <div class="detail-stat"><span>Tiempo en etapa</span><strong>${formatMinutes(order.elapsed_minutes ?? stageMinutes(order))}</strong></div>
    </div>
    <div class="detail-top-grid">
      <article class="panel"><h2 class="subsection-title">Información general</h2><div class="info-list">
        <div class="info-line"><span>Pedido</span><strong>${escapeHtml(order.order_id)}</strong></div>
        <div class="info-line"><span>Entrega</span><strong>${escapeHtml(order.delivery_id || 'No informado')}</strong></div>
        <div class="info-line"><span>Estado</span><strong>${escapeHtml(order.status || 'No informado')}</strong></div>
        <div class="info-line"><span>Etapa actual</span><strong>${escapeHtml(order.stage || 'Sin confirmar')}</strong></div>
        <div class="info-line"><span>Prioridad</span><strong>${escapeHtml(order.priority || 'No informada')}</strong></div>
      </div></article>
      <article class="panel"><h2 class="subsection-title">Avance del pedido</h2><div class="progress-timeline">${steps}</div><div class="location-box"><span>Última ubicación registrada</span><strong>${escapeHtml(order.location || 'Sin ubicación informada')}</strong><small>La ubicación corresponde al último registro disponible, no a una confirmación física en tiempo real.</small></div></article>
    </div>
    <div class="detail-lower-grid">
      <article class="panel"><h2 class="subsection-title">Productos del pedido</h2><div class="table-wrap"><table><thead><tr><th>Referencia</th><th>Descripción</th><th>Cantidad</th></tr></thead><tbody>${items}</tbody></table></div></article>
      <article class="panel"><h2 class="subsection-title">Unidades de manipulación (HU)</h2><div class="table-wrap"><table><thead><tr><th>HU</th><th>Contenido</th><th>Ubicación</th><th>Estado</th></tr></thead><tbody>${hus}</tbody></table></div></article>
    </div>
    <article class="panel"><h2 class="subsection-title">Historial de movimientos</h2><div class="event-list">${eventRows}</div></article>
    ${alert ? `<div class="notice-banner" style="margin-top:15px">Atención: el tiempo de permanencia supera el límite configurado por ${formatMinutes(alert.overdue_minutes)}. Esta alerta requiere revisión operativa.</div>` : ''}
  `;
  navigate('detail');
}
async function openOrder(orderId) {
  $('#detailContent').innerHTML = '<div class="loading-state">Consultando detalle del pedido…</div>';
  navigate('detail');
  try {
    const order = await api(`/api/orders/${encodeURIComponent(orderId)}`);
    renderDetail(order);
  } catch (error) {
    $('#detailContent').innerHTML = `<div class="empty-state"><h3>No fue posible abrir el pedido</h3><p>${escapeHtml(error.message)}</p></div>`;
  }
}
async function loadAlerts() {
  try {
    const data = await api('/api/alerts');
    state.alerts = data.alerts || [];
    $('#alertsNotice').textContent = data.message;
    $('#alertCount').textContent = data.configured ? state.alerts.length : '—';
    $('#alertStages').textContent = data.configured ? new Set(state.alerts.map(a => a.stage)).size : '—';
    $('#thresholdState').textContent = data.configured ? 'Activo' : 'Pendiente';
    if (!data.configured) {
      $('#alertsTable').innerHTML = '<tr><td colspan="7" class="table-empty">No se muestran demoras definitivas hasta que Operaciones defina los tiempos objetivo.</td></tr>';
      return;
    }
    if (!state.alerts.length) {
      $('#alertsTable').innerHTML = '<tr><td colspan="7" class="table-empty">No se identificaron pedidos por encima de los límites configurados.</td></tr>';
      return;
    }
    $('#alertsTable').innerHTML = state.alerts.map(a => `<tr><td><strong>${escapeHtml(a.order_id)}</strong></td><td>${escapeHtml(a.stage)}</td><td>${escapeHtml(a.location)}</td><td>${formatMinutes(a.elapsed_minutes)}</td><td>${formatMinutes(a.limit_minutes)}</td><td><span class="time-pill">+ ${formatMinutes(a.overdue_minutes)}</span></td><td><button class="table-action view-order" data-order="${escapeHtml(a.order_id)}">Ver detalle →</button></td></tr>`).join('');
  } catch (error) {
    $('#alertsTable').innerHTML = `<tr><td colspan="7" class="table-empty">${escapeHtml(error.message)}</td></tr>`;
  }
}
async function loadConnectionStatus() {
  try {
    const data = await api('/api/integration/status');
    const badge = $('#ewmStatusBadge');
    badge.className = `status-badge ${data.connected ? 'success' : 'neutral'}`;
    badge.textContent = data.connected ? 'Conectado' : 'Pendiente';
    $('#ewmMessage').textContent = data.message;
    if (data.status === 'connected') badge.classList.add('success');
  } catch (error) {
    $('#ewmMessage').textContent = error.message;
  }
}
async function connectionAction(endpoint, buttonId) {
  const button = $(buttonId);
  const initial = button.textContent;
  button.disabled = true;
  button.textContent = 'Consultando…';
  $('#ewmFeedback').className = 'feedback';
  $('#ewmFeedback').textContent = '';
  try {
    const data = await api(endpoint, {method:'POST'});
    $('#ewmFeedback').className = 'feedback success';
    $('#ewmFeedback').textContent = data.message || 'Operación completada.';
    if (endpoint.endsWith('/refresh')) {
      toast(`Pedidos recibidos: ${data.orders_received}`);
      await loadDashboard();
      await loadOrders();
    }
    await loadConnectionStatus();
  } catch (error) {
    $('#ewmFeedback').className = 'feedback error';
    $('#ewmFeedback').textContent = error.message;
    await loadConnectionStatus();
  } finally {
    button.disabled = false;
    button.textContent = initial;
  }
}
async function loadAIStatus() {
  try {
    const data = await api('/api/ai/status');
    $('#aiNotice').textContent = data.message;
    if (data.ready) $('#aiNotice').textContent = 'Servicio de IA configurado. Revisa que el uso de datos esté autorizado para el propósito solicitado.';
  } catch (error) {
    $('#aiNotice').textContent = error.message;
  }
}
function setAIAction(action) {
  state.aiAction = action;
  $$('.ai-action').forEach(btn => btn.classList.toggle('active', btn.dataset.aiAction === action));
  $('#aiReportControls').classList.toggle('hidden', action !== 'report');
  $('#aiAskControls').classList.toggle('hidden', action !== 'ask');
  $('#aiDelayControls').classList.toggle('hidden', action !== 'delays');
  const titles = {report:['Generar informe','Prepara un resumen operativo con los registros disponibles.'],ask:['Consultar la operación','Realiza una pregunta sobre pedidos y etapas logísticas.'],delays:['Analizar demoras','Revisa los pedidos que superan los tiempos configurados.']};
  $('#aiWorkspaceTitle').textContent = titles[action][0];
  $('#aiWorkspaceSubtitle').textContent = titles[action][1];
  $('#aiResult').innerHTML = '<div class="empty-state"><span class="empty-symbol">✧</span><h3>Tu análisis aparecerá aquí</h3><p>Ejecuta la consulta cuando la integración de IA esté autorizada y configurada.</p></div>';
}
async function runAI(endpoint, body = null) {
  const result = $('#aiResult');
  result.innerHTML = '<div class="loading-state">Preparando el análisis…</div>';
  const options = {method:'POST', headers:{}};
  if (body) { options.headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(body); }
  try {
    const data = await api(endpoint, options);
    result.innerHTML = `<div class="ai-result-content">${escapeHtml(data.text)}</div><div class="ai-result-meta">Origen: ${escapeHtml(data.source)} · Generado: ${formatDate(data.generated_at)} · Revisa el contenido antes de utilizarlo como informe.</div>`;
  } catch (error) {
    result.innerHTML = `<div class="empty-state"><span class="empty-symbol">ⓘ</span><h3>No se pudo generar el análisis</h3><p>${escapeHtml(error.message)}</p></div>`;
  }
}

// Navegación y eventos
$$('.nav-item').forEach(button => button.addEventListener('click', () => {
  navigate(button.dataset.page);
  if (button.dataset.page === 'orders') loadOrders();
  if (button.dataset.page === 'alerts') loadAlerts();
  if (button.dataset.page === 'connection') loadConnectionStatus();
  if (button.dataset.page === 'ai') loadAIStatus();
}));
$$('[data-goto]').forEach(button => button.addEventListener('click', () => {
  navigate(button.dataset.goto);
  if (button.dataset.goto === 'orders') loadOrders();
  if (button.dataset.goto === 'alerts') loadAlerts();
  if (button.dataset.goto === 'connection') loadConnectionStatus();
}));
$('#mobileMenu').addEventListener('click', () => $('#sidebar').classList.toggle('open'));
$('#orderSearchForm').addEventListener('submit', event => { event.preventDefault(); loadOrders(); });
$('#stageFilter').addEventListener('change', loadOrders);
$('#clearFilters').addEventListener('click', () => { $('#orderSearch').value = ''; $('#stageFilter').value = ''; loadOrders(); });
$('#backToOrders').addEventListener('click', () => { navigate('orders'); loadOrders(); });
document.addEventListener('click', event => {
  const button = event.target.closest('.view-order');
  if (button) openOrder(button.dataset.order);
});
$('#checkEwm').addEventListener('click', () => connectionAction('/api/integration/check', '#checkEwm'));
$('#refreshEwm').addEventListener('click', () => connectionAction('/api/integration/refresh', '#refreshEwm'));
$$('.ai-action').forEach(button => button.addEventListener('click', () => setAIAction(button.dataset.aiAction)));
$('#generateReport').addEventListener('click', () => runAI('/api/ai/report', {report_type:$('#reportType').value}));
$('#askAI').addEventListener('click', () => runAI('/api/ai/ask', {question:$('#aiQuestion').value.trim()}));
$('#aiQuestion').addEventListener('keydown', event => { if (event.key === 'Enter') $('#askAI').click(); });
$('#analyzeDelays').addEventListener('click', () => runAI('/api/ai/delays'));

// Inicio
loadDashboard();

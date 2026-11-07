const form = document.querySelector('#order-form');
const submitButton = document.querySelector('#submit-button');
const formMessage = document.querySelector('#form-message');
const latest = document.querySelector('#latest-order');
const serviceDot = document.querySelector('#service-dot');
const serviceStatus = document.querySelector('#service-status');
const ordersBody = document.querySelector('#orders-body');
let currentOrderId = null;
let pollTimer = null;
let pendingSubmission = null;

function showLatest(order) {
  latest.replaceChildren();
  const panel = document.createElement('div');
  panel.className = 'order-detail';
  const title = document.createElement('p');
  title.className = 'order-title';
  title.textContent = `${order.quantity} × ${order.product}`;
  const id = document.createElement('p');
  id.className = 'order-id';
  id.textContent = order.id;
  const meta = document.createElement('div');
  meta.className = 'order-meta';
  const timestamp = document.createElement('span');
  timestamp.textContent = new Date(order.created_at).toLocaleString();
  const status = document.createElement('span');
  status.className = `status ${order.status}`;
  status.textContent = order.status;
  meta.append(timestamp, status);
  panel.append(title, id, meta);
  latest.append(panel);
}

async function refreshOrder() {
  if (!currentOrderId) return;
  try {
    const response = await fetch(`/api/orders/${encodeURIComponent(currentOrderId)}`);
    if (!response.ok) throw new Error(`Order lookup returned ${response.status}`);
    const order = await response.json();
    showLatest(order);
    await refreshList();
    if (['completed', 'failed'].includes(order.status)) {
      clearInterval(pollTimer);
      formMessage.textContent = order.status === 'completed' ? 'Order finished successfully.' : 'Order processing failed.';
    }
  } catch (error) {
    formMessage.textContent = `Could not refresh order: ${error.message}`;
  }
}

async function refreshList() {
  try {
    const response = await fetch('/api/orders?limit=25');
    if (!response.ok) throw new Error(`Order list returned ${response.status}`);
    const orders = await response.json();
    ordersBody.replaceChildren();
    if (!orders.length) {
      const row = document.createElement('tr');
      const cell = document.createElement('td');
      cell.colSpan = 5;
      cell.className = 'empty-row';
      cell.textContent = 'No orders yet. Submit one to begin.';
      row.append(cell);
      ordersBody.append(row);
      return;
    }
    for (const order of orders) {
      const row = document.createElement('tr');
      const values = [order.id.slice(0, 8), order.product, String(order.quantity)];
      for (const value of values) {
        const cell = document.createElement('td');
        cell.textContent = value;
        if (value === order.id.slice(0, 8)) cell.className = 'id-cell';
        row.append(cell);
      }
      const statusCell = document.createElement('td');
      const badge = document.createElement('span');
      badge.className = `status ${order.status}`;
      badge.textContent = order.status;
      statusCell.append(badge);
      row.append(statusCell);
      const date = document.createElement('td');
      date.textContent = new Date(order.created_at).toLocaleString();
      row.append(date);
      ordersBody.append(row);
    }
  } catch (error) {
    ordersBody.replaceChildren();
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 5;
    cell.className = 'empty-row';
    cell.textContent = `Could not load orders: ${error.message}`;
    row.append(cell);
    ordersBody.append(row);
  }
}

async function refreshServices() {
  try {
    const response = await fetch('/ready');
    const ready = response.ok;
    serviceDot.className = `dot ${ready ? 'ok' : 'bad'}`;
    serviceStatus.textContent = ready ? 'API, database & Redis ready' : 'A dependency is unavailable';
  } catch {
    serviceDot.className = 'dot bad';
    serviceStatus.textContent = 'API unavailable';
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  submitButton.disabled = true;
  formMessage.textContent = 'Saving the order…';
  const payload = { product: form.elements.product.value.trim(), quantity: Number(form.elements.quantity.value) };
  const serialized = JSON.stringify(payload);
  if (!pendingSubmission || pendingSubmission.payload !== serialized) {
    pendingSubmission = { payload: serialized, key: crypto.randomUUID() };
  }
  try {
    const response = await fetch('/api/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': pendingSubmission.key },
      body: serialized,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `Request returned ${response.status}`);
    currentOrderId = result.id;
    pendingSubmission = null;
    showLatest(result);
    formMessage.textContent = 'Saved durably. Waiting for the worker…';
    await refreshList();
    clearInterval(pollTimer);
    pollTimer = setInterval(refreshOrder, 1500);
    await refreshOrder();
  } catch (error) {
    formMessage.textContent = `Could not confirm acceptance: ${error.message}. Retry the same order safely.`;
  } finally {
    submitButton.disabled = false;
  }
});

document.querySelector('#refresh-button').addEventListener('click', refreshOrder);
document.querySelector('#list-refresh').addEventListener('click', refreshList);
refreshServices();
refreshList();
setInterval(refreshServices, 10000);

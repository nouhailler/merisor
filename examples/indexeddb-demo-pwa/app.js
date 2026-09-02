function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("MerisorIndexedDbDemo", 1);

    request.onupgradeneeded = () => {
      const database = request.result;

      const customers = database.createObjectStore("customers", {
        keyPath: "id",
        autoIncrement: true,
      });
      customers.createIndex("name", "name", { unique: false });
      customers.createIndex("email", "email", { unique: true });

      const orders = database.createObjectStore("orders", {
        keyPath: "id",
        autoIncrement: true,
      });
      orders.createIndex("customerId", "customerId", { unique: false });
      orders.createIndex("description", "description", { unique: false });
      orders.createIndex("amount", "amount", { unique: false });
      orders.createIndex("createdAt", "createdAt", { unique: false });
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function requestResult(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function addRecord(storeName, value) {
  const database = await openDatabase();
  const transaction = database.transaction(storeName, "readwrite");
  await requestResult(transaction.objectStore(storeName).add(value));
  database.close();
}

async function allRecords(storeName) {
  const database = await openDatabase();
  const transaction = database.transaction(storeName, "readonly");
  const records = await requestResult(transaction.objectStore(storeName).getAll());
  database.close();
  return records;
}

async function render() {
  const customers = await allRecords("customers");
  const orders = await allRecords("orders");
  const customerNames = new Map(customers.map((item) => [item.id, item.name]));

  document.querySelector("#customers").replaceChildren(
    ...customers.map((customer) => {
      const item = document.createElement("li");
      item.textContent = `${customer.name} — ${customer.email}`;
      return item;
    }),
  );

  const customerSelect = document.querySelector('[name="customerId"]');
  customerSelect.replaceChildren(
    ...customers.map((customer) => {
      const option = document.createElement("option");
      option.value = String(customer.id);
      option.textContent = customer.name;
      return option;
    }),
  );

  document.querySelector("#orders").replaceChildren(
    ...orders.map((order) => {
      const item = document.createElement("li");
      const customer = customerNames.get(order.customerId) ?? "Client inconnu";
      item.textContent = `${customer} — ${order.description} — ${order.amount.toFixed(2)} €`;
      return item;
    }),
  );
}

document.querySelector("#customer-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  await addRecord("customers", {
    name: String(form.get("name")),
    email: String(form.get("email")),
  });
  event.currentTarget.reset();
  await render();
});

document.querySelector("#order-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  await addRecord("orders", {
    customerId: Number(form.get("customerId")),
    description: String(form.get("description")),
    amount: Number(form.get("amount")),
    createdAt: new Date(),
  });
  event.currentTarget.reset();
  await render();
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("service-worker.js");
}

render();

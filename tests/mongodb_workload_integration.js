use("shop_bench");
load("/tmp/06_queries_mongodb.js");

db.categories.insertOne({ _id: 1, name: "Test", parent_id: null });
db.customers.insertOne({
  _id: 1, full_name: "CI Customer", email: "ci@example.test",
  phone: "0900000000", city: "Hanoi", created_at: new Date()
});
db.stores.insertOne({ _id: 1, name: "CI Store", city: "Hanoi" });
db.products.insertMany([
  { _id: 1, sku: "CI-001", name: "Product 1", category_id: 1,
    price: NumberDecimal("10.00"), created_at: new Date() },
  { _id: 2, sku: "CI-002", name: "Product 2", category_id: 1,
    price: NumberDecimal("20.00"), created_at: new Date() },
  { _id: 3, sku: "CI-003", name: "Product 3", category_id: 1,
    price: NumberDecimal("30.00"), created_at: new Date() }
]);
db.inventory.insertMany([
  { _id: 1, store_id: 1, product_id: 1, quantity: 3 },
  { _id: 2, store_id: 1, product_id: 2, quantity: 1 },
  { _id: 3, store_id: 1, product_id: 3, quantity: 2147483640 }
]);

const created = W1_txn(1001, 2001, 1, 1, [
  { pid: 1, qty: 2 }, { pid: 2, qty: 1 }
]);
if (created.amount !== "40.00") throw new Error("CI: W1 total mismatch");
if (db.orders.findOne({ _id: 1001 }).items.length !== 2)
  throw new Error("CI: W1 did not create two lines");
if (db.inventory.findOne({ store_id: 1, product_id: 1 }).quantity !== 1)
  throw new Error("CI: W1 stock decrement mismatch");

let failed = false;
try {
  W1_txn(1002, 2002, 1, 1, [
    { pid: 1, qty: 1 }, { pid: 2, qty: 1 }
  ]);
} catch (e) {
  failed = true;
}
if (!failed) throw new Error("CI: W1 insufficient-stock call unexpectedly succeeded");
if (db.orders.findOne({ _id: 1002 }) !== null)
  throw new Error("CI: W1 rollback left an order behind");
if (db.inventory.findOne({ store_id: 1, product_id: 1 }).quantity !== 1)
  throw new Error("CI: W1 rollback did not restore earlier inventory update");

W2(1001);
const paid = db.orders.findOne({ _id: 1001 });
if (paid.status !== "PAID" || paid.payments[0].status !== "PAID")
  throw new Error("CI: W2 did not mark order and payment paid");

W3(1, 1, 5);
if (db.inventory.findOne({ store_id: 1, product_id: 1 }).quantity !== 6)
  throw new Error("CI: W3 successful restock mismatch");

failed = false;
try {
  W3(1, 3, 10);
} catch (e) {
  failed = true;
}
if (!failed) throw new Error("CI: W3 overflow call unexpectedly succeeded");
if (db.inventory.findOne({ store_id: 1, product_id: 3 }).quantity !== 2147483640)
  throw new Error("CI: W3 overflow changed inventory");

print("PASS: MongoDB W1 transaction/rollback, W2 state transition, and W3 bounds");

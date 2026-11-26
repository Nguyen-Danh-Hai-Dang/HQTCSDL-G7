// =====================================================================
// MỤC TIÊU 3 - MongoDB 7.x: thiết kế document cho quản lý bán hàng
// Chạy: mongosh --file 03_mongodb_schema.js
// An toàn: không tự drop collection. Nếu collection đã tồn tại, script dừng.
// Muốn dựng lại, chỉ drop database sau khi đã sao lưu và xác nhận.
//
// Quyết định thiết kế được giải thích trong README và báo cáo.
//  - orders: NHÚNG items[] và payments[] (đọc/ghi cùng nhau, số phần tử bị chặn)
//  - orders -> customers, products, stores: THAM CHIẾU bằng id (dữ liệu dùng chung,
//    thay đổi độc lập, nhúng sẽ trùng lặp và khó cập nhật)
//  - _id dùng lại đúng id của MySQL (order_id, customer_id, ...) để đối chiếu 1-1
//  - Tiền dùng Decimal128 để cùng độ chính xác với DECIMAL(12,2) của MySQL
//  - KHÔNG lưu total_amount, giống MySQL (tính từ items)
// =====================================================================
use("shop_bench");

const requiredCollections = ["categories", "customers", "products", "stores", "inventory", "orders"];
const existingCollections = new Set(db.getCollectionNames());
const conflicts = requiredCollections.filter(name => existingCollections.has(name));
if (conflicts.length > 0) {
  throw new Error("Collections already exist: " + conflicts.join(", ") +
    ". No data was changed. Back up first, then explicitly drop shop_bench if recreation is intended.");
}

const ID = { bsonType: ["int", "long"] };

db.createCollection("categories", { validator: { $jsonSchema: {
  bsonType: "object", required: ["_id", "name"],
  properties: { _id: ID, name: { bsonType: "string" },
                parent_id: { bsonType: ["int", "long", "null"] } } } } });

db.createCollection("customers", { validator: { $jsonSchema: {
  bsonType: "object",
  required: ["_id", "full_name", "email", "phone", "city", "created_at"],
  properties: { _id: ID, full_name: { bsonType: "string" }, email: { bsonType: "string" },
                phone: { bsonType: "string" }, city: { bsonType: "string" },
                created_at: { bsonType: "date" } } } } });

db.createCollection("products", { validator: { $jsonSchema: {
  bsonType: "object",
  required: ["_id", "sku", "name", "category_id", "price", "created_at"],
  properties: { _id: ID, sku: { bsonType: "string" }, name: { bsonType: "string" },
                category_id: ID, price: { bsonType: "decimal", minimum: 0.01 },
                created_at: { bsonType: "date" } } } } });

db.createCollection("stores", { validator: { $jsonSchema: {
  bsonType: "object", required: ["_id", "name", "city"],
  properties: { _id: ID, name: { bsonType: "string" }, city: { bsonType: "string" } } } } });

// Tồn kho: collection riêng (ghi thường xuyên, không nên nhúng vào product)
db.createCollection("inventory", { validator: { $jsonSchema: {
  bsonType: "object", required: ["_id", "store_id", "product_id", "quantity"],
  properties: { _id: ID, store_id: ID, product_id: ID,
                quantity: { bsonType: ["int", "long"], minimum: 0, maximum: 2147483647 } } } } });

db.createCollection("orders", { validator: { $jsonSchema: {
  bsonType: "object",
  required: ["_id", "customer_id", "store_id", "order_date", "status", "items", "payments"],
  properties: {
    _id: ID, customer_id: ID, store_id: ID,
    order_date: { bsonType: "date" },
    status: { enum: ["PENDING", "PAID", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"] },
    items: { bsonType: "array", minItems: 1, maxItems: 50,
      items: { bsonType: "object",
        required: ["line_no", "product_id", "quantity", "unit_price"],
        properties: { line_no: ID, product_id: ID,
                      quantity: { bsonType: ["int", "long"], minimum: 1 },
                      unit_price: { bsonType: "decimal", minimum: 0.01 } } } },
    payments: { bsonType: "array", maxItems: 10,
      items: { bsonType: "object",
        required: ["payment_id", "method", "amount", "status"],
        properties: { payment_id: ID,
          method: { enum: ["CARD", "EWALLET", "COD", "BANK_TRANSFER", "CASH"] },
          amount: { bsonType: "decimal", minimum: 0 },
          paid_at: { bsonType: ["date", "null"] },
          status: { enum: ["PENDING", "PAID", "FAILED", "REFUNDED"] } } } }
  } } } });

// Index nằm ở 03b_mongodb_indexes.js (tạo SAU khi mongoimport).
// Script dừng nếu collection đã tồn tại; nó không tự xoá dữ liệu.

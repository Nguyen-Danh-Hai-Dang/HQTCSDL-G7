// =====================================================================
// WORKLOAD MongoDB (tương đương 1-1 với 05_queries_mysql.sql)
// Chạy trong mongosh:  load("06_queries_mongodb.js")
// Mọi truy vấn dùng cùng tham số và cùng thứ tự sắp xếp (kể cả tie-break theo _id)
// để kết quả khớp từng dòng với MySQL.
// =====================================================================
use("shop_bench");

const oid  = 8, cid = 506;
const d1   = ISODate("2025-03-01T00:00:00Z"), d2   = ISODate("2025-04-01T00:00:00Z");
const day1 = ISODate("2025-03-15T00:00:00Z"), day2 = ISODate("2025-03-22T00:00:00Z");
const EXCL = ["CANCELLED", "RETURNED"];
// Biểu thức tổng tiền của một đơn: SUM(quantity * unit_price) trên items nhúng
const orderTotal = { $sum: { $map: { input: "$items", as: "i",
                      in: { $multiply: ["$$i.quantity", "$$i.unit_price"] } } } };

// ---------------------------------------------------------------- ĐỌC
// Q1 (20%) Tra cứu đơn theo khoá: một lần đọc lấy cả items + payments
function Q1() { return db.orders.findOne({ _id: oid }); }

// Q2 (20%) 20 đơn gần nhất của khách
function Q2() {
  return db.orders.find({ customer_id: cid }, { order_date: 1, status: 1 })
    .sort({ order_date: -1, _id: -1 }).limit(20).toArray();
}

// Q3 (10%) Khoảng thời gian + trạng thái + sắp xếp + phân trang
function Q3() {
  return db.orders.find(
    { order_date: { $gte: day1, $lt: day2 }, status: "SHIPPED" },
    { customer_id: 1, order_date: 1, status: 1 })
    .sort({ order_date: 1, _id: 1 }).limit(100).toArray();
}

// Q4 (4%) Doanh thu theo tháng (không cần $unwind vì items nhúng)
function Q4() {
  return db.orders.aggregate([
    { $match: { order_date: { $gte: ISODate("2024-01-01T00:00:00Z"),
                              $lt:  ISODate("2026-01-01T00:00:00Z") },
                status: { $nin: EXCL } } },
    { $group: { _id: { $dateToString: { format: "%Y-%m", date: "$order_date" } },
                orders: { $sum: 1 }, revenue: { $sum: orderTotal } } },
    { $sort: { _id: 1 } }
  ]).toArray();
}

// Q5 (4%) Top 10 sản phẩm theo doanh thu (cần $unwind + $lookup tới products)
function Q5() {
  return db.orders.aggregate([
    { $match: { order_date: { $gte: d1, $lt: d2 }, status: { $nin: EXCL } } },
    { $unwind: "$items" },
    { $group: { _id: "$items.product_id",
                revenue: { $sum: { $multiply: ["$items.quantity", "$items.unit_price"] } } } },
    { $sort: { revenue: -1, _id: 1 } },
    { $limit: 10 },
    { $lookup: { from: "products", localField: "_id", foreignField: "_id", as: "p" } },
    { $unwind: "$p" },
    { $project: { _id: 0, product_id: "$_id", name: "$p.name", revenue: 1 } }
  ]).toArray();
}

// Q6 (3%) Doanh thu theo danh mục: gom theo sản phẩm trước rồi mới $lookup (giảm số lần join)
function Q6() {
  return db.orders.aggregate([
    { $match: { order_date: { $gte: d1, $lt: d2 }, status: { $nin: EXCL } } },
    { $unwind: "$items" },
    { $group: { _id: "$items.product_id",
                revenue: { $sum: { $multiply: ["$items.quantity", "$items.unit_price"] } } } },
    { $lookup: { from: "products", localField: "_id", foreignField: "_id", as: "p" } },
    { $unwind: "$p" },
    { $group: { _id: "$p.category_id", revenue: { $sum: "$revenue" } } },
    { $lookup: { from: "categories", localField: "_id", foreignField: "_id", as: "c" } },
    { $unwind: "$c" },
    { $project: { _id: 0, category_id: "$_id", name: "$c.name", revenue: 1 } },
    { $sort: { revenue: -1, category_id: 1 } }
  ]).toArray();
}

// Q7 (15%) Chi tiết đơn + tên khách + tên sản phẩm (2 loại tham chiếu => $lookup)
function Q7() {
  return db.orders.aggregate([
    { $match: { _id: oid } },
    { $lookup: { from: "customers", localField: "customer_id", foreignField: "_id", as: "cu" } },
    { $unwind: "$cu" },
    { $unwind: "$items" },
    { $lookup: { from: "products", localField: "items.product_id", foreignField: "_id", as: "p" } },
    { $unwind: "$p" },
    { $project: { _id: 0, order_id: "$_id", order_date: 1, status: 1,
                  full_name: "$cu.full_name", email: "$cu.email",
                  line_no: "$items.line_no", sku: "$p.sku", product_name: "$p.name",
                  quantity: "$items.quantity", unit_price: "$items.unit_price" } },
    { $sort: { line_no: 1 } }
  ]).toArray();
}

// Q8 (4%) Top 10 khách theo chi tiêu
function Q8() {
  return db.orders.aggregate([
    { $match: { order_date: { $gte: d1, $lt: d2 }, status: { $nin: EXCL } } },
    { $group: { _id: "$customer_id", spend: { $sum: orderTotal } } },
    { $sort: { spend: -1, _id: 1 } },
    { $limit: 10 },
    { $lookup: { from: "customers", localField: "_id", foreignField: "_id", as: "cu" } },
    { $unwind: "$cu" },
    { $project: { _id: 0, customer_id: "$_id", full_name: "$cu.full_name", spend: 1 } }
  ]).toArray();
}

// ---------------------------------------------------------------- GHI
// W1: tạo đơn và trừ kho trong cùng transaction. Yêu cầu replica set.
function _decimalToCents(value) {
  const m = /^(\d+)(?:\.(\d{1,2}))?$/.exec(value.toString());
  if (!m) throw new Error("INVALID_PRICE_FORMAT: " + value.toString());
  return BigInt(m[1]) * 100n + BigInt((m[2] || "").padEnd(2, "0"));
}
function _centsToDecimal(cents) {
  return (cents / 100n).toString() + "." + (cents % 100n).toString().padStart(2, "0");
}
function _validateW1Lines(lines) {
  if (!Array.isArray(lines) || lines.length < 1 || lines.length > 50)
    throw new Error("INVALID_LINES: expected 1..50 order lines");
  const seen = new Set();
  for (const line of lines) {
    if (!line || typeof line !== "object" ||
        !Number.isSafeInteger(line.pid) || line.pid <= 0 || line.pid > 4294967295 ||
        !Number.isSafeInteger(line.qty) || line.qty <= 0 || line.qty > 65535)
      throw new Error("INVALID_LINE: pid and qty must be positive safe integers");
    if (seen.has(line.pid)) throw new Error("DUPLICATE_PRODUCT: combine quantities first");
    seen.add(line.pid);
  }
}
function _W1_body(sdb, newOid, payId, customerId, storeId, lines) {
  _validateW1Lines(lines);
  if (!Number.isSafeInteger(newOid) || newOid <= 0 ||
      !Number.isSafeInteger(payId) || payId <= 0 ||
      !Number.isSafeInteger(customerId) || customerId <= 0 || customerId > 4294967295 ||
      !Number.isSafeInteger(storeId) || storeId <= 0 || storeId > 65535)
    throw new Error("INVALID_IDENTIFIER");
  if (!sdb.customers.findOne({ _id: customerId })) throw new Error("CUSTOMER_NOT_FOUND");
  if (!sdb.stores.findOne({ _id: storeId })) throw new Error("STORE_NOT_FOUND");
  const products = sdb.products.find({ _id: { $in: lines.map(x => x.pid) } }).toArray();
  if (products.length !== lines.length) throw new Error("PRODUCT_NOT_FOUND");
  const prices = new Map(products.map(p => [p._id, p.price]));
  let total = 0n;
  const items = lines.map((line, index) => {
    const price = prices.get(line.pid);
    if (price === undefined) throw new Error("PRODUCT_NOT_FOUND: " + line.pid);
    total += BigInt(line.qty) * _decimalToCents(price);
    return { line_no: index + 1, product_id: line.pid,
             quantity: line.qty, unit_price: price };
  });
  if (total > 99999999999999n) throw new Error("PAYMENT_AMOUNT_OUT_OF_RANGE");
  sdb.orders.insertOne({
    _id: newOid, customer_id: customerId, store_id: storeId,
    order_date: new Date(), status: "PENDING", items,
    payments: [{ payment_id: payId, method: "CARD",
      amount: NumberDecimal(_centsToDecimal(total)), paid_at: null, status: "PENDING" }]
  });
  const inventoryLines = [...lines].sort((a, b) => a.pid - b.pid);
  for (const line of inventoryLines) {
    const result = sdb.inventory.updateOne(
      { store_id: storeId, product_id: line.pid, quantity: { $gte: line.qty } },
      { $inc: { quantity: -line.qty } }
    );
    if (result.matchedCount !== 1)
      throw new Error("OUT_OF_STOCK_OR_INVENTORY_MISSING: product " + line.pid);
  }
  return { order_id: newOid, payment_id: payId, amount: _centsToDecimal(total) };
}
function W1_txn(newOid, payId, customerId, storeId, lines) {
  const session = db.getMongo().startSession();
  try {
    let result;
    session.withTransaction(() => {
      result = _W1_body(session.getDatabase("shop_bench"), newOid, payId, customerId, storeId, lines);
    }, { writeConcern: { w: "majority", j: true } });
    return result;
  } finally {
    session.endSession();
  }
}

// W2: chỉ cập nhật khi đơn PENDING và tồn tại ít nhất một payment PENDING.
function W2(orderId) {
  if (!Number.isSafeInteger(orderId) || orderId <= 0)
    throw new Error("INVALID_ORDER_ID");
  const result = db.orders.updateOne(
    { _id: orderId, status: "PENDING", payments: { $elemMatch: { status: "PENDING" } } },
    { $set: { status: "PAID", "payments.$[p].status": "PAID",
              "payments.$[p].paid_at": new Date() } },
    { arrayFilters: [{ "p.status": "PENDING" }] }
  );
  if (result.matchedCount !== 1) throw new Error("ORDER_OR_PENDING_PAYMENT_NOT_FOUND");
  return result;
}

// W3: nhập kho, báo lỗi nếu cặp cửa hàng/sản phẩm không tồn tại.
function W3(storeId, productId, quantity) {
  if (!Number.isSafeInteger(storeId) || storeId <= 0 || storeId > 65535 ||
      !Number.isSafeInteger(productId) || productId <= 0 || productId > 4294967295 ||
      !Number.isSafeInteger(quantity) || quantity <= 0 || quantity > 2147483647)
    throw new Error("INVALID_RESTOCK_ARGUMENTS");
  const result = db.inventory.updateOne(
    { store_id: storeId, product_id: productId,
      quantity: { $lte: 2147483647 - quantity } },
    { $inc: { quantity } }
  );
  if (result.matchedCount !== 1)
    throw new Error("INVENTORY_ROW_NOT_FOUND_OR_INT32_OVERFLOW");
  return result;
}

// ---------------------------------------------------------------- ĐỐI CHIẾU SAU NẠP
function verifyLoad() {
  const counts = {};
  ["categories", "stores", "customers", "products", "inventory", "orders"]
    .forEach(c => counts[c] = db[c].countDocuments());
  const itemCount = db.orders.aggregate([{ $group: { _id: null, n: { $sum: { $size: "$items" } } } }]).toArray()[0];
  const paymentCount = db.orders.aggregate([{ $group: { _id: null, n: { $sum: { $size: "$payments" } } } }]).toArray()[0];
  const grossResult = db.orders.aggregate([{ $group: { _id: null, r: { $sum: orderTotal } } }]).toArray()[0];
  counts.order_item = itemCount ? itemCount.n : 0;
  counts.payment = paymentCount ? paymentCount.n : 0;
  const gross = grossResult ? grossResult.r : NumberDecimal("0.00");
  const byStatus = db.orders.aggregate([{ $group: { _id: "$status", n: { $sum: 1 } } }]).toArray();
  printjson({ counts, revenue_gross: gross.toString(), byStatus });   // so với manifest.json
}

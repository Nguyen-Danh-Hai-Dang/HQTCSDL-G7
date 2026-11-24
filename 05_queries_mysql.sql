-- =====================================================================
-- WORKLOAD ĐỌC MySQL (Q1-Q8), tương ứng với 06_queries_mongodb.js
-- Tham số: dùng biến phiên. Khi benchmark thật, tham số được sinh ngẫu nhiên
-- theo CÙNG phân phối Zipf (khách/sản phẩm hot được truy cập nhiều hơn) và
-- dùng chung một file tham số (seed cố định) cho cả hai CSDL.
-- Tỉ lệ workload thiết kế là 80% đọc / 20% ghi; thao tác ghi được tách riêng.
-- =====================================================================
USE shop_bench;

SET @oid   = 8;
SET @cid   = 506;
SET @d1    = '2025-03-01 00:00:00';
SET @d2    = '2025-04-01 00:00:00';   -- khoảng [d1, d2)
SET @day1  = '2025-03-15 00:00:00';
SET @day2  = '2025-03-22 00:00:00';

-- ---------------------------------------------------------------- ĐỌC
-- Q1 (20%) Tra cứu đơn theo khoá + toàn bộ chi tiết + thanh toán
SELECT * FROM orders     WHERE order_id = @oid;
SELECT * FROM order_item WHERE order_id = @oid ORDER BY line_no;
SELECT * FROM payment    WHERE order_id = @oid ORDER BY payment_id;

-- Q2 (20%) 20 đơn gần nhất của một khách hàng (lọc + sắp xếp + giới hạn)
SELECT order_id, order_date, status
FROM orders
WHERE customer_id = @cid
ORDER BY order_date DESC, order_id DESC
LIMIT 20;

-- Q3 (10%) Lọc theo khoảng thời gian + trạng thái, sắp xếp, phân trang
SELECT order_id, customer_id, order_date, status
FROM orders
WHERE order_date >= @day1 AND order_date < @day2
  AND status = 'SHIPPED'
ORDER BY order_date, order_id
LIMIT 100;

-- Q4 (4%) Thống kê doanh thu theo tháng (loại đơn huỷ/trả)
SELECT DATE_FORMAT(o.order_date, '%Y-%m')     AS month,
       COUNT(DISTINCT o.order_id)             AS orders,
       SUM(i.quantity * i.unit_price)         AS revenue
FROM orders o
JOIN order_item i ON i.order_id = o.order_id
WHERE o.order_date >= '2024-01-01' AND o.order_date < '2026-01-01'
  AND o.status NOT IN ('CANCELLED', 'RETURNED')
GROUP BY month
ORDER BY month;

-- Q5 (4%) Top 10 sản phẩm theo doanh thu trong một khoảng thời gian
SELECT i.product_id, p.name, SUM(i.quantity * i.unit_price) AS revenue
FROM orders o
JOIN order_item i ON i.order_id   = o.order_id
JOIN product    p ON p.product_id = i.product_id
WHERE o.order_date >= @d1 AND o.order_date < @d2
  AND o.status NOT IN ('CANCELLED', 'RETURNED')
GROUP BY i.product_id, p.name
ORDER BY revenue DESC, i.product_id
LIMIT 10;

-- Q6 (3%) Doanh thu theo danh mục (kết hợp 4 thực thể)
SELECT c.category_id, c.name, SUM(i.quantity * i.unit_price) AS revenue
FROM orders o
JOIN order_item i ON i.order_id    = o.order_id
JOIN product    p ON p.product_id  = i.product_id
JOIN category   c ON c.category_id = p.category_id
WHERE o.order_date >= @d1 AND o.order_date < @d2
  AND o.status NOT IN ('CANCELLED', 'RETURNED')
GROUP BY c.category_id, c.name
ORDER BY revenue DESC, c.category_id;

-- Q7 (15%) Chi tiết đơn kèm tên khách và tên sản phẩm (join nhiều thực thể)
SELECT o.order_id, o.order_date, o.status,
       cu.full_name, cu.email,
       i.line_no, p.sku, p.name AS product_name, i.quantity, i.unit_price
FROM orders o
JOIN customer   cu ON cu.customer_id = o.customer_id
JOIN order_item i  ON i.order_id     = o.order_id
JOIN product    p  ON p.product_id   = i.product_id
WHERE o.order_id = @oid
ORDER BY i.line_no;

-- Q8 (4%) Top 10 khách hàng theo tổng chi tiêu trong khoảng thời gian
SELECT o.customer_id, cu.full_name, SUM(i.quantity * i.unit_price) AS spend
FROM orders o
JOIN order_item i ON i.order_id    = o.order_id
JOIN customer  cu ON cu.customer_id = o.customer_id
WHERE o.order_date >= @d1 AND o.order_date < @d2
  AND o.status NOT IN ('CANCELLED', 'RETURNED')
GROUP BY o.customer_id, cu.full_name
ORDER BY spend DESC, o.customer_id
LIMIT 10;

-- ---------------------------------------------------------------- GHI
-- W1-W3 được tách sang 07_write_workload_mysql.sql.
-- File này chỉ chứa Q1-Q8 và phần đối chiếu, tránh chạy nhầm thao tác ghi.

-- ---------------------------------------------------------------- ĐỐI CHIẾU SAU NẠP
SELECT 'category' t, COUNT(*) FROM category UNION ALL SELECT 'store', COUNT(*) FROM store
UNION ALL SELECT 'customer', COUNT(*) FROM customer UNION ALL SELECT 'product', COUNT(*) FROM product
UNION ALL SELECT 'inventory', COUNT(*) FROM inventory UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_item', COUNT(*) FROM order_item UNION ALL SELECT 'payment', COUNT(*) FROM payment;
-- So với manifest.json: revenue_gross
SELECT SUM(quantity * unit_price) AS revenue_gross FROM order_item;
SELECT status, COUNT(*) FROM orders GROUP BY status;

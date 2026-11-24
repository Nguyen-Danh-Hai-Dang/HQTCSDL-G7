-- =====================================================================
-- Nạp CSV vào MySQL bằng LOAD DATA LOCAL INFILE.
-- 1) Chạy 01_mysql_schema.sql.
-- 2) Bật local_infile trên server và client/Workbench.
-- 3) Thay C:/PATH/TO/PROJECT bằng đường dẫn project thật; dùng dấu /.
-- 4) Đổi data/s/mysql thành data/custom_N/mysql nếu dùng --orders N.
-- 5) Database phải rỗng. Script không xoá dữ liệu cũ và giữ FK checks bật.
-- =====================================================================
USE shop_bench;
SET NAMES utf8mb4;

LOAD DATA LOCAL INFILE 'C:/PATH/TO/PROJECT/data/s/mysql/category.csv' INTO TABLE category
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';
SHOW WARNINGS;
LOAD DATA LOCAL INFILE 'C:/PATH/TO/PROJECT/data/s/mysql/store.csv' INTO TABLE store
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';
SHOW WARNINGS;
LOAD DATA LOCAL INFILE 'C:/PATH/TO/PROJECT/data/s/mysql/customer.csv' INTO TABLE customer
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';
SHOW WARNINGS;
LOAD DATA LOCAL INFILE 'C:/PATH/TO/PROJECT/data/s/mysql/product.csv' INTO TABLE product
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';
SHOW WARNINGS;
LOAD DATA LOCAL INFILE 'C:/PATH/TO/PROJECT/data/s/mysql/inventory.csv' INTO TABLE inventory
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';
SHOW WARNINGS;
LOAD DATA LOCAL INFILE 'C:/PATH/TO/PROJECT/data/s/mysql/orders.csv' INTO TABLE orders
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';
SHOW WARNINGS;
LOAD DATA LOCAL INFILE 'C:/PATH/TO/PROJECT/data/s/mysql/order_item.csv' INTO TABLE order_item
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';
SHOW WARNINGS;
LOAD DATA LOCAL INFILE 'C:/PATH/TO/PROJECT/data/s/mysql/payment.csv' INTO TABLE payment
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '\\'
  LINES TERMINATED BY '\r\n';
SHOW WARNINGS;

SELECT 'category' AS table_name, COUNT(*) AS row_count FROM category UNION ALL
SELECT 'store', COUNT(*) FROM store UNION ALL
SELECT 'customer', COUNT(*) FROM customer UNION ALL
SELECT 'product', COUNT(*) FROM product UNION ALL
SELECT 'inventory', COUNT(*) FROM inventory UNION ALL
SELECT 'orders', COUNT(*) FROM orders UNION ALL
SELECT 'order_item', COUNT(*) FROM order_item UNION ALL
SELECT 'payment', COUNT(*) FROM payment;
SELECT SUM(quantity * unit_price) AS revenue_gross FROM order_item;

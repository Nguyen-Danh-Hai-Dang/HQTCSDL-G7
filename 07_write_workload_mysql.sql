-- =====================================================================
-- WRITE WORKLOAD MySQL: W1-W3 có kiểm tra điều kiện và xử lý lỗi.
-- Chạy sau schema và nạp dữ liệu. Script chỉ tạo procedure, không tự CALL.
-- W1/W2 dùng transaction; SQLEXCEPTION đều rollback rồi trả lỗi.
-- =====================================================================
USE shop_bench;
DROP PROCEDURE IF EXISTS W1_create_order;
DROP PROCEDURE IF EXISTS W2_mark_paid;
DROP PROCEDURE IF EXISTS W3_restock;
DELIMITER $$

CREATE PROCEDURE W1_create_order(
  IN p_order_id BIGINT UNSIGNED, IN p_payment_id BIGINT UNSIGNED,
  IN p_customer_id INT UNSIGNED, IN p_store_id SMALLINT UNSIGNED,
  IN p_product_1 INT UNSIGNED, IN p_quantity_1 INT UNSIGNED,
  IN p_product_2 INT UNSIGNED, IN p_quantity_2 INT UNSIGNED
)
BEGIN
  DECLARE v_price_1 DECIMAL(12,2);
  DECLARE v_price_2 DECIMAL(12,2);
  DECLARE v_stock INT;
  DECLARE EXIT HANDLER FOR NOT FOUND
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  IF p_product_1 = p_product_2 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: product IDs must be different';
  END IF;
  IF p_quantity_1 = 0 OR p_quantity_2 = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: quantities must be positive';
  END IF;

  START TRANSACTION;
  SELECT price INTO v_price_1 FROM product WHERE product_id = p_product_1;
  SELECT price INTO v_price_2 FROM product WHERE product_id = p_product_2;

  -- Khoá tồn kho theo thứ tự product_id tăng dần để giảm nguy cơ deadlock.
  IF p_product_1 < p_product_2 THEN
    SELECT quantity INTO v_stock FROM inventory
      WHERE store_id = p_store_id AND product_id = p_product_1 FOR UPDATE;
    IF v_stock < p_quantity_1 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: insufficient stock for product 1';
    END IF;
    SELECT quantity INTO v_stock FROM inventory
      WHERE store_id = p_store_id AND product_id = p_product_2 FOR UPDATE;
    IF v_stock < p_quantity_2 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: insufficient stock for product 2';
    END IF;
  ELSE
    SELECT quantity INTO v_stock FROM inventory
      WHERE store_id = p_store_id AND product_id = p_product_2 FOR UPDATE;
    IF v_stock < p_quantity_2 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: insufficient stock for product 2';
    END IF;
    SELECT quantity INTO v_stock FROM inventory
      WHERE store_id = p_store_id AND product_id = p_product_1 FOR UPDATE;
    IF v_stock < p_quantity_1 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: insufficient stock for product 1';
    END IF;
  END IF;

  INSERT INTO orders (order_id, customer_id, store_id, order_date, status)
  VALUES (p_order_id, p_customer_id, p_store_id, UTC_TIMESTAMP(), 'PENDING');
  INSERT INTO order_item (order_id, line_no, product_id, quantity, unit_price)
  VALUES (p_order_id, 1, p_product_1, p_quantity_1, v_price_1),
         (p_order_id, 2, p_product_2, p_quantity_2, v_price_2);
  INSERT INTO payment (payment_id, order_id, method, amount, paid_at, status)
  VALUES (p_payment_id, p_order_id, 'CARD',
          p_quantity_1 * v_price_1 + p_quantity_2 * v_price_2, NULL, 'PENDING');

  UPDATE inventory SET quantity = quantity - p_quantity_1
    WHERE store_id = p_store_id AND product_id = p_product_1
      AND quantity >= p_quantity_1;
  IF ROW_COUNT() <> 1 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: inventory update failed for product 1';
  END IF;
  UPDATE inventory SET quantity = quantity - p_quantity_2
    WHERE store_id = p_store_id AND product_id = p_product_2
      AND quantity >= p_quantity_2;
  IF ROW_COUNT() <> 1 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: inventory update failed for product 2';
  END IF;
  COMMIT;
END$$

CREATE PROCEDURE W2_mark_paid(IN p_order_id BIGINT UNSIGNED)
BEGIN
  DECLARE v_status VARCHAR(20);
  DECLARE v_payment_rows INT DEFAULT 0;
  DECLARE EXIT HANDLER FOR NOT FOUND
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;
  START TRANSACTION;
  SELECT status INTO v_status FROM orders
    WHERE order_id = p_order_id FOR UPDATE;
  IF v_status <> 'PENDING' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W2: order is not PENDING';
  END IF;
  UPDATE payment SET status = 'PAID', paid_at = UTC_TIMESTAMP()
    WHERE order_id = p_order_id AND status = 'PENDING';
  SET v_payment_rows = ROW_COUNT();
  IF v_payment_rows = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W2: no PENDING payment exists';
  END IF;
  UPDATE orders SET status = 'PAID'
    WHERE order_id = p_order_id AND status = 'PENDING';
  IF ROW_COUNT() <> 1 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W2: order state changed unexpectedly';
  END IF;
  COMMIT;
END$$

CREATE PROCEDURE W3_restock(
  IN p_store_id SMALLINT UNSIGNED, IN p_product_id INT UNSIGNED,
  IN p_quantity INT UNSIGNED
)
BEGIN
  IF p_quantity = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W3: quantity must be positive';
  END IF;
  UPDATE inventory SET quantity = quantity + p_quantity
    WHERE store_id = p_store_id AND product_id = p_product_id;
  IF ROW_COUNT() <> 1 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W3: inventory row not found';
  END IF;
END$$
DELIMITER ;

-- Ví dụ gọi thủ công sau khi xác minh ID và tồn kho:
-- CALL W1_create_order(100000001, 900000001, 5439, 7, 1124, 2, 3103, 1);
-- CALL W2_mark_paid(123456);
-- CALL W3_restock(7, 1124, 50);

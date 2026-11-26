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
  IN p_order_id BIGINT UNSIGNED,
  IN p_payment_id BIGINT UNSIGNED,
  IN p_customer_id INT UNSIGNED,
  IN p_store_id SMALLINT UNSIGNED,
  IN p_lines JSON
)
BEGIN
  DECLARE v_len INT UNSIGNED;
  DECLARE v_i INT UNSIGNED DEFAULT 0;
  DECLARE v_item JSON;
  DECLARE v_pid_json JSON;
  DECLARE v_qty_json JSON;
  DECLARE v_pid_num DECIMAL(20,0);
  DECLARE v_qty_num DECIMAL(20,0);
  DECLARE v_count INT UNSIGNED DEFAULT 0;
  DECLARE v_distinct INT UNSIGNED DEFAULT 0;
  DECLARE v_total DECIMAL(24,2);
  DECLARE v_pid INT UNSIGNED;
  DECLARE v_qty SMALLINT UNSIGNED;

  DECLARE cur_inventory CURSOR FOR
    SELECT jt.product_id, jt.quantity
    FROM JSON_TABLE(
      p_lines,
      '$[*]' COLUMNS (
        product_id INT UNSIGNED PATH '$.pid',
        quantity SMALLINT UNSIGNED PATH '$.qty'
      )
    ) AS jt
    ORDER BY jt.product_id;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  -- Xác thực JSON trước khi ép kiểu bằng JSON_TABLE để tránh chuyển kiểu ngầm.
  IF p_order_id = 0 OR p_payment_id = 0
     OR p_order_id > 9007199254740991 OR p_payment_id > 9007199254740991 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: order and payment IDs must be positive safe integers';
  END IF;

  IF p_lines IS NULL OR JSON_TYPE(p_lines) <> 'ARRAY' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: lines must be a JSON array';
  END IF;

  SET v_len = JSON_LENGTH(p_lines);
  IF v_len < 1 OR v_len > 50 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: expected 1..50 order lines';
  END IF;

  WHILE v_i < v_len DO
    SET v_item = JSON_EXTRACT(p_lines, CONCAT('$[', v_i, ']'));
    IF JSON_TYPE(v_item) <> 'OBJECT'
       OR JSON_CONTAINS_PATH(v_item, 'all', '$.pid', '$.qty') <> 1 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: each line must contain pid and qty';
    END IF;

    SET v_pid_json = JSON_EXTRACT(v_item, '$.pid');
    SET v_qty_json = JSON_EXTRACT(v_item, '$.qty');
    IF JSON_TYPE(v_pid_json) <> 'INTEGER'
       OR JSON_TYPE(v_qty_json) <> 'INTEGER' THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: pid and qty must be JSON integers';
    END IF;

    SET v_pid_num = CAST(JSON_UNQUOTE(v_pid_json) AS DECIMAL(20,0));
    SET v_qty_num = CAST(JSON_UNQUOTE(v_qty_json) AS DECIMAL(20,0));
    IF v_pid_num < 1 OR v_pid_num > 4294967295
       OR v_qty_num < 1 OR v_qty_num > 65535 THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: pid or qty is outside the supported range';
    END IF;
    SET v_i = v_i + 1;
  END WHILE;

  SELECT COUNT(*), COUNT(DISTINCT jt.product_id)
    INTO v_count, v_distinct
  FROM JSON_TABLE(
    p_lines,
    '$[*]' COLUMNS (product_id INT UNSIGNED PATH '$.pid')
  ) AS jt;
  IF v_count <> v_len OR v_distinct <> v_len THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: duplicate product IDs are not allowed';
  END IF;

  START TRANSACTION;

  SELECT COUNT(*) INTO v_count
  FROM customer WHERE customer_id = p_customer_id;
  IF v_count <> 1 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: customer not found';
  END IF;

  SELECT COUNT(*) INTO v_count
  FROM store WHERE store_id = p_store_id;
  IF v_count <> 1 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: store not found';
  END IF;

  SELECT COUNT(*) INTO v_count
  FROM JSON_TABLE(
    p_lines,
    '$[*]' COLUMNS (product_id INT UNSIGNED PATH '$.pid')
  ) AS jt
  JOIN product p ON p.product_id = jt.product_id;
  IF v_count <> v_len THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: one or more products do not exist';
  END IF;

  SELECT COUNT(*) INTO v_count
  FROM JSON_TABLE(
    p_lines,
    '$[*]' COLUMNS (product_id INT UNSIGNED PATH '$.pid')
  ) AS jt
  JOIN inventory i
    ON i.product_id = jt.product_id AND i.store_id = p_store_id;
  IF v_count <> v_len THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: inventory row missing for this store';
  END IF;

  SELECT SUM(jt.quantity * p.price) INTO v_total
  FROM JSON_TABLE(
    p_lines,
    '$[*]' COLUMNS (
      product_id INT UNSIGNED PATH '$.pid',
      quantity SMALLINT UNSIGNED PATH '$.qty'
    )
  ) AS jt
  JOIN product p ON p.product_id = jt.product_id;

  IF v_total > 999999999999.99 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'W1: payment total exceeds DECIMAL(14,2)';
  END IF;

  INSERT INTO orders (order_id, customer_id, store_id, order_date, status)
  VALUES (p_order_id, p_customer_id, p_store_id, UTC_TIMESTAMP(), 'PENDING');

  INSERT INTO order_item (order_id, line_no, product_id, quantity, unit_price)
  SELECT p_order_id, jt.line_no, jt.product_id, jt.quantity, p.price
  FROM JSON_TABLE(
    p_lines,
    '$[*]' COLUMNS (
      line_no FOR ORDINALITY,
      product_id INT UNSIGNED PATH '$.pid',
      quantity SMALLINT UNSIGNED PATH '$.qty'
    )
  ) AS jt
  JOIN product p ON p.product_id = jt.product_id
  ORDER BY jt.line_no;

  INSERT INTO payment (payment_id, order_id, method, amount, paid_at, status)
  VALUES (p_payment_id, p_order_id, 'CARD', v_total, NULL, 'PENDING');

  -- Cập nhật từng inventory theo product_id tăng dần để giảm deadlock.
  BEGIN
    DECLARE v_done BOOLEAN DEFAULT FALSE;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = TRUE;

    OPEN cur_inventory;
    inventory_loop: LOOP
      FETCH cur_inventory INTO v_pid, v_qty;
      IF v_done THEN
        LEAVE inventory_loop;
      END IF;

      UPDATE inventory
      SET quantity = quantity - v_qty
      WHERE store_id = p_store_id
        AND product_id = v_pid
        AND quantity >= v_qty;

      IF ROW_COUNT() <> 1 THEN
        SIGNAL SQLSTATE '45000'
          SET MESSAGE_TEXT = 'W1: insufficient stock or inventory row changed';
      END IF;
    END LOOP;
    CLOSE cur_inventory;
  END;

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
-- CALL W1_create_order(100000001, 900000001, 5439, 7,
--   JSON_ARRAY(JSON_OBJECT('pid', 1124, 'qty', 2),
--              JSON_OBJECT('pid', 3103, 'qty', 1)));
-- CALL W2_mark_paid(123456);
-- CALL W3_restock(7, 1124, 50);

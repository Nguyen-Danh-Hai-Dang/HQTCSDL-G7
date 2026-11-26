USE shop_bench;

-- Minimal deterministic fixture. This test runs only in an ephemeral CI database.
INSERT INTO category (category_id, name, parent_id) VALUES (1, 'Test', NULL);
INSERT INTO customer (customer_id, full_name, email, phone, city, created_at)
VALUES (1, 'CI Customer', 'ci@example.test', '0900000000', 'Hanoi', UTC_TIMESTAMP());
INSERT INTO store (store_id, name, city) VALUES (1, 'CI Store', 'Hanoi');
INSERT INTO product (product_id, sku, name, category_id, price, created_at) VALUES
  (1, 'CI-001', 'Product 1', 1, 10.00, UTC_TIMESTAMP()),
  (2, 'CI-002', 'Product 2', 1, 20.00, UTC_TIMESTAMP()),
  (3, 'CI-003', 'Product 3', 1, 30.00, UTC_TIMESTAMP());
INSERT INTO inventory (store_id, product_id, quantity) VALUES
  (1, 1, 3),
  (1, 2, 0),
  (1, 3, 2147483640);

-- Successful multi-line W1: payment total and inventory must match.
CALL W1_create_order(
  1001, 2001, 1, 1,
  JSON_ARRAY(JSON_OBJECT('pid', 1, 'qty', 2), JSON_OBJECT('pid', 2, 'qty', 1))
);

DELIMITER $$
CREATE PROCEDURE assert_mysql_workload()
BEGIN
  DECLARE v_count INT DEFAULT 0;
  DECLARE v_qty INT DEFAULT 0;
  DECLARE v_amount DECIMAL(14,2) DEFAULT 0;
  DECLARE v_failed BOOLEAN DEFAULT FALSE;

  SELECT COUNT(*) INTO v_count FROM order_item WHERE order_id = 1001;
  IF v_count <> 2 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CI: W1 did not create two order lines';
  END IF;

  SELECT amount INTO v_amount FROM payment WHERE payment_id = 2001;
  IF v_amount <> 40.00 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CI: W1 payment total mismatch';
  END IF;

  SELECT quantity INTO v_qty FROM inventory WHERE store_id = 1 AND product_id = 1;
  IF v_qty <> 1 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CI: W1 product 1 stock mismatch';
  END IF;

  -- Product 1 update happens before product 2 fails. Entire W1 must roll back.
  SET v_failed = FALSE;
  BEGIN
    DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET v_failed = TRUE;
    CALL W1_create_order(
      1002, 2002, 1, 1,
      JSON_ARRAY(JSON_OBJECT('pid', 1, 'qty', 1), JSON_OBJECT('pid', 2, 'qty', 1))
    );
  END;
  IF NOT v_failed THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CI: W1 insufficient-stock call unexpectedly succeeded';
  END IF;

  SELECT COUNT(*) INTO v_count FROM orders WHERE order_id = 1002;
  IF v_count <> 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CI: W1 rollback left an order behind';
  END IF;
  SELECT COUNT(*) INTO v_count FROM payment WHERE payment_id = 2002;
  IF v_count <> 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CI: W1 rollback left a payment behind';
  END IF;
  SELECT quantity INTO v_qty FROM inventory WHERE store_id = 1 AND product_id = 1;
  IF v_qty <> 1 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CI: W1 rollback did not restore earlier inventory update';
  END IF;

  CALL W3_restock(1, 1, 5);
  SELECT quantity INTO v_qty FROM inventory WHERE store_id = 1 AND product_id = 1;
  IF v_qty <> 6 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CI: W3 successful restock mismatch';
  END IF;

  -- The signed INT ceiling must be enforced before arithmetic overflows.
  SET v_failed = FALSE;
  BEGIN
    DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET v_failed = TRUE;
    CALL W3_restock(1, 3, 10);
  END;
  IF NOT v_failed THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CI: W3 overflow call unexpectedly succeeded';
  END IF;
  SELECT quantity INTO v_qty FROM inventory WHERE store_id = 1 AND product_id = 3;
  IF v_qty <> 2147483640 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'CI: W3 overflow changed inventory';
  END IF;
END$$
DELIMITER ;

CALL assert_mysql_workload();
DROP PROCEDURE assert_mysql_workload;
SELECT 'PASS: MySQL W1 multi-line, rollback, and W3 bounds' AS integration_test;

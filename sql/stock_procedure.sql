-- One stock change and its audit record form one unit of work.
-- Caller controls COMMIT. Use fl_demo_start for demonstrations, never fl_post_sp.
CREATE OR REPLACE PROCEDURE post_inventory_movement (
    p_task_id IN NUMBER,
    p_bin_id IN NUMBER,
    p_product_id IN NUMBER,
    p_lot_code IN VARCHAR2,
    p_quantity_change IN NUMBER,
    p_remarks IN VARCHAR2 DEFAULT NULL
) AUTHID DEFINER
AS
    v_task_wh NUMBER;
    v_bin_wh NUMBER;
    v_shipment NUMBER;
    v_status warehouse_task.status%TYPE;
    v_type warehouse_task.task_type%TYPE;
    v_lot inventory.lot_code%TYPE;
    v_balance inventory.quantity_on_hand%TYPE;
    v_count NUMBER;
BEGIN
    SAVEPOINT fl_post_sp;
    IF p_quantity_change IS NULL OR p_quantity_change = 0
       OR p_quantity_change <> ROUND(p_quantity_change, 3)
       OR ABS(p_quantity_change) > 999999999.999 THEN
        RAISE_APPLICATION_ERROR(-20001, 'Quantity must be nonzero, with at most 3 decimals and within range.');
    END IF;
    IF TRIM(p_lot_code) IS NULL OR LENGTHB(TRIM(p_lot_code)) > 30 THEN
        RAISE_APPLICATION_ERROR(-20002, 'Provide a lot code of 1 to 30 bytes; use NOLOT if untracked.');
    END IF;
    v_lot := TRIM(p_lot_code);
    IF LENGTHB(p_remarks) > 200 THEN
        RAISE_APPLICATION_ERROR(-20012, 'Remarks exceed 200 bytes.');
    END IF;
    BEGIN
        SELECT warehouse_id, shipment_id, status, task_type
        INTO v_task_wh, v_shipment, v_status, v_type
        FROM warehouse_task WHERE task_id = p_task_id FOR UPDATE;
    EXCEPTION WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(-20003, 'Task does not exist.');
    END;
    IF v_status NOT IN ('OPEN', 'IN_PROGRESS') THEN
        RAISE_APPLICATION_ERROR(-20004, 'Task is completed or cancelled.');
    END IF;
    BEGIN
        SELECT z.warehouse_id INTO v_bin_wh
        FROM storage_bin b JOIN warehouse_zone z ON z.zone_id = b.zone_id
        WHERE b.bin_id = p_bin_id;
    EXCEPTION WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(-20005, 'Storage bin does not exist.');
    END;
    IF v_bin_wh <> v_task_wh THEN
        RAISE_APPLICATION_ERROR(-20006, 'Bin and task belong to different warehouses.');
    END IF;
    SELECT COUNT(*) INTO v_count FROM product WHERE product_id = p_product_id;
    IF v_count = 0 THEN RAISE_APPLICATION_ERROR(-20007, 'Product does not exist.'); END IF;
    IF v_shipment IS NOT NULL THEN
        SELECT COUNT(*) INTO v_count FROM shipment_item
        WHERE shipment_id = v_shipment AND product_id = p_product_id;
        IF v_count = 0 THEN RAISE_APPLICATION_ERROR(-20008, 'Product is absent from the task shipment.'); END IF;
    END IF;
    IF (v_type = 'RECEIVE' AND p_quantity_change < 0)
       OR (v_type = 'DISPATCH' AND p_quantity_change > 0)
       OR v_type = 'PACK' THEN
        RAISE_APPLICATION_ERROR(-20009, 'Movement direction is invalid for this task type.');
    END IF;
    -- Duplicate protection also handles simultaneous creation of the same balance.
    BEGIN
        INSERT INTO inventory (bin_id, product_id, lot_code, quantity_on_hand)
        VALUES (p_bin_id, p_product_id, v_lot, 0);
    EXCEPTION WHEN DUP_VAL_ON_INDEX THEN NULL;
    END;
    SELECT quantity_on_hand INTO v_balance FROM inventory
    WHERE bin_id = p_bin_id AND product_id = p_product_id AND lot_code = v_lot
    FOR UPDATE;
    IF v_balance + p_quantity_change < 0 THEN
        RAISE_APPLICATION_ERROR(-20010, 'Insufficient stock. Available=' || v_balance);
    END IF;
    IF v_balance + p_quantity_change > 999999999.999 THEN
        RAISE_APPLICATION_ERROR(-20011, 'Resulting stock exceeds the supported quantity range.');
    END IF;
    UPDATE inventory SET quantity_on_hand = quantity_on_hand + p_quantity_change
    WHERE bin_id = p_bin_id AND product_id = p_product_id AND lot_code = v_lot;
    INSERT INTO inventory_movement
        (task_id, bin_id, product_id, lot_code, quantity_change, remarks)
    VALUES (p_task_id, p_bin_id, p_product_id, v_lot, p_quantity_change, p_remarks);
EXCEPTION
    WHEN OTHERS THEN
        ROLLBACK TO fl_post_sp;
        RAISE;
END post_inventory_movement;
/
-- Compilation errors must not be mistaken for a successfully created procedure.
DECLARE
    v_errors NUMBER;
BEGIN
    SELECT COUNT(*) INTO v_errors FROM user_errors
    WHERE name = 'POST_INVENTORY_MOVEMENT' AND type = 'PROCEDURE';
    IF v_errors > 0 THEN RAISE_APPLICATION_ERROR(-20090, 'Stock procedure has compilation errors. Inspect USER_ERRORS.'); END IF;
END;
/

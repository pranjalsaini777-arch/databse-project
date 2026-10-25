-- Q01 Shipment overview
SELECT s.shipment_ref, c.customer_name, o.city AS origin_city,
       d.city AS destination_city, s.status
FROM shipment s JOIN customer c ON c.customer_id = s.customer_id
JOIN location o ON o.location_id = s.origin_location_id
JOIN location d ON d.location_id = s.destination_location_id
ORDER BY s.shipment_id;

-- Q02 Itinerary for SHP-001
SELECT s.shipment_ref, sl.sequence_no, f.location_name AS from_point,
       t.location_name AS to_point, m.mode_name, c.carrier_name,
       COALESCE(v.registration_no, 'UNASSIGNED') AS vehicle
FROM shipment_leg sl JOIN shipment s ON s.shipment_id = sl.shipment_id
JOIN location f ON f.location_id = sl.from_location_id
JOIN location t ON t.location_id = sl.to_location_id
JOIN transport_mode m ON m.mode_id = sl.mode_id
JOIN carrier c ON c.carrier_id = sl.carrier_id
LEFT JOIN vehicle v ON v.vehicle_id = sl.vehicle_id
WHERE s.shipment_ref = 'SHP-001' ORDER BY sl.sequence_no;

-- Q03 Contents of SHP-001
SELECT s.shipment_ref, p.sku, p.product_name, si.quantity, p.unit_of_measure,
       si.quantity * p.unit_weight_kg AS total_weight_kg
FROM shipment_item si JOIN shipment s ON s.shipment_id = si.shipment_id
JOIN product p ON p.product_id = si.product_id
WHERE s.shipment_ref = 'SHP-001' ORDER BY p.sku;

-- Q04 Stock by warehouse bin and lot
SELECT warehouse_code, zone_name, bin_id, bin_code, sku, lot_code,
       quantity_on_hand, unit_of_measure
FROM v_inventory_detail ORDER BY warehouse_id, bin_id, sku, lot_code;

-- Q05 Product totals in each warehouse
SELECT warehouse_code, sku, product_name, unit_of_measure,
       SUM(quantity_on_hand) AS total_quantity
FROM v_inventory_detail
GROUP BY warehouse_code, sku, product_name, unit_of_measure
ORDER BY warehouse_code, sku;

-- Q06 Open warehouse work
SELECT t.task_id, w.warehouse_code, t.task_type, t.status,
       t.assigned_to, COALESCE(s.shipment_ref, 'INTERNAL') AS shipment
FROM warehouse_task t JOIN warehouse w ON w.warehouse_id = t.warehouse_id
LEFT JOIN shipment s ON s.shipment_id = t.shipment_id
WHERE t.status IN ('OPEN', 'IN_PROGRESS') ORDER BY w.warehouse_code, t.task_id;

-- Q07 Audit history for SKU-001 LOT_A
SELECT im.movement_id, im.task_id, im.bin_id, p.sku, im.lot_code,
       im.quantity_change, im.remarks
FROM inventory_movement im JOIN product p ON p.product_id = im.product_id
WHERE p.sku = 'SKU-001' AND im.lot_code = 'LOT_A'
ORDER BY im.movement_id;

-- Q08 Shipments using multiple transport modes
SELECT s.shipment_ref, COUNT(sl.leg_id) AS leg_count,
       COUNT(DISTINCT sl.mode_id) AS mode_count
FROM shipment s JOIN shipment_leg sl ON sl.shipment_id = s.shipment_id
GROUP BY s.shipment_ref HAVING COUNT(DISTINCT sl.mode_id) > 1
ORDER BY s.shipment_ref;

-- Q09 Legs awaiting a vehicle
SELECT s.shipment_ref, sl.sequence_no, m.mode_name, c.carrier_name
FROM shipment_leg sl JOIN shipment s ON s.shipment_id = sl.shipment_id
JOIN transport_mode m ON m.mode_id = sl.mode_id
JOIN carrier c ON c.carrier_id = sl.carrier_id
WHERE sl.vehicle_id IS NULL AND s.status NOT IN ('DELIVERED', 'CANCELLED')
ORDER BY s.shipment_ref, sl.sequence_no;

-- Q10 Shipment counts by customer and status
SELECT c.customer_name, s.status, COUNT(*) AS shipment_count
FROM customer c JOIN shipment s ON s.customer_id = c.customer_id
GROUP BY c.customer_name, s.status ORDER BY c.customer_name, s.status;

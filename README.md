# Freight Logistics — Oracle website

A browser interface for the existing Multimodal Freight Logistics and Automated Warehouse Distribution database.

## Run in GitHub Codespaces

1. Put the contents of this folder at your repository root: `app.py`, `requirements.txt`, `templates/`, `static/`, `sql/`, and `.devcontainer/`.
2. On GitHub choose **Code → Codespaces → Create codespace on main** (or your default branch).
3. Wait for the container and dependency installation to finish.
4. In the Codespaces terminal, run:

```bash
python -m flask --app app run --host=0.0.0.0 --port=5000
```

5. Open the **Ports** tab. Port 5000 must have **Private** visibility. Click its globe / Open in Browser button.
6. Click **Connect Oracle** and enter the database username, database password and connection string from your FreeSQL account's application connection details.

If dependency installation did not run automatically:

```bash
python -m pip install -r requirements.txt
```

The `.devcontainer` folder is helpful but optional. These commands also work in a default Python Codespace with the project at its root.

## Database connection

Use the existing populated Oracle project schema. Do not rerun table creation or seed data.
The connection checks the shipment table, inventory view and valid POST_INVENTORY_MOVEMENT procedure.
Use the Python/Oracle DSN, without a JDBC `jdbc:oracle:thin:@` prefix.
Database credentials can differ from the Oracle website login.
Never commit credentials or put them in GitHub issues, screenshots, or terminal commands.
Credentials stay in process memory and must be reentered after restarting the server.

The Codespace must be able to reach Oracle's database endpoint. Live connectivity is not yet verified.
Keep the Codespace and server running for the demonstration. Codespaces can stop when idle and usage is subject to your GitHub account quota.

## Demonstration

- Dashboard: live shipment, warehouse, product and pending task counts.
- Shipments: view SHP-001, its products and road/rail/road route.
- Transport: assign a matching vehicle to an open shipment leg.
- Inventory: filter SKU-001 and LOT_A; note bin 1's current balance.
- Stock operations: task 7 RECEIVE, bin 1 SKU-001 LOT_A, quantity +20.
- Task 8 DISPATCH, same stock line, quantity -5.
- Attempt -10000 through task 8: Oracle should reject insufficient stock.
- Reports: show inventory and movement results and the original SQL.

Every successful write commits to Oracle. The audit history remains after a demonstration.
If restoring the balance after +20 and -5, post -15 through task 8. This restores quantity, not the original movement count.

## Checks

```bash
python -m unittest discover -v
```

These application checks do not substitute for live Oracle testing. No mock data is used by the website.

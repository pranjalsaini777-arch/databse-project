FREIGHT LOGISTICS — LOCAL WEBSITE

1. Double-click START_WEBSITE.bat. Keep its terminal open.
   First run installs Flask and python-oracledb if needed.
   If Python is missing, install Python 3.11+ from python.org and enable Add Python to PATH.
2. Open http://127.0.0.1:5000 on this laptop.
3. Click Connect Oracle. In your FreeSQL account, open the Connect/application connection details.
   Enter the database username, database password and full Oracle connection string.
   These are database credentials; the Oracle website password may be different.
   Never paste a JDBC prefix (jdbc:oracle:thin:@); use the Python/Oracle connection string.
4. The existing project schema must contain all 15 tables, the inventory view and the valid stock procedure.
   Do not rerun CREATE TABLE or sample data in the existing populated account.

LIVE DEMONSTRATION
- Dashboard: show live shipment counts and warehouses.
- Shipments: search SHP-001, inspect the three-leg road/rail/road itinerary and products.
- Transport: find SHP-007's unassigned leg and assign a matching vehicle.
- Inventory: search SKU-001 and LOT_A; note bin 1's balance (original baseline 85).
- Stock operations: select task 7 (RECEIVE), bin 1 / SKU-001 / LOT_A, post +20.
- Select task 8 (DISPATCH), same stock line, post -5. Audit trail and inventory reflect both.
- Try -10000 using task 8. Oracle rejects insufficient stock; balance stays unchanged.
- To restore the original balance after this sequence: post -15 through task 8.
  This restores quantity, but audit rows intentionally remain. Counts therefore exceed the original 35 movements.
- Reports: inspect the stock, movement and multimodal queries and expand View executed SQL.

REAL DATABASE BEHAVIOUR
Every successful write is committed to Oracle. Closing the browser does not undo it.
There is no mock database or automatic switch to sample outputs.
The website runs locally; Oracle FreeSQL is remote, so internet is required.
Passwords are kept only in Python memory, never saved to files or browser storage.
Restarting requires reconnecting. No app login is used.

FILES
app.py: Python API, parameterized SQL, PL/SQL calls and transactions.
templates/index.html + static/: local website.
sql/reports.sql: the ten original reporting queries.
sql/stock_procedure.sql: reference copy of the submitted Oracle procedure, not auto-executed.

VALIDATION STATUS
The application requires a real connection to verify Oracle integration.
If no credentials were entered during preparation, do not describe it as Oracle-tested.

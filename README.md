# Starbucks Capacity Dashboard - Complete Deployment Package

## 📦 What's Included

This package contains everything needed to deploy a production-ready Starbucks inventory capacity dashboard:

### Frontend
- `starbucks_capacity_dashboard.html` - Branded UI with Starbucks colors/fonts

### Backend
- `backend_server.py` - Flask server that queries Epicor via CData Connect AI
- `requirements.txt` - Python dependencies

### Documentation
- This file - Complete deployment guide

## 🚀 Quick Start (5 minutes)

### Step 1: Set Environment Variable

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Run Server

```bash
python backend_server.py
```

### Step 4: Open Dashboard

```
http://localhost:5000
```

**Done!** Dashboard will query live Epicor data on refresh.

## 🔧 How It Works

### Architecture

```
┌─────────────────┐
│   Browser       │
│  (Dashboard)    │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  Flask Server   │
│  (Port 5000)    │
└────────┬────────┘
         │ Anthropic API
         ▼
┌─────────────────┐
│  Claude API     │
│  (Tool Calls)   │
└────────┬────────┘
         │ CData Connect AI
         ▼
┌─────────────────┐
│  Epicor ERP     │
│  (Live Data)    │
└─────────────────┘
```

### API Endpoints

**GET /api/inventory**
- Queries PartWhses table for current inventory
- Returns: Part numbers, on-hand qty, allocated, available

**GET /api/pos**
- Queries MRP_POs BAQ for open purchase orders  
- Returns: PO numbers, quantities, due dates, vendors

**GET /api/bom**
- Returns master BOM from Quote 109209
- Static data, no Epicor query

**POST /api/capacity**
- Calculates production capacity per SKU
- Takes inventory + PO data
- Returns: Current capacity, future capacity, limiting components

**GET /health**
- Health check endpoint
- Verifies API key is set

## 📊 Data Flow

1. User opens dashboard at `http://localhost:5000`
2. User clicks "Refresh Data"
3. Frontend calls `/api/inventory` and `/api/pos`
4. Backend queries Epicor via Claude + CData Connect AI
5. Backend returns structured JSON
6. Frontend calculates capacity using `/api/capacity`
7. Dashboard updates with live data

## 🎯 What Queries Run

### Inventory Query (PartWhses)
```sql
SELECT 
  [PartNum],
  [WarehouseCode],
  [OnHandQty],
  [AllocatedQty],
  (OnHandQty - AllocatedQty) AS AvailableQty,
  [PartNumPartDescription],
  [PartNumIUM]
FROM [Amtrend_Epicor_Kinetic_PartSvc].[EpicorERP].[PartWhses]
WHERE [PartNum] IN ('SBX-118', 'SBX-119', 'POLB-129', ...)
ORDER BY [PartNum], [WarehouseCode]
```

### PO Query (MRP_POs BAQ)
```sql
SELECT 
  [PORel_PONum],
  [PORel_POLine],
  [PODetail_PartNum],
  [Vendor_Name],
  [PORel_XRelQty],
  [PORel_ReceivedQty],
  [PORel_DueDate],
  [PORel_PromiseDt]
FROM [Amtrend_EpicorKinetic_BaqSvc].[EpicorERP].[MRP_POs]
WHERE [PODetail_PartNum] IN ('SBX-118', 'SBX-119', ...)
  AND [POHeader_OpenOrder] = 1
```

## 🔐 Security

### API Key
- Stored in environment variable (not in code)
- Required for Anthropic API access
- Backend validates on startup

### CORS
- Enabled for localhost development
- Restrict in production to specific origins

### Production Deployment
For production, update:
```python
# backend_server.py
CORS(app, origins=["https://yourdomain.com"])
```

## 🐛 Troubleshooting

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
# Or add to ~/.bashrc for persistence
```

### "Import Error: No module named flask"
```bash
pip install -r requirements.txt
```

### "Connection refused"
- Ensure backend server is running: `python backend_server.py`
- Check port 5000 is not in use: `lsof -i :5000`

### "Load failed" in browser
- Open browser console (F12)
- Check if backend URL is correct
- Verify backend is running: `curl http://localhost:5000/health`

### "Query failed" errors
- Check CData Connect AI credentials
- Verify Epicor connectivity
- Check BAQ names (MRP_POs) exist in your Epicor instance

## 📝 Customization

### Change Port
```python
# backend_server.py, line at bottom
app.run(debug=True, host='0.0.0.0', port=8080)  # Change 5000 to 8080
```

### Add More SKUs
```python
# backend_server.py
MASTER_BOM["NEW-SKU"] = {
    "description": "New Product",
    "starbucksPartNum": "12345678",
    "quoteLine": "109209-6",
    "components": {
        "PART-A": {"qty": 1.0, "uom": "EA", "type": "Frame"},
        # ... add components
    }
}
```

### Update Branding
Edit `starbucks_capacity_dashboard.html`:
```css
/* Change colors */
.header {
    background: linear-gradient(135deg, #YOUR_COLOR 0%, #YOUR_COLOR_2 100%);
}
```

## 🚢 Production Deployment

### Option 1: Cloud Run (Recommended)
```bash
# Create Dockerfile
docker build -t starbucks-dashboard .
gcloud run deploy starbucks-dashboard --image gcr.io/PROJECT/starbucks-dashboard
```

### Option 2: Traditional Server
```bash
# Install on server
pip install -r requirements.txt gunicorn
export ANTHROPIC_API_KEY="..."

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 backend_server:app
```

### Option 3: Heroku
```bash
# Add Procfile
echo "web: gunicorn backend_server:app" > Procfile

# Deploy
heroku create starbucks-dashboard
heroku config:set ANTHROPIC_API_KEY="..."
git push heroku main
```

## ✅ Verification Checklist

Before deploying:
- [ ] API key set: `echo $ANTHROPIC_API_KEY`
- [ ] Dependencies installed: `pip list | grep flask`
- [ ] Server starts: `python backend_server.py`
- [ ] Health check passes: `curl http://localhost:5000/health`
- [ ] Dashboard loads: Open `http://localhost:5000`
- [ ] Data refreshes: Click "Refresh Data" button
- [ ] SKU details show: Verify all 5 SKUs display
- [ ] PO data appears: Check incoming POs show in tables

## 📞 Support

**For Deployment Issues:**
- Check logs: Server prints detailed startup info
- Health endpoint: `/health` shows system status
- Browser console: F12 for frontend errors

**For Data Issues:**
- Verify CData Connect AI access
- Check Epicor BAQ exists: MRP_POs
- Confirm part numbers in master BOM match Epicor

**For Custom Features:**
- Pass this entire package to Claude Code
- Specify requirements clearly
- Include sample data/screenshots

## 🎯 Key Benefits

1. **Real-Time**: Queries live Epicor data on demand
2. **Accurate**: Uses actual MRP_POs BAQ (confirmed working)
3. **Professional**: Starbucks-branded UI
4. **SKU-Level**: Complete BOM breakdown per product
5. **Production-Ready**: Error handling, health checks, CORS

The dashboard is **ready to deploy** - just set your API key and run!

# Starbucks Dashboard - Quick Start

## 📁 What's in This Folder

```
starbucks-dashboard/
├── starbucks_capacity_dashboard.html  ← Frontend (Starbucks-branded UI)
├── backend_server.py                  ← Backend (Flask API server)
├── requirements.txt                   ← Python dependencies
├── .env.template                      ← Environment setup template
├── start.sh                          ← One-command startup script
├── README.md                         ← Full deployment guide
├── PACKAGE_SUMMARY.md                ← Overview of everything
├── STARBUCKS_PO_STATUS_LIVE.md       ← Current inventory data
└── SKU_MAPPING_SUMMARY.md            ← SKU number reference
```

## 🚀 Get Started in 3 Steps

### Step 1: Set Your API Key

**Mac/Linux:**
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY="sk-ant-api03-your-key-here"
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Run the Dashboard

```bash
python backend_server.py
```

Open browser to: **http://localhost:5000**

**That's it!** 🎉

---

## 🎯 For Claude Code

Drop this entire folder to Claude Code and say:

> "Deploy the Starbucks capacity dashboard. Set up the Flask backend on port 5000, 
> query Epicor via CData Connect AI using the MRP_POs BAQ for PO data and PartWhses 
> for inventory, and serve the branded frontend. Make it production-ready."

Claude Code will:
1. Read all the code
2. Install dependencies automatically
3. Prompt you for your API key
4. Start the server
5. Show you the dashboard URL

---

## 📊 What You'll See

**Dashboard Features:**
- **Summary Cards**: Current vs. future capacity (0 vs. 65 units)
- **SKU Reference**: Starbucks SKU → Amtrend Part mapping (prominent!)
- **5 SKU Cards**: Each showing complete BOM with incoming POs
- **Inventory Table**: All materials with real-time availability
- **Refresh Button**: Query live Epicor data on demand

**Starbucks SKU Mapping (Clearly Displayed):**
- SKU: 11174933 → SBX-22721 (Moon Chair, Fern Green)
- SKU: 11174935 → SBX-24545 (Moon Chair, Roast Natural)
- SKU: 11174936 → SBX-24540 (Comf Chair, Fern Green)
- SKU: 11174937 → SBX-22880 (Comf Chair, Tan Brown)
- SKU: 11174939 → SBX-24541 (Comf Chair, Roast Natural)

---

## 💡 Key Files Explained

**starbucks_capacity_dashboard.html**
- Beautiful Starbucks-branded UI (#00704a green)
- SKU-level capacity breakdowns
- Real-time refresh capability
- Ready to screenshot for reports

**backend_server.py**
- Flask REST API (4 endpoints)
- Queries Epicor via CData Connect AI
- Working SQL queries included
- Production-ready error handling

**requirements.txt**
- Flask, Anthropic, CORS libraries
- Everything needed to run

**README.md**
- Complete deployment guide
- Troubleshooting section
- Production deployment options

---

## 🔧 Troubleshooting

**"API key not set"**
```bash
export ANTHROPIC_API_KEY="your-key"
```

**"Module not found"**
```bash
pip install -r requirements.txt
```

**"Port 5000 in use"**
Edit backend_server.py line 286:
```python
app.run(debug=True, host='0.0.0.0', port=8080)  # Change to 8080
```

---

## ✅ What's Working RIGHT NOW

Based on today's queries (Feb 2, 2026):

**Inventory (Confirmed Accurate):**
- LEA-SBX14 (Fern leather): 6,470.25 SQFT ✅
- LEA-SBX15 (Tan leather): 530 SQFT ⚠️ LOW
- LEA-SBX16 (Roast leather): 2,291.15 SQFT ✅
- All foams queried and accurate

**Incoming POs (Confirmed):**
- SBX-118 frames: 120 EA (60 arriving Feb 3, 60 Mar 2)
- SBX-119 frames: 160 EA (80 arriving Feb 3, 80 Mar 2)
- POLB-129 polybags: 25 RL (late - follow up)

**Critical Shortage:**
- FOAM-170 (Comf pattern): 0 EA, NO POs ❌
- FOAM-171 (Moon pattern): 0 EA, NO POs ❌
- **Action**: Order immediately!

---

## 🎨 Design Features

- Authentic Starbucks branding
- Professional, executive-ready
- Mobile responsive
- Color-coded status badges
- Hover effects
- Loading states

---

## 📞 Need Help?

Check the README.md for:
- Full architecture diagram
- API endpoint documentation
- Production deployment guide
- Advanced customization

**Everything you need is in this folder!**

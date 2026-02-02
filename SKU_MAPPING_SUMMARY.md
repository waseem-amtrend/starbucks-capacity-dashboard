# Starbucks SKU Mapping - Updated Dashboard

## ✅ Starbucks SKU Numbers Now Prominently Displayed

### Where They Appear:

#### 1. Dashboard Header (Top)
```
SKU Mapping: 11174933→SBX-22721 | 11174935→SBX-24545 | 11174936→SBX-24540 | 11174937→SBX-22880 | 11174939→SBX-24541
```

#### 2. Reference Card (Before Capacity Section)
Large, prominent yellow alert box showing:
```
📋 Starbucks SKU Reference

SKU: 11174933 → Amtrend Part: SBX-22721 (Moon Chair, Fern Green)
SKU: 11174935 → Amtrend Part: SBX-24545 (Moon Chair, Roast Natural)
SKU: 11174936 → Amtrend Part: SBX-24540 (Comf Chair, Fern Green)
SKU: 11174937 → Amtrend Part: SBX-22880 (Comf Chair, Tan Brown)
SKU: 11174939 → Amtrend Part: SBX-24541 (Comf Chair, Roast Natural)
```

#### 3. Each SKU Card Header
Each product card shows the Starbucks SKU in a highlighted badge:

**Example:**
```
┌─────────────────────────────────────────────────────┐
│  [SKU: 11174933]  → Amtrend Part: SBX-22721        │
│  Moon Chair, Fern Green F0244 • Quote 109209-5     │
└─────────────────────────────────────────────────────┘
```

The SKU number is:
- ✅ Large (24px font)
- ✅ Bold (700 weight)
- ✅ In a highlighted badge (white background with transparency)
- ✅ First element (most prominent position)

### Complete SKU Mapping

| Starbucks SKU | Amtrend Part | Description |
|---------------|--------------|-------------|
| **11174933** | SBX-22721 | Moon Chair, Fern Green F0244 |
| **11174935** | SBX-24545 | Moon Chair, Roast Natural F0262 |
| **11174936** | SBX-24540 | Comf Chair, Fern Green F0244 |
| **11174937** | SBX-22880 | Comf Chair, Tan Brown F0245 |
| **11174939** | SBX-24541 | Comf Chair, Roast Natural F0262 |

### Visual Hierarchy

**Most Prominent → Least Prominent:**
1. Reference Card (Yellow box at top)
2. SKU Card Headers (Large badge for each SKU)
3. Dashboard Header (Quick reference line)

### For Starbucks Communication

When referencing products, you can now say:

"**Starbucks SKU 11174933** (our part SBX-22721) has X units available..."

Or use the Amtrend part for internal communication:

"**SBX-22721** (Starbucks SKU 11174933) is blocked by foam patterns..."

Both formats are clearly shown throughout the dashboard!

---

## Backend Data Structure

The backend `MASTER_BOM` dictionary also includes this mapping:

```python
MASTER_BOM = {
    "SBX-22721": {
        "starbucksPartNum": "11174933",
        # ...
    },
    "SBX-24545": {
        "starbucksPartNum": "11174935",
        # ...
    },
    # ... etc
}
```

So the mapping is:
✅ Hard-coded in backend
✅ Displayed in frontend
✅ Prominent in UI
✅ Easy to reference

**The Starbucks SKU numbers are now impossible to miss!**

# Starbucks Capacity - Live PO Status
**Date**: February 2, 2026  
**Source**: MRP_POs BAQ (Epicor)

---

## 🚚 INCOMING MATERIALS - CONFIRMED

### FRAMES (Arriving Tomorrow!)

**SBX-118 (Moon Chair Frames)**
- ✅ PO 75612: **60 EA** - Promise date: **Feb 3, 2026** (TOMORROW!)
- ✅ PO 75760: **60 EA** - Due date: March 2, 2026
- **Total incoming: 120 EA**
- Vendor: Ergoing Group Limited

**SBX-119 (Comf Chair Frames)**
- ✅ PO 75612: **80 EA** - Promise date: **Feb 3, 2026** (TOMORROW!)
- ✅ PO 75760: **80 EA** - Due date: March 2, 2026
- **Total incoming: 160 EA**
- Vendor: Ergoing Group Limited

### PACKAGING

**POLB-129 (Polybags)**
- ⚠️ PO 75932: **25 RL** - Due date: Jan 29, 2026 (LATE - follow up!)
- Vendor: MLR Packaging, Inc.

---

## ❌ CRITICAL: NO POs FOR FOAM PATTERNS

### Missing Open POs:
- **FOAM-170** (Comf Chair Pattern): **0 EA on order** ❌
- **FOAM-171** (Moon Chair Pattern): **0 EA on order** ❌
- **FOAM-136** (Base Foam): 0 EA on order (PO 74233 already received 40 EA)
- **FOAM-125, FOAM-130, FOAM-132**: No open POs found

**IMMEDIATE ACTION REQUIRED**: Order foam patterns ASAP!

---

## 📊 PRODUCTION CAPACITY PROJECTIONS

### Current (Feb 2, 2026):
- **Total capacity: 0 units** (blocked by foam patterns)
- All 5 SKUs: BLOCKED

### After Frames Arrive (Feb 3, 2026):
- **Still BLOCKED by foam patterns**
- Frames available:
  - SBX-118: 60 EA
  - SBX-119: 80 EA

### After Foam Patterns Ordered:
Assuming foam patterns arrive in 2 weeks (Feb 17):

**With current inventory + first frame shipment (60/80 EA):**

| SKU | Current Materials Limit | With 1st Frame Shipment |
|-----|------------------------|------------------------|
| SBX-22721 (Moon, Fern) | BLOCKED (no FOAM-171) | 13 units (limited by FOAM-132) |
| SBX-24540 (Comf, Fern) | BLOCKED (no FOAM-170) | 13 units (limited by FOAM-132) |
| SBX-24541 (Comf, Roast) | BLOCKED (no FOAM-170) | 13 units (limited by FOAM-132) |
| SBX-24545 (Moon, Roast) | BLOCKED (no FOAM-171) | 13 units (limited by FOAM-132) |
| SBX-22880 (Comf, Tan) | BLOCKED (no FOAM-170) | 5 units (limited by LEA-SBX15) |

**Maximum capacity with current inventory:**
- Limited by FOAM-132: ~13 units per SKU
- Limited by LEA-SBX15 for SBX-22880: 5 units only

### With Second Frame Shipment (March 2):
Additional frames available, but still limited by:
- FOAM-132 inventory (6.5 EA on hand)
- LEA-SBX15 leather (530 SQFT on hand)

---

## 📋 ACTION ITEMS FOR ANGELA

### TODAY (Feb 2):
1. ✅ **Confirm frame delivery tomorrow** with Ergoing Group Limited
2. ✅ **Follow up on POLB-129** late PO with MLR Packaging
3. ❌ **ORDER FOAM PATTERNS IMMEDIATELY**:
   - FOAM-170 (Comf Chair): Recommend 50+ EA
   - FOAM-171 (Moon Chair): Recommend 50+ EA
   - Vendor: Foam Express Inc. (they supplied FOAM-136)
4. ✅ **Order additional FOAM-132**: Only 6.5 EA on hand (bottleneck)
5. ✅ **Order LEA-SBX15** (Tan Brown leather): Only 530 SQFT on hand

### TUESDAY (Feb 3):
1. ✅ Receive and verify frame delivery (60 + 80 EA)
2. ✅ Update capacity dashboard with confirmed receipts
3. ✅ Confirm foam pattern orders

### WEDNESDAY (Feb 4):
1. ✅ Prepare Starbucks report with:
   - Current status: Blocked by foam patterns
   - Frames received: 140 EA total
   - Projected capacity after foam arrives: ~13-57 units (pending additional foam orders)

---

## 🎯 RECOMMENDATIONS FOR STARBUCKS REPORT

**Be transparent about current situation:**

*"Dear Starbucks Team,*

*We currently have limited production capacity due to foam pattern component shortages. However, we have strong incoming material pipeline:*

**Confirmed Incoming:**
- *Frame assemblies: 140 EA arriving Feb 3*
- *Leather, cartons, base foams: In stock*

**Production Timeline:**
- *Foam patterns: Ordered Feb 2, estimated arrival Feb 17*
- *Projected capacity Feb 20+: 13-57 units initially*
- *Full production ramp: By end of February*

*We're working closely with our suppliers to expedite component delivery and will provide weekly updates on material availability and production capacity."*

---

## ✅ DASHBOARD STATUS

The live dashboard (`starbucks_capacity_dashboard_LIVE.html`) now:
- ✅ Queries real Epicor inventory (PartWhses)
- ✅ Queries real Epicor POs (MRP_POs BAQ)
- ✅ Calculates current vs. future capacity
- ✅ Shows PO details (number, quantity, date, vendor)
- ✅ Updates on demand via Refresh button

**Ready for production use!**

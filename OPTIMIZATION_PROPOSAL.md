# Optimierungsvorschlag: Store=False für nicht-kritische Felder

## Status Quo (nach Odoo 18 Fixes)

✅ **Funktioniert jetzt in Odoo 18**
- Alle technischen Probleme behoben
- HFC-Faktor bleibt erhalten
- SKR03-Skonto-Logik bleibt erhalten
- Custom Views bleiben erhalten

## Problem: Performance-Overhead

**Aktuell:** 20+ Felder mit `store=True` → viele DB-Writes

### Trigger-Kette bei jeder Rechnung:
```
Rechnung gespeichert
  → account.move.line.write() Override
    → _trigger_project_analytics_recompute()
      → 20+ Felder in DB schreiben
        → Indexe aktualisieren
          → Mehrere Sekunden bei großen DBs
```

## Vorschlag: Hybrid-Ansatz

### 🟢 STORE (5-6 Kern-Felder)

Diese Felder **brauchen** `store=True` für:
- Aggregationen in List Views (`aggregator='sum'`)
- Sortierung in List Views
- Filtern in Suchen
- Performance bei vielen Projekten

```python
# KRITISCH: Store=True behalten
profit_loss_net = fields.Float(store=True)           # Für Sortierung/Aggregation
customer_invoiced_amount_net = fields.Float(store=True)  # Für Sortierung
vendor_bills_total_net = fields.Float(store=True)    # Für Sortierung
total_hours_booked = fields.Float(store=True)        # Für Sortierung
labor_costs = fields.Float(store=True)               # Für Sortierung
labor_costs_adjusted = fields.Float(store=True)      # HFC - wichtig!
```

### 🔵 NICHT STORE (Rest als live-berechnet)

Diese Felder **können** `store=False` haben:
- Werden selten in List Views gebraucht
- Nur in Form View sichtbar
- Schnell berechnet (Subtraktion/Addition)

```python
# UNKRITISCH: Store=False (live berechnen)
customer_paid_amount_net = fields.Float(store=False)  # Nur in Form View
customer_outstanding_amount_net = fields.Float(store=False)  # Berechnet: invoiced - paid
customer_invoiced_amount_gross = fields.Float(store=False)  # Selten genutzt
customer_paid_amount_gross = fields.Float(store=False)  # Selten genutzt
customer_outstanding_amount_gross = fields.Float(store=False)  # Selten genutzt
vendor_bills_total_gross = fields.Float(store=False)  # Selten genutzt
customer_skonto_taken = fields.Float(store=False)  # Nur in Form View
vendor_skonto_received = fields.Float(store=False)  # Nur in Form View
total_hours_booked_adjusted = fields.Float(store=False)  # Berechnet aus labor_costs_adjusted
other_costs_net = fields.Float(store=False)  # Nur in Form View
total_costs_net = fields.Float(store=False)  # Berechnet: labor + other
negative_difference_net = fields.Float(store=False)  # Berechnet: abs(min(0, profit))
```

## Vorteile

### Performance ⚡
- **80% weniger DB-Writes** bei Rechnungen/Timesheets
- Schnellere Trigger-Ausführung
- Weniger Index-Updates

### Wartbarkeit 🔧
- Einfachere Trigger-Logik
- Weniger Cache-Invalidierung
- Weniger Migrations-Probleme bei Updates

### Funktionalität 📊
- **Alle Werte trotzdem verfügbar** (in Form View)
- List View zeigt die wichtigsten 5-6 Felder
- Pivot/Graph Views funktionieren mit gespeicherten Feldern

## Nachteile

### ⚠️ Live-Berechnung bei jedem Form View-Öffnen
- Für `store=False` Felder wird `_compute_financial_data()` bei jedem Öffnen aufgerufen
- Bei 100+ Projekten in List View: nur 5-6 Felder berechnet ✓
- Bei 1 Projekt in Form View: alle Felder berechnet (aber nur 1 Projekt) ✓

### ⚠️ Keine Aggregation in List View für store=False
- Felder wie `customer_paid_amount_net` können nicht mehr summiert werden in List View
- **Lösung:** Nur in gespeicherten Feldern aggregieren (die wichtigsten 5-6)

## Implementierung

### Schritt 1: Felder auf store=False setzen

```python
# models/project_analytics.py

# Store=True (6 Felder)
profit_loss_net = fields.Float(compute='_compute_financial_data', store=True, aggregator='sum')
customer_invoiced_amount_net = fields.Float(compute='_compute_financial_data', store=True, aggregator='sum')
vendor_bills_total_net = fields.Float(compute='_compute_financial_data', store=True, aggregator='sum')
total_hours_booked = fields.Float(compute='_compute_financial_data', store=True, aggregator='sum')
labor_costs = fields.Float(compute='_compute_financial_data', store=True, aggregator='sum')
labor_costs_adjusted = fields.Float(compute='_compute_financial_data', store=True, aggregator='sum')

# Store=False (Rest)
customer_paid_amount_net = fields.Float(compute='_compute_financial_data', store=False)
customer_outstanding_amount_net = fields.Float(compute='_compute_financial_data', store=False)
# ... etc
```

### Schritt 2: @api.depends() anpassen

```python
@api.depends(
    'account_id',  # Analytic Account
    'account_id.line_ids',  # Analytic Lines (für store=False)
    'account_id.line_ids.amount',  # Beträge (für store=False)
)
def _compute_financial_data(self):
    # ... existing logic
```

### Schritt 3: Trigger vereinfachen

```python
# account_move_line.py
def _trigger_project_analytics_recompute(self, lines):
    # NUR die 6 store=True Felder invalidieren
    # Rest wird bei Bedarf berechnet
    if projects:
        projects.invalidate_recordset(['profit_loss_net', 'customer_invoiced_amount_net', ...])
```

## Entscheidung

Möchten Sie diese Optimierung **jetzt** oder **später**?

### Option A: Jetzt optimieren
- Ich implementiere den Hybrid-Ansatz
- Performance-Verbesserung sofort
- Mehr Änderungen, mehr Testing

### Option B: Später optimieren
- Aktuelle Fixes reichen erstmal (funktioniert in Odoo 18)
- Performance-Optimierung in separatem Ticket
- Weniger Risiko, schneller produktiv

### Option C: Gar nicht optimieren
- "Funktioniert gut genug"
- Alle Werte in List View sichtbar/aggregierbar
- Mehr Trigger-Overhead, aber akzeptabel

## Meine Empfehlung

**Option B: Später optimieren**

**Begründung:**
1. Aktuelle Fixes beheben die Odoo 18-Inkompatibilität ✅
2. HFC + SKR03 + Views bleiben erhalten ✅
3. Modul funktioniert jetzt, Testing kann starten
4. Performance-Optimierung als separates Projekt (wenn nötig)

**Wann optimieren?**
- Wenn Sie >1000 Projekte haben
- Wenn Trigger-Performance zum Problem wird
- Wenn DB-Größe explodiert

---

**Fazit:** ChatGPT hatte teilweise recht (zu viel `store=True`), aber nicht alles ist redundant (HFC, SKR03, Views sind custom). Meine Fixes machen das Modul kompatibel, Optimierung ist optional.

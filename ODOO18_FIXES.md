# Odoo 18 Compatibility Fixes

## Zusammenfassung

Dieses Modul wurde für Odoo 18 aktualisiert, um Kompatibilitätsprobleme mit der neuen Analytic-Architektur zu beheben.

## Hauptprobleme in Odoo 18

### 1. ❌ Feld `analytic_account_id` wurde entfernt

**Problem:**
- In Odoo 18 wurde das Feld `analytic_account_id` von `project.project` entfernt
- Stattdessen gibt es jetzt ein **Analytic Notebook** mit mehreren Analytic Accounts (einen pro Plan)
- Projekte verwenden jetzt nur noch `account_id` für ihren primären Analytic Account

**Symptom:**
- Code in Zeile 272-273 (`project.analytic_account_id`) gab immer `False` zurück
- Projekten wurde kein Analytic Account zugeordnet → alle Werte blieben 0

**Lösung:**
- Alle Referenzen zu `analytic_account_id` entfernt
- Nur noch `account_id` wird verwendet
- Code in 3 Dateien aktualisiert:
  - `models/project_analytics.py`
  - `models/account_move_line.py`
  - `models/account_analytic_line.py`

### 2. ⚠️ External ID `analytic.analytic_plan_projects` könnte fehlen

**Problem:**
- Der Code verließ sich auf die External ID `analytic.analytic_plan_projects`
- Wenn diese nicht existiert, scheiterte die gesamte Berechnung

**Symptom:**
- "Project plan not found" Fehler
- Keine Berechnungen möglich

**Lösung:**
- **Robustes Fallback-System:**
  1. Versuche External ID `analytic.analytic_plan_projects` zu laden
  2. Falls nicht gefunden: Suche nach Plan mit "project" im Namen
  3. Falls kein Plan gefunden: Verwende Analytic Account ohne Plan-Verifikation
- Besseres Logging für Debugging

### 3. 🔧 Leeres `@api.depends()` war problematisch

**Problem:**
- `@api.depends()` ohne Parameter bedeutet: Compute-Methode wird NIE automatisch getriggert
- Das Modul verließ sich komplett auf manuelle Trigger in Override-Methoden
- Wenn Änderungen an Daten vorbeigehen (z.B. Wizard-Buchungen, Imports), bleiben Felder veraltet

**Lösung:**
- **Hybrid-Ansatz implementiert:**
  - `@api.depends('account_id')` hinzugefügt → Neuberechnung wenn Analytic Account ändert
  - Trigger in `account.move.line` und `account.analytic.line` bleiben aktiv
  - Manueller Refresh-Wizard bleibt verfügbar
- Bessere Dokumentation der Trigger-Strategie

### 4. 📊 analytic_distribution Struktur in v18

**Problem:**
- In Odoo 18 ist `analytic_distribution` ein JSON-Feld mit Multi-Plan-Support
- Die Struktur: `{"<account_id>": <percentage>, ...}`
- Mehrere Analytic Plans möglich (nicht nur Projects)

**Lösung:**
- Code bereits kompatibel (JSON-Parsing war bereits implementiert)
- Filter auf Project Plan wird korrekt angewandt
- Prozentuale Verteilung wird berücksichtigt

## Verwendung des Diagnose-Scripts

Um Ihre Odoo 18 Installation zu überprüfen:

```bash
# Starten Sie Odoo Shell
odoo-bin shell -d ihre_datenbank --config=/pfad/zu/odoo.conf

# Führen Sie das Diagnose-Script aus
exec(open('/pfad/zu/projekt-statistik-v3/tools/diagnose_odoo18_analytics.py').read())
```

Das Script überprüft:
- ✓ Verfügbare Analytic Plans
- ✓ External ID `analytic.analytic_plan_projects`
- ✓ Vorhandene Felder auf `project.project`
- ✓ Beispiel-Projekt Konfiguration
- ✓ `analytic_distribution` Struktur

## Was funktioniert jetzt?

✅ **Projekt-Analytic-Account Zuordnung**
- Verwendet `account_id` (nicht mehr `analytic_account_id`)
- Robustes Fallback-System für External IDs
- Funktioniert auch ohne perfekte Plan-Konfiguration

✅ **Automatische Neuberechnung**
- Bei Änderung des Projekt-Analytic-Accounts
- Bei Erstellen/Ändern/Löschen von Rechnungen mit `analytic_distribution`
- Bei Erstellen/Ändern/Löschen von Timesheet-Einträgen

✅ **Rechnungen & Bills**
- Korrekte Verarbeitung von `analytic_distribution` (JSON)
- Unterstützung für prozentuale Verteilung
- Filter auf Projects Plan funktioniert

✅ **Skonto-Berechnung**
- SKR03-Konten werden korrekt ausgewertet
- Gewährte und erhaltene Skonti getrennt

## Empfehlungen für langfristige Verbesserungen

Wie in der ursprünglichen Analyse beschrieben, gibt es drei Ansätze:

### Option A: Aktueller Ansatz (IMPLEMENTIERT)
- ✅ Alle kritischen Bugs behoben
- ✅ Funktioniert in Odoo 18
- ⚠️ Viele gespeicherte Felder (`store=True`)
- ⚠️ Weiterhin Abhängigkeit von Triggern

### Option B: Abgespeckte Version (EMPFOHLEN für Zukunft)
- Nur wenige Kern-Felder als `store=True`:
  - `profit_loss_net`
  - `customer_invoiced_amount_net`
  - `vendor_bills_total_net`
  - `total_hours_booked`
  - `labor_costs`
- Rest als `store=False` (live berechnet)
- Weniger Komplexität, bessere Performance
- Weniger Wartungsaufwand

### Option C: Standard Odoo Reports (LANGFRISTIG)
- Für "normale" Projekt-Profitabilität reichen Standard-Odoo-Berichte
- **Analytic Reports** → Umsatz/Kosten pro Projekt
- **Project Profitability** → Standard-Auswertung
- **Timesheet Reports** → Personalkosten
- Nur eigenes Modul für SKR03-spezifische Logik (Skonto, HFC-Faktoren, etc.)

## Was wurde geändert?

### Geänderte Dateien

1. **`models/project_analytics.py`**
   - Zeile 217: `@api.depends('account_id')` statt `@api.depends()`
   - Zeile 266-303: Robustes Analytic Account Lookup (ohne `analytic_account_id`)
   - Zeile 767-778: `action_view_account_analytic_line()` verwendet nur `account_id`

2. **`models/account_move_line.py`**
   - Zeile 113-116: Project Lookup nur mit `account_id` (kein `analytic_account_id`)

3. **`models/account_analytic_line.py`**
   - Zeile 95-98: Project Lookup nur mit `account_id` (kein `analytic_account_id`)

4. **`tools/diagnose_odoo18_analytics.py`** (NEU)
   - Diagnose-Script für Odoo 18 Setup-Überprüfung

## Quellen & Referenzen

- [Analytic Accounting In Odoo 18 Accounting Module](https://www.cybrosys.com/blog/analytic-accounting-in-odoo-18-accounting-module)
- [Master Odoo Accounting in Odoo 18](https://www.moonsun.au/blog/moonsun-mag-1/how-to-master-odoo-accounting-in-odoo-18-a-comprehensive-guide-25)
- [From Budgetary Positions to Analytic Plans: Upgrading Odoo 17 to 18](https://www.rocketsystems.com.au/blog/our-blog-1/from-budgetary-positions-to-analytic-plans-upgrading-odoo-17-to-18-8)
- [Odoo Forum: What happened to analytic_account_id in v17/v18?](https://www.odoo.com/forum/help-1/what-happened-to-analytic-account-id-on-sales-order-in-v17-v18-271002)
- [Odoo Forum: Odoo v18 analytic items analytic distribution](https://www.odoo.com/forum/help-1/odoo-v18-analytic-items-analytic-distribution-280325)

## Testing

Nach der Installation sollten Sie:

1. **Diagnose-Script ausführen** (siehe oben)
2. **Testprojekt erstellen** mit Analytic Account
3. **Testrechnung buchen** mit `analytic_distribution` auf das Projekt
4. **Timesheet-Eintrag erstellen** für das Projekt
5. **Projekt-Analytics öffnen** → Alle Werte sollten korrekt sein
6. **"Refresh Financial Data" Wizard** testen

## Support

Bei Problemen:
1. Odoo Logs prüfen (`/var/log/odoo/odoo.log`)
2. Diagnose-Script ausführen
3. Debug-Modus aktivieren (URL: `?debug=1`)
4. Developer Mode aktivieren → Technical → Database Structure → Models → `project.project` → Fields prüfen

---

**Version:** 18.0.1.0.10
**Datum:** 2025-12-04
**Autor:** Alex Feld

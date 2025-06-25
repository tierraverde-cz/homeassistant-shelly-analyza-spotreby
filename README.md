# analyzuj_homeassistant_wattmeter_csv.py

## 📊 Analýza spotřeby energie z chytrého wattmetru Shelly 3EM nebo jiného 1F wattmetru

Tento skript umožňuje analyzovat elektrickou spotřebu **třífázového nebo jednofázového zařízení** (např. čerpadla) ze souboru CSV exportovaného z Home Assistanta. Testováno pro 3F elektroměr Shelly Pro 3EM a 1F elektroměr Solight.

Provádí výpočet energie na základě měřeného **okamžitého výkonu (W)** v čase pro:

* celkový výkon (`total_active_power`)
* jednotlivé fáze: `phase_a_active_power`, `phase_b_active_power`, `phase_c_active_power` pro 3F měřák

---

### ⚙️ Jak to funguje

Výpočet energie se provádí **diskrétní integrací metodou step hold**:

* Každý vzorek výkonu se považuje za konstantní až do následujícího vzorku.
* Energie se spočítá podle vzorce:

```text
E = výkon × čas = P × Δt  → převedeno na Wh = (P × Δt) / 3600
```

Tím je skript robustní i vůči:

* nepravidelnému vzorkování
* rozdílné frekvenci mezi `total` a jednotlivými fázemi
* redundantním záznamům

---

### 🧾 Vstupní data

Skript očekává CSV soubor s následující strukturou (3 sloupce):

```csv
entity_id,state,last_changed
sensor.shellypro3em_XXXX_total_active_power,8.953,2025-06-19T04:00:00.000Z
sensor.shellypro3em_XXXX_phase_a_active_power,1432.1,2025-06-19T04:00:01.000Z
...
```

* `state` je výkon ve **wattech \[W]**
* `last_changed` je časová značka v ISO 8601 formátu (UTC, končící `Z`)

---

### 🧰 Použití

#### ✅ Spuštění

```bash
python3 analyzuj_homeassistant_wattmeter_csv.py path/to/history.csv
```

nebo jen:

```bash
python3 analyzuj_homeassistant_wattmeter_csv.py
```

otevře GUI dialog pro výběr souboru

---

### 📦 Výstup

Skript vygeneruje 2 soubory do stejné složky jako skript:

#### 1. Textový přehled (`.txt`)

Obsahuje:

* název vstupního souboru
* časové rozmezí dat
* spotřebu energie celkem a na jednotlivých fázích (v kWh)

#### 2. Graf spotřeby (`.png`)

* Zobrazuje výkon v čase pro total a všechny fáze
* Styl křivky: **step** (přímo odpovídá způsobu výpočtu)

---

### 💻 Závislosti

* Python 3.8+
* `pandas`
* `matplotlib`
* `tkinter` *(je součástí standardní knihovny Pythonu na většině systémů)*

Instalace závislostí např.:

```bash
pip install pandas matplotlib
```

---

### 🧊 Pokročilé možnosti (nepovinné)

* Skript se dá přeložit pomocí `pyinstaller` do `.exe`:

```bash
pyinstaller --onefile analyzuj_homeassistant_wattmeter_csv.py
```

* Lze jej pak používat přetažením CSV souboru na ikonu.

---

### 🧠 Poznámky

* Výsledky jsou v **kWh** (1 kWh = 1000 Wh).
* Pokud poslední vzorek nemá následující čas, jeho příspěvek do energie se **ignoruje** (což je korektní pro integraci).
* Časy jsou zpracovány jako UTC; graf je v čase UTC (doporučeno pro unifikaci z Home Assistanta).

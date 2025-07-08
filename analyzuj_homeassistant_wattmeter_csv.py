import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import sys

# Volitelný dialog pro výběr CSV souboru
if len(sys.argv) < 2:
    import tkinter as tk
    from tkinter import filedialog
    default_dir = Path(sys.argv[0]).parent.resolve() if hasattr(sys, 'argv') and sys.argv[0] else Path.cwd()
    tk.Tk().withdraw()
    csv_path = filedialog.askopenfilename(
        filetypes=[("CSV files", "*.csv")],
        title="Vyber CSV soubor ze Shelly nebo Solight elektroměru",
        initialdir=default_dir
    )
    if not csv_path:
        print("Nebyl vybrán žádný soubor.")
        sys.exit(1)
else:
    csv_path = sys.argv[1]

input_csv = Path(csv_path)
if not input_csv.exists():
    print(f"Soubor {input_csv} neexistuje.")
    sys.exit(1)

# === Načtení a korekce sloupců ===
df = pd.read_csv(input_csv)

# Normalizace názvů sloupců (bez ohledu na pořadí)
df.columns = [col.strip().lower() for col in df.columns]
expected_cols = set(['entity_id', 'state', 'last_changed'])
if set(df.columns) != expected_cols:
    raise ValueError(f"Neočekávané sloupce v CSV: {df.columns}")

# Uspořádání sloupců podle očekávání
df = df[['entity_id', 'state', 'last_changed']]

# Konverze typů
df['last_changed'] = pd.to_datetime(df['last_changed'])
# Nejprve načti 'state' jako string, abychom mohli manipulovat s čárkou
df['state'] = df['state'].astype(str).str.replace(',', '.', regex=False)
# Až poté převedeme na čísla
df['state'] = pd.to_numeric(df['state'], errors='coerce')
df = df.dropna(subset=['state']).sort_values('last_changed')

# === Detekce typu zařízení ===
valid_suffixes = ["_power", "_napajeni"]  # jen měření výkonu, ignorujeme napětí, proudy atd.

# Filtrovat na řádky s relevantním suffixem
df = df[df['entity_id'].apply(lambda eid: any(eid.endswith(suf) for suf in valid_suffixes))]

# Detekovat dostupné entity
unique_entities = sorted(df['entity_id'].unique())

print("Detekce více entit...")
if len(unique_entities) > 1:
    print("Načteno více entit. Vyber jednu pro analýzu:\n")
    for idx, eid in enumerate(unique_entities, start=1):
        print(f"{idx}. {eid}")

    while True:
        try:
            choice = int(input(f"\nZadej číslo (1-{len(unique_entities)}): "))
            if 1 <= choice <= len(unique_entities):
                selected_entity = unique_entities[choice - 1]
                break
            else:
                print("Zadané číslo je mimo rozsah.")
        except ValueError:
            print("Zadej prosím platné číslo.")
else:
    selected_entity = unique_entities[0]

print(f"\nVybraná entita: {selected_entity}")
df = df[df['entity_id'] == selected_entity]

# === Detekce 3F / 1F automaticky ===
is_three_phase = any(suf in selected_entity for suf in ["phase_a_active_power", "phase_b_active_power", "phase_c_active_power"])
is_singlephase = not is_three_phase


# === Výpočet energie ===
def calculate_energy(sensor_df: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    sensor_df = sensor_df.sort_values('last_changed')
    sensor_df['next_time'] = sensor_df['last_changed'].shift(-1)
    sensor_df['duration_s'] = (sensor_df['next_time'] - sensor_df['last_changed']).dt.total_seconds()
    sensor_df = sensor_df[sensor_df['duration_s'].notna()]
    sensor_df['energy_wh'] = (sensor_df['state'] * sensor_df['duration_s']) / 3600
    total_kwh = sensor_df['energy_wh'].sum() / 1000
    return sensor_df, total_kwh

# === Výpočet pro 1F elektroměr Solight nebo 3F elektroměr Shelly ===
if is_singlephase: # 1F elektroměr
    total_df, total_kwh = calculate_energy(df)
    start_time = total_df['last_changed'].iloc[0]
    end_time = total_df['last_changed'].iloc[-1]
else: # 3F elektroměr
    total_df, total_kwh = calculate_energy(df[df['entity_id'].str.endswith("total_active_power")])
    phase_a_df, phase_a_kwh = calculate_energy(df[df['entity_id'].str.endswith("phase_a_active_power")])
    phase_b_df, phase_b_kwh = calculate_energy(df[df['entity_id'].str.endswith("phase_b_active_power")])
    phase_c_df, phase_c_kwh = calculate_energy(df[df['entity_id'].str.endswith("phase_c_active_power")])
    start_time = total_df['last_changed'].iloc[0]
    end_time = total_df['last_changed'].iloc[-1]

# === Výstupní soubory
timestamp_now = datetime.now().isoformat(timespec="seconds").replace(":", "-")
start_str = start_time.isoformat().replace(":", "-")
end_str = end_time.isoformat().replace(":", "-")
output_stem = f"{timestamp_now}__{start_str}_to_{end_str}"

output_dir = Path(sys.argv[0]).parent
output_txt = output_dir / f"{output_stem}.txt"
output_png = output_dir / f"{output_stem}.png"

# === Výstup do textového souboru
with open(output_txt, "w", encoding="utf-8") as f:
    f.write(f"Soubor: {input_csv.name}\n")
    f.write(f"Začátek dat: {start_time.isoformat()}\n")
    f.write(f"Konec dat:   {end_time.isoformat()}\n\n")
    f.write(f"Spotřeba total: {total_kwh:.3f} kWh\n")
    if not is_singlephase:
        f.write(f"Spotřeba fáze A: {phase_a_kwh:.3f} kWh\n")
        f.write(f"Spotřeba fáze B: {phase_b_kwh:.3f} kWh\n")
        f.write(f"Spotřeba fáze C: {phase_c_kwh:.3f} kWh\n")

# === Graf
plt.figure(figsize=(12, 5))
plt.step(total_df['last_changed'], total_df['state'], where='post', label='Total [W]', linewidth=1.5)
if not is_singlephase:
    if not phase_a_df.empty:
        plt.step(phase_a_df['last_changed'], phase_a_df['state'], where='post', label='Fáze A [W]', alpha=0.6)
    if not phase_b_df.empty:
        plt.step(phase_b_df['last_changed'], phase_b_df['state'], where='post', label='Fáze B [W]', alpha=0.6)
    if not phase_c_df.empty:
        plt.step(phase_c_df['last_changed'], phase_c_df['state'], where='post', label='Fáze C [W]', alpha=0.6)

plt.xlabel("Čas (UTC)")
plt.ylabel("Výkon [W]")
plt.title("Spotřeba na 1F elektroměru" if is_singlephase else "Spotřeba na 3F elektroměru")
plt.legend()
plt.grid(True)
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(output_png)

# === Volitelné zobrazení
try:
    plt.show()
except:
    pass

print(f"Hotovo.\nTXT: {output_txt.name}\nPNG: {output_png.name}")

# Unit Conventions

ecproc uses consistent SI-based unit conventions throughout the Faraday IR. Input files may use common electrochemistry units which are automatically normalized during IR generation.

## Input Units (ECDL / YAML)

These units are accepted in `.ecproc` files and parsed automatically:

| Quantity | Accepted Input | Example |
|----------|---------------|---------|
| Potential | V, mV | `1.2 V`, `50 mV` |
| Current | A, mA, µA | `200 mA` |
| Scan rate | V/s, mV/s | `50 mV/s` |
| Time | s, min, h | `300 s`, `24 h` |
| Frequency | Hz, kHz, MHz | `100 kHz` |
| Area | cm², m² | `0.196 cm²` |
| Concentration | M, mM | `0.1 M` |
| Temperature | C, °C | `25 C` |
| Rotation | rpm | `1600 rpm` |
| Loading | µg/cm², mg/cm² | `20 µg/cm²` |

## Faraday IR (Normalized)

All values in the intermediate representation use SI base units:

| Quantity | IR Unit | Conversion |
|----------|---------|------------|
| Potential | V | — |
| Scan rate | V/s | mV/s → V/s (÷1000) |
| Current | A | mA → A (÷1000) |
| Area | m² | cm² → m² (÷10000) |
| Concentration | mol/m³ | M → mol/m³ (×1000) |
| Time | s | min → s (×60), h → s (×3600) |
| Frequency | Hz | kHz → Hz (×1000) |
| Temperature | K | °C → K (+273.15) |

## Examples

### Scan Rate

```
Input:  rate: 50 mV/s
IR:     scan_rate_V_s: 0.05
```

### Current

```
Input:  max_current: 200 mA
IR:     max_current_A: 0.2
```

### Electrode Area

```
Input:  area_cm2: 0.196
IR:     area_m2: 0.0000196
```

### Concentration

```
Input:  concentration_M: 0.1
IR:     concentration_mol_m3: 100.0
```

## Design Rationale

Normalizing to SI units in the IR ensures:

1. **Unambiguous calculations** — no unit confusion in downstream validation or execution
2. **Cross-target compatibility** — all targets consume the same normalized values
3. **Physics validation** — L2 electrochemistry rules operate on consistent units
4. **Reproducibility** — the IR is a canonical, deterministic representation

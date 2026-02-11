---
title: "Network Cables and Optics Reference"
category: web_content
tags: [cables, optics, sfp, qsfp, fiber, dac, transceiver]
---

# Network Cables and Optics Reference

## 1. Cable Types

### 1.1 Direct Attach Copper (DAC)
- **Passive DAC**: Up to 5m (25G), 3m (100G), 2m (400G)
- **Active DAC**: Up to 10m (signal conditioning built-in)
- **Advantages**: Low cost, low latency, low power
- **Disadvantages**: Short reach, heavy, heat

### 1.2 Active Optical Cable (AOC)
- Optical fiber with integrated transceivers
- Reach: 10-100m typically
- Lighter than DAC, longer reach
- Not field-terminable

### 1.3 Fiber Optic (Structured Cabling)
- Separable transceiver + fiber patch cord
- **MMF (Multi-Mode Fiber)**: Short reach (up to 300m OM4)
- **SMF (Single-Mode Fiber)**: Long reach (up to 80km+)

## 2. Transceiver Form Factors

| Form Factor | Lanes | Max Speed | Introduced |
|------------|-------|-----------|------------|
| SFP | 1 | 1G | ~2000 |
| SFP+ | 1 | 10G | ~2006 |
| SFP28 | 1 | 25G | ~2014 |
| SFP56 | 1 | 50G | ~2018 |
| SFP112 | 1 | 100G | ~2022 |
| QSFP+ | 4 | 40G (4×10G) | ~2009 |
| QSFP28 | 4 | 100G (4×25G) | ~2014 |
| QSFP56 | 4 | 200G (4×50G) | ~2018 |
| QSFP-DD | 8 | 400G (8×50G) | ~2019 |
| OSFP | 8 | 800G (8×100G) | ~2020 |

## 3. Speed and Lane Configuration

| Speed | Common Form Factor | Lanes × Lane Rate |
|-------|-------------------|-------------------|
| 10G | SFP+ | 1 × 10G |
| 25G | SFP28 | 1 × 25G |
| 40G | QSFP+ | 4 × 10G |
| 50G | SFP56 or QSFP28(2x) | 1 × 50G |
| 100G | QSFP28 | 4 × 25G |
| 200G | QSFP56 | 4 × 50G (PAM4) |
| 400G | QSFP-DD or OSFP | 8 × 50G or 4 × 100G |
| 800G | OSFP | 8 × 100G (PAM4) |

## 4. Fiber Types

### 4.1 Multi-Mode Fiber (MMF)

| Type | Core | Bandwidth | Max 100G Reach | Color |
|------|------|-----------|---------------|-------|
| OM1 | 62.5μm | 200 MHz·km | Not used | Orange |
| OM2 | 50μm | 500 MHz·km | Not used | Orange |
| OM3 | 50μm | 2000 MHz·km | 70m (SR4) | Aqua |
| OM4 | 50μm | 4700 MHz·km | 100m (SR4) | Aqua |
| OM5 | 50μm | 4700 MHz·km | 100m+ | Lime green |

### 4.2 Single-Mode Fiber (SMF)
- Core: 9μm
- Wavelengths: 1310nm (LR), 1550nm (ER)
- Reach: 10km (LR), 40km (ER), 80km (ZR)
- Color: Yellow jacket

## 5. Connector Types

| Connector | Fibers | Use |
|-----------|--------|-----|
| LC | 2 (duplex) | SFP, SFP+, SFP28 |
| MPO-12 | 12 | QSFP+ (40G), QSFP28 breakout |
| MPO-16 | 16 | QSFP-DD (400G SR8) |
| CS | 2 | Compact SFP-DD |
| SC | 2 | Legacy, patch panels |

## 6. Breakout Cables

```
100G QSFP28 → 4 × 25G SFP28
200G QSFP56 → 4 × 50G SFP56 (or 2 × 100G QSFP28)
400G QSFP-DD → 4 × 100G QSFP28 (or 8 × 50G SFP56)
800G OSFP → 2 × 400G QSFP-DD (or 4 × 200G)
```

## 7. InfiniBand Cables

| IB Rate | Cable Type | Connector |
|---------|-----------|-----------|
| EDR (100G) | QSFP28 DAC/AOC | QSFP28 |
| HDR (200G) | QSFP56 DAC/AOC | QSFP56 |
| HDR100 (100G/port) | QSFP56 split | QSFP56→2×QSFP56 |
| NDR (400G) | OSFP/QSFP-DD | OSFP |
| NDR200 (200G/port) | OSFP split | OSFP→2×QSFP-DD |
| XDR (800G) | OSFP | OSFP |

## 8. FEC (Forward Error Correction)

| FEC Type | Overhead | Latency | Used With |
|----------|----------|---------|-----------|
| None (No FEC) | 0% | 0 | 10G, clean links |
| FC-FEC (Firecode) | ~3% | ~50ns | 25G |
| RS-FEC (Reed-Solomon) | ~3% | ~100ns | 50G+, PAM4 |

```bash
# Check FEC status
ethtool --show-fec eth0

# Set FEC mode
ethtool --set-fec eth0 encoding rs

# FEC corrected/uncorrected errors (key for cable health)
ethtool -S eth0 | grep fec
```

## 9. Troubleshooting Cable/Optics Issues

### 9.1 Symptoms and Causes

| Symptom | Likely Cause |
|---------|-------------|
| Link down | Bad cable, dirty connector, wrong cable type |
| Link flapping | Marginal cable, EMI, bend radius violation |
| FEC uncorrectable errors | Bad cable/optic, exceeds reach |
| CRC errors | Cable quality, connector dirty |
| Speed lower than expected | Wrong cable, auto-negotiation issue |

### 9.2 Diagnostic Commands
```bash
# Check link status
ethtool eth0
ip link show eth0

# Transceiver info
ethtool --module-info eth0
# Shows: temperature, voltage, TX/RX power (dBm)

# For InfiniBand
ibstat
ibdiagnet --cable_info

# FEC error rates
ethtool -S eth0 | grep -E "fec|phy"

# NVIDIA cable diagnostics
mlxcables  # List all cables and their info
mlxlink -d mlx5_0 -p 1  # Detailed port diagnostics
mlxlink -d mlx5_0 -p 1 --cable  # Cable info
mlxlink -d mlx5_0 -p 1 --show_fec  # FEC details
```

### 9.3 Cleaning and Inspection
- Use IPA (Isopropyl Alcohol) fiber wipes for connectors
- Inspect with fiber scope before inserting
- Never touch ferrule end-faces
- Keep dust caps on unused ports
- Check bend radius (minimum varies by cable type)

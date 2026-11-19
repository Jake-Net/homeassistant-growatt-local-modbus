# jake-net customisations — Home Assistant Growatt Local Modbus

> **Status:** rebased onto upstream **v0.3.1** on branch `master` (fork version
> **`0.3.1-jakenet1`**, release `v0.3.1-jakenet1`, 2026-11-19). Branch
> `jake-net-mods` keeps the original v0.2.1-based history. See
> `MERGE-NOTES-v0.3.1.md` for how the merge was reconciled.

Record of the local modifications made to the `growatt_local` custom component on
this Home Assistant installation, kept in a git repo with the upstream project as
its ancestry so future upstream updates can be merged rather than re-patched.

## Provenance

| Item | Value |
|---|---|
| Upstream | `WouterTuinstra/Homeassistant-Growatt-Local-Modbus` |
| Base tag | `v0.2.1` (commit this branch is built on) |
| Installed `manifest.json` version | `0.2.1` |
| Upstream latest at capture | `v0.3.1` (released 2026-11-09) |
| Capture date | 2026-11-19 |
| Branch | `jake-net-mods` |
| Tag | `jake-net-v0.2.1-mods` |
| Device | Growatt SPF off-grid inverter ("Big Barn") |

The installed `manifest.json` still reports `0.2.1`, which matches the base tag —
the customisations were applied on top of `v0.2.1` and the version was never
bumped, so Home Assistant (and HACS) see it as `0.2.1` and offer the `v0.3.1`
update. **That is why the update cannot be installed: it would overwrite every
change below.**

## Why these changes

Upstream `v0.2.1` does not expose writable control for an SPF off-grid inverter:
no output-source-priority control, no writable charge-current numbers, and no
on/off switch for AC (grid) charging. This fork adds those so the SPF can be
driven from Home Assistant (nightly `UTI` transfer plus AC-charge enable, SBU by
day, and manual control from the dashboard).

## Change summary (vs `v0.2.1`)

`11 files changed, 346 insertions(+), 8 deletions(-)`

| File | Change |
|---|---|
| `API/device_type/base.py` | New attribute names: `ATTR_MAX_CHARGE_CURRENT` (reg 34), `ATTR_AC_CHARGE_CURRENT` (reg 38), `ATTR_OUTPUT_SOURCE_PRIORITY` (reg 1); whitespace tidy. |
| `API/device_type/inverter_315.py` | Added the three writable holding registers to the inverter register map (reg 1 output source priority, reg 34 max charge current, reg 38 AC charge current). |
| `__init__.py` | `write_register()` now logs the key and resolved register at WARNING and returns early if the register is missing (was a DEBUG TODO). |
| `const.py` | Added `Platform.SELECT` to `PLATFORMS`. |
| `number.py` | Added `INVERTER_MAX_CHARGE_CURRENT` and `INVERTER_AC_CHARGE_CURRENT` number entities; WARNING log in `async_set_native_value`. |
| `sensor_types/inverter.py` | Defined the `INVERTER_MAX_CHARGE_CURRENT` (0–180 A) and `INVERTER_AC_CHARGE_CURRENT` (0–80 A) number descriptions. |
| `switch.py` | Added off-grid switch support (`OFFGRID_SWITCH_TYPES` for SPF) and a custom `GrowattOffgridACChargeSwitch` that toggles AC charging by driving register 38 (on = restore stored current, off = 0). |
| `select.py` | **New file.** Select platform; for SPF off-grid devices exposes `select.big_barn_growatt_output_source_priority` (SBU / SOL / UTI / SUB), writing `ATTR_OUTPUT_SOURCE_PRIORITY`. |
| `sensor_types/offgrid_select.py` | **New file.** `OFFGRID_SELECT_TYPES` describing the output-source-priority select and its option↔value maps. |
| `sensor_types/offgrid_switch.py` | **New file.** `OFFGRID_SWITCH_TYPES` describing a generic AC Charge Enable switch bound to register 38. |
| `sensor_types/select_entity_description.py` | **New file.** `GrowattSelectEntityDescription` with `option_to_value` / `value_to_option` maps. |

### Entities this produces on the SPF

- `select.big_barn_growatt_output_source_priority` — UTI/SBU/SOL/SUB.
- `number.big_barn_growatt_max_charge_current` — reg 34.
- `number.big_barn_growatt_ac_charge_current` — reg 38.
- `switch.big_barn_growatt_ac_charge_enable` — custom switch over register 38.
- `switch.big_barn_growatt_ac_charge_enable_2` — the generic register-38 switch
  created by `OFFGRID_SWITCH_TYPES` (see issue below).

## Evaluation / known issues

1. **Duplicate AC-charge switch — removed (0.3.1-jakenet2).** Upstream previously
   had both the custom `GrowattOffgridACChargeSwitch` and a generic switch from
   `OFFGRID_SWITCH_TYPES` bound to register 38, so Home Assistant showed
   `…_ac_charge_enable` and `…_ac_charge_enable_2`. The generic one wrote
   `state_on = 1` (1 A) on `turn_on`, which silently under-charged the nightly
   window. `offgrid_switch.py` and its use in `switch.py` are now deleted; only
   the custom switch (restores the stored current) is created.
2. **Debug logging left at WARNING.** `__init__.py::write_register`,
   `number.py::async_set_native_value` and the switch log at WARNING level, which
   is very noisy in the log. Should be `debug` (or removed) before any upstream PR.
3. **Range comment mismatch.** `base.py` comments register 38 as "range 0-100A"
   but `INVERTER_AC_CHARGE_CURRENT` sets `native_max_value = 80`. Pick one.
4. **Mid-file import.** `switch.py` imports `ATTR_AC_CHARGE_CURRENT` halfway down
   the file ("to avoid circular import"). Works, but a code smell — move the
   constant to a location that can be imported at top level.
5. **SPF output-source-priority value mapping.** The select maps
   `SBU=0, SOL=1, UTI=2, SUB=3`. Upstream convention elsewhere differs; confirm
   against the actual SPF register before extending.
6. No tests accompany the new entities.

## Diff artefacts

- `docs/jake-net-mods_vs_v0.2.1.diff` — this fork against the base tag.
- `docs/upstream_v0.2.1_to_v0.3.1.diff` — what upstream changed since the base.

## Reproducing this branch

```
git clone https://github.com/WouterTuinstra/Homeassistant-Growatt-Local-Modbus.git
cd Homeassistant-Growatt-Local-Modbus
git checkout -b jake-net-mods v0.2.1
# overlay custom_components/growatt_local/ from this repo
git commit
```

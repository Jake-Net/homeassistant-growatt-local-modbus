# Merging this fork with upstream v0.3.1

Evaluation of what upstream changed between the fork's base (`v0.2.1`) and the
current upstream release (`v0.3.1`, 2026-11-09), where it collides with the local
customisations, and how to reconcile them.

## What upstream changed (`v0.2.1` → `v0.3.1`)

`26 files changed, 1418 insertions(+), 89 deletions(-)` — this was a large
release. The material points:

- **New `SELECT` platform.** `select.py` (new, 156 lines) plus
  `sensor_types/select_entity_description.py` (new). It serves inverter meter
  selects and storage charge/discharge select entities. `const.py` gains
  `Platform.SELECT`.
- **New `TIME` platform.** `time.py` + `sensor_types/time_entity_description.py`
  (new). `const.py` gains `Platform.TIME`.
- **`switch.py` refactored** (107 lines): introduces `GrowattBaseSwitchEntity`
  and `GrowattSwitchEntity`, gates `STORAGE_SWITCH_TYPES` behind device type, and
  adds storage charge/discharge period switches.
- **`number.py` refactored** (65 lines): replaces the single fixed
  `INVERTER_OUTPUT_POWER_LIMIT` with list-driven, device-type-gated
  `INVERTER_NUMBER_TYPES` / `INVERTER_NUMBER_TYPES_W_METER` / `STORAGE_NUMBER_TYPES`.
- **`API/device_type/base.py`, `storage_120.py`, `inverter_120.py`,
  `API/growatt.py`, `API/utils.py`** changed substantially; new
  `API/pymodbus_ext.py` and `API/__init__.py`; new `CONF_METER_CONNECTED` in
  `config_flow.py`.
- **`sensor_types/offgrid.py`**: additive only — `state_class` added to existing
  sensors. **No conflict** with this fork (we did not touch it).
- **`manifest.json`** bumped to `0.3.1`.

Upstream `v0.3.1` still has **no SPF off-grid select/switch entities**: off-grid
support is limited to sensors (`sensor.py`, `OFFGRID_SENSOR_TYPES`) and the input
register map (`API/device_type/offgrid.py`). So this fork's value — writable
output-source-priority, charge-current numbers and the AC-charge switch — is not
superseded by the update.

## Conflict matrix

| File | Nature of clash | Resolution |
|---|---|---|
| `sensor_types/select_entity_description.py` | **Both define `GrowattSelectEntityDescription`** with different shapes. Ours uses `option_to_value` / `value_to_option`; upstream uses a `GrowattSelectRequiredKeysMixin` with `value_to_state_dict`. | Rename ours to `GrowattOffgridSelectEntityDescription`, **or** adapt our off-grid select to upstream's `value_to_state_dict` shape and delete our file. Prefer adapting to upstream's shape so there is one description class. |
| `select.py` | Both add the select platform. Ours branches to `OFFGRID_SPF`; upstream branches to meter + storage device types. | Merge into one `async_setup_entry`: keep upstream's meter/storage branches, add our `OFFGRID_SPF` branch and the `GrowattOffgridSelectEntity` class. Ensure the off-grid branch runs regardless of `CONF_INVERTER_POWER_CONTROL`. |
| `switch.py` | Upstream refactored the base class and gating; we added `OFFGRID_SWITCH_TYPES` + `GrowattOffgridACChargeSwitch`. | Re-apply our additions on top of upstream's `GrowattBaseSwitchEntity` / `GrowattSwitchEntity`. Make `GrowattOffgridACChargeSwitch` subclass the new base class. Consider dropping `OFFGRID_SWITCH_TYPES` (see MODIFICATIONS.md issue 1 — it duplicates the custom switch). |
| `number.py` | Upstream replaced explicit appends with list-driven, device-type-gated setup. We appended two descriptions. | Do **not** re-add the explicit appends. Add `INVERTER_MAX_CHARGE_CURRENT` and `INVERTER_AC_CHARGE_CURRENT` into upstream's `INVERTER_NUMBER_TYPES` list **and** ensure the `OFFGRID_SPF` path includes them (upstream's gate is `INVERTER / INVERTER_315 / INVERTER_120 / HYBRID…`, which excludes `OFFGRID_SPF`). |
| `sensor_types/inverter.py` | We define the two charge-current number descriptions; upstream restructured the same module into `INVERTER_NUMBER_TYPES`. | Add our two descriptions to upstream's list; keep the descriptions themselves. |
| `API/device_type/base.py` | Both add attribute constants. Upstream may have renamed/added constants in the same region. | Keep upstream's file and re-add only our three constants (`ATTR_MAX_CHARGE_CURRENT`, `ATTR_AC_CHARGE_CURRENT`, `ATTR_OUTPUT_SOURCE_PRIORITY`) if upstream lacks them. Verify no name collision. |
| `API/device_type/inverter_315.py` | We added three holding registers to the inverter map. Upstream changed this file too. | Re-apply the three `GrowattDeviceRegisters` entries (reg 1, 34, 38) into upstream's map. Confirm the register numbers against upstream's current map (avoid duplicates). |
| `const.py` | Ours adds `Platform.SELECT`; upstream adds `Platform.SELECT` **and** `Platform.TIME`. | Take upstream's line verbatim (it already includes SELECT). |
| `__init__.py` | Ours added WARNING-level logging + a `None` guard in `write_register`; upstream changed `__init__.py` elsewhere (device gating around line 238). | Re-apply just the `None` guard (keep it); drop the WARNING logging or downgrade to DEBUG (see MODIFICATIONS.md issue 2). |
| `manifest.json` | Version mismatch (`0.2.1` vs `0.3.1`). | Take upstream `0.3.1`, then bump to a fork-specific value (e.g. `0.3.1-jakenet1`) so HACS updates are trackable. |
| `sensor_types/offgrid.py` | Additive only. | Take upstream; no action. |

## Recommended merge procedure

1. Work on a branch off the new upstream tag so ancestry stays correct:
   ```
   git fetch upstream --tags
   git checkout -b merge-v0.3.1 upstream/v0.3.1   # or the chosen release
   ```
2. Re-apply the mods **file by file** against the conflict matrix above. Prefer
   upstream's structure and adapt our additions into it rather than pasting the
   old code. `git checkout jake-net-mods -- <file>` is a useful starting point
   only for files upstream did not restructure (`offgrid_select.py`,
   `offgrid_switch.py`, `sensor_types/inverter.py` descriptions).
3. Resolve the `GrowattSelectEntityDescription` clash **first** — it is the only
   true name collision.
4. Keep the **entity IDs stable**. The Home Assistant automations and dashboard
   reference these by `entity_id`:
   - `select.big_barn_growatt_output_source_priority`
   - `number.big_barn_growatt_ac_charge_current`
   - `number.big_barn_growatt_max_charge_current`
   - `switch.big_barn_growatt_ac_charge_enable`
   These derive from `unique_id = f"{DOMAIN}_{serial}_{key}"` and the
   `friendly_name`; do not rename the `key`s or the device name.
5. Update `manifest.json` version and, when ready, push to the `jake-net` fork.

## Post-merge verification checklist

- Component loads with no errors in the log before/after (new `SELECT`/`TIME`
  platforms plus our off-grid entities).
- The four entities above still exist with the same `entity_id`s and sensible
  states (`select` shows the current priority; `…ac_charge_current` reads the
  register; the AC-charge switch mirrors register 38 > 0).
- `write_register` for the select and the AC-charge switch still reaches the
  inverter (toggle the switch and confirm register 38 changes).
- The 06:00 / 23:00 automations still drive the switch (they now enable/disable
  the AC-charge window — see the change applied 2026-11-19).

## Notes

- `growatt_local` is a custom component, so a changed file requires a **Home
  Assistant restart**, not just a reload.
- Upstream moves quickly (v0.2.1 → v0.3.1 in the interval); re-check the latest
  release before starting the merge, since this evaluation is pinned to `v0.3.1`.

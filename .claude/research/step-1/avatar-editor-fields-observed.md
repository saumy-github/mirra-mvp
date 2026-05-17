# CLO Avatar Editor Fields Observed From UI Screenshots

Source:
- User-provided screenshots of the CLO `Avatar Editor` on the `Avatar Size` tab
- Same avatar shown once in `Millimeter` and once in `Centimeter`

## Main Takeaways

- The editable avatar-size fields shown in the UI are grouped under `Size` and `Shape`.
- The measurement unit dropdown can be switched between `Millimeter` and `Centimeter`.
- For our work, we should standardize all length, height, circumference, and width values in `cm`.
- The two screenshots confirm the unit conversion is direct:
  - `965.2 mm = 96.52 cm`
  - `1879.6 mm = 187.96 cm`
  - `409.6 mm = 40.96 cm`
- Not every visible control is a centimeter-based measurement.
  - Size-related numeric fields are shown as physical measurements.
  - Some shape controls are shown as percentages.

## UI Context Visible In The Screenshot

- Window: `Avatar Editor`
- Active tab: `Avatar Size`
- Other visible tabs:
  - `Measure`
  - `Arrangement`
  - `Fitting Suit`
  - `IK Joint`
- Size preset dropdown is set to `Custom`.
- Unit dropdown is shown as `Centimeter` in one screenshot and `Millimeter` in the other.

## Size Fields Visible In The UI

The top-level editable size controls visible are:

- `Width`
  - Selected field: `Chest`
  - Value: `96.52 cm`
- `Height`
  - Selected field: `Total Height`
  - Value: `187.96 cm`

### Circumference Fields

Visible fields and values:

- `Neck Base`: `40.96 cm`
- `Bicep`: `32.39 cm`
- `Waist`: `82.55 cm`
- `High Hip`: `88.26 cm`
- `Low Hip`: `95.25 cm`
- `Thigh`: `55.88 cm`

### Height Fields

Visible fields and values:

- `Inseam`: `86.36 cm`

### Length Fields

Visible fields and values:

- `Across Shoulder (Curvilinear)`: `44.13 cm`
- `Arm`: `64.85 cm`

## Shape Controls Visible In The UI

These are visible under the `Shape` section, but they are not all centimeter-based inputs.

### Hand & Head

- `Hand`: `20.00`
- `Head`: `56.00`

Note:
- The UI does not clearly show a `cm` suffix beside these two values in the screenshot.
- They may still be size-related controls, but we should not assume their import format until we confirm how CLO stores them.

### Crotch

- `Width`: `30%`
- `Volume`: `30%`

### Hip

- `Dips`: `50%`
- `Volume`: `50%`
- The `Volume` slider appears to range from `Flat` to `Curved`.

## Exact Field Labels We Can Reuse In Experiments

The screenshot gives us a useful set of exact CLO-visible labels to test against:

- `Chest`
- `Total Height`
- `Neck Base`
- `Bicep`
- `Waist`
- `High Hip`
- `Low Hip`
- `Thigh`
- `Inseam`
- `Across Shoulder (Curvilinear)`
- `Arm`
- `Hand`
- `Head`

## Practical Implications For Step-1

- We should store linear body-measurement values in `cm` on our side.
- The most promising first measurement-import candidates are the size fields with explicit length units:
  - `Chest`
  - `Total Height`
  - `Neck Base`
  - `Bicep`
  - `Waist`
  - `High Hip`
  - `Low Hip`
  - `Thigh`
  - `Inseam`
  - `Across Shoulder (Curvilinear)`
  - `Arm`
- Shape sliders should be treated separately from centimeter-based body measurements.
- `Chest` and `Total Height` look like the primary width/height drivers in this specific UI state.

## Open Questions

- Whether these visible UI labels match the exact field names required by the plugin measurement-import path.
- Whether `Hand` and `Head` should be treated as centimeter fields, unitless values, or a different avatar-property type.
- Whether the percentage-based shape controls can be imported through the same measurement mechanism as the centimeter-based size fields.

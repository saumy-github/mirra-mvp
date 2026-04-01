# Unconfirmed Measurement CSV Template

This CSV is a starter template for the isolated CLO-native avatar experiment.

File:
- `measurement_template_unconfirmed.csv`

Current status:
- `unconfirmed`

What this file is:
- a best-effort CSV template based on the current repo research
- useful for local experimentation and field planning
- a convenient starting point for `avatar_setup/run_avatar.py`

What this file is not:
- a fully validated CLO export/import sample
- proof that CLO will accept these exact column names unchanged

Current header fields included:
- `Total Height`
- `Weight`
- `Waist`
- `Low Hip`
- `Inseam`
- `Bust`
- `Under Bust`
- `Neck Base`
- `Bicep`
- `Across Shoulder (Curvilinear)`
- `Arm`

Why these fields were chosen:
- they are the strongest direct or near-direct candidates from the current CLO notes
- they align with the fields documented in `measurement_inventory.py`
- they align with the working mapping direction in `measurement_mapping.py`

How to use it:
1. Copy the CSV to a working location if needed.
2. Replace the sample values with the user-specific values.
3. Pass the edited CSV to:
   `python -m clo_avatar_generation.avatar_setup.run_avatar --avt-path "C:\real\path\avatar.avt" --csv-path "C:\real\path\measurement_template_unconfirmed.csv"`

Important caution:
- If CLO rejects this file, that does not mean the plugin is broken.
- It only means the exact CLO CSV schema differs from this starter template.
- The proper long-term fix is to obtain one real CLO-compatible measurement CSV and update this template from that evidence.

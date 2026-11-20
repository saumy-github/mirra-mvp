# CV project rules (read before any work in this folder)

*Status: in force from 2026-11-20 until the CV submission is done*
*Last updated: 2026-11-20*

These rules apply to every plan in `PLAN.md`, every record in `plans/`, and every sub-agent. If a rule blocks the work, stop that piece of work, add a question to `questions.md`, and carry on with something else. Never bend the rule.

**Never stop completely.** If something cannot work (a tool, a permission, a download, a crash), record it in `ISSUES.md` (what happened, the cause, what was done) and move on to other work.

## 1. What this work is for
- **Course:** college Computer Vision project. The goal is to improve how `product_ingestion/` reads cloth photos: **garment outline and shape, colour, designs and design patterns**, from one or several unlabelled photos of a garment.
- **Deliverables** (instructor's post of 2026-11-14):
  1. A research paper in a journal format (IEEE or Elsevier LaTeX template, finished on Overleaf). **The user writes the paper.** I do not write paper text. I prepare what it needs: results tables, figures, the `plans/` records and a summary of methods and numbers in `paper/`.
  2. An executable implementation: a GitHub link with a README. The instructor will share the upload link.
- **Deadline:** final draft due 2026-11-21.
- **Start signal:** no research code is written or run until the user gives the start command.
- **Way of working:** the user leaves me to work overnight and checks `PLAN.md`, the outcomes and `questions.md` in the morning. I choose the direction and record why in each plan record. I run plans in parallel through sub-agents and judge their work (`PLAN.md` section 3a).
- **Questions for the user go only in `questions.md`**, nowhere else.

## 2. Where I may change things
- **Code:** only inside `product_ingestion/`. Change code in another folder only when it is truly needed, and write the reason in that plan's record.
- **Exception for P20 (live CLO test, user-approved 2026-11-20):** the CLO plugin (`clo_workspace/`) and Step 3 fabric code (`clo_vto/native_vto/step_08_apply_fabric.py`) may be changed to give each panel its own fabric and place the pixel maps 1:1. Bump the plugin version and keep the current 1.3.2 DLL in the vault so it can be switched back; keep the Windows and macOS plugin contract in step. Run only one CLO session for this, and stop at any modal dialog that cannot be dismissed safely.
- **Keep the rest of Mirra working.** Other folders read from `product_ingestion/`:
  - `clo_vto/native_vto/helpers.py`, `worker/tasks.py` and `utils/prune_output.py` import `product_ingestion.run_manifest`.
  - Step 3 and the worker read the run output layout (`output/<cloth>/<size>/<run>/image_info/*.json`, `panels/...`).
  - So do not rename or remove existing output files or JSON keys; adding new ones is fine. Keep the public functions the runner calls (`run_segmentation`, `extract_colours`, `extract_design`, `select_primary_image`, `generate_panels`, ...) working with the same inputs and return types.
- **Keep the baseline runnable.** Every changed method keeps the old behaviour selectable (for example `method="v0"`), so before/after comparisons can be re-run.
- **Parallel sub-agents edit only the files they own** (table in `PLAN.md` section 3a). Shared files (`run_product_ingestion.py`, `scripts/evaluate.py`, reference labels, `tests/`) are changed only by me, the orchestrator.
- **Inputs are read-only:** `product_ingestion/input/c_001` to `c_005`, and everything in `data/` after download. Do not delete or overwrite existing runs in `product_ingestion/output/`.

## 3. Where notes, images and outputs go
Everything for this project lives in `product_ingestion/CV/`:

| Path | Holds |
|---|---|
| `INDEX.md` | List of every md file and folder here, one line each |
| `RULES.md` | This file |
| `PLAN.md` | The master plan: every plan, its order, priority and status, and the change log |
| `questions.md` | Open and answered questions for the user |
| `plans/NN_<name>.md` | One record per plan, numbered in the order it was done: goal, what changed, how it was run, results, verdict, next step |
| `scripts/` | Experiment and comparison scripts, each runnable with one command from the repo root |
| `out/` | Generated outputs (masks, overlays, JSON, CSV), one subfolder per plan |
| `images/` | Figures chosen for the paper and the md files |
| `results/` | Final metric tables (CSV or JSON) that the paper quotes |
| `paper/` | Material for the paper the user writes (summary of methods, numbers, figure list); no paper text |
| `data/` | Downloaded datasets (and later the user's own photos) |
| `env/` | `pip freeze` snapshot of the `.venv` and the restore guide (`env/ENVIRONMENT.md`), with a log of every package change |
| `DELETIONS.md` | Log of everything deleted to free disk space |
| `ISSUES.md` | Log of everything that failed or was blocked, its cause and what was done |
| `MIRRA_product_ingestion_review.md` | The user's suggestion file (input to the plans, not a record of work) |
| `syllabus-cv.png` | The course syllabus (CO CSC 601 Computer Vision); the plans use its methods where they fit |

- **Never delete a run, output or experiment**, including failed or weak ones. Their images show how the pipeline improved. A new attempt gets a new subfolder (`out/p05_design/try_02/`), never an overwrite.
- Add every new md file or folder to `INDEX.md` when it is created.
- When a plan finishes or is dropped, update its status in `PLAN.md` and write its record in `plans/`.

## 4. Evidence and honesty
- **The code and output folders are the source of truth.** Older md files (including `.claude/` docs and earlier notes) can be out of date. Treat the review file's claims as suggestions until checked against the code.
- Every claim in a plan record must come from a run: the command, the input, the output path and the numbers. Mark each claim **[V]** (verified by a run) or **[I]** (inference, not run).
- Never invent or round up numbers. Never give completion percentages.
- State the data honestly: 5 Mirra product photos (c_001 to c_005), one photo each, 3 on a person and 2 flat; public datasets are named with their size and licence. Reference labels I make myself are marked *approximate*.
- When a result goes against what we hoped, record it. Failed attempts feed the "how we improved it over time" part of the paper.

## 5. Environment
- **Python:** the repo `.venv` only (`.venv/Scripts/python.exe`). Record every new dependency in the root `requirements.txt`, the one allowed edit outside `product_ingestion/` for this reason.
- **Packages may be installed or upgraded during the research** (user's permission, 2026-11-20), including torch and transformers if a method needs it. The working state before the research is saved in `env/pip-freeze-2026-11-20.txt`; the user restores it afterwards using `env/ENVIRONMENT.md`.
  - Log every install, upgrade or removal in `env/ENVIRONMENT.md` section 4 (date, package, old and new version, why).
  - Prefer versions that leave torch, numpy and opencv as they are, because the pipeline code and the other agents depend on them. If an upgrade is needed, run the pipeline's unit tests afterwards and tell the other running agents.
  - Record new research dependencies in the root `requirements.txt` as well.
- **Datasets and pretrained models:** I may download them without asking (user's permission, 2026-11-20). Record each one (name, source, size, licence) in `INDEX.md` and the plan record. Research-only licences are fine for the course; mark them so they are not shipped in Mirra.
- **GPU:** NVIDIA RTX 4050 Laptop GPU, 6 GB, used by default. Only one large model job at a time: GPU jobs take the lock file `out/.gpu.lock`, while CPU-only work (filters, colour, geometry) runs in parallel. Cache model outputs in `out/` so a model runs once per photo.
- **Disk:** about 17.6 GB free on C: after setup (2026-11-20). Check before any download over 1 GB and keep at least 5 GB free.
- **If space runs out, I may delete only:** (1) packages in `.venv`, (2) datasets I downloaded, (3) earlier versions of models I trained, (4) open-weight pretrained models or algorithm files I downloaded and used. **Nothing that existed before the work started may be deleted**, and outputs in `out/` are never deleted. Every deletion is logged in `DELETIONS.md`.
- Fixed random seeds in every experiment.

## 6. Safety and privacy
- **Never read `.env*` files.** If a key is needed, the user sets an environment variable.
- **Never send the user's photos or data to an external service** (Gemini or any other API) without the user's explicit yes. Downloading public datasets and models is allowed.
- **No git operations:** never stage, commit, push or stash. Use plain `mv` for renames. The user handles GitHub.
- After any `cd`, return to the repo root (`C:\D-drive-data\mirra-mvp`).

## 7. Testing
- Time is short: **do not run the tests after every small change.** Run them only after a change is complete and working, or when something looks broken. Command: `.venv/Scripts/python.exe -m pytest product_ingestion/tests -q` (35 passed on 2026-10-18).
- Each fixed bug gets a regression test in `product_ingestion/tests/`, built from the synthetic case that reproduced it.
- Before the end, run the full pipeline once on c_001 to c_005 and check that the output layout is unchanged apart from added files and keys.

## 8. Writing style for the md files
- Status and dates go in *italics*, never bold.
- Plain language, short sentences, tables where they help.
- A plan record holds only that plan's content and outcome.
- Name files by number and topic (`plans/03_colour_fixes.md`), never by date alone.

## 9. Paper support rules
- Citations follow the course rule: journal or magazine papers from 2024 to 2026 for the "inspiration" papers. Classic method papers (Canny, bilateral filter, CIEDE2000, ...) may be older. Tools such as SAM 2, CLIP, SigLIP and YOLO come from conference or arXiv papers; list them as software and tools (open question in `questions.md`).
- Every number given for the paper must be traceable to a file in `results/`.
- The "how we improved it" timeline is built from the `plans/` records, in order.

## 10. Time
- Each plan in `PLAN.md` has a time box for its first pass. When a plan runs over, record what was reached, mark it partial, and move on.
- Priority order: **Must** first, then **Should**, then **Could**. Later-phase plans (L1, L2) wait for the user.

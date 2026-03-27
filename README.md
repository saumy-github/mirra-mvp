# MIRRA – Development & Pipeline Rules

This document defines the mandatory structure and workflow rules for all contributors working on MIRRA.

## 📂 Shared Google Drive

All large files, models, datasets, input/output images, and external assets must be uploaded here:

[Open Shared Drive Folder](https://drive.google.com/drive/folders/1ai7GjC5sbHLoOzAHbXUIEoEJXwMQWc_h)

Do NOT upload large files or media directly to GitHub.

---

## 1. Personal Feature Branch Requirement

*(e.g., `saumy`, `tanmay`)*
Every contributor must create and work in a **separate personal feature branch**.

---

## 2. One Dedicated Root Folder per Pipeline / Technology

*(e.g., `avatar_generation`, `clo_workspace`)*
Each technology or pipeline must exist in its own separate root-level folder to ensure modularity and prevent mixing of logic.

---

## 3. Mandatory Internal Structure for Every Pipeline  

*(e.g., `README.md`, `SETUP.md`, `.gitignore`, `input/`, `generated/`)*  
Every pipeline folder must contain this standardized internal structure to ensure reproducibility, clarity, and clean collaboration.

- **README.md** - Must contain a short description of the pipeline, command to run it, folder structure, and expected input/output formats.
- **SETUP.md** - Must contain installation steps.
- **.gitignore** - Must ignore input/output media files, temporary files, and large artifacts while preserving folder structure using `.gitkeep`.

    ```plain
    generated/*  
    !generated/.gitkeep  
    ```

- **input/** - Contains all raw files required to run the pipeline. Only `.gitkeep` should be committed.
- **generated/ (or output/)** - Contains all outputs produced by the pipeline. Only `.gitkeep` should be committed.

---

## 4. Dedicated `libs/` Folder (Submodules Only)

*(e.g., `libs/star/`)*  

- The `libs/` folder must contain only Git submodules or external repositories. No internal project logic should be placed here.
- Every submodule added inside `libs/` must also be registered in the root `.gitmodules` file.

Example entry inside `.gitmodules`:

```plain
[submodule "libs/star"]
    path = libs/star
    url = https://github.com/<repo-owner>/<repo-name>.git
```

---

## 5. Centralized `models/` Folder (Not Committed)

*(e.g., `star_1_1`, any other software packages )*  
The `models/` folder is used to store large files required for pipelines but must not be committed to GitHub.

---

## 6. Single Root-Level `requirements.txt`
  
There must be only one `requirements.txt` file in the root folder that contains all project-wide dependencies.

---

## 7. Reusable & Generalized Pipeline Architecture  

*(e.g., no hardcoded paths, no single-use scripts, configurable parameters)*  

- All pipelines must be designed to be reusable and generalized.
- Avoide hardcoded values and build pipeline which can supporting multiple inputs and configurations.
- No harcode line for your own PC like
 /home/saumy/Documents/mirra-mvp/Working_Cloth_3D_Pipeline/input_image.jpg

---

## 8. Mandatory Versioned Input–Output Serialization  

*(e.g., `male_001.json`, `male_002.json`, `male_003.json`)*  
All input and output files must follow a structured, incremented numbering format (e.g., `001`, `002`) to ensure traceability, reproducibility, and proper version tracking across pipeline runs.

---

## 9. Dedicated `scripts/` Folder for Executable Files  

*(e.g., `avatar_generation/scripts/`)*  
All runnable scripts must be placed inside a `scripts/` folder within their respective pipeline.

---

## 10. Dedicated `notes/` Folder for AI-Generated or Reference Markdown  

*(e.g., `avatar_generation/notes/`)*

- Any Markdown files created for understanding AI outputs, experiments, or temporary documentation must be placed inside a `notes/` folder and not mixed with core documentation.
- Documentation should remain concise.
- Avoid uploading excessively large Markdown files when the content can be modularized.

---

## 11. Register Pipeline Setup in Root `SETUP.md`

*(e.g., `avatar_generation/SETUP.md` linked inside root `SETUP.md` table)*  

Once a pipeline is implemented, its `SETUP.md` must be referenced inside the root-level `SETUP.md` under the **Pipeline & Technology Setup** section.

Example format in root `SETUP.md`:

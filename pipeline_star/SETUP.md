# STAR Body Model

The avatar pipeline uses the **STAR** (Sparse Trained Articulated Human Body Regressor) model.

## 1. Download the STAR model files

1. Download the STAR model files as a zip archive from the following Google Drive link (under Technical Side/STAR):
    👉 <https://drive.google.com/drive/folders/1ai7GjC5sbHLoOzAHbXUIEoEJXwMQWc_h>

    Alternatively, you can register and download from the official website:
    👉 <https://star.is.tue.mpg.de/>

2. Extract the downloaded zip file. Place the extracted model files in the models folder:

   ```plain
   models/
   ├── .gitkeep
   └── star_1_1/
      ├── male/
      │   └── model.npz
      ├── female/
      │   └── model.npz
      └── neutral/
         └── model.npz
   ```

## 2. Install the STAR library

   1. Clone the STAR repository into `libs/star` (use the fork and branch we maintain):

      ```bash
      git clone -b star_mirra https://github.com/saumy-github/STAR.git libs/star
      ```

      Or, if you later add multiple submodules to this repository, clone all submodules in one step with:

      ```bash
      # clone the superproject (if not already cloned) and all submodules
      git clone --recurse-submodules <superproject-url>

      # or, from an existing clone of the superproject, initialize and fetch every submodule
      git submodule update --init --recursive
      ```

      The `git submodule` commands read `.gitmodules` to find each submodule's URL/path/branch and fetch them automatically.

   2. Update `libs/star/star/config.py` to point model paths to the project root.
   Replace the entire contents of that file with the following:

      ```python
      import os

      # Get the directory where this config.py file is located
      config_dir = os.path.dirname(os.path.abspath(__file__))
      # Navigate to project root (3 levels up from libs/star/star/)
      project_root = os.path.abspath(os.path.join(config_dir, '..', '..', '..'))

      # Define model paths relative to project root
      path_male_star    = os.path.join(project_root, 'models', 'star_1_1', 'male',    'model.npz')
      path_female_star  = os.path.join(project_root, 'models', 'star_1_1', 'female',  'model.npz')
      path_neutral_star = os.path.join(project_root, 'models', 'star_1_1', 'neutral', 'model.npz')

      data_type = 'float32'

      if data_type not in ['float16', 'float32', 'float64']:
         raise RuntimeError('Invalid data type %s' % (data_type))

      class meta(object):
         pass

      cfg = meta()
      cfg.data_type = data_type

      cfg.path_male_star    = path_male_star
      cfg.path_female_star  = path_female_star
      cfg.path_neutral_star = path_neutral_star
      ```

3.Install the STAR library in editable mode:

   ```bash
   pip install -e libs/star/
   ```

# Free 3D clothes: where to get them and how they are made

*Status: current; based on web searches on 2026-10-18. Licenses change, so open each asset page and read its license before using anything*
*Written: 2026-10-18*

---

## 1. First, which kind of asset do we actually need?

There are three very different things people call "a 3D garment":

| Kind | What it is | Can Mirra's pipeline use it? |
|---|---|---|
| **A. Flat sewing pattern** (DXF, SVG, JSON, or a CLO/Marvelous project) | the 2D pieces plus how they stitch together | **Yes.** This is exactly what Step 2 produces and Step 3 (CLO) consumes |
| **B. Static 3D mesh** (OBJ, FBX, GLB) | a finished garment shape, already "worn" on a body | **Only partly.** It has no pattern pieces or seams, so CLO cannot re-fit it to a new avatar. Good for visual reference, texture tests, or a web viewer |
| **C. Dataset** (many patterns and/or meshes, for research) | thousands of examples | **Yes, for testing and learning.** Not for shipping garments |

This matters because most "free 3D clothes" you find online are type B.

---

## 2. How 3D clothes are made

| Method | How | Tools | Output |
|---|---|---|---|
| **Pattern-based simulation** | Draw or import 2D pattern pieces, place them around an avatar, define seams, run a cloth simulation until the cloth settles | **CLO3D**, **Marvelous Designer**, **Style3D** | a draped garment *and* the original patterns |
| **Cloth simulation in a general 3D tool** | Model flat pieces as meshes, set up a Cloth modifier with pins and sewing springs, simulate | **Blender** | a draped mesh; more freedom but more manual work (a Blender wiki guide and a free five-part course on sewing in Blender exist) |
| **Hand modelling and sculpting** | Model the garment surface directly, then clean up the mesh (retopology) | Blender, ZBrush and similar *(general practice)* | a static mesh, no patterns |
| **Scanning / capture** | Scan a real garment or a person wearing it | photogrammetry, multi-camera scanners | meshes with texture; sometimes registered to a body model |
| **Procedural / programmatic generation** | A program makes pattern pieces from parameters, then a simulator drapes them | **GarmentCode** (patterns), a simulator such as an XPBD solver | patterns and draped 3D, at large scale |
| **Parametric pattern generators** | Code or measurement files produce 2D patterns only | **FreeSewing**, **Seamly2D**, **Valentina**, **GarmentCode** | flat patterns |

How the common free sources were made (where I could confirm it):

- **GarmentCodeData** (ETH Zürich): patterns made by GarmentCode programs and draped with an open-source **XPBD** (extended position-based dynamics) pipeline on bodies from a statistical model built on CAESAR scans.
- **Deep Fashion3D**: 2,078 models reconstructed from **real garments**, 563 garment instances in 10 categories, each randomly posed, with feature lines (neckline, cuff, hem) and multi-view images annotated.
- **4D-DRESS**: **real captured** 4D scans of 64 outfits, 520 motion sequences (78,000 frames), with garment templates and SMPL/SMPL-X registration.
- **BEDLAM**: clothing **physically simulated** by commercial cloth software on moving bodies; garments were created by an outside studio, and the clothing assets and textures are released.
- **CLOTH3D**: synthetic clothed-human sequences (the page I read does not say which software made the garments).

---

## 3. Where to get free ones

### 3.1 Free garment assets and projects

| Source | What you get | License and caveats | Made with | Useful to Mirra? |
|---|---|---|---|---|
| **CLO-SET CONNECT** (CLO's marketplace) | patterns, avatars, fabrics, accessories, scenes, some free | per item; free items only appear in the CLO library's community section; your CLO and CONNECT accounts must be linked | CLO | **Yes (type A)**: loads straight into CLO |
| **Marvelous Designer Connect store** | garments, fabrics, avatars, some free; free project files also shared by users (e.g. a free dress project with skirt, waistband, two sleeve and bodice patterns) | per item; some tutorial garments only ship with newer MD versions | Marvelous Designer | **Possibly (type A)**; needs checking that the file can be opened in our CLO |
| **Sketchfab** | many free garment meshes; **Style3D** posts free downloads (a hooded sweatshirt, a jacket coat) in FBX, OBJ, ABC, USD, glTF, GLB | the clothing models I saw were mostly **CC Attribution** (credit required); I found **no CC0** garments in the results; check each page | mixed (Style3D, Marvelous Designer, Blender) | type B: reference or viewer use |
| **BlenderKit** | community assets inside Blender, including a free t-shirt | license not shown on the page I found | Blender | type B |
| **MakeHuman** | clothes for the MakeHuman character base | core assets are **CC0**; the user-contributed clothing library mixes licenses (CC-BY and others); a downloader is built into 1.2.0 and later | MakeHuman and Blender | type B, low-poly game-style |
| **Itch.io, Gumroad free packs** | individual free garments | e.g. one free t-shirt requires credit; many are "name your own price" | Blender and others | type B |
| **Paid packs** (RenderHub, Superhive and others) | not free | n/a | n/a | out of scope |

### 3.2 Pattern generators and libraries (free software)

| Source | Notes | License |
|---|---|---|
| **GarmentCode** (`maria-korosteleva/GarmentCode`) | Python library (PyGarment) for parametric sewing patterns with example garments, body presets, a GUI and a web configurator; the page does not mention DXF or SVG output, so conversion to DXF would be our job *(not verified)* | **MIT** (code) |
| **FreeSewing** | open-source JavaScript library for measurement-driven patterns, with seam-allowance offsetting and SVG output | individual pattern packages shown as MIT on npm; I did not check the core library's license |
| **Seamly2D** (fork of Valentina) | open-source parametric pattern software | **GPLv3+** |
| **Valentina** | free and open source parametric patterns with measurement tables | DXF export support is unclear: a developer forum post called AAMA DXF low priority; a Style3D blog describes exporting Valentina patterns as DXF *(conflicting; check current release notes)* |

### 3.3 Research datasets

| Dataset | Content | Size | Access and license |
|---|---|---|---|
| **GarmentCodeData** (ECCV 2024) | sewing patterns + 3D draped garments + body measurements | 115,000 | DOI links on the project page (v2 released Sept 2024); **no dataset license stated** on the pages I read |
| **GCD-MM** | adds text and images for the AIpparel work | about 120,000 | on Hugging Face (AIpparel release) |
| **SewFactory** | 1 million images with 19,100 patterns (Sewformer) | 1M images | project page sewformer.github.io |
| **Deep Fashion3D** | garments reconstructed from real clothes | 2,078 models | license not found in the results |
| **4D-DRESS** (CVPR 2024) | real 4D scans of 64 outfits | 78k frames | project page `ait.ethz.ch/4d-dress`; license not found in the results |
| **CLOTH3D / CLOTH3D++** | synthetic clothed humans | very large (a mirror splits about 160 GB) | project page `chalearnlap.cvc.uab.es/dataset/38`; license not found in the results |
| **BEDLAM** | simulated clothed bodies; clothing assets and textures released | large | project page `bedlam.is.tue.mpg.de` |
| **Dress Code** | 50k+ image pairs of people wearing tops, bottoms, dresses (try-on images, not 3D) | 50k+ | public on GitHub `aimagelab/dress-code` |

---

## 4. What I would do for Mirra

1. **Use type A sources for new garment types.** Search CLO-SET CONNECT first (patterns load straight into the CLO we already automate). Check Marvelous Designer's free project files for pieces we could rebuild in `clo_block`.
2. **Use GarmentCode as a pattern reference and test generator.** It is MIT licensed and already models many garment types (tops, skirts, trousers, dresses). We would need a converter from its patterns to DXF with our edge manifest; check whether the GarmentCode tooling already exports something CLO can read.
3. **Use datasets for tests, not shipping.** GarmentCodeData gives patterns to run our geometry and seam checks on. Check the dataset license before any commercial use.
4. **Treat meshes (type B) as visual references only**, or for the web viewer. They cannot be re-fitted to a new avatar the way a pattern can.
5. **Record the license of everything we keep** (a `LICENSES.md` next to the asset), and prefer CC0 and MIT. I found **no CC0 clothing meshes** in these searches.

---

## 5. Sources

- CLO assets and CONNECT: https://support.clo3d.com/hc/en-us/articles/115015461808-What-kinds-of-assets-are-provided-by-CLO
- Marvelous Designer free assets: https://support.marvelousdesigner.com/hc/en-us/articles/47358206966937-Are-there-any-assets-that-I-can-use-beyond-the-library
- Sketchfab Style3D free garments (examples): https://sketchfab.com/3d-models/pink-drawstring-hooded-sweatshirt-fd03f442026f4252b2507dda53bba564
- MakeHuman asset packs and licenses: https://static.makehumancommunity.org/assets/assetpacks.html and https://static.makehumancommunity.org/makehuman/faq/are_makehuman_files_free.html
- GarmentCode: https://github.com/maria-korosteleva/GarmentCode
- GarmentCodeData: https://igl.ethz.ch/projects/GarmentCodeData/ and https://arxiv.org/abs/2405.17609
- Deep Fashion3D: https://arxiv.org/abs/2003.12753
- 4D-DRESS: https://arxiv.org/abs/2404.18630
- BEDLAM: https://arxiv.org/abs/2306.16940
- CLOTH3D: https://arxiv.org/abs/1912.02792
- Sewformer / SewFactory: https://arxiv.org/abs/2311.04218
- AIpparel / GCD-MM: https://arxiv.org/abs/2412.03937
- Dress Code: https://github.com/aimagelab/dress-code
- FreeSewing: https://www.npmjs.com/package/freesewing
- Seamly2D and Valentina: https://en.wikipedia.org/wiki/Valentina_(software)
- Blender sewing guide: https://wiki.blender.org/index.php/User:Roger/Sewing_Clothes

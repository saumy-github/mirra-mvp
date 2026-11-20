# Questions for the user

*Last updated: 2026-11-20*
*Open: 3 · Answered: 5*

When you answer a question (in chat), I change its status to **answered**. A question marked **open** still needs your answer. No answers are written here.

| Status | # | Question | Needed for |
|---|---|---|---|
| answered | Q8 | At 15:14 Claude Code stopped three of my background jobs because the computer was critically low on memory (`ISSUES.md` I22), and its rules say I may restart them only when you ask. May I run them again, one at a time with no other model jobs running? They are: (1) the final end-to-end pipeline run on the 5 photos (`scripts/p10_run_all.py`, about 5 minutes; this gives the final pipeline score for the paper), (2) the multi-photo demo after the outline fix (`out/demo/multi_photo_demo_after_fix.log`, about 2 minutes), (3) the resource watchdog (`scripts/resource_watch.py`). | P10 final score, P14 demo |
| answered | Q1 | Which image enhancement and filtering topics are in your syllabus? | P03 |
| answered | Q2 | For the GitHub link, should I prepare a separate repository with only `product_ingestion/` and this CV folder, or will you share the whole `mirra-mvp` repository? | P13 |
| open | Q3 | Later phase L1: will you take your own photos of 2 or 3 T-shirts (front, back, print close-up, angled shot, one worn, with an A4 sheet in frame)? | L1 |
| open | Q4 | Later phase L2: should Gemini be used as a comparison? If yes, set the `GEMINI_API_KEY` environment variable (do not paste the key in chat). | L2 |
| open | Q7 | Copying a rebuilt plugin into `C:\Program Files\CLO Standalone OnlineAuth\plugins` needs administrator rights (that folder is read-only for normal users), and nobody can click a Windows admin prompt overnight. If you want me to install a rebuilt plugin while you sleep, please run this once in an **administrator** PowerShell: `icacls "C:\Program Files\CLO Standalone OnlineAuth\plugins" /grant "$env:USERNAME:(OI)(CI)M"` (it gives your user write access to that one folder; remove it later with `icacls "C:\Program Files\CLO Standalone OnlineAuth\plugins" /remove "$env:USERNAME"`). Without it I can still test CLO with the plugin already installed. | P20 |
| answered | Q6 | Multi-colour shirts and the per-panel pixel maps (P19) cannot show correctly in CLO yet: the plugin gives every panel the same fabric and applies each image as a repeating swatch, so the images tile and overwrite each other. May I change the CLO plugin and Step 3 code (outside `product_ingestion/`) so each panel gets its own fabric with its image placed 1:1 (or placed as a graphic covering the panel)? Testing it needs CLO running with you present. | 3D result (later phase) |
| answered | Q5 | Please check with your instructor: may tools such as SAM 2, CLIP and YOLO, which come from conference or arXiv papers, be cited as software under the journal-only rule? | your paper |

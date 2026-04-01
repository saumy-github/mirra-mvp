# Research & Comparison: TAAS.nyc vs. MIRRA

This document provides in-depth research into **TAAS.nyc** (specifically their 3D virtual fit simulation services) and compares it with the **MIRRA** project currently under development.

---

## Part 1: In-Depth Research on TAAS.nyc

**Website Overview:** [TAAS.nyc (Technology Advanced Apparel Services)](https://www.taas.nyc/3d-virtual-fit-simulation)  
**Core Offering:** TAAS.nyc is a B2B fashion technology service provider focusing on 3D virtual fit engineering and advanced digital pattern making. They help clothing brands digitize their design, sizing, and product development phases.

### Key Features & Services:
1. **3D Virtual Fit Simulation:** They use 3D digital avatars (live fit models) to simulate garment drape, sizing, and fit. This allows brands to prevent development drape errors virtually before physical sampling.
2. **Digital Pattern Engineering:** They convert physical paper patterns into digital formats (DXF blocks).
3. **Tech Packs & Grading:** They generate comprehensive tech packs, digital pattern measurement charts, and precise numeric/alpha grading for manufacturing.
4. **Market Audience:** Aimed primarily at fashion brands, technical designers, and production managers looking to optimize manufacturing workflows, decrease physical fabric waste, and speed up the time-to-market.
5. **Asset Provisioning:** They allow users to download digital avatars, avatar body measurements, and DXF block patterns directly from their store.

### Main Value Proposition:
- Building a competitive "fit signature" for brands.
- Minimizing physical sampling rounds (lowering costs and waste).
- Ensuring precise apparel production and accurate specs across all sizes.

---

## Part 2: Overview of MIRRA Project

Based on the repository architecture (`avatar_generation`, `product_ingestion`, and `vto` pipelines), **MIRRA** is an automated pipeline that aims to ingest, process, and simulate virtual clothing on digital avatars.

### Key Pipeline Components:
1. **Avatar Generation (`avatar_generation` / step 1):** Automatically generates digital generic user avatars (`avatar.glb`, `avatar.obj`, `measurements.json`) mapped directly to user IDs.
2. **Product Ingestion (`product_ingestion` / step 2):** Ingests raw 2D images of garments, runs segmentation and color/design extraction, and procedurally generates 2D sewing pieces (Panels) into `.dxf` and `.svg` formats. 
3. **Virtual Try-On (`vto` / step 3):** An orchestrated pipeline combining the avatar (Step 1) and the garment DXF panels (Step 2) using heavily automated **CLO3D** workspaces (via REST & plugins) to simulate a Virtual Try-On (VTO) experience.

---

## Part 3: Direct Comparison (TAAS vs. MIRRA)

While both TAAS and MIRRA operate in the 3D digital fashion space and utilize similar baseline technologies (avatars, DXF pattern files, 3D simulation mechanics), their **target use cases, workflows, and automation levels** are entirely different.

### 1. Business Model & Automation
* **TAAS:** Operates fundamentally as a **technical service agency**. They take a brand's rough sketches or physical paper patterns and use expert human intervention supplemented with 3D CAD tools to produce highly optimized, production-ready manufacturing patterns.
* **MIRRA:** Operates as an **automated software pipeline**. It is designed to take raw 2D apparel photos and automatically extract 2D patterns (DXFs), generate an avatar, and simulate a Virtual Try-On programmatically without requiring manual CAD manipulation per garment. 

### 2. Primary Goals
* **TAAS:** **Production & Manufacturing Optimization.** The goal is to perfect standard sizing logic (alpha/numeric grading), create tech packs, and make a physical factory's life easier.
* **MIRRA:** **Virtual Try-On (VTO) / E-Commerce.** The goal is to ingest real-world garments quickly and show a consumer exactly how that garment maps onto their personalized 3D avatar.

### 3. Core Technologies & Inputs 
* **Inputs:** 
   * **TAAS** requires paper patterns or specific size charts to construct a precise fit.
   * **MIRRA** requires raw flat/model images of clothing (e.g., images of a blue Zara t-shirt), and automates the panel extraction procedurally.
* **Avatar Usage:** 
   * **TAAS** utilizes standard, live fit models (Digital Avatars) explicitly tailored to standard brand sizing blocks (Small, Medium, Large).
   * **MIRRA** dynamically generates `avatar.obj` per individual user (`u_001`, `u_002`) aiming for personalization.
* **Outputs:** 
   * **TAAS** outputs production-ready DXF patterns, tech packs, and strict measurement charts for a factory.
   * **MIRRA** outputs a rendered Virtual Try-On (`run_vto.py`) scene inside CLO3D showing the consumer wearing the outfit.

### Summary

**How similar is TAAS.nyc to MIRRA?**
They share the same **technological DNA** (using `.dxf` panel generation, CLO3D/CAD workflows, and 3D digital avatars), but they diverge entirely in purpose. TAAS focuses on *B2B supply chain optimization* (helping manufacturers cut physical sample costs), whereas MIRRA is building an automated *B2C retail/tech pipeline* that scalably maps 2D images of clothing onto dynamically generated user avatars for Virtual Try-On.

# MVP Step 1: 3D Avatar Generation System

## Executive Summary

### Core Objective & Scope

**Goal**: To create a unique, reusable, and anatomically accurate 3D avatar which is representation of a specific user based on manual measurements.

**Purpose**: This avatar serves as the persistent "mannequin" for all future virtual try-on sessions. It acts as the foundational body block upon which clothing will be simulated.

**Key Characteristic**: The system prioritizes dimensional accuracy (fit) over aesthetic realism (face/hair). The avatar is generated once, stored permanently, and retrieved for every session to ensure consistency and minimize processing overhead.

---

## Input Data Collection

The system will implement a frontend form linked to a specific User ID to collect the necessary data. This data drives the morphing algorithm to ensure the mesh matches the user's real-world dimensions.

### A. Manual Tailor Measurements

Users will manually enter specific tape measurements. The form dynamically adjusts based on gender selection.

#### MEN (Tape Inputs)

- **Height**: [cm]
- **Weight**: [kg]
- **Shoulder Width**: [cm] (Measured shoulder tip to shoulder tip)
- **Chest Circumference**: [cm] (Measured at the widest part)
- **Waist Circumference**: [cm] (Measured at the belly button)
- **Hip Circumference**: [cm] (Measured at the widest part of buttocks)
- **Leg Length**: [cm] (Measured from Waist to Ankle)

#### WOMEN (Tape Inputs)

- **Height**: [cm]
- **Weight**: [kg]
- **Shoulder Width**: [cm]
- **Bust Circumference**: [cm] (Measured at the widest part)
- **Under-Bust Circumference**: [cm] (Measured at the Ribcage/Band)
- **Waist Circumference**: [cm] (Measured at the narrowest part)
- **Hip Circumference**: [cm] (Measured at the widest part)
- **Leg Length**: [cm] (Measured from Waist to Ankle)

### B. Physical Traits

- **Body Shape Type**: Selection of general archetype to assist initial mesh topology (e.g., hourglass, rectangle, inverted triangle)
- **Skin Tone**: Hex code input or colour picker
  - _Note: While the MVP is a black silhouette, this data is collected now for future rendering layers_

---

## Visual Style & Rendering Specifications

The MVP (Minimum Viable Product) direction focuses strictly on silhouette and fit validation.

### Aesthetic

- **Visual Style**: A featureless, skin colour silhouette with a matte finish
- **Detailing**: No skin texture, no face, and no hair details

### Mesh Exclusions

To optimize the mesh for clothing fit without unnecessary polygons, the following parts are not to be modified:

- **Head/Neck**: Do not modify or simplified to a basic stump
- **Hands**: Do not modify below the wrist
- **Feet**: Do not modify below the ankle
- **Crotch Area**: Private parts will be smoothed/covered (resembling a mannequin)

### Rationale

This visual style highlights the fit of the garment rather than the look of the user, reducing the "uncanny valley" effect while keeping the file size low.

---

## Generation Pipeline & Functionality

### A. Static Generation Strategy

Instead of creating a fully rigged, animation-ready character with bones and skin weights (which is computationally expensive), the system will generate a **Static 3D Mesh**.

- **Morphing Logic**: The base mesh vertices are displaced/morphed to become an exact replica of the input numbers (e.g., expanding the chest vertices to match the chest circumference input)
- **Pose**: The avatar stands in a single, static **T-pose** (arms extended horizontally, forming a "T" shape) optimized for clothing attachment and measurement consistency

### B. Persistence & Storage

- **Creation Frequency**: The avatar is generated once. It is not recreated every session
- **Storage**: The resulting 3D model file (likely `.glb` or `.obj`) is stored in the database/cloud storage bucket
- **Retrieval**: The file path is linked to the User ID. When the user logs in, the existing file is fetched. This ensures immediate availability without re-processing

---

## User Interaction & Performance

### Interaction

The user can inspect their digital body using a **360-degree camera rotation control**. The avatar remains static; the camera moves around it.

### Performance Optimization

- **Focus**: "Loading time" optimization is the priority
- **Method**: By stripping extremities (hands/feet/head) and using a matte black texture (no high-resolution maps), the file size is kept minimal for instant rendering on web browsers

---

## Future (Post-MVP)

While the current requirements are specific, the system architecture allows for the following future upgrades:

1. **Realism**: Implementing realistic skin tones, facial features, and hair simulations
2. **VTO**: Virtual try-on of clothes on the mannequin
3. **Other jobs to be done separately**: Conversion of 2D garments to 3D for the VTO to happen on the mannequin created

---

## MVP Roadmap Context

This document describes **Step 1** of the 3-step MVP:

- **Step 1** (This Document): Clean 3D Avatar Generation for AI Usage
- **Step 2**: TBD
- **Step 3**: TBD

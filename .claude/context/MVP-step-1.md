# MVP Step 1: 3D digital twin Generation System

## Executive Summary

### Core Objective & Scope

**Goal**: To create a unique, reusable, and anatomically accurate 3D digital twin which is representation of a specific user based on manual measurements.

**Purpose**: This digital twin serves as the persistent "mannequin" for all future virtual try-on sessions. It acts as the foundational body block upon which clothing will be simulated.

**Key Characteristic**: The system combines dimensional accuracy (for fit) with personalized facial features. The digital twin is generated once, stored permanently, and retrieved for every session to ensure consistency and minimize processing overhead.

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

### B. Physical Traits & Appearance

- **Body Shape Type**: Selection of general archetype (e.g., hourglass, rectangle, inverted triangle)
- **Skin Tone**: Hex code input or colour picker for avatar rendering
- **Facial Characteristics**: Data inputs to customize facial features (to be defined based on measurement data)

---

## Visual Style & Rendering Specifications

The MVP includes both body shape morphing and basic facial customization to create a personalized digital twin.

### Body Aesthetic

- **Visual Style**: Realistic 3D body model in T-pose with proper proportions
- **Features**: Body customization based on measurements (height, width, proportions)
- **Skin Tone**: Applied based on user input

### Facial Customization (MVP Scope)

The avatar includes facial features that are customized to match the user:
- **Face Shape & Proportions**: Adapted based on body measurements and facial data collection
- **Features**: Eyes, hair, and basic facial attributes
- **Future Enhancement**: Detailed facial expressions and realism (post-MVP)

### Rationale

The digital twin should be recognizable as the user while maintaining accuracy for clothing fit simulation. Facial customization adds personal identity while body morphing ensures accurate garment fit.

---

## Generation Pipeline & Functionality

### A. Static Generation Strategy

Instead of creating a fully rigged, animation-ready character with bones and skin weights (which is computationally expensive), the system will generate a **Static 3D Mesh**.

- **Morphing Logic**: The base mesh vertices are displaced/morphed to become an exact replica of the input numbers (e.g., expanding the chest vertices to match the chest circumference input)
- **Pose**: The digital twin stands in a single, static **T-pose** (arms extended horizontally, forming a "T" shape) optimized for clothing attachment and measurement consistency

### B. Persistence & Storage

- **Creation Frequency**: The digital twin is generated once. It is not recreated every session
- **Storage**: The resulting 3D model file (likely `.glb` or `.obj`) is stored in the database/cloud storage bucket
- **Retrieval**: The file path is linked to the User ID. When the user logs in, the existing file is fetched. This ensures immediate availability without re-processing

---

## User Interaction & Performance

### Interaction

The user can inspect their digital body using a **360-degree camera rotation control**. The digital twin remains static; the camera moves around it.

### Performance Optimization

- **Focus**: Generation speed and file size optimization
- **Method**: Optimized 3D model formats and efficient storage in cloud/database for instant retrieval on user login

---

## Future (Post-MVP)

While the current requirements are specific, the system architecture allows for the following future upgrades:

1. **Advanced Facial Realism**: Detailed expressions, micro-features, and advanced rendering
2. **Body Shape Archetypes**: Support for diverse body type variations (athletic, curvy, etc.)
3. **Dynamic Customization**: Real-time adjustments to avatar based on user feedback
4. **Multi-gender Expansion**: Extended female and non-binary avatar support with specialized measurements

---

## MVP Roadmap Context

This document describes **Step 1** of the 3-step MVP:

- **Step 1** (This Document): Clean 3D digital twin Generation for AI Usage
- **Step 2**: TBD
- **Step 3**: TBD

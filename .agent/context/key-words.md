# Project Keywords & Terminology

This document defines key terms and concepts used throughout the project. These terms will be used consistently in all discussions, planning, and implementation.

---

## Keywords

1. **Digital Twin / avatar**
   - The custom body model we create for each user so that they can try clothes on it
   - Generated once per user based on their measurements, stored permanently

2. **Live Try-On**
   - Real-time trying of clothes using camera (photo or video)
   - Allows users to see how clothes look on them in real-time using their device camera

3. **VTO (Virtual Try-On)**
   - 3D clothes displayed on the 3D digital twin
   - The core simulation experience where users see garments fitted to their digital twin

4. **3D Clothes / 3D Assets**
   - Digital clothing items we put on the digital twin
   - The virtual garments that have been converted from 2D to 3D for VTO purposes

5. **Seller Websites / Amazon**
   - External websites from which we scrape products
   - Source of product data and images for ingestion

6. **Sellers**
   - Direct retailers who sell their products on our website
   - Partners who directly provide product listings on our platform

7. **Product Ingestion**
   - The process of taking 2D images and converting them into 3D clothes/assets
   - The workflow that transforms flat product images into 3D models

8. **3D Assets Ingestion / AI Ingestion Engine / AI-Powered 3D Assets Ingestion**
   - The model we create for product ingestion
   - The AI-powered engine that automates the 2D-to-3D conversion process

9. **Inventory**
   - Universal stock of 3D assets which can be reused by all users
   - Centralized library of converted 3D garments available for all VTO sessions

10. **Live Try-On Conference**
    - Multiple people join when one person wants to buy something
    - Social shopping feature where friends can join a session to provide feedback

NFS GUIDEBOOK - CHAPTER STRUCTURE REFERENCE
============================================

Master Titles File
------------------
Location: chapters/_template/Titles

This file contains the complete list of all 47 chapters organized by domain.
Use this as the master reference for chapter titles and organization.

Chapter Directory Structure
---------------------------
Each chapter has its own directory:
- ch01/ through ch47/

Each directory contains:
1. chapter.json - JSON configuration file with chapter metadata and content
2. Titles - Quick reference file showing chapter number, domain, and title

Chapter JSON Structure
---------------------
Each chapter.json includes:
- number: Chapter number (1-47)
- title: Full chapter title
- domain: The domain this chapter belongs to
- series_subtitle: Standard subtitle for the series
- cover_tagline: Short tagline for the cover (to be defined per chapter)
- build_standard: Include in standard edition (true/false)
- build_clinical: Include in clinical edition (true/false)
- sections: Array of content sections

Domains and Chapter Ranges
--------------------------
1. Nervous system, mood, and cognition (Chapters 1-12)
2. Sleep, body, pain, and substances (Chapters 13-20)
3. Relationships, family, and parenting (Chapters 21-27)
4. Intimacy, sex, and emotional connection (Chapters 28-35)
5. Moral injury, guilt, shame, and spirituality (Chapters 36-40)
6. Work, mission, identity, and transition (Chapters 41-46)
7. Dopamine, habits, and modern addictions (Chapter 47)

Working with Chapters
--------------------
To develop a chapter:
1. Navigate to the chapter directory (e.g., chapters/ch01/)
2. Open chapter.json
3. Update the cover_tagline if needed
4. Define section headings in the sections array
5. Add content blocks (paragraphs, bullets, callouts, etc.)
6. Follow the template structure in chapters/_template/chapter.json for examples

Building Chapters
----------------
Use the build scripts in the root directory:
- build_chapters.py - Build individual chapters
- build_docs.py - Build documentation
- build_pdf.py - Build PDF outputs

Quick Access to Any Chapter
---------------------------
All chapters now have their own dedicated files for easy access and parallel development.
Each chapter can be worked on independently following the same structure/pattern.

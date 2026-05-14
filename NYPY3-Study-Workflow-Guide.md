# NYPY3 Study Workflow Guide

**Purpose:** Complete guide for using Obsidian (NYPY3 vault) + Windsurf/Cascade AI assistant for effective studying, note ingestion, organization, and assignment management.

**Goal:** Document this workflow to enable replication in other projects.

---

## Table of Contents

1. [Vault Structure](#vault-structure)
2. [Ingestion Workflow](#ingestion-workflow)
3. [Organization System](#organization-system)
4. [Study Workflow](#study-workflow)
5. [AI Assistant Usage](#ai-assistant-usage)
6. [Assignment Workflow](#assignment-workflow)
7. [Tracking & Maintenance](#tracking--maintenance)
8. [Handling Diagrams](#handling-diagrams)
9. [Replication Guide](#replication-guide)

---

## Vault Structure

### Root-Level Files
- `.vault-index.md` — Agent-readable index (AI reads this first for any vault work)
- `.daily-maintenance-prompt.md` — Copy-paste prompt for daily vault upkeep
- `📅 Schedule & Assessments Dashboard.md` — Due dates, class schedule
- `NYPY3 - Main Index.md` — Human-readable main index
- MOC files for each course (e.g., `EGE353 Autonomous Mobile Robotics - MOC.md`)

### Course Folder Structure
```
EGE353 Autonomous Robotics/
├── EGE353 Lab 1 Notes.md
├── EGE353 Lab 2 - ROS Nodes and Topics.md
├── Lesson 1-Introduction.md
├── assets/ (for images - mostly empty per no-images policy)
└── EGE353 Autonomous Mobile Robotics - MOC.md
```

### Reference Materials
- `Senior Notes/` — 5,728 files from previous student (indexed for cross-reference)
- `_tools/` — Conversion scripts and utilities
- `_to_upload/` — Staging area for new materials

---

## Ingestion Workflow

### Step 1: Collect Materials
- Download PDFs/PPTX from Brightspace
- Type notes during/after class
- Take photos of whiteboards (if needed)

### Step 2: Stage for Conversion
- Drop files into `_to_upload/` folder
- Supported formats: PDF, PPTX, DOCX, XLSX, XLS, CSV, HTML

### Step 3: Run Conversion Script
```bash
python _tools/convert_to_md.py
```

**What the script does:**
- Converts files to Markdown using MarkItDown
- Detects course code from content (EGE353, EGE321, etc.)
- Adds YAML frontmatter with tags, course, topic, source, date
- Auto-moves files to correct course folder
- Formats markdown with proper headers and bullet points
- **Note:** Image extraction is DISABLED (no-images policy for labs/notes)

### Step 4: Review & Edit
- Open converted file
- Double-check formatting
- Add cross-links to related files using Obsidian syntax: `[[File Name|Display Text]]`
- Fill in missing frontmatter fields (topic, tags)
- Remove any remaining artifacts (page numbers, "Official (Open)" headers)

### Recommended Frequency
- **Ideal:** After each class (immediate conversion)
- **Minimum:** Daily batch conversion

---

## Organization System

### Navigation Methods

**1. MOC Files (Map of Content)**
- Use for: High-level course overview
- Contains: Course structure, key topics, assessment breakdown
- Example: `EGE353 Autonomous Mobile Robotics - MOC.md`

**2. Vault Index (.vault-index.md)**
- Use for: AI agent coordination, tracking gaps
- Contains: Course metadata, file lists, missing notes, maintenance log
- AI reads this first for any vault work

**3. Obsidian Graph View**
- Use for: Visual exploration of connections
- Shows: Cross-links between files, related topics

**4. Main Index (NYPY3 - Main Index.md)**
- Use for: Human-readable navigation
- Contains: Quick links to all courses and key files

### Cross-Linking Strategy
- Link related labs: `[[EGE353 Lab 1 Notes|Lab 1]] | [[EGE353 Lab 2 - ROS Nodes and Topics|Lab 2]]`
- Link to appendix: `[[EGE321 Lab3 Time and Frequency Domain Analysis of a digital signal- Appendix|Lab 3 Appendix]]`
- Link across courses when topics overlap

---

## Study Workflow

### Topic-Focused Study
1. **Select topic** (e.g., "ROS Services")
2. **Navigate** to relevant files via MOC or search
3. **Read** main content
4. **Cross-reference** with linked files
5. **Consult Senior Notes** for alternative explanations
6. **Ask AI** to summarize or explain concepts

### Example Study Session
```
1. Open EGE353 MOC → Find "ROS Services" section
2. Click link to EGE353 Lab 3 - ROS Services.md
3. Read through lab content
4. Follow cross-link to related topics
5. If confused, ask AI: "Explain ROS services and parameters"
6. Check Senior Notes for additional examples
7. Add personal notes/annotations
```

### Tracking Progress
- Use vault index "Missing Notes" section to track what's missing
- Mark completed topics in MOC files
- Update `.daily-maintenance-prompt.md` after study sessions

---

## AI Assistant Usage

### Common Tasks

**1. Formatting & Cleanup**
- "Format this lab file properly"
- "Remove page numbers and 'Official (Open)' headers"
- "Add proper markdown headings and bullet points"

**2. Summarization**
- "Summarize this chapter in 5 bullet points"
- "Give me an overview of ROS topics"
- "What are the key concepts in this lab?"

**3. Explanation**
- "Explain Fourier series for square waves"
- "How does the spectrum analyzer work?"
- "What's the difference between time and frequency domain?"

**4. Finding Information**
- "Find all notes about oscilloscopes"
- "What files mention ROS services?"
- "Show me all lab files for EGE321"

**5. Assignment Help**
- "Write a brief for this assignment"
- "Draft a response to this question"
- "Find relevant info for this topic"
- "Suggest formatting for this report"

**6. Deadline Management**
- "What deadlines are coming up this week?"
- "Remind me about upcoming assessments"
- "Update the schedule dashboard"

### Study Assistance
- "Quiz me on ROS topics"
- "Explain this concept in simpler terms"
- "Create a study plan for EGE353"
- "What should I focus on for the exam?"

---

## Assignment Workflow

### Step 1: Understand Requirements
- Open assignment file
- Ask AI to summarize requirements
- Identify key deliverables

### Step 2: Gather Information
- Search vault for relevant notes
- Consult Senior Notes for examples
- Ask AI to find specific information

### Step 3: Draft Content
- Ask AI to write draft/outline
- Use vault content as reference
- Cite sources with cross-links

### Step 4: Format & Polish
- Ask AI to suggest formatting
- Apply consistent markdown structure
- Add proper YAML frontmatter

### Step 5: Review
- Cross-check with assignment requirements
- Ensure all deliverables are met
- Final polish

---

## Tracking & Maintenance

### Daily Maintenance (via .daily-maintenance-prompt.md)
1. Check `_to_upload/` for new files
2. Run conversion script
3. Format and link new files
4. Update vault index
5. Check for missing notes

### Weekly Maintenance
1. Review all new notes from the week
2. Add cross-links between related files
3. Update MOC files with new topics
4. Check Senior Notes for relevant additions
5. Update schedule dashboard

### What to Track
- Uploaded vs. not uploaded materials
- Studied vs. not studied topics
- Upcoming deadlines
- Missing notes/gaps
- Assignment progress

### Pain Point Solution: Tracking Unuploaded Materials
**Problem:** Hard to figure out what hasn't been uploaded yet.

**Solution:**
1. Keep a simple checklist in `_to_upload/README.md`:
```markdown
## Upload Checklist
- [ ] EGE321 Lesson 6
- [ ] EGE353 Lab 5
- [ ] EGE351 Lecture 5
```
2. After conversion, mark as done
3. Cross-reference with Brightspace file list

---

## Handling Diagrams

### The Problem
- PDFs/PPTX contain diagrams
- Too many screenshots clog vault/brain
- Hard to gauge what to screenshot vs. leave

### Current Policy
- **No-images policy** for labs and notes in EGE320, EGE321, EGE322, EGE351, EGE353, EGE301
- Images extracted by conversion script are deleted
- Rationale: Text is more searchable, less clutter

### Recommended Approach

**1. Text-First Strategy**
- Convert diagrams to text descriptions
- Example: Instead of screenshot of circuit diagram, write:
  ```
  ## Circuit Diagram
  - Input: 5V DC
  - Components: R1=1kΩ, R2=2kΩ, C1=10µF
  - Configuration: Voltage divider with RC filter
  ```

**2. Selective Screenshot Policy**
- Only screenshot if:
  - Diagram is critical and cannot be described in text
  - It's a reference image you'll need frequently
  - It's a complex visual that text can't capture

**3. External Reference Strategy**
- Keep original PDF/PPTX in a separate folder (not in vault)
- Reference the original file in markdown:
  ```
  See original PDF: `../_originals/EGE321 Lab3.pdf` page 5
  ```

**4. Diagram Description Template**
```markdown
## [Diagram Name]
**Type:** [Circuit diagram/Flow chart/Block diagram/etc]
**Key Elements:**
- [Element 1]: [Description]
- [Element 2]: [Description]
**Relationships:** [How elements connect]
**Purpose:** [What the diagram shows]
```

---

## Replication Guide

### To Replicate This Workflow in Another Project

#### Phase 1: Setup Vault Structure
```
NewProject/
├── .vault-index.md
├── .daily-maintenance-prompt.md
├── 📅 Schedule & Assessments Dashboard.md
├── NewProject - Main Index.md
├── Course1 - MOC.md
├── Course2 - MOC.md
├── Course1/
│   ├── Topic1.md
│   ├── Topic2.md
│   └── assets/
├── Course2/
│   ├── Topic1.md
│   └── Topic2.md
├── _tools/
│   └── convert_to_md.py
├── _to_upload/
│   ├── README.md
│   ├── converted/
│   └── done/
└── _docs/
    └── Study-Workflow-Guide.md
```

#### Phase 2: Copy Conversion Script
- Copy `_tools/convert_to_md.py` from NYPY3
- Update COURSE_MAP with new course codes
- Update COURSE_PATTERNS if needed
- Test with sample files

#### Phase 3: Create Index Files
- Create `.vault-index.md` with course metadata
- Create `.daily-maintenance-prompt.md` with maintenance checklist
- Create MOC files for each course
- Create main index for navigation

#### Phase 4: Define Policies
- Decide on no-images policy (or modify)
- Define naming conventions
- Set up cross-linking strategy
- Define YAML frontmatter structure

#### Phase 5: Ingest Initial Content
- Collect existing materials
- Run conversion script
- Format and link files
- Update vault index

#### Phase 6: Establish Routines
- Daily: Check _to_upload, run conversion
- Weekly: Review and link new files
- Per assignment: Use AI for drafting and formatting

### Key Files to Copy
1. `_tools/convert_to_md.py` — Conversion script
2. `.vault-index.md` — Index structure (adapt to new courses)
3. `.daily-maintenance-prompt.md` — Maintenance checklist
4. MOC file templates — Course organization structure
5. This guide — For reference

### Customization Points
- Course codes and folder names
- Frontmatter fields
- Tagging strategy
- Cross-linking patterns
- Maintenance frequency

---

## Quick Reference

### Common Commands
```bash
# Convert all files in _to_upload/
python _tools/convert_to_md.py

# Search for specific topic (in Obsidian)
Ctrl+Shift+F: Search across all files

# Open graph view
Ctrl+G: Visualize connections
```

### AI Prompt Templates
- **Summarize:** "Summarize this [file/topic] in [X] bullet points"
- **Explain:** "Explain [concept] like I'm new to this"
- **Find:** "Find all notes about [topic]"
- **Format:** "Format this file properly with headings and bullet points"
- **Draft:** "Write a draft for [assignment] based on these notes"

### File Naming Conventions
- Labs: `[Course Code] Lab [Number] - [Topic].md`
- Lessons: `Lesson [Number] [Topic].md`
- Assignments: `[Course Code] Assignment [Number].md`
- Reference: `[Topic] - Reference.md`

### Frontmatter Template
```yaml
---
tags:
  - [COURSE]
  - [TYPE]
course: [Course Name]
topic: [Topic Name]
source: [Source File]
converted: [YYYY-MM-DD]
---
```

---

## Conclusion

This workflow enables efficient ingestion, organization, and study of course materials using Obsidian + AI assistance. The key principles are:

1. **Automate ingestion** with conversion script
2. **Organize by course** with consistent structure
3. **Cross-link everything** for easy navigation
4. **Use AI strategically** for formatting, summarizing, and drafting
5. **Track progress** with index and maintenance prompts
6. **Keep text-first** for searchability and reduced clutter

To replicate in another project, copy the structure, adapt the course mappings, and establish the same routines.

---

**Last Updated:** 2026-05-14
**Version:** 1.0

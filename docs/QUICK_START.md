# CAIS Autopoietic System - Quick Start Guide

## What is this?

This system creates itself from your documents. It reads your instructions from Google Drive and builds a complete working system.

## Step 1: Setup

1. Clone or download this repository
2. Run `bash scripts/deploy.sh`
3. Place your Google Drive service account key in `config/security/gdrive-credentials.json`

## Step 2: Add Your Documents

1. **Constitution PDFs** (Required): Place in `input/constitution/`
   - These are the PDFs that define the system architecture
   - Include all PDFs from your conversation

2. **Building Code PDFs** (Optional): Place in `input/laws/`
   - Building codes and regulations for each jurisdiction
   - The system will index them for semantic search

3. **Instruction PDFs** (Optional): Place in `input/instructions/`
   - Your own instruction documents
   - Alternative to downloading from Google Drive

## Step 3: Run the System

```bash
cd ~/PROMETHEUS
source venv_prometheus/bin/activate
python -m src.dashboard.sovereign_dashboard

# CAIS Code Compliance Documentation

Welcome to the CAIS Code Compliance documentation.

## Overview

CAIS Code Compliance is a forensic evidence generation tool for construction code violations. It receives documents from 21 platforms, analyzes them visually and semantically, detects code violations using AI, generates forensic evidence, and delivers a Forensic Facts Dossier without CAIS commentary.

## Key Features

- **21 Platform Integration**: Procore, Autodesk Forma, Oracle Aconex, Bentley iTwin, PlanGrid, Fieldwire, Buildertrend, Newforma, SharePoint, Dropbox, Google Workspace, ServiceTitan, Simpro, Esri ArcGIS, Cityworks, Revit, AutoCAD, Bluebeam Revu, Accela, AppStore, GooglePlay

- **Multi-Agent System**:
  - PlanInspector: Visual scanning with OCR at 200 DPI
  - CodeMatcher: Semantic code matching with pgvector
  - JurisdictionOrchestrator: Jurisdiction detection
  - ReportGenerator: Forensic Facts Dossier creation
  - ChameleonEngine: Visual adaptation for 21 marketplaces
  - SelfHealingSystem: Automatic recovery from failures

- **Security Features**:
  - WORM Ledger: Immutable audit trail
  - SecurityGuard: Anti-hacker protection
  - Kill Switch: Emergency operation termination
  - Rate Limiting: API protection

- **Subscription Plans**:
  - Free Trial: 30 days
  - Monthly: $299/month
  - Annual: $2,999/year

## Quick Links

- [Getting Started](getting_started.md)
- [API Reference](api_reference.md)
- [Deployment Guide](deployment.md)
- [Architecture](architecture.md)

## Version

**Current Version:** 10.0

## License

Proprietary - All rights reserved.

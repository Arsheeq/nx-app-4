# Nubinix Cloud Insights - System Architecture

## Overview

Nubinix Cloud Insights is a Flask-based web application for generating cloud utilization and billing reports for AWS and Azure resources. The system features a modern HTML/CSS frontend with Alpine.js for interactivity and a Python Flask backend. The application provides a wizard-based interface that connects to your organization's SSM Parameter Store to fetch client credentials automatically, eliminating the need for manual credential entry.

## User Preferences

Preferred communication style: Simple, everyday language.
Uses organization SSM for AWS credential management - no manual credential entry required.

## System Architecture

### Frontend Architecture
- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS with shadcn/ui component library
- **State Management**: Zustand for global state management
- **Data Fetching**: TanStack Query (React Query) for server state
- **Routing**: Wouter for lightweight client-side routing
- **Build Tool**: Vite with custom plugins for theme and development

### Backend Architecture
- **Flask Backend**: Pure Python Flask application for API and web interface
- **Data Storage**: Local JSON file-based storage for minimal data persistence
- **Auto-Cleanup Service**: Automatic removal of sensitive data 5 minutes after report generation
- **Cloud SDKs**: Boto3 for AWS integration and Azure SDK for Azure resource management
- **SSM Integration**: Organization SSM Parameter Store for client credential management

### Data Storage Solutions
- **Local Storage**: Simple JSON file-based storage in `local_data` directory
- **No Database**: Lightweight approach without database dependencies
- **Data Models**: Simple Python classes for CloudAccount, Resource, and Report data structures

## Key Components

### 1. Wizard-Based User Interface
The frontend implements a multi-step wizard for report generation:
- Cloud provider selection (AWS/Azure)
- Report type selection (utilization/billing)
- Credential input and validation
- Resource discovery and selection
- Report frequency configuration
- Report generation and download

### 2. Cloud Integration Layer
- **AWS Integration**: EC2 and RDS resource discovery across all regions with SSM credential management
- **Azure Integration**: VM and database resource discovery with manual credentials
- **Nubinix Client Management**: Fetch client list and credentials from organization SSM
- **Credential Validation**: Real-time validation of cloud credentials
- **Resource Caching**: Stores discovered resources in PostgreSQL for performance

### 3. Report Generation Service
- **Python Backend**: Separate Flask service for PDF generation
- **Metrics Collection**: Collects utilization metrics from cloud APIs
- **Visualization**: Matplotlib for charts and graphs
- **PDF Generation**: ReportLab for professional report layout

### 4. Local Data Storage
- **Cloud Accounts**: JSON files storing cloud provider credentials and account information
- **Resources**: JSON files caching discovered cloud resources with metadata
- **Reports**: JSON files tracking generated reports with status and download URLs

## Data Flow

### 1. User Authentication & Setup (AWS)
1. User selects AWS cloud provider
2. System fetches available Nubinix clients from organization SSM
3. User selects client from dropdown
4. System automatically retrieves credentials from SSM
5. Credentials validated and cloud account record created

### 1a. User Authentication & Setup (Azure)
1. User selects Azure cloud provider
2. Enters Azure service principal credentials manually
3. System validates credentials against Azure APIs
4. Cloud account record created in database

### 2. Resource Discovery
1. Backend scans all regions for the selected cloud provider
2. Discovers EC2/RDS instances (AWS) or VMs/databases (Azure)
3. Stores resource metadata in PostgreSQL
4. Frontend displays resources in filterable tables

### 3. Report Generation
1. User selects resources and report frequency
2. Frontend sends request to Flask backend
3. Flask backend calls utility functions directly
4. Backend collects metrics and generates PDF using matplotlib/ReportLab
5. PDF returned directly to user for download
6. Report metadata stored in database

## External Dependencies

### Cloud Provider SDKs
- **AWS SDK v3**: For EC2 and RDS operations
- **Azure SDK**: For resource management (planned implementation)

### UI Framework
- **shadcn/ui**: Comprehensive component library built on Radix UI
- **Radix UI**: Headless, accessible UI primitives
- **Tailwind CSS**: Utility-first CSS framework

### Development Tools
- **Vite**: Fast build tool with HMR and plugins
- **TypeScript**: Type safety across frontend and backend
- **ESBuild**: Fast JavaScript bundler for production builds

### Report Generation
- **Matplotlib**: Chart generation in Python service
- **ReportLab**: PDF document creation
- **Flask**: Lightweight Python web framework

## Deployment Strategy

### Development Environment
- **Local Development**: Flask development server with automatic reloading
- **Hot Reloading**: Flask's built-in development mode with automatic reload
- **Data Storage**: Local JSON files in `local_data` directory

### Production Build
- **Frontend**: HTML templates with Alpine.js served by Flask
- **Backend**: Single Flask process serving API and templates
- **Data Storage**: Local JSON files for lightweight data persistence
- **SSM Integration**: AWS SDK accessing organization parameter store

### Configuration Management
- **Environment Variables**: Cloud credentials and session secrets
- **No Build Scripts**: Simple Flask application with direct file serving
- **Asset Management**: Static assets served through Flask

## Recent Changes (July 22, 2025)

- **Auto-Cleanup Service**: Added automatic cleanup service that removes all client details and sensitive data 5 minutes after report downloads
- **Security Enhancement**: Implemented comprehensive data sanitization including credentials, temp files, and client information
- **Manual Cleanup**: Added force cleanup endpoint for immediate data removal when needed
- **Database Removal**: Removed all database dependencies and configurations per user request
- **Local Storage Implementation**: Migrated to simple JSON file-based storage in `local_data` directory
- **Chart Format Enhancement**: Updated chart generation to match exact formatting requirements with proper time/date displays
- **Report Generator Updated**: Enhanced PDF report generation to match exact format from provided examples
- **Custom Canvas Implementation**: Added NumberedCanvas for proper page numbering and footer placement
- **Cover Page Enhancement**: Implemented account-specific cover page with proper branding
- **Metric Display Simplification**: Updated metric displays to use simple average values without complex charts
- **Instance State Handling**: Added proper handling for stopped instances (no metrics processing)
- **RDS Support**: Enhanced RDS instance reporting with appropriate metric labels and units
- **Migration to Replit**: Successfully migrated project from Replit Agent to standard Replit environment

Previous Changes (July 20, 2025):
- **Migration Completed**: Successfully migrated from Node.js/TypeScript to pure Flask application
- **SSM Integration Added**: Implemented organization SSM integration for automatic AWS credential management
- **Client Selection**: Added Nubinix client dropdown with automatic credential fetching
- **Simplified Architecture**: Consolidated to single Flask backend with integrated report generation
- **Storage Simplification**: Moved from database dependency to lightweight JSON file storage

The architecture now prioritizes simplicity and security with organization-managed credentials, eliminating manual AWS credential entry while maintaining full functionality for cloud resource reporting. The application uses local JSON storage for maximum simplicity and portability. Report generation has been enhanced to match professional PDF formatting standards.
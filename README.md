# PULSE V2 — Backend

PULSE is an AI-assisted civic engagement platform that enables citizens to report local issues, track their resolution, and participate in community-driven initiatives through a gamified experience.

This repository contains the Django REST Framework backend, which powers authentication, report management, AI-assisted verification, gamification, media storage, and administrative workflows. The React frontend is available in the related repository.

The project was built with significant AI assistance. The developer was responsible for project ideation, feature planning, workflow design, testing, debugging, deployment, and iterative refinement. The AI-assisted development process is documented in a dedicated section below.

---

## Highlights

- JWT authentication with access and refresh token support
- AI-powered image verification using Google Gemini
- Gamification engine with XP tracking, automatic level calculation, and leaderboards
- Twilio SMS notifications for report submissions
- Cloudinary media storage for all uploaded images
- Graceful AI fallback behavior when external services are unavailable
- CORS restricted to trusted frontend origins
- Configured for deployment on Render

---

## Demo

A walkthrough demonstrating the backend APIs, AI verification workflow, Django administration panel, and overall backend functionality.

[Watch the Demo Video](https://drive.google.com/file/d/1_Zes1qMhu4ZLVhEQ-AJWJl2Gh9DkSDW4/view?usp=drive_link)

---

## Table of Contents

- [Overview](#overview)
- [Backend Responsibilities](#backend-responsibilities)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Database Models](#database-models)
- [API Endpoints](#api-endpoints)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [AI-Assisted Development](#ai-assisted-development)
- [Known Limitations](#known-limitations)
- [Related Repositories](#related-repositories)

---

## Overview

The PULSE backend is a REST API built on Django and Django REST Framework. It serves the React frontend and handles all data persistence, business logic, and third-party integrations.

When a citizen submits a civic report, the backend processes the uploaded image and description using Google Gemini. Based on the AI analysis and confidence score, the report is marked as **Verified**, **Pending**, or **Rejected**. Reports that cannot be confidently verified remain pending for manual review.

A similar AI-assisted verification process is also applied to community mission proof submissions before rewards are granted.

The backend also manages the gamification layer. XP is awarded for verified reports (either immediately after AI verification or later through manual admin approval) and for successfully completed missions. User levels are calculated automatically based on accumulated XP. Leaderboard rankings are derived from the same data.

All media uploads — profile pictures, report images, resolution proofs, and mission submissions — are stored on Cloudinary rather than the local filesystem, making the backend stateless and deployment-friendly.

---

## Backend Responsibilities

The backend is responsible for:

- User authentication and profile management
- Civic report creation, retrieval, and moderation
- AI-assisted image verification using Google Gemini
- Mission management and participation tracking
- XP management, user levels, and leaderboard generation
- Community notice management
- Media upload handling through Cloudinary
- SMS notifications via Twilio
- REST API endpoints consumed by the React frontend

---

## Tech Stack

| Layer             | Technology                          |
| ----------------- | ----------------------------------- |
| Framework         | Django, Django REST Framework       |
| Database          | PostgreSQL                          |
| Authentication    | JWT (djangorestframework-simplejwt) |
| AI Integration    | Google Gemini API                   |
| Media Storage     | Cloudinary                          |
| SMS Notifications | Twilio                              |
| Static Files      | WhiteNoise                          |
| Deployment        | Render                              |

---

## Project Structure

```
PULSE-V2-Backend/
├── api/
│   ├── migrations/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── serializers.py
│   ├── urls.py
│   ├── utils.py
│   └── views.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── media/
├── manage.py
├── requirements.txt
└── build.sh
```

---

## Database Models

The backend uses five primary models.

### Profile

Extends Django's built-in `User` model with civic engagement and profile information.

- One-to-one relationship with `User`
- Stores XP, user level, profile details, and contact information
- Automatically recalculates the user's level based on accumulated XP

| XP Range  | Level    |
| --------- | -------- |
| 0 – 99    | Citizen  |
| 100 – 299 | Scout    |
| 300 – 499 | Guardian |
| 500+      | Hero     |

A Django signal automatically creates a Profile whenever a new User registers.

### Report

Stores civic issue reports submitted by users.

- Linked to User through a foreign key
- Stores report details, location, uploaded media, and timestamps
- Maintains AI analysis, confidence scores, report status, and reward tracking to prevent duplicate XP awards.
- Supports user feedback and post-resolution ratings

### Mission

Represents community missions that users can participate in to earn XP.

- Stores mission details, reward points, and display icon
- Managed through the Django administration panel

### UserMission

Tracks each user's participation in community missions.

- Links a user to a mission
- Stores submitted proof images and AI verification results
- Tracks mission completion status and reward eligibility

### Notice

Stores community announcements displayed within the platform.

- Includes title, content, author, creation timestamp, and pinned status
- Pinned notices are prioritized in the frontend notice board

### Relationship Overview

```
User
 ├── One-to-One ──► Profile
 ├── One-to-Many ─► Report
 ├── One-to-Many ─► Notice
 └── One-to-Many ─► UserMission
                      └── Many-to-One ─► Mission
```

---

## API Endpoints

### Authentication

| Method | Endpoint              | Description                          | Auth Required |
| ------ | --------------------- | ------------------------------------ | ------------- |
| POST   | `/api/token/`         | Obtain JWT access and refresh tokens | No            |
| POST   | `/api/token/refresh/` | Refresh an expired access token      | No            |

### User

| Method      | Endpoint              | Description                               | Auth Required |
| ----------- | --------------------- | ----------------------------------------- | ------------- |
| POST        | `/api/user/register/` | Register a new user account               | No            |
| GET         | `/api/user/profile/`  | Retrieve the authenticated user's profile | Yes           |
| PUT / PATCH | `/api/user/update/`   | Update profile information                | Yes           |

### Reports

| Method      | Endpoint                    | Description                                     | Auth Required |
| ----------- | --------------------------- | ----------------------------------------------- | ------------- |
| GET         | `/api/reports/`             | List all civic reports                          | No            |
| POST        | `/api/reports/`             | Submit a new civic report (multipart/form-data) | Yes           |
| GET         | `/api/reports/<id>/`        | Retrieve a specific report                      | Yes           |
| PUT / PATCH | `/api/reports/<id>/`        | Update a report                                 | Yes           |
| DELETE      | `/api/reports/<id>/delete/` | Delete a report                                 | Yes           |

Users can only access and delete their own reports.

### Missions

| Method | Endpoint                           | Description                                                    | Auth Required |
| ------ | ---------------------------------- | -------------------------------------------------------------- | ------------- |
| GET    | `/api/missions/`                   | List available missions                                        | Yes           |
| POST   | `/api/missions/<id>/join/`         | Join a mission                                                 | Yes           |
| POST   | `/api/missions/<id>/submit_proof/` | Submit mission proof for AI verification (multipart/form-data) | Yes           |

### Community

| Method | Endpoint            | Description                   | Auth Required |
| ------ | ------------------- | ----------------------------- | ------------- |
| GET    | `/api/notices/`     | List community notices        | No            |
| POST   | `/api/notices/`     | Create a community notice     | Yes           |
| GET    | `/api/leaderboard/` | Retrieve leaderboard rankings | Yes           |

### AI Assistant

| Method | Endpoint        | Description                              | Auth Required |
| ------ | --------------- | ---------------------------------------- | ------------- |
| POST   | `/api/ai-chat/` | Send a message to the PULSE AI assistant | No            |

### System

| Method | Endpoint     | Description                 | Auth Required |
| ------ | ------------ | --------------------------- | ------------- |
| GET    | `/api/ping/` | Health check endpoint       | No            |
| GET    | `/admin/`    | Django administration panel | Admin only    |

---

## Getting Started

### Prerequisites

- Python 3.10 or above
- PostgreSQL database (local or hosted)
- A `.env` file with the required environment variables (see below)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/Prakhar4real/PULSE-V2-Backend.git
cd PULSE-V2-Backend
```

2. Create and activate a virtual environment:

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root and populate the required variables (see Environment Variables below). Ensure a PostgreSQL database is available and its connection string is set in `DATABASE_URL`.

5. Apply database migrations:

```bash
python manage.py migrate
```

6. (Optional) Create an administrator account:

```bash
python manage.py createsuperuser
```

7. Start the development server:

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`.

---

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
SECRET_KEY=
DEBUG=

DATABASE_URL=

GEMINI_API_KEY=

TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
ADMIN_PHONE_NUMBER=

CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

Some features depend on third-party service credentials. Missing Cloudinary, Gemini, or Twilio credentials will disable their respective functionality.

---

## Deployment

The backend is configured for deployment on Render. The `build.sh` script handles the deployment sequence automatically:

```bash
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
```

Static files are served using WhiteNoise. Media files are stored on Cloudinary and do not require persistent disk storage on the server.

CORS is configured to allow requests only from the local React development server and the deployed Vercel frontend. All other origins are blocked.

---

## AI-Assisted Development

This project was built with substantial AI assistance, primarily through Google Gemini. A significant portion of the implementation was developed through iterative AI-assisted workflows involving prompting, testing, debugging, and refinement.

The developer's contributions included:

- Product ideation and feature planning
- API design and workflow decisions
- Prompt engineering and iterative refinement
- Integration testing and debugging
- Deployment configuration and management

This disclosure is intentional. AI-assisted development is a legitimate and increasingly common approach to building software. The goal here is transparency about the process, not concealment of it.

---

## Known Limitations

- AI image verification depends on access to the Google Gemini API. On a free-tier key, verification may fail under load or after quota limits are reached. When the AI service is unavailable, reports and mission submissions fall back to manual review instead of interrupting the submission process.
- The platform has not been load-tested for large-scale production use.
- Twilio SMS notifications require an active Twilio account with a verified number. Notification failures are handled gracefully and do not interrupt report creation.
- There is no API rate limiting configured at the application layer. For production use, rate limiting should be implemented or handled at the infrastructure level.

---

## Related Repositories

- [PULSE V2 Frontend](https://github.com/Prakhar4real/PULSE-V2-Frontend) — React frontend with citizen dashboard, reporting interface, gamification UI, and administrative workflows.

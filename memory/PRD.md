# MyHostIQ - Product Requirements Document

## Original Problem Statement
AI-powered virtual concierge platform for short-term rental hosts. Hosts create chatbots for their apartments that answer guest questions about check-in, WiFi, house rules, local recommendations, and nearby places — in the guest's language. Uses Mapbox for proximity search with smart fallback (host recommendations first, Mapbox API second).

## Architecture
- **Frontend**: React 19 + Tailwind CSS + Shadcn/UI (single App.js)
- **Backend**: FastAPI + Motor (async MongoDB) (single server.py)
- **Database**: MongoDB (Atlas or local)
- **AI**: GPT-4o-mini via Emergent Integrations
- **Maps**: Mapbox Geocoding & Search API
- **Email**: SendGrid

## What's Been Implemented
- User auth (register, login, forgot/reset password)
- Apartment CRUD with geocoding
- AI chatbot per apartment (GPT-4o-mini)
- Smart proximity search (host recommendations → Mapbox fallback)
- Multilingual support (BS, EN, DE, FR, ES, IT)
- Property import from Airbnb/Booking.com
- Local recommendations with address autocomplete & walking distances
- QR code PDF generation
- White-label branding per host
- Admin dashboard (users, apartments, stats)
- Email integration (SendGrid)
- Analytics dashboard with AI insights — ALL REAL DATA
- Mobile-optimized UI
- Comprehensive README.md for GitHub/local setup
- Phone input with country code selector (24 countries)
- Email input validation with visual feedback
- Time picker for check-in/check-out (AM/PM dropdown)
- Real-time billing stats (trial days from user created_at, real chat/session counts)
- AI Response Quality computed from actual success rate
- Guest sessions and views from real MongoDB data

## Completed Tasks (This Session)
- [2026-06-30] Created comprehensive README.md for GitHub with local setup guide
- [2026-06-30] Added PhoneInput, EmailInput, TimePicker components across all forms
- [2026-06-30] Replaced ALL hardcoded analytics/billing values with real MongoDB data
- [2026-06-30] Free trial now calculates from user.created_at (7-day window, real dates)
- [2026-06-30] AI Response Quality computed from actual chat success rate
- [2026-06-30] Billing stats (AI Chats, Guest Sessions) fetched from analytics endpoint

## Backlog
- P1: Refactor backend server.py into modular routes/models/services
- P1: Refactor frontend App.js into separate components and pages
- P2: Stripe payment integration
- P2: Advanced analytics dashboard
- P3: Email notifications for bookings
- P3: Minor backend linting fixes (F811)

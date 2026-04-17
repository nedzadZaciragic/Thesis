# MyHostIQ

AI-powered virtual concierge for short-term rental hosts. MyHostIQ lets property owners create intelligent chatbots for their apartments that answer guest questions about check-in instructions, WiFi, house rules, local recommendations, and nearby places — all in the guest's language.

Hosts share a simple link (or QR code) with their guests through Airbnb/Booking.com automated messages. Guests click the link and chat directly with an AI assistant that knows everything about the property and its surroundings.

---

## Features

- **AI Chatbot per Apartment** — Each property gets its own context-aware assistant powered by GPT-4o-mini that knows check-in/out details, WiFi credentials, house rules, and item locations
- **Smart Proximity Search** — Guests ask "Where is the nearest pharmacy?" and get real results via Mapbox, with host recommendations prioritized over API results
- **Multilingual Support** — Automatic language detection (Bosnian, English, German, French, Spanish, Italian) for both proximity queries and general chat
- **Property Import** — Import apartment details directly from Airbnb or Booking.com URLs
- **Local Recommendations** — Hosts add restaurants, hidden gems, and attractions with addresses (autocomplete-powered) and walking distances
- **QR Code Generation** — Downloadable PDF with QR code linking to the apartment's chatbot
- **White-label Branding** — Custom brand name, colors, and AI assistant name per host
- **Admin Dashboard** — Platform-wide management of users, apartments, and analytics
- **Email Integration** — Password reset and notifications via SendGrid
- **Analytics** — Dashboard with chat statistics, popular questions, and AI-powered insights

---

## Tech Stack

| Layer     | Technology                                    |
| --------- | --------------------------------------------- |
| Frontend  | React 19, Tailwind CSS, Shadcn/UI, Axios      |
| Backend   | FastAPI (Python), Pydantic, Motor (async MongoDB driver) |
| Database  | MongoDB (local or Atlas)                       |
| AI        | OpenAI GPT-4o-mini via Emergent Integrations   |
| Maps      | Mapbox Geocoding & Search API                  |
| Email     | SendGrid                                       |

---

## Prerequisites

- **Node.js** v18+ and **Yarn**
- **Python** 3.10+
- **MongoDB** — either a local instance or a [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) free cluster
- **API Keys** (see [Environment Variables](#environment-variables) below)

---

## Project Structure

```
myhost-iq/
├── backend/
│   ├── server.py           # FastAPI application (routes, models, AI logic)
│   ├── requirements.txt    # Python dependencies
│   └── .env                # Backend environment variables
├── frontend/
│   ├── src/
│   │   ├── App.js          # Main React application
│   │   ├── components/ui/  # Shadcn UI components
│   │   └── index.js        # Entry point
│   ├── package.json
│   ├── tailwind.config.js
│   └── .env                # Frontend environment variables
└── README.md
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/myhost-iq.git
cd myhost-iq
```

### 2. Set up the backend

```bash
cd backend

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Install Emergent Integrations (required for AI features)
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
```

### 3. Configure backend environment variables

Create a `.env` file inside the `backend/` folder:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=myhostiq
JWT_SECRET=change-this-to-a-strong-random-string
ENCRYPTION_KEY=change-this-32-character-string!!
FRONTEND_URL=http://localhost:3000
CORS_ORIGINS=*
EMERGENT_LLM_KEY=your-emergent-universal-key
MAPBOX_API_KEY=your-mapbox-api-key
SENDGRID_API_KEY=your-sendgrid-api-key
```

> **Where to get the keys:**
>
> | Key                  | Where to get it                                                                                     |
> | -------------------- | --------------------------------------------------------------------------------------------------- |
> | `EMERGENT_LLM_KEY`   | [Emergent Platform](https://emergentagent.com) → Profile icon (top-right) → Universal Key → Copy   |
> | `MAPBOX_API_KEY`     | [Mapbox](https://account.mapbox.com/access-tokens/) → Create a free account → Copy default token    |
> | `SENDGRID_API_KEY`   | [SendGrid](https://app.sendgrid.com/settings/api_keys) → Create a free account → Create API Key    |
>
> **Note:** If you're using MongoDB Atlas instead of a local instance, replace `MONGO_URL` with your Atlas connection string:
> ```
> MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/?appName=Cluster0
> ```

### 4. Start the backend

```bash
cd backend
uvicorn server:app --reload --port 8001
```

The API will be available at `http://localhost:8001`. You can verify it's running by visiting `http://localhost:8001/api/` in your browser.

### 5. Set up the frontend

Open a new terminal:

```bash
cd frontend

# Install dependencies
yarn install
```

### 6. Configure frontend environment variables

Create a `.env` file inside the `frontend/` folder:

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

### 7. Start the frontend

```bash
cd frontend
yarn start
```

The app will open at `http://localhost:3000`.

---

## Usage

### As a Host

1. **Register** — Create an account on the landing page
2. **Add an Apartment** — Fill in address, check-in/out details, WiFi info, house rules, and item locations
3. **Add Recommendations** — Add your favorite restaurants, hidden gems, and attractions with real addresses
4. **Get the Guest Link** — Copy the chatbot link or download the QR code PDF
5. **Share with Guests** — Add the link to your Airbnb/Booking.com automated messages

### As a Guest

1. **Click the link** your host shared (or scan the QR code)
2. **Chat** — Ask anything about the apartment, neighborhood, or city
3. Examples:
   - "What's the WiFi password?"
   - "Where is the nearest supermarket?"
   - "What time is check-out?"
   - "Can you recommend a good restaurant?"

### As an Admin

Navigate to `/admin` and log in with admin credentials to manage all users and apartments on the platform.

---

## API Endpoints

### Authentication
| Method | Endpoint                    | Description              |
| ------ | --------------------------- | ------------------------ |
| POST   | `/api/auth/register`        | Register a new host      |
| POST   | `/api/auth/login`           | Host login               |
| POST   | `/api/auth/forgot-password` | Request password reset   |
| POST   | `/api/auth/reset-password`  | Reset password with token|
| GET    | `/api/auth/me`              | Get current user profile |

### Apartments
| Method | Endpoint                              | Description                      |
| ------ | ------------------------------------- | -------------------------------- |
| POST   | `/api/apartments`                     | Create a new apartment           |
| GET    | `/api/apartments`                     | List host's apartments           |
| GET    | `/api/apartments/{id}`                | Get apartment details            |
| PUT    | `/api/apartments/{id}`                | Update apartment                 |
| GET    | `/api/public/apartments/{id}`         | Public apartment info (for guests)|
| POST   | `/api/apartments/import-from-url`     | Import from Airbnb/Booking.com   |

### Chat
| Method | Endpoint          | Description                              |
| ------ | ----------------- | ---------------------------------------- |
| POST   | `/api/guest-chat` | Public AI chat (no auth, rate-limited)   |
| POST   | `/api/chat`       | Authenticated AI chat                    |

### Admin
| Method | Endpoint                      | Description             |
| ------ | ----------------------------- | ----------------------- |
| POST   | `/api/admin/login`            | Admin login             |
| GET    | `/api/admin/users`            | List all users          |
| GET    | `/api/admin/apartments`       | List all apartments     |
| PUT    | `/api/admin/apartments/{id}`  | Edit any apartment      |
| DELETE | `/api/admin/apartments/{id}`  | Delete apartment        |
| GET    | `/api/admin/stats`            | Platform statistics     |

### Analytics
| Method | Endpoint                                      | Description                    |
| ------ | --------------------------------------------- | ------------------------------ |
| GET    | `/api/analytics/dashboard`                    | Host analytics dashboard       |
| GET    | `/api/analytics/insights/{apartment_id}`      | AI-powered property insights   |
| GET    | `/api/analytics/normalized-questions/{id}`    | Grouped guest questions        |
| GET    | `/api/apartments/{id}/chat-history`           | Chat history for apartment     |

---

## Troubleshooting

### "I'm having trouble connecting" in chat
This means the frontend can't reach the backend AI service. Check:
1. **Backend is running** on port 8001 — check the terminal for errors
2. **`EMERGENT_LLM_KEY`** is set correctly in `backend/.env`
3. **`emergentintegrations`** is installed — run: `pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/`
4. **`REACT_APP_BACKEND_URL`** in `frontend/.env` points to `http://localhost:8001`

### MongoDB connection errors
- **Local MongoDB**: Make sure `mongod` is running (`brew services start mongodb-community` on macOS)
- **Atlas**: Verify your IP is whitelisted in Atlas → Network Access, and the connection string is correct

### Frontend not connecting to backend
- Ensure `REACT_APP_BACKEND_URL=http://localhost:8001` in `frontend/.env`
- Restart the frontend after changing `.env` files (`yarn start`)

### Mapbox features not working
- Verify `MAPBOX_API_KEY` is set in `backend/.env`
- Check the key is valid at [Mapbox Account](https://account.mapbox.com/)

---

## License

This project was built as a diploma thesis practical component. All rights reserved.

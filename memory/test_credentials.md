# Test Credentials

## Host Account (Local dev)
- Email: `test.debug@example.com`
- Password: `TestPass123!`
- Created via API registration

## Admin Account
- Username: `myhomeiq_admin`
- Password: `Admin123!MyHomeIQ`
- Endpoint: POST `/api/admin/login`

## Special Access
- Name: `Nedzad Zaciragic` (case-insensitive) — universal guest access, bypasses booking restrictions

## Notes
- Preview environment uses Atlas MONGO_URL which has SSL/IP restrictions. For local testing, switch to `mongodb://localhost:27017`.
- Production: Netlify (Frontend) + Render.com (Backend) + MongoDB Atlas (DB)

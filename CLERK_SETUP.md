# Clerk Authentication Setup Guide

This guide walks you through integrating Clerk authentication with ShelfSense.

## ✅ What's Already Done

The following has been implemented:

### Frontend (Next.js)
- ✅ Installed `@clerk/nextjs` package
- ✅ Created `middleware.ts` for route protection
- ✅ Wrapped app in `ClerkProvider` in `layout.tsx`
- ✅ Created `/sign-in` and `/sign-up` pages with Clerk components
- ✅ Created `.env.local.example` with required environment variables

### Backend (FastAPI)
- ✅ Added `clerk_id` column to User model
- ✅ Created webhook handler at `/api/webhook/clerk`
- ✅ Webhook syncs Clerk users to database automatically

## 🚀 Setup Steps

### 1. Create Clerk Account

1. Go to [Clerk Dashboard](https://dashboard.clerk.com)
2. Sign up or log in
3. Create a new application
4. Select authentication methods (Email, Google, etc.)

### 2. Configure Frontend Environment Variables

1. Copy the example environment file:
   ```bash
   cd frontend
   cp .env.local.example .env.local
   ```

2. Add your Clerk keys to `frontend/.env.local`:
   ```env
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxxx
   CLERK_SECRET_KEY=sk_test_xxxxx
   ```

   Get these from: **Clerk Dashboard → API Keys**

### 3. Configure Backend Environment Variables

Add to `backend/.env`:
```env
CLERK_WEBHOOK_SECRET=whsec_xxxxx
```

Get this from: **Clerk Dashboard → Webhooks** (after creating webhook in step 5)

### 4. Run Database Migration

Add `clerk_id` column to existing database:

```bash
cd backend
python migrate_add_clerk_id.py
```

### 5. Set Up Clerk Webhook

1. In Clerk Dashboard, go to **Webhooks**
2. Click **Add Endpoint**
3. Enter your backend URL: `https://your-domain.com/api/webhook/clerk`
   - For local development: Use [ngrok](https://ngrok.com) or [localtunnel](https://localtunnel.me)
   - Example: `https://abc123.ngrok.io/api/webhook/clerk`
4. Subscribe to these events:
   - `user.created`
   - `user.updated`
   - `user.deleted`
5. Copy the **Signing Secret** and add to backend `.env` as `CLERK_WEBHOOK_SECRET`

### 6. Test the Integration

1. Start backend:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. Start frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Visit `http://localhost:3000`
4. You should be redirected to `/sign-in`
5. Create an account
6. Check backend logs to verify webhook received
7. Verify user created in database:
   ```bash
   sqlite3 backend/shelfsense.db "SELECT id, clerk_id, email, full_name FROM users;"
   ```

## 📝 How It Works

### Authentication Flow

1. **Sign Up/In**: User authenticates via Clerk
2. **Webhook**: Clerk sends `user.created` event to backend
3. **Sync**: Backend creates/updates user in database
4. **Session**: Frontend gets user session from Clerk
5. **API Calls**: Frontend passes Clerk user ID to backend endpoints

### User Context (Hybrid Approach)

ShelfSense uses a hybrid authentication approach:

- **Clerk** handles authentication, sessions, and user management
- **UserContext** (localStorage) remains for backwards compatibility
- Both work together seamlessly

### Protected Routes

The `middleware.ts` protects all routes except:
- `/sign-in`
- `/sign-up`
- `/api/webhook` (for Clerk webhooks)

## 🔧 Updating Existing Components

### Get Current User

```typescript
import { useUser } from '@clerk/nextjs'

function MyComponent() {
  const { user, isLoaded, isSignedIn } = useUser()

  if (!isLoaded) return <div>Loading...</div>
  if (!isSignedIn) return <div>Please sign in</div>

  return <div>Welcome, {user.firstName}!</div>
}
```

### Sign Out Button

```typescript
import { useClerk } from '@clerk/nextjs'

function SignOutButton() {
  const { signOut } = useClerk()

  return (
    <button onClick={() => signOut()}>
      Sign Out
    </button>
  )
}
```

### Backend API with Clerk ID

Update API endpoints to use `clerk_id`:

```python
from app.models.models import User

# Find user by Clerk ID
user = db.query(User).filter(User.clerk_id == clerk_user_id).first()
```

## 🎨 Customizing Clerk UI

The sign-in/up pages use custom styling to match ShelfSense's black theme.

To customize further, edit:
- `app/sign-in/[[...sign-in]]/page.tsx`
- `app/sign-up/[[...sign-up]]/page.tsx`

See [Clerk Appearance Customization](https://clerk.com/docs/components/customization/overview) for options.

## 🔒 Security Considerations

1. **Environment Variables**: Never commit `.env.local` or `.env` files
2. **Webhook Secret**: Keep `CLERK_WEBHOOK_SECRET` secure
3. **HTTPS**: Use HTTPS in production for webhook endpoint
4. **Signature Verification**: Uncomment signature verification in `clerk_webhook.py` for production

## 📚 Resources

- [Clerk Documentation](https://clerk.com/docs)
- [Clerk Next.js Quickstart](https://clerk.com/docs/quickstarts/nextjs)
- [Clerk Webhooks Guide](https://clerk.com/docs/integrations/webhooks/overview)

## 🐛 Troubleshooting

### "Invalid Clerk Keys"
- Check that keys in `.env.local` match your Clerk dashboard
- Ensure keys start with correct prefixes: `pk_test_` and `sk_test_`

### Webhook Not Receiving Events
- Verify webhook URL is accessible (test with ngrok for local dev)
- Check Clerk Dashboard → Webhooks → Recent Events
- Ensure endpoint subscribed to correct events

### User Not Syncing to Database
- Check backend logs for webhook errors
- Verify webhook secret matches Clerk dashboard
- Test webhook endpoint: `GET /api/webhook/clerk/test`

## ✨ Benefits of Clerk

- 🔐 Secure authentication without managing passwords
- 🎨 Customizable UI components
- 📧 Email verification and magic links
- 🔗 Social login (Google, GitHub, etc.)
- 👥 User management dashboard
- 🔔 Webhooks for user events
- 📱 Mobile SDK support
- 🌍 Multi-factor authentication

---

**Questions?** Check the [Clerk Community](https://clerk.com/discord)

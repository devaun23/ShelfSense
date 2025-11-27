# Custom Domain Setup Guide for ShelfSense

Domain: **shelfsense.com**
Registrar: **Cloudflare**

## Domain Structure

| Subdomain | Service | Platform |
|-----------|---------|----------|
| `shelfsense.com` | Frontend (Next.js) | Netlify |
| `www.shelfsense.com` | Redirects to apex | Netlify |
| `api.shelfsense.com` | Backend (FastAPI) | Railway |

---

## Step 1: Cloudflare DNS Setup

Go to [Cloudflare Dashboard](https://dash.cloudflare.com) → Select `shelfsense.com` → **DNS**

### Add these DNS records:

#### Frontend (Netlify)
```
Type: CNAME
Name: @  (or shelfsense.com)
Target: shelfsense99.netlify.app
Proxy: OFF (DNS only - grey cloud)
TTL: Auto
```

```
Type: CNAME
Name: www
Target: shelfsense99.netlify.app
Proxy: OFF (DNS only - grey cloud)
TTL: Auto
```

#### Backend API (Railway)
```
Type: CNAME
Name: api
Target: shelfsense-api.up.railway.app
Proxy: OFF (DNS only - grey cloud)
TTL: Auto
```

> ⚠️ **Important**: Set proxy to OFF (grey cloud) for all records. Netlify and Railway need to handle SSL themselves.

---

## Step 2: Netlify Custom Domain

1. Go to [Netlify Dashboard](https://app.netlify.com) → Your site → **Domain settings**

2. Click **"Add custom domain"**

3. Enter: `shelfsense.com`

4. Click **"Verify"** → **"Add domain"**

5. Netlify will show "Awaiting External DNS" - this is expected

6. Add the www subdomain:
   - Click **"Add domain alias"**
   - Enter: `www.shelfsense.com`

7. **Configure SSL**:
   - Scroll to **HTTPS** section
   - Click **"Verify DNS configuration"**
   - Once verified, click **"Provision certificate"**
   - Wait 1-2 minutes for Let's Encrypt certificate

8. **Set primary domain**:
   - Click **"Set as primary domain"** on `shelfsense.com`
   - This makes www redirect to the apex domain

---

## Step 3: Railway Custom Domain

1. Go to [Railway Dashboard](https://railway.app) → Your project → Backend service

2. Click **Settings** tab → **Networking** section

3. Click **"+ Custom Domain"**

4. Enter: `api.shelfsense.com`

5. Railway will show the CNAME target (should match `shelfsense-api.up.railway.app`)

6. Click **"Add Domain"**

7. Wait for SSL certificate provisioning (automatic via Let's Encrypt)

8. Status should change to **"Active"** with a green checkmark

---

## Step 4: Update Environment Variables

### Railway (Backend)
Go to Railway → Backend service → **Variables**:

```
FRONTEND_URL=https://shelfsense.com
API_URL=https://api.shelfsense.com
```

### Netlify (Frontend)
Go to Netlify → Site settings → **Environment variables**:

```
NEXT_PUBLIC_API_URL=https://api.shelfsense.com
```

Trigger a redeploy after updating environment variables.

---

## Step 5: Update External Services

### Clerk Authentication
Go to [Clerk Dashboard](https://dashboard.clerk.com) → Your app → **Paths**:

1. Update **Home URL**: `https://shelfsense.com`
2. Update **Sign-in URL**: `https://shelfsense.com/sign-in`
3. Update **Sign-up URL**: `https://shelfsense.com/sign-up`
4. Add domain to **Allowed origins**: `https://shelfsense.com`

### Stripe
Go to [Stripe Dashboard](https://dashboard.stripe.com) → **Settings** → **Checkout settings**:

1. Add `shelfsense.com` to allowed domains
2. Update webhook endpoint (if using):
   - Old: `https://shelfsense-api.up.railway.app/webhooks/stripe`
   - New: `https://api.shelfsense.com/webhooks/stripe`

### Resend Email
Go to [Resend Dashboard](https://resend.com) → **Domains**:

1. Add `shelfsense.com` domain for sending
2. Add DNS records for email authentication (DKIM, SPF)
3. Update `EMAIL_FROM` to: `ShelfSense <noreply@shelfsense.com>`

---

## Step 6: Verify Setup

### Test Frontend
```bash
curl -I https://shelfsense.com
# Should return 200 OK with valid SSL

curl -I https://www.shelfsense.com
# Should redirect (301/308) to https://shelfsense.com
```

### Test Backend API
```bash
curl https://api.shelfsense.com/health
# Should return: {"status": "healthy"}

curl https://api.shelfsense.com/docs
# Should load OpenAPI documentation
```

### Test CORS
Open browser console on `https://shelfsense.com` and run:
```javascript
fetch('https://api.shelfsense.com/health')
  .then(r => r.json())
  .then(console.log)
// Should return {"status": "healthy"} without CORS errors
```

---

## Troubleshooting

### "DNS_PROBE_FINISHED_NXDOMAIN"
- DNS hasn't propagated yet. Wait 5-30 minutes.
- Check DNS with: `dig shelfsense.com`

### "SSL Certificate Error"
- Ensure Cloudflare proxy is OFF (grey cloud)
- Wait for Netlify/Railway to provision certificates (up to 10 min)

### "CORS Error"
- Verify `FRONTEND_URL` is set correctly in Railway
- Check `main.py` includes `https://shelfsense.com` in allowed origins
- Redeploy backend after CORS changes

### "Mixed Content" warnings
- Ensure `NEXT_PUBLIC_API_URL` uses `https://`
- Rebuild and redeploy frontend

---

## DNS Propagation Check

Use these tools to verify DNS is working:
- https://dnschecker.org/#CNAME/shelfsense.com
- https://dnschecker.org/#CNAME/api.shelfsense.com

Full propagation can take up to 48 hours, but usually completes in 5-30 minutes.

---

## Rollback Plan

If something goes wrong, revert to Netlify/Railway subdomains:

1. Update Netlify env: `NEXT_PUBLIC_API_URL=https://shelfsense-api.up.railway.app`
2. Update Railway env: `FRONTEND_URL=https://shelfsense99.netlify.app`
3. Redeploy both services
4. Remove custom domains from Netlify and Railway dashboards

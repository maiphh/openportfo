# OpenPortfo — Amazon Cognito Auth Integration

**Status:** Locked (PRD v1.2)  
**Stack:** Next.js (S3 + CloudFront) · FastAPI (Elastic Beanstalk) · DynamoDB profiles · Cognito User Pool (+ Google IdP)

---

## 1. Responsibility split

| Concern | Owner |
|---------|--------|
| Sign-up, login, logout, password reset, email verify | **Amazon Cognito** |
| Sign in with Google | **Cognito** + Google as federated IdP |
| Issue / refresh tokens | **Cognito** |
| Validate tokens on API | **FastAPI** (JWKS) |
| App profile (role, keywords, emailOptIn, currency) | **DynamoDB** keyed by Cognito `sub` |
| Portfolio / holdings authorization | FastAPI uses `sub` as `userId` |

**Do not** implement `POST /auth/register` or `POST /auth/login` with bcrypt in FastAPI.

---

## 2. End-to-end flow

```
┌─────────────┐   Hosted UI / Amplify    ┌──────────────────┐
│  Next.js    │ ───────────────────────► │ Cognito User Pool│
│  (CloudFront)│ ◄──── ID + Access JWT ── │ (+ Google IdP)   │
└──────┬──────┘                          └────────┬─────────┘
       │ Authorization: Bearer <id_token>         │
       ▼                                          │ Google OAuth
┌─────────────┐                          ┌────────▼─────────┐
│  FastAPI    │  verify JWKS             │ Google Cloud     │
│  Beanstalk  │ ─────────────────────    │ OAuth client     │
└──────┬──────┘                          └──────────────────┘
       │ userId = token.sub
       ▼
┌─────────────┐
│  DynamoDB   │  Users profile, holdings, …
└─────────────┘
```

---

## 3. AWS setup (console / lab)

### 3.1 Cognito User Pool

1. **Cognito → Create user pool** (region: same as app, e.g. `us-east-1`).
2. **Sign-in options:** Email.
3. **Password policy:** default or moderate (fine for demo).
4. **Self-service sign-up:** enabled.
5. **Required attributes:** email; optional name.
6. **MFA:** optional (off for simpler demo).
7. **App client:**
   - Name: `openportfo-web`
   - **Public client** (no client secret) — required for SPA
   - Auth flows: `ALLOW_USER_SRP_AUTH`, `ALLOW_REFRESH_TOKEN_AUTH` (and Hosted UI flows if used)
8. **Hosted UI (recommended for Google):**
   - Domain prefix: e.g. `openportfo-xxxx`
   - Callback URLs:
     - `http://localhost:3000/auth/callback`
     - `https://<cloudfront-domain>/auth/callback`
   - Sign-out URLs:
     - `http://localhost:3000/`
     - `https://<cloudfront-domain>/`
   - OAuth scopes: `openid`, `email`, `profile`
   - OAuth grant: **Authorization code grant** (with PKCE for public client)

Save:

- `UserPoolId` → `COGNITO_USER_POOL_ID`
- `AppClientId` → `COGNITO_APP_CLIENT_ID` / `NEXT_PUBLIC_COGNITO_CLIENT_ID`
- Region → `COGNITO_REGION`
- Hosted UI domain → `NEXT_PUBLIC_COGNITO_DOMAIN`

### 3.2 Google as federated IdP

1. [Google Cloud Console](https://console.cloud.google.com/) → OAuth consent screen → OAuth **Web** client.
2. Authorized redirect URI must be the **Cognito** callback, not only your site:

   ```text
   https://<cognito-domain>.auth.<region>.amazoncognito.com/oauth2/idpresponse
   ```

3. Cognito → **Social and custom providers → Google**  
   - Paste Google Client ID + Client Secret  
   - Attribute mapping: `email` → email, `username` / sub as needed  
4. App client → **Identity providers:** Cognito + Google.

### 3.3 IAM (Beanstalk)

Beanstalk instance role does **not** need special Cognito IAM for JWT verify (verification is public JWKS over HTTPS).  
Only if you call Cognito Admin APIs from the server (e.g. list users) would you add `cognito-idp:...` permissions — **not required** for MVP token verify + profile.

---

## 4. Frontend integration

### 4.1 Env (Next.js public)

```env
NEXT_PUBLIC_COGNITO_REGION=us-east-1
NEXT_PUBLIC_COGNITO_USER_POOL_ID=us-east-1_XXXX
NEXT_PUBLIC_COGNITO_CLIENT_ID=xxxxxxxx
NEXT_PUBLIC_COGNITO_DOMAIN=openportfo-xxxx.auth.us-east-1.amazoncognito.com
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4.2 Option A — Hosted UI (simplest for Google + email)

Redirect user to:

```text
https://{domain}/oauth2/authorize?
  client_id={clientId}
  &response_type=code
  &scope=openid+email+profile
  &redirect_uri={encodeURIComponent(appUrl + '/auth/callback')}
  &identity_provider=Google    # omit for Cognito login page (email or Google buttons)
```

On `/auth/callback`, exchange `code` for tokens via Cognito token endpoint (PKCE), store tokens (memory + `localStorage` or sessionStorage for demo), then call `GET /api/auth/me`.

Logout:

```text
https://{domain}/logout?client_id=...&logout_uri=...
```

### 4.3 Option B — Amplify Auth / cognito-identity-js

Use AWS Amplify `signIn` / `signUp` / `federatedSignIn({ provider: 'Google' })` against the same User Pool. Still send **ID token** to FastAPI.

### 4.4 Calling the API

```http
GET /api/portfolio
Authorization: Bearer <Cognito_ID_Token>
```

Use the **ID token** (contains `sub`, `email`) for user identity on the API. Access token is for Cognito/AWS resource servers if configured; for custom FastAPI, **ID token** is the usual choice.

---

## 5. Backend integration (FastAPI)

### 5.1 Env

```env
COGNITO_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_XXXX
COGNITO_APP_CLIENT_ID=xxxxxxxx
```

### 5.2 Verify token (conceptual)

```python
# pip install python-jose httpx  (or PyJWT + requests)
import httpx
from jose import jwt
from functools import lru_cache

REGION = os.environ["COGNITO_REGION"]
POOL_ID = os.environ["COGNITO_USER_POOL_ID"]
CLIENT_ID = os.environ["COGNITO_APP_CLIENT_ID"]
ISSUER = f"https://cognito-idp.{REGION}.amazonaws.com/{POOL_ID}"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"

@lru_cache
def get_jwks():
    return httpx.get(JWKS_URL, timeout=10).json()

def verify_cognito_token(token: str) -> dict:
    headers = jwt.get_unverified_header(token)
    key = next(k for k in get_jwks()["keys"] if k["kid"] == headers["kid"])
    claims = jwt.decode(
        token,
        key,
        algorithms=["RS256"],
        audience=CLIENT_ID,   # ID token uses aud = app client id
        issuer=ISSUER,
        options={"verify_at_hash": False},
    )
    return claims  # sub, email, token_use == "id", ...
```

FastAPI dependency:

```python
async def current_user(authorization: str = Header(...)) -> dict:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Missing bearer token")
    claims = verify_cognito_token(token)
    user_id = claims["sub"]
    profile = await users_repo.get_or_create(user_id, email=claims.get("email"), name=claims.get("name"))
    return profile
```

### 5.3 Endpoints

| Method | Path | Auth | Behaviour |
|--------|------|------|-----------|
| `GET` | `/api/auth/me` | Cognito JWT | Return profile; create default profile if first login |
| `PUT` | `/api/settings` | Cognito JWT | Update keywords, emailOptIn, preferredCurrency |
| All business APIs | `...` | Cognito JWT | Authorize by `profile.userId` / `role` |

---

## 6. Data model (profile)

```
Users
  PK: userId          # Cognito sub (string)
  email: string
  name: string | null
  role: "user" | "admin"
  newsKeywords: string[]
  emailOptIn: bool
  preferredCurrency: string   # display preference only
  createdAt, updatedAt
```

**Admin bootstrap:** after creating Cognito user in console, put DynamoDB item with same `sub` and `role=admin`.

---

## 7. CORS

FastAPI must allow:

- `http://localhost:3000`
- CloudFront origin  

Headers: `Authorization`, `Content-Type`.  
Methods: `GET, POST, PUT, DELETE, OPTIONS`.

---

## 8. Architecture diagram labels (for report)

Include Cognito in the request path:

```
Browser → Cognito (auth)
Browser → CloudFront → S3 (UI)
Browser → Beanstalk FastAPI (Bearer Cognito JWT) → DynamoDB / S3 / external APIs
```

Cognito is **Authentication / Identity**; it does not replace Beanstalk or DynamoDB.

---

## 9. Implementation checklist

- [ ] Create User Pool + public app client in lab account  
- [ ] Hosted UI domain + callback URLs (localhost + CloudFront)  
- [ ] (Optional) Google IdP + Google redirect to Cognito `idpresponse`  
- [ ] Frontend login/logout/callback  
- [ ] FastAPI JWKS middleware + `/auth/me`  
- [ ] DynamoDB profile on first login  
- [ ] Seed admin profile  
- [ ] Document pool id / region in architecture doc (no secrets)  

---

## 10. Cost & lab notes

- Cognito MAU free tier is usually enough for a class demo.  
- Confirm **Cognito** is allowed in AWS Academy Learner Lab service list.  
- Lab credentials rotate; Cognito **resources** persist in the lab account until reset.

---

## 11. Related documents

- PRD: `docs/prd/OpenPortfo_PRD.md` (v1.2, decision D1)  
- Architecture: `docs/architecture-design.md` §6  

# 🌟 SANSKAR – AI-Based Age-Adaptive Child Learning Platform

> Safe • Smart • Age-Appropriate • Child-First

---

## 📋 Project Overview

SANSKAR is a full-stack web application that provides curated, age-filtered educational content to children aged 2–14. Every piece of content is filtered by the child's age, pulled only from pre-approved YouTube channels, and monitored through a hidden parent portal.

---

## 🏗️ Architecture

```
sanskar/
├── backend/              ← Spring Boot (Java 17)
│   └── src/main/java/com/sanskar/
│       ├── controller/   ← AuthController, ContentController, ParentController
│       ├── service/      ← UserService, VideoService, RecommendationService
│       ├── model/        ← User, Video, VideoHistory, SearchHistory, Category
│       ├── repository/   ← JPA repositories
│       ├── security/     ← JwtUtil, JwtAuthFilter
│       └── config/       ← SecurityConfig, GlobalExceptionHandler
│
├── frontend/             ← React + Vite
│   └── src/
│       ├── pages/        ← LoginPage, SignupPage, Dashboard, VideoPage,
│       │                    SearchPage, CategoryPage, ParentPortal
│       ├── components/   ← Navbar, VideoCard
│       ├── store/        ← Zustand auth store
│       ├── utils/        ← Axios API client
│       └── styles/       ← global.css (design tokens, animations)
│
└── database/
    └── schema.sql        ← Complete MySQL schema
```

---

## ⚙️ Setup Instructions

### Prerequisites
- Java 17+
- Node.js 18+
- MySQL 8+
- YouTube Data API v3 key ([Get one here](https://console.cloud.google.com/))

---

### 1. Database Setup

```sql
-- Run the schema file
mysql -u root -p < database/schema.sql
```

---

### 2. Backend Setup

```bash
cd backend

# Edit application.yml
# Set: spring.datasource.password, youtube.api-key, jwt.secret

mvn clean install
mvn spring-boot:run
# Runs on http://localhost:8080
```

**First Run:** Set `spring.jpa.hibernate.ddl-auto: create` in application.yml, then switch to `validate`.

---

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

Create `.env` file:
```
VITE_API_URL=http://localhost:8080/api
```

---

## 🔑 Key Features

| Feature | How It Works |
|---|---|
| **Age Filtering** | Every API call checks `user.age`; videos outside age range are excluded |
| **Safe Search** | `safeSearch=strict` on all YouTube API calls + keyword blocklist |
| **Curated Channels** | Only 10 pre-approved educational channels are ever queried |
| **JWT Auth** | Stateless JWT with age embedded in token claims |
| **Parent Portal** | Triggered by 3-second long-press on 🔒 icon; requires PIN on every access |
| **Watch Tracking** | Duration + completion recorded; drives "Continue Watching" |
| **Recommendation Engine** | Weighted scoring: category match (+3), search match (+2), channel match (+1) |
| **Safety Content** | Age-specific safety topics always visible on dashboard |

---

## 🛡️ Security Measures

- ✅ BCrypt password hashing (strength 12)
- ✅ BCrypt parent PIN hashing (stored separately)
- ✅ JWT tokens expire in 24 hours
- ✅ CORS restricted to localhost:3000
- ✅ All YouTube results pass through blocklist filter
- ✅ `safeSearch=strict` on all YouTube API calls
- ✅ Parent portal re-verifies PIN on every access (no token caching)
- ✅ Age checked on every content endpoint

---

## 🎨 UI Design Principles

- **Fonts:** Baloo 2 (headings) + Nunito (body) — playful but readable
- **Colors:** Warm yellows, oranges, teals — safe and energetic
- **Touch targets:** Min 52px height on all buttons (child-friendly)
- **Animations:** Framer Motion spring physics — bouncy and delightful
- **Skeleton loaders:** Shimmer effect while content loads

---

## 📡 API Endpoints

### Auth
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/signup` | Register child account |
| POST | `/api/auth/login`  | Login, receive JWT |

### Content (requires JWT)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/content/dashboard` | Personalized homepage data |
| GET | `/api/content/categories` | Age-filtered categories |
| GET | `/api/content/videos/{id}` | Videos in a category |
| GET | `/api/content/search?q=` | Safe search |
| POST | `/api/content/watch` | Record watch event |

### Parent Portal (requires JWT + PIN)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/parent/verify` | Check PIN validity |
| POST | `/api/parent/portal` | Get full activity report |

---

## 🚀 YouTube API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **YouTube Data API v3**
3. Create API key → Restrict to YouTube Data API
4. Add key to `application.yml` under `youtube.api-key`

**Daily quota:** 10,000 units/day (free). Each search = ~100 units.

---

## 🔮 Optional Enhancements

### Voice Search
Add to Navbar.jsx:
```javascript
const recognition = new webkitSpeechRecognition();
recognition.onresult = (e) => setQuery(e.results[0][0].transcript);
recognition.start();
```

### AI Recommendations (Claude API)
In `RecommendationService.java`, call Anthropic API with:
- Child's age, watch history titles, search history
- Ask for video topic suggestions
- Use topics as YouTube search queries

---

## 📁 File Summary

| File | Purpose |
|---|---|
| `database/schema.sql` | Complete MySQL schema with seed data |
| `backend/pom.xml` | Maven dependencies |
| `backend/.../SanskarApplication.java` | Spring Boot entry point |
| `backend/.../model/User.java` | User entity with age group derivation |
| `backend/.../model/Models.java` | Video, VideoHistory, SearchHistory, Category |
| `backend/.../security/JwtUtil.java` | JWT generation and validation |
| `backend/.../security/JwtAuthFilter.java` | Request-level JWT authentication |
| `backend/.../config/SecurityConfig.java` | Spring Security configuration |
| `backend/.../config/GlobalExceptionHandler.java` | Centralised error handling |
| `backend/.../dto/Dtos.java` | All request/response DTOs |
| `backend/.../service/UserService.java` | Registration, login, PIN verification |
| `backend/.../service/VideoService.java` | YouTube API integration + caching |
| `backend/.../service/RecommendationService.java` | Weighted recommendation engine |
| `backend/.../controller/Controllers.java` | Auth, Content, Parent controllers |
| `backend/.../repository/Repositories.java` | All JPA repositories |
| `frontend/src/App.jsx` | React router setup |
| `frontend/src/styles/global.css` | Design system (tokens, animations) |
| `frontend/src/utils/api.js` | Axios client with JWT interceptors |
| `frontend/src/store/authStore.js` | Zustand auth state |
| `frontend/src/pages/LoginPage.jsx` | Login UI |
| `frontend/src/pages/SignupPage.jsx` | 3-step signup UI |
| `frontend/src/pages/Dashboard.jsx` | Child's home page |
| `frontend/src/pages/VideoPage.jsx` | Video player |
| `frontend/src/pages/SearchPage.jsx` | Search results |
| `frontend/src/pages/CategoryPage.jsx` | Category browser + ParentPortal |
| `frontend/src/components/common/Navbar.jsx` | Navigation + secret parent trigger |
| `frontend/src/components/video/VideoCard.jsx` | YouTube-style video card |

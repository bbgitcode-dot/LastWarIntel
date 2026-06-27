# Sentinel Architecture
Web
│
▼
Application
│
▼
Analytics
│
▼
Domain
│
▼
Persistence

## Responsibilities

### Web

Presentation only.

No business logic.

---

### Application

Builds view models.

Coordinates multiple analytics modules.

---

### Analytics

Contains business logic.

Generates knowledge from raw datasets.

---

### Domain

Core business entities.

Independent from UI and storage.

---

### Persistence

Snapshots

Repositories

Database

Import pipeline
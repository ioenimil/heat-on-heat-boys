ServiceHub - Team 12 

Team Configuration 

| Role | Name & Email | Location |
| --- | --- | --- |
| **Backend with Java** | Eugene Dokye Anokye (eugene.anokye@amalitech.com) | Kumasi |
| **Backend with Java** | Bernard Mawulorm Kofi Wodoame (bernard.wodoame@amalitech.com) | Accra |
| **Backend with Java** | Jacob Quaye (jacob.quaye@amalitech.com) | Kumasi |
| **Quality Assurance** | Francis Roland Bissah (francis.bissah@amalitech.com) | Takoradi |
| **DevOps** | Isaac Obo Enimil (isaac.enimil@amalitech.com) | Kumasi |
| **Data Engineering** | Manaf Mohammed (manaf.mohammed@amalitech.com) | Kumasi |

* 
**Product Owner:** Lute 


* 
**Scrum Master:** Selected by PO from team members 



---

Problem Statement 

Organizations need a centralized system to manage internal service requests across departments. **ServiceHub** is an internal service request and ticketing system where employees can submit requests in specific categories, assign priorities, and track them through a complete workflow.

MVP Requirements 

* 
**Submit service requests:** Categories include `IT_SUPPORT`, `FACILITIES`, and `HR_REQUEST`.


* 
**Priorities:** Levels include `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL`.


* 
**Auto-routing:** Automatically assign requests to the correct department based on category.


* 
**Status workflow:** `OPEN` -> `ASSIGNED` -> `IN_PROGRESS` -> `RESOLVED` -> `CLOSED`.


* 
**SLA tracking:** Per category and priority combination for both response and resolution times.


* 
**Dashboard APIs:** Showing request volumes, SLA compliance, and resolution times.


* 
**UI:** Thymeleaf-based interface for request management.



**Stretch Goals:**

* Email notifications on status changes.


* Automatic escalation when SLA is breached.



---

Tech Stack 

* 
**Backend:** Java 17 / Spring Boot 3.2 / Spring Security with JWT / JPA / PostgreSQL / Lombok.


* 
**Frontend:** Thymeleaf server-side rendering with Bootstrap.


* 
**Data/Analytics:** Python 3.11+ / Pandas.


* 
**Testing:** REST Assured (API) / Selenium (UI) / JUnit 5 (Unit).


* 
**Infrastructure:** Docker / Docker Compose / GitHub Actions CI/CD.



Default Credentials 

| Role | Email | Password |
| --- | --- | --- |
| **ADMIN** | admin@amalitech.com | password123 |
| **AGENT** | agent@amalitech.com | password123 |
| **USER** | user@amalitech.com | password123 |

---

Starter Code & Setup 

* 
**Location:** [GitHub Repository Link](https://www.google.com/search?q=https://github.com/AmaliTech-Training-Academy/Phase1-Group-Projects/tree/126e143b8dd03752be797fede9f538436cbf3b91/4-ServiceHub).


* 
**Instructions:** Review `README.md` and look for `TODO` comments in the codebase.


* 
**Run Command:** `docker-compose up --build`.



---

Role-Specific Deliverables 

Backend Developer A: Request Management 

* **Request CRUD API:** Create, read, update service requests with category and priority.
* **Category System:** Implementation of auto-routing for IT, Facilities, and HR.
* **Priority Management:** Implementation of the four priority levels.
* **Request Validation:** Input validation and business rules enforcement.
* **Thymeleaf Views:** Request submission and list views.

Backend Developer B: Workflow & SLA 

* **Status Workflow:** Managing transitions from `OPEN` to `CLOSED`.
* **SLA Engine:** Define and track SLA per category and priority combination.
* **Time Tracking:** Track time from creation to first response and final resolution.
* **SLA Breach Detection:** Flag requests that exceed thresholds.

Backend Developer C: Auth & Dashboard 

* **Auth System:** JWT-based authentication for ADMIN, AGENT, and USER roles.
* **Dashboard APIs:** Metrics for volumes, SLA compliance, and resolution times.
* **Reporting Endpoints:** Aggregate statistics per category, priority, and agent.
* **Thymeleaf Dashboard:** Visual views with charts and metrics.
* **Role-based Access:** Enforce different views per role (e.g., users only see own tickets).

QA Engineer 

* **Test Plan:** Comprehensive plan covering all MVP features.
* **Workflow & API Tests:** Test status transitions and REST Assured endpoint testing.
* **UI & SLA Tests:** Selenium tests for Thymeleaf and verification of SLA calculations.

Data Engineer 

* **Analytics Pipeline:** Extract ticket data and compute SLA metrics.
* **Sample Data:** Generate realistic tickets across all categories.
* **Visualizations:** Prepared datasets for dashboard and trend analysis (weekly/monthly).
* **Documentation:** Schema and metrics documentation.

DevOps Engineer 

* **Docker:** Setup Dockerfiles for Spring Boot and the database.
* **Orchestration:** Multi-container setup via Docker Compose.
* **CI/CD:** GitHub Actions for build, test, and deployment.
* **Environment:** Configuration for Dev and Test environments.

---

Daily Milestones 

* 
**Day 1: Setup & Foundation:** Environment setup, database schema migration, and auth system working.


* 
**Day 2: Core Features:** CRUD operations complete, UI connected to APIs, and initial test suite running.


* 
**Day 3: Integration & Testing:** All MVP features implemented, data pipeline working, and bug fixing.


* 
**Day 4: Polish & Preparation:** Critical bug fixes, final QA, documentation, and demo rehearsal.



---

Collaboration Guidelines 

* 
**Daily Standup:** Brief meeting covering yesterday's work, today's plan, and blockers.


* 
**Project Management:** Use GitHub Projects (Kanban board) for task tracking.


* **Version Control:** Use feature branches; never push directly to `main`. Pull requests are required for merges.


* 
**Project Log:** Maintain a shared document for daily progress and decisions.



---

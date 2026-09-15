# ATS Tracker — Functional Specification

**What this document is:** a description of what the system does, written for
recruiters, hiring managers, and anyone evaluating or approving the tool. It
describes behaviour, not implementation.

**Version:** reflects the codebase as of the pilot release.
Anything not yet built is listed in [§14](#14-not-yet-built).

---

## Contents

1. [Purpose](#1-purpose)
2. [Who uses it](#2-who-uses-it)
3. [Core concepts](#3-core-concepts)
4. [The hiring pipeline](#4-the-hiring-pipeline)
5. [Jobs and requisitions](#5-jobs-and-requisitions)
6. [Candidates](#6-candidates)
7. [Applications](#7-applications)
8. [AI résumé review](#8-ai-résumé-review)
9. [Interviews](#9-interviews)
10. [Offers](#10-offers)
11. [Onboarding](#11-onboarding)
12. [Supporting modules](#12-supporting-modules)
13. [Access control and audit](#13-access-control-and-audit)
14. [Not yet built](#14-not-yet-built)

---

## 1. Purpose

ATS Tracker manages the full recruiting lifecycle for a staffing or consulting
business: publishing roles, receiving and screening applicants, scoring résumés
against job requirements with AI assistance, running interviews, issuing offers,
and tracking onboarding to day one.

It is built for **agency and client-based recruiting** as well as internal
hiring — jobs can be attached to a client account and a delivery vendor, not just
an internal department.

The system is **multi-tenant by design**: every record belongs to an
organization, and no data is visible across organizations.

---

## 2. Who uses it

Seven roles ship with the system. Permissions are enforced on the server for
every request, not just hidden in the interface.

| Role | What they can do |
| --- | --- |
| **Super Admin** | Everything, including editing role permissions and previewing the app as any other role |
| **Admin** | Everything operational: users, invitations, all recruiting data, settings, audit log. Cannot delete the organization |
| **Executive** | Read-only across all recruiting data and reports. No access to settings |
| **Recruiter** | Day-to-day recruiting: create and edit jobs, candidates, applications; move stages; schedule interviews; raise offers; open onboarding; create and edit email templates |
| **Hiring Manager** | Read access **scoped to their own jobs** only — candidates, applications, interviews for those roles. Can submit interview feedback and raise offers |
| **Interviewer** | Sees only the interviews they are assigned to, plus the candidate and application behind them. Submits feedback |
| **Candidate** | Applies to published jobs. Read access to their own applications |

### Data scoping

Beyond permissions, some roles see a filtered slice of data:

- A **Hiring Manager** sees only jobs where they are the named hiring manager, and only the candidates and applications attached to those jobs.
- An **Interviewer** sees only interviews on which they sit on the panel.
- **Recruiters, Admins, and Executives** see everything in their organization.

### Role preview

A Super Admin can switch into a **"view as"** session to see the application
exactly as another role sees it, without logging out or knowing anyone's
password. The preview carries genuinely reduced permissions — it is not a
cosmetic filter — and every preview session is recorded in the audit log.

---

## 3. Core concepts

| Concept | Meaning |
| --- | --- |
| **Organization** | The tenant. Everything belongs to exactly one |
| **Client** | The end customer a role is being filled for. Carries contacts, category, and visibility |
| **Vendor** | A delivery or staffing partner associated with fulfilment |
| **Job** | A requisition — the role being filled |
| **Candidate** | A person in the database. Exists independently of any job |
| **Application** | One candidate against one job. This is what moves through the pipeline |
| **Stage** | A step in the pipeline. An application sits in exactly one at a time |
| **Interview** | A scheduled round against an application, with a panel and feedback |
| **Offer** | A compensation package against an application, with versions and approvals |
| **Onboarding case** | Post-acceptance task tracking through to start date |

The key distinction: **a candidate is a person, an application is that person
being considered for one specific job.** The same candidate can hold several
applications, each at its own stage, each independently scored.

---

## 4. The hiring pipeline

Every application moves through a configured sequence of stages. The default
pipeline has twelve:

```
 1  Applied                    7  Panel Interview
 2  Screening                  8  Background Check
 3  Shortlisted                9  Offer
 4  Recruiter Interview       10  Offer Accepted
 5  Technical Assessment      11  Onboarding
 6  Hiring Manager Interview  12  Hired  ← terminal
```

**Hired** is a *terminal* stage: reaching it marks the application as filled and
is what the time-to-fill and hiring-trend reports count.

### Movement rules

- An application sits in one stage at a time.
- Any stage change is recorded with **who moved it, when, and an optional note**. That history is permanent and visible on the application.
- Applications can be moved forward or backward — the pipeline is not one-way.
- An application can be put **On Hold** or **Rejected** at any stage, and later **Restored**. Nothing is deleted.
- The funnel report counts the **furthest stage each application ever reached**, not where it sits now, so progress is not erased by a later rejection.

The **Pipeline** view presents all active applications grouped by stage for
at-a-glance load assessment.

---

## 5. Jobs and requisitions

A job captures far more than a title, reflecting agency requirements:

- **Basics** — title, department, location, workplace type (Remote / Hybrid / Onsite), employment type (Full-time / Contract / Part-time / Intern), number of openings, pay range, priority (Low → Urgent)
- **Content** — summary, description, responsibilities, required skills, nice-to-have skills, experience and education requirements, screening questions
- **Commercial** — client account, end client, vendor, business unit, facility, contract duration, hours per week
- **Compliance** — work authorizations accepted, security clearance requirement, required documents
- **Ownership** — recruiter, hiring manager, account manager, sales manager, recruitment manager, and additional assignees
- **Service levels** — respond-by date, turnaround time
- **Search criteria** — a stored sourcing profile: boolean string, title, location and radius, experience range, education, employer, relocation and clearance filters
- **Custom fields** — free-form additional data per job
- **Notes and documents** attached to the requisition

### Job lifecycle

```
Draft → Active → On Hold → Closed / Cancelled
```

Only **Active** jobs appear on the public careers portal. Publishing and
unpublishing are separate recorded actions.

Every job gets a human-readable **requisition ID** and a URL slug.

---

## 6. Candidates

The candidate record holds the person, independent of any single role.

- **Identity and contact** — name, email, phone, location, LinkedIn
- **Current position** — company, title
- **Experience** — total years and relevant years, tracked separately
- **Commercials** — current CTC, expected CTC, notice period
- **Eligibility** — work authorization, willingness to relocate
- **Skills** — a searchable list, used by AI matching and talent-pool rediscovery
- **Education** — structured history
- **Tags** — free-form labels, which drive talent-pool segments
- **Rating** — a manual recruiter score
- **Status** — Active, Passive, Silver Medalist, or Do Not Contact

### Duplicate detection

When a candidate is created, the system checks for existing records with the same
**email or phone** and surfaces a duplicate warning on the record. It warns
rather than blocks — the recruiter decides.

### Documents and notes

Résumés and other documents are uploaded per candidate and stored securely.
Uploading a résumé can trigger automatic parsing (see §8). Notes are timestamped
and attributed.

### Deletion

Candidates are **soft-deleted** — hidden from all lists but retained, so a
deletion can be reversed and the audit trail stays intact.

---

## 7. Applications

An application is created when a candidate is put forward for a job — either by a
recruiter internally, or by the candidate applying through the careers portal.

Each application records its **source** (careers page, referral, agency, and so
on), which feeds the source-effectiveness report.

Statuses: **Active**, **On Hold**, **Rejected**, **Hired**, **Withdrawn**.

The application detail view is the working surface for a candidacy:

- Current stage and status, applied date, source
- **Stage movement** with an optional note
- **Hold / Reject / Restore** actions
- Full **timeline** of every stage change, with who and when
- All **interviews** scheduled against it
- The **AI review** summary, with a link to the full breakdown

---

## 8. AI résumé review

Two AI capabilities operate on applications.

### Résumé parsing

An uploaded résumé is read and turned into structured data: name, contact
details, location, total experience, skills, education, and work history. Parsing
runs in the background — the recruiter is not blocked waiting for it.

Parsed data is kept **separate** from the recruiter-entered candidate record, so
extraction never silently overwrites something a human typed.

### Match scoring

Each application can be scored against its job's requirements. The result:

- **Overall match score** (0–100)
- **Recommendation** — Strong Fit, Fit, Partial Fit, or Not a Fit
- **Matched skills** and **missing skills**
- **Strengths**, **gaps**, and **risk flags**
- A **criterion-by-criterion breakdown**: each requirement, its weight, what the candidate offers against it, and a per-criterion score
- **Suggested interview questions** targeting the gaps
- A written **explanation** of the assessment
- A **confidence** value

### How the score is composed

Two independent signals are blended:

- a **rule score** — measurable requirement fit, chiefly skills and experience
- a **semantic score** — how well the résumé reads against the role as a whole

The balance is a configurable weight. At the default of 0.6, the score is 60%
requirement fit and 40% holistic fit. Lowering it rewards strong generalists who
miss niche must-have tags; raising it enforces the checklist more strictly.

### Human override

A recruiter can **override** the AI recommendation. The override records the
previous value, the new value, who changed it, and an optional note. The original
AI output is never destroyed — both are visible.

### JD-to-résumé comparison

A side-by-side view puts job requirements against candidate profile with a
per-criterion verdict, for explaining a shortlist decision to a hiring manager.

**Every score is advisory.** Nothing is auto-rejected and no stage moves on its
own. A human decides.

---

## 9. Interviews

An interview is a round scheduled against an application.

- **Round name** (e.g. Technical Round 1), **mode** (Video / Onsite / Phone), and scheduled date and time
- A **panel** of internal users, one optionally marked as lead
- **Status** — Scheduled, Completed, Cancelled, Rescheduled

### Feedback

Each panel member submits independently:

- a **rating** out of five
- a **recommendation** — Strong Yes, Yes, No, or Strong No
- **notes**

The interview view shows a **consolidated result**: average rating, a tally of
recommendations, and every individual submission. It also shows which panel
members have **submitted versus still pending**, so chasing feedback does not
require asking around.

Rescheduling from the interview view updates the time and marks the round
Rescheduled.

---

## 10. Offers

An offer is raised against an application.

- **Package** — base salary, bonus, equity, joining date
- **Versioning** — every revision is kept as a numbered version with its author and timestamp, so negotiation history is preserved
- **Approvals** — an offer can be routed to approvers, each recording a decision (Pending / Approved / Rejected) with an optional note and decision timestamp

### Offer lifecycle

```
Draft → Approval Pending → Sent → Accepted / Declined / Expired
```

The offer-acceptance metric counts only **decided** offers — accepted versus
declined — so outstanding offers do not distort the rate.

---

## 11. Onboarding

Once an offer is accepted, an onboarding case tracks the candidate to day one.

- **Start date** and an assigned **coordinator**
- A **task checklist**, each task with a category, owner, due date, and status (Pending / In Progress / Completed / Blocked)
- Case status — In Progress, Completed, or Cancelled

Task categories: **Documentation**, **Compliance**, **Equipment**,
**Provisioning**, **Orientation**.

**Blocked** is a first-class status, so a stalled joiner is visible rather than
buried in an unfinished list.

---

## 12. Supporting modules

### Dashboard

Three views for three audiences:

- **Recruiter** — my open jobs, applications this week, interviews scheduled, offers pending, hiring funnel, source performance, recently added candidates, upcoming interviews, aging jobs, recent activity
- **Leadership** — open positions, average time to fill, offer acceptance, active recruiters, 12-month hiring trend, recruiter productivity table
- **Executive** — total hires, open requisitions, candidate database size, offers outstanding, organization-wide funnel, AI score distribution

### Reports

Six reports, each exportable to **CSV**:

| Report | Shows |
| --- | --- |
| Funnel | Applications reaching each stage |
| Trend | Offers versus hires by month, last 12 months |
| Source | Applications by origin channel |
| AI scores | Distribution of match scores |
| Recruiter | Open jobs, applications, and hires per recruiter |
| Aging jobs | Active requisitions by age, oldest first |

Charts state plainly when there is no data yet, rather than showing zero as
though it were a measurement.

### Talent Pool

Candidates marked **Passive** or **Silver Medalist** form a re-engagement pool,
segmented by status and by the tags recruiters actually use.

**Rediscovery** matches pool candidates against currently open jobs on required
skills, surfacing people already in the database who fit a live role.

### Careers portal

A public, unauthenticated job board at `/careers`:

- Lists Active, published jobs for the organization
- Candidates apply with name, email, phone, and a résumé
- An application and candidate record are created automatically, and résumé parsing plus AI scoring are triggered

Can be switched off entirely from Settings.

### Clients and vendors

Client accounts carry contacts, industry, category (Direct, Implementation
Partner, Staffing Partner, System Integrator, Internal), status, visibility
scope, and typed notes — including applicant references. Vendors are tracked with
status and their own contact and note records.

### Email templates

Reusable templates by type — Interview Invite, Offer, Rejection, Follow-up,
Acknowledgment — with subject, body, and **merge tokens** such as
`{{candidate_first_name}}`, `{{job_title}}`, and `{{recruiter_name}}`. Templates
can be created, edited, duplicated, and deleted.

### Candidate messaging

From a candidate record, a recruiter can compose a message, optionally starting
from a template with tokens pre-filled and optionally linked to a specific
application. Every message is recorded as outreach history with a delivery
status. If no email provider is configured, messages are still recorded — the
interface says so rather than implying they were sent.

### Admin console

User management, invitations, role assignment, per-role permission editing, and
the full audit log with per-user activity summaries.

### Settings

Organization name and locale, careers-portal toggle, the configured pipeline
(read-only), the active AI configuration (read-only, no secrets shown), email
delivery status, and audit-trail export.

---

## 13. Access control and audit

### Permission model

Every action is a **resource + action** pair — for example `job:create`,
`offer:approve`. Roles hold sets of these pairs, stored in the database rather
than hard-coded, so a Super Admin can adjust them without a code change. The
Super Admin role itself is immutable.

Checks run on the server for every request. Hiding a button never constitutes the
control.

### Authentication

Email and password, with short-lived access tokens and longer-lived refresh
tokens. Sessions renew silently and expire cleanly. Password reset is
self-service by emailed link, valid for 30 minutes.

New users join by **invitation**, not self-registration: an admin invites an
address with a role, and the invitee sets their own name and password.

The password-reset endpoint returns an identical response whether or not the
address exists, so it cannot be used to discover who has an account.

### Audit log

Privileged and consequential actions are recorded with actor, action, resource,
timestamp, and IP address. Coverage includes logins, user and role changes,
permission edits, settings changes, job and candidate changes, every stage
movement, interview scheduling and feedback, the full offer lifecycle, template
changes, AI evaluations and overrides, role-preview sessions, and onboarding
progress.

Records are retained indefinitely and exportable to CSV.

---

## 14. Not yet built

Stated plainly so expectations are set correctly. These are unbuilt, not broken,
and the interface says so where a user would otherwise go looking.

**Configuration**
- Pipeline stages are viewable but not editable in the interface
- No automation on stage entry (no auto-email or auto-task)
- All jobs share one pipeline template; no per-job pipelines
- AI provider and model are set per deployment, not per organization
- Scoring weights are configuration, not a UI control

**Integrations**
- No Slack, calendar sync, video-conferencing links, or e-signature
- No job-board syndication (LinkedIn, Indeed)
- Email requires an SMTP provider to be configured; without one, messages are recorded but not delivered

**Candidate experience**
- Candidates can apply but cannot log in to track their own status
- No candidate self-service profile

**Compliance**
- No automatic data-retention or purge rules; nothing is deleted on a schedule
- No GDPR subject-access or right-to-erasure workflow
- No EEO/OFCCP reporting — demographic data is not collected

**Other**
- Offers have approvals but no electronic signature
- No bulk import of candidates or jobs
- No resume search by full-text content (skills and names are searchable)

"""The five things that can be imported, and how each is matched, created,
updated, protected on undo, and exported.

Candidates, vendors and clients arrive in the tens of thousands, so they are
matched and created a chunk at a time with one query per chunk. Jobs and bench
profiles arrive in the hundreds and go through their existing services one
row at a time, which keeps their numbering and ownership rules in one place.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session

from app.core.enums import (
    BenchStatus,
    CandidateStatus,
    ClientStatus,
    JobPriority,
    VendorStatus,
)
from app.db.models.application import Application
from app.db.models.bench import BenchProfile, BenchSubmission
from app.db.models.candidate import Candidate, CandidateNote, CandidateTag
from app.db.models.client import Client
from app.db.models.communication import OutboundMessage
from app.db.models.hotlist import HotlistMember, HotlistRecipient
from app.db.models.job import Job
from app.db.models.vendor import Vendor
from app.services.imports.fields import Field, phone_digits

# The last ten digits of a candidate's phone, written out literally (not as
# bound parameters) so it matches the ix_candidates_org_phone_digits
# expression index exactly and the planner can use it.
PHONE_DIGITS_SQL = literal_column(r"right(regexp_replace(candidates.phone, '\D', '', 'g'), 10)")

IMPORTED_TAG = "Imported"
MISSING_EMAIL_TAG = "Missing email"


@dataclass
class ImportContext:
    organization_id: uuid.UUID
    actor_id: uuid.UUID | None
    import_job_id: uuid.UUID
    file_name: str


@dataclass
class RowValues:
    """One row after conversion: typed field values, plus the note lines and
    warnings collected on the way."""

    values: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def get(self, key, default=None):
        value = self.values.get(key)
        return default if value is None else value


def _set_attrs(obj, values: dict, keys) -> None:
    """Copy the non-empty `keys` of `values` onto `obj`, for an "update the
    existing record" import: an empty cell never blanks out what is there."""
    for key in keys:
        value = values.get(key)
        if value is not None and value != []:
            setattr(obj, key, value)


def _in_use(db: Session, ids: list[uuid.UUID], *columns) -> set[uuid.UUID]:
    used: set[uuid.UUID] = set()
    for column in columns:
        used |= set(db.scalars(select(column).where(column.in_(ids)).distinct()).all())
    return used


class Importer:
    key: str
    label: str
    model: type
    fields: tuple[Field, ...]
    # Whether rows can match existing records (and so skip or update them).
    matches_existing = True

    def field(self, key: str) -> Field:
        return next(f for f in self.fields if f.key == key)

    def prepare(self, row: RowValues) -> str | None:
        """Derive combined fields; return a rejection reason, or None."""
        return None

    def resolve(self, db: Session, ctx: ImportContext, rows: list[RowValues]) -> list[str | None]:
        """Look up anything a row refers to in the database (a client by
        name, a candidate by email); return a rejection reason per row."""
        return [None] * len(rows)

    def match_keys(self, row: RowValues) -> list[tuple[str, str]]:
        """What identifies this record, strongest first, for spotting the same
        record twice within one file."""
        return []

    def find_existing(self, db: Session, ctx: ImportContext, rows: list[RowValues]) -> list[uuid.UUID | None]:
        return [None] * len(rows)

    def create_many(self, db: Session, ctx: ImportContext, rows: list[RowValues]) -> list[uuid.UUID]:
        raise NotImplementedError

    def update(self, db: Session, ctx: ImportContext, record_id: uuid.UUID, row: RowValues) -> None:
        raise NotImplementedError

    def in_use(self, db: Session, ids: list[uuid.UUID]) -> set[uuid.UUID]:
        return set()

    # -- export
    export_fields: tuple[str, ...] = ()

    def export_query(self, organization_id: uuid.UUID):
        return select(self.model).where(self.model.organization_id == organization_id).order_by(self.model.created_at)

    def export_value(self, obj, key: str):
        return getattr(obj, key, None)


# ----------------------------------------------------------------- candidates


class CandidateImporter(Importer):
    key = "candidates"
    label = "Candidates"
    model = Candidate
    fields = (
        Field("external_id", "External ID", aliases=("Applicant ID", "Candidate ID", "ID"), max_length=100),
        Field(
            "full_name",
            "Full name",
            aliases=("Applicant Name", "Candidate Name", "Name"),
            max_length=255,
            help="Or map First name and Last name instead.",
        ),
        Field("first_name", "First name", aliases=("First", "Given Name"), max_length=120),
        Field("last_name", "Last name", aliases=("Last", "Surname", "Family Name"), max_length=120),
        Field("email", "Email", kind="email", aliases=("Email Address", "E-mail", "Email ID", "Mail"), max_length=255),
        Field(
            "phone",
            "Phone",
            kind="phone",
            aliases=("Mobile Number", "Mobile", "Phone Number", "Contact Number", "Cell"),
            max_length=50,
        ),
        Field("city", "City", max_length=100),
        Field("state", "State", aliases=("Province", "Region"), max_length=100),
        Field("country", "Country", max_length=100),
        Field("location", "Location", aliases=("Address", "Current Location"), max_length=255),
        Field("current_title", "Current title", aliases=("Job Title", "Title", "Designation"), max_length=255),
        Field("current_company", "Current company", aliases=("Company", "Employer", "Current Employer"), max_length=255),
        Field(
            "total_experience_years",
            "Experience (years)",
            kind="decimal",
            aliases=("Experience", "Total Experience", "Years of Experience"),
        ),
        Field("skills", "Skills", kind="list", aliases=("Skill Set", "Key Skills", "Primary Skills")),
        Field("source", "Source", max_length=100),
        Field(
            "status",
            "Status",
            kind="choice",
            aliases=("Applicant Status", "Candidate Status"),
            choices=tuple(s.value for s in CandidateStatus),
            default=CandidateStatus.ACTIVE.value,
        ),
        Field(
            "work_auth",
            "Work authorization",
            aliases=("Work Authorization", "Visa Status", "Visa", "Work Permit"),
            max_length=100,
        ),
        Field("linkedin_url", "LinkedIn URL", aliases=("LinkedIn", "LinkedIn Profile"), max_length=500),
        Field("notice_period", "Notice period", max_length=50),
        Field(
            "created_at",
            "Created on",
            kind="datetime",
            aliases=("Created On", "Created date", "Created Date", "Date Created"),
        ),
        Field(
            "note",
            "Add to note",
            kind="note",
            aliases=("Ownership", "Created By", "Comments", "Remarks"),
            help="Any number of columns can go here; each becomes a line of one note.",
        ),
    )
    export_fields = (
        "external_id",
        "full_name",
        "email",
        "phone",
        "location",
        "current_title",
        "current_company",
        "total_experience_years",
        "skills",
        "source",
        "status",
        "work_auth",
        "linkedin_url",
        "notice_period",
        "created_at",
    )
    _updatable = (
        "external_id",
        "full_name",
        "email",
        "phone",
        "location",
        "current_title",
        "current_company",
        "total_experience_years",
        "skills",
        "source",
        "status",
        "work_auth",
        "linkedin_url",
        "notice_period",
    )

    def prepare(self, row: RowValues) -> str | None:
        v = row.values
        if not v.get("full_name"):
            combined = " ".join(p for p in (v.get("first_name"), v.get("last_name")) if p)
            v["full_name"] = combined or None
        if not v.get("full_name"):
            return "A name is required (map Full name, or First name and Last name)."
        if len(v["full_name"]) > 255:
            return "Full name is longer than 255 characters."
        if not v.get("location"):
            v["location"] = ", ".join(p for p in (v.get("city"), v.get("state"), v.get("country")) if p) or None
        return None

    def match_keys(self, row: RowValues) -> list[tuple[str, str]]:
        keys = []
        if row.get("external_id"):
            keys.append(("external_id", row.get("external_id")))
        if row.get("email"):
            keys.append(("email", row.get("email")))
        digits = phone_digits(row.get("phone"))
        if digits:
            keys.append(("phone", digits))
        return keys

    def find_existing(self, db, ctx, rows):
        external_ids = {r.get("external_id") for r in rows if r.get("external_id")}
        emails = {r.get("email") for r in rows if r.get("email")}
        phones = {d for r in rows if (d := phone_digits(r.get("phone")))}
        by_external: dict[str, uuid.UUID] = {}
        by_email: dict[str, uuid.UUID] = {}
        by_phone: dict[str, uuid.UUID] = {}

        base = select(Candidate.id, Candidate.external_id, Candidate.email, Candidate.phone).where(
            Candidate.organization_id == ctx.organization_id, Candidate.deleted_at.is_(None)
        )
        if external_ids:
            for r in db.execute(base.where(Candidate.external_id.in_(external_ids))).all():
                by_external.setdefault(r.external_id, r.id)
        if emails:
            for r in db.execute(base.where(func.lower(Candidate.email).in_(emails))).all():
                by_email.setdefault(r.email.lower(), r.id)
        if phones:
            for r in db.execute(base.where(PHONE_DIGITS_SQL.in_(phones))).all():
                by_phone.setdefault(phone_digits(r.phone), r.id)

        found = []
        for r in rows:
            found.append(
                by_external.get(r.get("external_id"))
                or by_email.get(r.get("email"))
                or by_phone.get(phone_digits(r.get("phone")))
            )
        return found

    def create_many(self, db, ctx, rows):
        candidates = []
        for row in rows:
            v = row.values
            tags = [IMPORTED_TAG] + ([] if v.get("email") else [MISSING_EMAIL_TAG])
            candidate = Candidate(
                organization_id=ctx.organization_id,
                import_job_id=ctx.import_job_id,
                created_by=ctx.actor_id,
                updated_by=ctx.actor_id,
                full_name=v["full_name"],
                email=v.get("email"),
                external_id=v.get("external_id"),
                phone=v.get("phone"),
                location=v.get("location"),
                current_title=v.get("current_title"),
                current_company=v.get("current_company"),
                total_experience_years=v.get("total_experience_years"),
                skills=v.get("skills") or [],
                source=v.get("source") or "Import",
                status=v.get("status") or CandidateStatus.ACTIVE.value,
                work_auth=v.get("work_auth"),
                linkedin_url=v.get("linkedin_url"),
                notice_period=v.get("notice_period"),
                tags=[CandidateTag(tag=t) for t in tags],
            )
            if v.get("created_at"):
                candidate.created_at = v["created_at"]
            if row.notes:
                candidate.notes = [
                    CandidateNote(author_id=ctx.actor_id, body=f"Imported from {ctx.file_name}\n" + "\n".join(row.notes))
                ]
            candidates.append(candidate)
        db.add_all(candidates)
        db.flush()
        return [c.id for c in candidates]

    def update(self, db, ctx, record_id, row):
        candidate = db.get(Candidate, record_id)
        _set_attrs(candidate, row.values, self._updatable)
        candidate.updated_by = ctx.actor_id
        if row.notes:
            db.add(
                CandidateNote(
                    candidate_id=candidate.id,
                    author_id=ctx.actor_id,
                    body=f"Updated from {ctx.file_name}\n" + "\n".join(row.notes),
                )
            )

    def in_use(self, db, ids):
        return _in_use(db, ids, Application.candidate_id, BenchProfile.candidate_id, OutboundMessage.candidate_id)

    def export_query(self, organization_id):
        return (
            select(Candidate)
            .where(Candidate.organization_id == organization_id, Candidate.deleted_at.is_(None))
            .order_by(Candidate.created_at)
        )


# -------------------------------------------------------------------- vendors


class VendorImporter(Importer):
    key = "vendors"
    label = "Vendors"
    model = Vendor
    fields = (
        Field(
            "name",
            "Vendor name",
            required=True,
            aliases=("Vendor", "Name", "Company Name", "Vendor Company"),
            max_length=255,
        ),
        Field("email_id", "Email", kind="email", aliases=("Email Address", "Email ID", "E-mail"), max_length=255),
        Field(
            "contact_number", "Contact number", aliases=("Phone", "Phone Number", "Mobile Number", "Contact"), max_length=50
        ),
        Field("website", "Website", aliases=("URL", "Web Site"), max_length=255),
        Field("federal_id", "Federal ID", aliases=("EIN", "Tax ID", "FEIN"), max_length=50),
        Field("fax", "Fax", max_length=50),
        Field("vendor_type", "Vendor type", aliases=("Type",), max_length=50),
        Field("vendor_classification", "Classification", aliases=("Vendor Classification",), max_length=50),
        Field("specialization", "Specialization", max_length=100),
        Field(
            "status",
            "Status",
            kind="choice",
            aliases=("Vendor Status",),
            choices=tuple(s.value for s in VendorStatus),
            default=VendorStatus.ACTIVE.value,
        ),
        Field("payment_terms", "Payment terms", max_length=50),
        Field("address", "Address", aliases=("Street", "Address Line 1"), max_length=500),
        Field("city", "City", max_length=100),
        Field("state", "State", aliases=("Province",), max_length=100),
        Field("country", "Country", max_length=100),
        Field("zip_code", "Zip code", aliases=("Zip", "Postal Code", "Pincode"), max_length=20),
        Field("technologies", "Technologies", kind="list", aliases=("Skills", "Tech Stack")),
        Field("about_vendor", "About", aliases=("Description", "About Vendor", "Notes", "Comments")),
        Field("created_at", "Created on", kind="datetime", aliases=("Created On", "Created date", "Date Created")),
    )
    export_fields = (
        "name",
        "email_id",
        "contact_number",
        "website",
        "federal_id",
        "vendor_type",
        "specialization",
        "status",
        "payment_terms",
        "address",
        "city",
        "state",
        "country",
        "zip_code",
        "technologies",
        "created_at",
    )
    _columns = tuple(f.key for f in fields if f.key != "created_at")

    def match_keys(self, row):
        return [("name", row.get("name").lower())] if row.get("name") else []

    def find_existing(self, db, ctx, rows):
        names = {r.get("name").lower() for r in rows if r.get("name")}
        existing: dict[str, uuid.UUID] = {}
        if names:
            query = select(Vendor.id, Vendor.name).where(
                Vendor.organization_id == ctx.organization_id, func.lower(Vendor.name).in_(names)
            )
            for r in db.execute(query).all():
                existing.setdefault(r.name.lower(), r.id)
        return [existing.get((r.get("name") or "").lower()) for r in rows]

    def create_many(self, db, ctx, rows):
        vendors = []
        for row in rows:
            v = {k: row.values.get(k) for k in self._columns if row.values.get(k) is not None}
            vendor = Vendor(
                organization_id=ctx.organization_id,
                import_job_id=ctx.import_job_id,
                created_by=ctx.actor_id,
                updated_by=ctx.actor_id,
                **v,
            )
            if row.values.get("created_at"):
                vendor.created_at = row.values["created_at"]
            vendors.append(vendor)
        db.add_all(vendors)
        db.flush()
        return [v.id for v in vendors]

    def update(self, db, ctx, record_id, row):
        vendor = db.get(Vendor, record_id)
        _set_attrs(vendor, row.values, self._columns)
        vendor.updated_by = ctx.actor_id

    def in_use(self, db, ids):
        return _in_use(db, ids, BenchSubmission.vendor_id, HotlistRecipient.vendor_id)


# -------------------------------------------------------------------- clients


class ClientImporter(Importer):
    key = "clients"
    label = "Clients"
    model = Client
    fields = (
        Field(
            "name", "Client name", required=True, aliases=("Client", "Name", "Company Name", "Account Name"), max_length=255
        ),
        Field(
            "client_code",
            "Client ID",
            aliases=("Client Code", "Client Id", "Account ID"),
            max_length=50,
            help="Left empty, one is generated.",
        ),
        Field("short_name", "Short name", max_length=100),
        Field("industry", "Industry", aliases=("Sector",), max_length=100),
        Field(
            "status",
            "Status",
            kind="choice",
            aliases=("Client Status",),
            choices=tuple(s.value for s in ClientStatus),
            default=ClientStatus.ACTIVE.value,
        ),
        Field("category", "Category", max_length=50),
        Field("contact_number", "Contact number", aliases=("Phone", "Phone Number", "Contact"), max_length=50),
        Field("email_id", "Email", kind="email", aliases=("Email Address", "Email ID", "E-mail"), max_length=255),
        Field("website", "Website", aliases=("URL", "Web Site"), max_length=255),
        Field("federal_id", "Federal ID", aliases=("EIN", "Tax ID", "FEIN"), max_length=50),
        Field("fax", "Fax", max_length=50),
        Field("payment_terms", "Payment terms", max_length=50),
        Field("address", "Address", aliases=("Street", "Address Line 1"), max_length=500),
        Field("city", "City", max_length=100),
        Field("state", "State", aliases=("Province",), max_length=100),
        Field("country", "Country", max_length=100),
        Field("postal_code", "Postal code", aliases=("Zip", "Zip Code", "Pincode"), max_length=20),
        Field("business_unit", "Business unit", max_length=100),
        Field("about_company", "About", aliases=("Description", "About Company", "Notes", "Comments")),
        Field("created_at", "Created on", kind="datetime", aliases=("Created On", "Created date", "Date Created")),
    )
    export_fields = (
        "client_code",
        "name",
        "short_name",
        "industry",
        "status",
        "category",
        "contact_number",
        "email_id",
        "website",
        "address",
        "city",
        "state",
        "country",
        "postal_code",
        "business_unit",
        "created_at",
    )
    _columns = tuple(f.key for f in fields if f.key not in ("created_at", "client_code"))

    def match_keys(self, row):
        if row.get("client_code"):
            return [("code", row.get("client_code").lower())]
        return [("name", row.get("name").lower())] if row.get("name") else []

    def find_existing(self, db, ctx, rows):
        codes = {r.get("client_code").lower() for r in rows if r.get("client_code")}
        names = {r.get("name").lower() for r in rows if r.get("name") and not r.get("client_code")}
        by_code: dict[str, uuid.UUID] = {}
        by_name: dict[str, uuid.UUID] = {}
        base = select(Client.id, Client.client_code, Client.name).where(Client.organization_id == ctx.organization_id)
        if codes:
            for r in db.execute(base.where(func.lower(Client.client_code).in_(codes))).all():
                by_code[r.client_code.lower()] = r.id
        if names:
            for r in db.execute(base.where(func.lower(Client.name).in_(names))).all():
                by_name.setdefault(r.name.lower(), r.id)
        return [
            by_code.get(r.get("client_code").lower()) if r.get("client_code") else by_name.get((r.get("name") or "").lower())
            for r in rows
        ]

    def _next_codes(self, db: Session, organization_id: uuid.UUID, count: int) -> list[str]:
        """`count` unused client codes in the app's CLI-<year><n> format, found
        with a couple of queries rather than one existence check per code."""
        year = datetime.now(UTC).year
        start = db.scalar(select(func.count(Client.id)).where(Client.organization_id == organization_id)) or 0
        codes: list[str] = []
        n = start
        while len(codes) < count:
            batch = [f"CLI-{year}{i:04d}" for i in range(n + 1, n + 1 + (count - len(codes)) * 2)]
            n += len(batch)
            taken = set(
                db.scalars(
                    select(Client.client_code).where(
                        Client.organization_id == organization_id, Client.client_code.in_(batch)
                    )
                ).all()
            )
            codes += [c for c in batch if c not in taken][: count - len(codes)]
        return codes

    def create_many(self, db, ctx, rows):
        generated = iter(self._next_codes(db, ctx.organization_id, sum(1 for r in rows if not r.get("client_code"))))
        clients = []
        for row in rows:
            v = {k: row.values.get(k) for k in self._columns if row.values.get(k) is not None}
            client = Client(
                organization_id=ctx.organization_id,
                import_job_id=ctx.import_job_id,
                created_by=ctx.actor_id,
                updated_by=ctx.actor_id,
                client_code=row.get("client_code") or next(generated),
                **v,
            )
            if row.values.get("created_at"):
                client.created_at = row.values["created_at"]
            clients.append(client)
        db.add_all(clients)
        db.flush()
        return [c.id for c in clients]

    def update(self, db, ctx, record_id, row):
        client = db.get(Client, record_id)
        _set_attrs(client, row.values, self._columns)
        client.updated_by = ctx.actor_id

    def in_use(self, db, ids):
        return _in_use(
            db, ids, Job.client_id, Client.parent_client_id, BenchSubmission.client_id, HotlistRecipient.client_id
        )


# ----------------------------------------------------------------------- jobs


class JobImporter(Importer):
    key = "jobs"
    label = "Jobs"
    model = Job
    fields = (
        Field("title", "Job title", required=True, aliases=("Title", "Position", "Job Name", "Role"), max_length=255),
        Field(
            "client",
            "Client",
            aliases=("Client Name", "Account"),
            help="Matched to an existing client by name or Client ID.",
        ),
        Field("department", "Department", max_length=100),
        Field("location", "Location", max_length=255),
        Field("city", "City", max_length=100),
        Field("country", "Country", max_length=100),
        Field(
            "workplace",
            "Workplace",
            kind="choice",
            aliases=("Work Mode", "Remote", "Workplace Type"),
            choices=("Onsite", "Hybrid", "Remote"),
            default="Onsite",
        ),
        Field(
            "employment_type",
            "Employment type",
            kind="choice",
            aliases=("Job Type", "Type", "Employment"),
            choices=("Full-time", "Contract", "Part-time", "Intern"),
            default="Full-time",
        ),
        Field("openings", "Openings", kind="int", aliases=("Positions", "Number of Positions", "No of Positions")),
        Field("pay_min", "Pay min", kind="int", aliases=("Min Pay", "Salary Min", "Pay Rate Min")),
        Field("pay_max", "Pay max", kind="int", aliases=("Max Pay", "Salary Max", "Pay Rate Max")),
        Field(
            "priority",
            "Priority",
            kind="choice",
            choices=tuple(p.value for p in JobPriority),
            default=JobPriority.MEDIUM.value,
        ),
        Field("summary", "Summary", aliases=("Short Description",)),
        Field("description", "Description", aliases=("Job Description", "JD")),
        Field("required_skills", "Required skills", kind="list", aliases=("Skills", "Must Have Skills", "Primary Skills")),
        Field("nice_to_have", "Nice-to-have skills", kind="list", aliases=("Secondary Skills", "Good to Have")),
        Field("experience", "Experience", aliases=("Experience Required",), max_length=100),
        Field("end_client", "End client", max_length=255),
        Field("duration", "Duration", aliases=("Contract Duration",), max_length=100),
        Field("business_unit", "Business unit", max_length=100),
    )
    export_fields = (
        "req_id",
        "title",
        "client",
        "status",
        "department",
        "location",
        "workplace",
        "employment_type",
        "openings",
        "pay_min",
        "pay_max",
        "priority",
        "required_skills",
        "created_at",
    )
    _columns = tuple(f.key for f in fields if f.key != "client")

    def resolve(self, db, ctx, rows):
        refs = {r.get("client").lower() for r in rows if r.get("client")}
        lookup: dict[str, uuid.UUID] = {}
        if refs:
            query = select(Client.id, Client.name, Client.client_code).where(
                Client.organization_id == ctx.organization_id,
                (func.lower(Client.name).in_(refs)) | (func.lower(Client.client_code).in_(refs)),
            )
            for r in db.execute(query).all():
                lookup.setdefault(r.client_code.lower(), r.id)
                lookup.setdefault(r.name.lower(), r.id)
        for r in rows:
            ref = r.get("client")
            r.values["client_id"] = lookup.get(ref.lower()) if ref else None
            if ref and r.values["client_id"] is None:
                r.warnings.append(f"No client named '{ref}'; the job was imported without one.")
        return [None] * len(rows)

    def match_keys(self, row):
        return [("title", f"{row.get('title').lower()}|{row.get('client_id') or ''}")] if row.get("title") else []

    def find_existing(self, db, ctx, rows):
        titles = {r.get("title").lower() for r in rows if r.get("title")}
        existing: dict[tuple, uuid.UUID] = {}
        if titles:
            query = select(Job.id, Job.title, Job.client_id).where(
                Job.organization_id == ctx.organization_id,
                Job.deleted_at.is_(None),
                func.lower(Job.title).in_(titles),
            )
            for r in db.execute(query).all():
                existing.setdefault((r.title.lower(), r.client_id), r.id)
        return [existing.get(((r.get("title") or "").lower(), r.get("client_id"))) for r in rows]

    def create_many(self, db, ctx, rows):
        from app.services.jobs.service import create_job

        ids = []
        for row in rows:
            fields = {k: row.values.get(k) for k in self._columns if row.values.get(k) is not None}
            fields.setdefault("workplace", "Onsite")
            fields.setdefault("employment_type", "Full-time")
            job = create_job(
                db,
                organization_id=ctx.organization_id,
                actor_id=ctx.actor_id,
                client_id=row.get("client_id"),
                import_job_id=ctx.import_job_id,
                **fields,
            )
            ids.append(job.id)
        return ids

    def update(self, db, ctx, record_id, row):
        job = db.get(Job, record_id)
        _set_attrs(job, row.values, self._columns)
        job.updated_by = ctx.actor_id

    def in_use(self, db, ids):
        return _in_use(db, ids, Application.job_id, BenchSubmission.job_id)

    def export_query(self, organization_id):
        return select(Job).where(Job.organization_id == organization_id, Job.deleted_at.is_(None)).order_by(Job.created_at)

    def export_value(self, obj, key):
        if key == "client":
            return obj.client.name if getattr(obj, "client", None) else None
        return getattr(obj, key, None)


# ---------------------------------------------------------------------- bench


class BenchImporter(Importer):
    key = "bench"
    label = "Talent bench"
    model = BenchProfile
    fields = (
        Field(
            "candidate_email",
            "Candidate email",
            kind="email",
            aliases=("Email", "Email Address", "Consultant Email"),
            help="Each row must name a candidate already in the system, by email or External ID.",
        ),
        Field("candidate_external_id", "Candidate external ID", aliases=("Applicant ID", "Candidate ID")),
        Field("marketing_title", "Marketing title", aliases=("Title", "Job Title", "Headline"), max_length=255),
        Field(
            "status",
            "Bench status",
            kind="choice",
            aliases=("Status",),
            choices=tuple(s.value for s in BenchStatus),
            default=BenchStatus.ACTIVE.value,
        ),
        Field("bench_start_date", "Bench start date", kind="date", aliases=("Start Date", "On Bench Since")),
        Field("available_from", "Available from", kind="date", aliases=("Availability", "Available Date")),
        Field("desired_rate", "Desired rate", kind="decimal", aliases=("Rate", "Bill Rate", "Expected Rate")),
        Field("rate_unit", "Rate unit", aliases=("Per",), max_length=20),
        Field("tax_term", "Tax term", aliases=("Tax Terms", "Employment Type"), max_length=20),
        Field("preferred_locations", "Preferred locations", aliases=("Locations", "Preferred Location"), max_length=500),
        Field("willing_to_relocate", "Willing to relocate", kind="bool", aliases=("Relocation", "Relocate")),
        Field("marketing_summary", "Marketing summary", aliases=("Summary", "Profile Summary")),
    )
    export_fields = (
        "candidate_email",
        "marketing_title",
        "status",
        "bench_start_date",
        "available_from",
        "desired_rate",
        "rate_unit",
        "tax_term",
        "preferred_locations",
        "willing_to_relocate",
    )
    _columns = (
        "marketing_title",
        "status",
        "bench_start_date",
        "available_from",
        "desired_rate",
        "rate_unit",
        "tax_term",
        "preferred_locations",
        "willing_to_relocate",
        "marketing_summary",
    )

    def prepare(self, row):
        if not row.get("candidate_email") and not row.get("candidate_external_id"):
            return "Each row needs the candidate's email or External ID, to find them."
        return None

    def resolve(self, db, ctx, rows):
        emails = {r.get("candidate_email") for r in rows if r.get("candidate_email")}
        external_ids = {r.get("candidate_external_id") for r in rows if r.get("candidate_external_id")}
        by_email: dict[str, uuid.UUID] = {}
        by_external: dict[str, uuid.UUID] = {}
        base = select(Candidate.id, Candidate.email, Candidate.external_id).where(
            Candidate.organization_id == ctx.organization_id, Candidate.deleted_at.is_(None)
        )
        if emails:
            for r in db.execute(base.where(func.lower(Candidate.email).in_(emails))).all():
                by_email.setdefault(r.email.lower(), r.id)
        if external_ids:
            for r in db.execute(base.where(Candidate.external_id.in_(external_ids))).all():
                by_external.setdefault(r.external_id, r.id)

        errors: list[str | None] = []
        for r in rows:
            candidate_id = by_external.get(r.get("candidate_external_id")) or by_email.get(r.get("candidate_email"))
            r.values["candidate_id"] = candidate_id
            if candidate_id:
                errors.append(None)
                continue
            who = (
                f"email {r.get('candidate_email')}"
                if r.get("candidate_email")
                else f"External ID {r.get('candidate_external_id')}"
            )
            errors.append(f"No candidate with {who}. Import candidates first.")
        return errors

    def match_keys(self, row):
        return [("candidate", str(row.get("candidate_id")))] if row.get("candidate_id") else []

    def find_existing(self, db, ctx, rows):
        candidate_ids = {r.get("candidate_id") for r in rows if r.get("candidate_id")}
        existing: dict[uuid.UUID, uuid.UUID] = {}
        if candidate_ids:
            query = select(BenchProfile.id, BenchProfile.candidate_id).where(
                BenchProfile.organization_id == ctx.organization_id,
                BenchProfile.deleted_at.is_(None),
                BenchProfile.candidate_id.in_(candidate_ids),
            )
            existing = {r.candidate_id: r.id for r in db.execute(query).all()}
        return [existing.get(r.get("candidate_id")) for r in rows]

    def create_many(self, db, ctx, rows):
        from app.services.bench.service import create_profile

        ids = []
        for row in rows:
            fields = {k: row.values.get(k) for k in self._columns if row.values.get(k) is not None}
            profile = create_profile(
                db,
                organization_id=ctx.organization_id,
                actor_id=ctx.actor_id,
                candidate_id=row.get("candidate_id"),
                **fields,
            )
            profile.import_job_id = ctx.import_job_id
            db.flush()
            ids.append(profile.id)
        return ids

    def update(self, db, ctx, record_id, row):
        profile = db.get(BenchProfile, record_id)
        _set_attrs(profile, row.values, self._columns)
        profile.updated_by = ctx.actor_id

    def in_use(self, db, ids):
        return _in_use(db, ids, BenchSubmission.bench_profile_id, HotlistMember.bench_profile_id)

    def export_query(self, organization_id):
        return (
            select(BenchProfile)
            .where(BenchProfile.organization_id == organization_id, BenchProfile.deleted_at.is_(None))
            .order_by(BenchProfile.created_at)
        )

    def export_value(self, obj, key):
        if key == "candidate_email":
            return obj.candidate.email if obj.candidate else None
        return getattr(obj, key, None)


IMPORTERS: dict[str, Importer] = {
    importer.key: importer
    for importer in (CandidateImporter(), VendorImporter(), ClientImporter(), JobImporter(), BenchImporter())
}

# Mappings shipped with the app. Keys are source column headers exactly as the
# other system exports them; values are field keys above.
BUILT_IN_PRESETS: dict[str, dict[str, dict[str, str]]] = {
    "candidates": {
        "Ceipal applicants": {
            "Applicant ID": "external_id",
            "Applicant Name": "full_name",
            "Email Address": "email",
            "Mobile Number": "phone",
            "City": "city",
            "Source": "source",
            "State": "state",
            "Applicant Status": "status",
            "Job Title": "current_title",
            "Ownership": "note",
            "Work Authorization": "work_auth",
            "Created By": "note",
            "Created On": "created_at",
            "Created date": "created_at",
        }
    }
}

// Centralized mock data for ATS Tracker

export type JobStatus = "Draft" | "Active" | "On Hold" | "Closed" | "Cancelled";
export type Priority = "Low" | "Medium" | "High" | "Urgent";
export type Stage =
  | "Applied"
  | "Screening"
  | "Shortlisted"
  | "Recruiter Interview"
  | "Technical Assessment"
  | "Hiring Manager Interview"
  | "Panel Interview"
  | "Background Check"
  | "Offer"
  | "Offer Accepted"
  | "Onboarding"
  | "Hired"
  | "Rejected"
  | "On Hold";

export const STAGES: Stage[] = [
  "Applied",
  "Screening",
  "Shortlisted",
  "Recruiter Interview",
  "Technical Assessment",
  "Hiring Manager Interview",
  "Panel Interview",
  "Background Check",
  "Offer",
  "Offer Accepted",
  "Onboarding",
  "Hired",
];

export interface Job {
  id: string;
  reqId: string;
  title: string;
  department: string;
  client: string;
  hiringManager: string;
  recruiter: string;
  location: string;
  workplace: "Remote" | "Hybrid" | "Onsite";
  employmentType: "Full-time" | "Contract" | "Part-time" | "Intern";
  openings: number;
  payMin: number;
  payMax: number;
  priority: Priority;
  status: JobStatus;
  postedAt: string;
  applications: number;
  shortlisted: number;
  interviews: number;
  offers: number;
  hires: number;
  summary: string;
  description: string;
  responsibilities: string[];
  requiredSkills: string[];
  niceToHave: string[];
  experience: string;
  education: string;
}

export interface Candidate {
  id: string;
  name: string;
  email: string;
  phone: string;
  location: string;
  currentCompany: string;
  currentTitle: string;
  totalExperience: number;
  relevantExperience: number;
  noticePeriod: string;
  currentCTC: number;
  expectedCTC: number;
  skills: string[];
  source: string;
  tags: string[];
  rating: number;
  linkedin: string;
  avatar?: string;
  appliedJobs: string[];
  stage: Stage;
  aiScore: number;
  lastActivity: string;
  status: "Active" | "Passive" | "Silver Medalist" | "Do Not Contact";
  education: { degree: string; school: string; year: string }[];
  workAuth: string;
  relocation: boolean;
}

const recruiters = ["Priya Sharma", "Marcus Chen", "Elena Rodriguez", "Aditya Nair", "Sarah Kim"];
const managers = ["David Park", "Rachel Wu", "James O'Brien", "Nadia Ahmed", "Tom Bergman"];
const clients = [
  "Acme Financial",
  "Northwind Health",
  "Zephyr Cloud",
  "Orion Retail",
  "Kestrel AI",
  "Internal",
];
const depts = ["Engineering", "Data", "Product", "Design", "People", "Sales", "Operations"];
const locations = [
  "Bengaluru, IN",
  "New York, NY",
  "Berlin, DE",
  "London, UK",
  "Singapore",
  "Austin, TX",
  "Toronto, CA",
  "Remote",
];

const jobTemplates: Array<Partial<Job> & { title: string; skills: string[] }> = [
  {
    title: "Senior Java Developer",
    skills: ["Java", "Spring Boot", "Microservices", "Kafka", "PostgreSQL"],
  },
  { title: "AWS Cloud Engineer", skills: ["AWS", "Terraform", "EKS", "Lambda", "CloudFormation"] },
  {
    title: "Kubernetes Platform Engineer",
    skills: ["Kubernetes", "Helm", "Istio", "Prometheus", "Go"],
  },
  {
    title: "Senior React Developer",
    skills: ["React", "TypeScript", "Next.js", "GraphQL", "Testing Library"],
  },
  { title: "Data Engineer", skills: ["Python", "Spark", "Airflow", "Snowflake", "dbt"] },
  {
    title: "Business Analyst",
    skills: ["SQL", "Tableau", "Requirements", "Agile", "Stakeholder Mgmt"],
  },
  {
    title: "Talent Acquisition Specialist",
    skills: ["Sourcing", "LinkedIn Recruiter", "Boolean Search", "ATS"],
  },
  {
    title: "Senior QA Engineer",
    skills: ["Cypress", "Playwright", "TestRail", "API Testing", "CI/CD"],
  },
  { title: "Product Manager", skills: ["Roadmapping", "Discovery", "Analytics", "SQL", "Figma"] },
  {
    title: "Machine Learning Engineer",
    skills: ["Python", "PyTorch", "MLOps", "SageMaker", "NLP"],
  },
  { title: "DevSecOps Engineer", skills: ["Security", "Vault", "SIEM", "Terraform", "Kubernetes"] },
  { title: "iOS Engineer", skills: ["Swift", "SwiftUI", "Combine", "XCTest"] },
  { title: "Android Engineer", skills: ["Kotlin", "Jetpack Compose", "Coroutines"] },
  { title: "Staff Platform Engineer", skills: ["Distributed Systems", "Go", "gRPC", "Kubernetes"] },
  { title: "UX Designer", skills: ["Figma", "Prototyping", "User Research", "Design Systems"] },
  { title: "Salesforce Administrator", skills: ["Salesforce", "Apex", "Flow", "Reports"] },
  { title: "Financial Analyst", skills: ["Excel", "Modeling", "SQL", "Power BI"] },
  {
    title: "Site Reliability Engineer",
    skills: ["Prometheus", "Grafana", "Kubernetes", "Go", "Incident Mgmt"],
  },
];

function pick<T>(a: T[], i: number): T {
  return a[i % a.length];
}

const statuses: JobStatus[] = [
  "Active",
  "Active",
  "Active",
  "Active",
  "Draft",
  "On Hold",
  "Closed",
];
const priorities: Priority[] = ["Low", "Medium", "High", "Urgent"];

export const jobs: Job[] = jobTemplates.map((t, i) => ({
  id: `job-${1000 + i}`,
  reqId: `REQ-${2025000 + i}`,
  title: t.title,
  department: pick(depts, i),
  client: pick(clients, i),
  hiringManager: pick(managers, i),
  recruiter: pick(recruiters, i),
  location: pick(locations, i),
  workplace: (["Hybrid", "Remote", "Onsite"] as const)[i % 3],
  employmentType: (["Full-time", "Full-time", "Full-time", "Contract"] as const)[i % 4],
  openings: (i % 4) + 1,
  payMin: 80000 + i * 5000,
  payMax: 140000 + i * 6000,
  priority: pick(priorities, i + 1),
  status: pick(statuses, i),
  postedAt: `2025-${String(1 + (i % 11)).padStart(2, "0")}-${String(1 + (i % 27)).padStart(2, "0")}`,
  applications: 12 + ((i * 7) % 80),
  shortlisted: 3 + (i % 12),
  interviews: 1 + (i % 8),
  offers: i % 3,
  hires: i % 2,
  summary: `We're hiring a ${t.title} to join our ${pick(depts, i)} team and drive impact across ${pick(clients, i)} initiatives.`,
  description: `As a ${t.title}, you will collaborate cross-functionally to design, build and ship high quality, scalable solutions. You'll partner with engineering, product, and design to deliver measurable outcomes for our customers.`,
  responsibilities: [
    `Own delivery of key ${t.title.split(" ")[0]} initiatives end-to-end`,
    "Collaborate with peers on architecture, code reviews, and standards",
    "Mentor teammates and raise the technical bar",
    "Partner with stakeholders on prioritization and trade-offs",
  ],
  requiredSkills: t.skills,
  niceToHave: ["Open-source contributions", "Startup experience", "Public speaking"],
  experience: `${3 + (i % 6)}–${7 + (i % 6)} years`,
  education: "Bachelor's degree in Computer Science or equivalent experience",
}));

const firstNames = [
  "Aarav",
  "Priya",
  "Marcus",
  "Sofia",
  "Chen",
  "Elena",
  "Aditya",
  "Sarah",
  "Liam",
  "Ava",
  "Noah",
  "Mia",
  "Oliver",
  "Zara",
  "Ethan",
  "Isla",
  "Kai",
  "Amelia",
  "Rohan",
  "Nora",
  "Yara",
  "Diego",
  "Hana",
  "Ivan",
  "Layla",
  "Omar",
  "Sana",
  "Theo",
  "Uma",
  "Vera",
  "Wren",
  "Ximena",
  "Yusuf",
  "Zane",
  "Anaya",
  "Bruno",
  "Cora",
  "Dante",
  "Eva",
  "Farhan",
  "Gia",
  "Hugo",
  "Ines",
  "Jai",
  "Kavya",
  "Leo",
  "Maya",
  "Nikhil",
  "Olga",
  "Pablo",
];
const lastNames = [
  "Kapoor",
  "Chen",
  "Rodriguez",
  "Nair",
  "Kim",
  "Park",
  "Wu",
  "O'Brien",
  "Ahmed",
  "Bergman",
  "Sharma",
  "Silva",
  "Patel",
  "Nguyen",
  "Kumar",
  "Lopez",
  "Iyer",
  "Rossi",
  "Fischer",
  "Anderson",
  "Sato",
  "Kowalski",
  "Petrova",
  "Hassan",
  "Yildiz",
];

const stagesForSample: Stage[] = [
  "Applied",
  "Applied",
  "Screening",
  "Screening",
  "Shortlisted",
  "Recruiter Interview",
  "Technical Assessment",
  "Hiring Manager Interview",
  "Panel Interview",
  "Offer",
  "Offer Accepted",
  "Onboarding",
  "Hired",
  "Rejected",
  "On Hold",
];
const sources = [
  "Careers Page",
  "LinkedIn",
  "Referral",
  "Naukri",
  "Indeed",
  "Recruiter Sourced",
  "Talent Pool",
];

export const candidates: Candidate[] = Array.from({ length: 56 }, (_, i) => {
  const first = pick(firstNames, i * 3 + 1);
  const last = pick(lastNames, i * 5 + 2);
  const job = pick(jobs, i);
  return {
    id: `cand-${5000 + i}`,
    name: `${first} ${last}`,
    email: `${first.toLowerCase()}.${last.toLowerCase().replace(/[^a-z]/g, "")}@example.com`,
    phone: `+1 (555) ${String(100 + (i % 900)).padStart(3, "0")}-${String(1000 + ((i * 17) % 9000)).padStart(4, "0")}`,
    location: pick(locations, i + 2),
    currentCompany: pick(
      [
        "Acme Corp",
        "Meta",
        "Google",
        "Amazon",
        "Startup XYZ",
        "Freelance",
        "Netflix",
        "Stripe",
        "Shopify",
        "Uber",
        "Airbnb",
      ],
      i,
    ),
    currentTitle: job.title.replace("Senior ", "").replace("Staff ", ""),
    totalExperience: 2 + (i % 14),
    relevantExperience: 1 + (i % 10),
    noticePeriod: pick(["Immediate", "15 days", "30 days", "60 days", "90 days"], i),
    currentCTC: 60000 + i * 3200,
    expectedCTC: 90000 + i * 4100,
    skills: job.requiredSkills
      .slice(0, 3 + (i % 3))
      .concat(pick(["Docker", "AWS", "Python", "SQL", "Leadership", "Mentoring"], i)),
    source: pick(sources, i),
    tags: i % 4 === 0 ? ["Top Talent"] : i % 5 === 0 ? ["Silver Medalist"] : [],
    rating: (i % 5) + 1,
    linkedin: `https://linkedin.com/in/${first.toLowerCase()}-${last.toLowerCase()}`,
    appliedJobs: [job.id, ...(i % 3 === 0 ? [pick(jobs, i + 3).id] : [])],
    stage: pick(stagesForSample, i),
    aiScore: 45 + ((i * 13) % 55),
    lastActivity: `${1 + (i % 30)}d ago`,
    status: pick(["Active", "Active", "Active", "Passive", "Silver Medalist"] as const, i),
    education: [
      {
        degree: "B.S. Computer Science",
        school: pick(["IIT Bombay", "Stanford", "MIT", "TU Berlin", "NUS", "U of Toronto"], i),
        year: `${2010 + (i % 12)}`,
      },
    ],
    workAuth: pick(["Citizen", "Work Permit", "H1B", "EU Blue Card", "No sponsorship needed"], i),
    relocation: i % 3 === 0,
  };
});

export interface Interview {
  id: string;
  candidateId: string;
  jobId: string;
  round: string;
  interviewer: string;
  scheduledAt: string;
  status: "Scheduled" | "Completed" | "Cancelled" | "Rescheduled";
  mode: "Video" | "Onsite" | "Phone";
  feedback?: {
    rating: number;
    recommendation: "Strong Yes" | "Yes" | "No" | "Strong No";
    notes: string;
  };
}

export const interviews: Interview[] = candidates.slice(0, 22).map((c, i) => ({
  id: `int-${9000 + i}`,
  candidateId: c.id,
  jobId: c.appliedJobs[0],
  round: pick(["Recruiter Screen", "Technical", "Hiring Manager", "Panel", "HR"], i),
  interviewer: pick(managers.concat(recruiters), i),
  scheduledAt: `2026-07-${String(10 + (i % 20)).padStart(2, "0")} ${9 + (i % 8)}:00`,
  status: pick(["Scheduled", "Scheduled", "Completed", "Completed", "Rescheduled"] as const, i),
  mode: pick(["Video", "Onsite", "Phone"] as const, i),
  feedback:
    i % 2 === 0
      ? {
          rating: (i % 5) + 1,
          recommendation: pick(["Strong Yes", "Yes", "No"] as const, i),
          notes: "Solid fundamentals, communicates clearly. Recommend advancing.",
        }
      : undefined,
}));

export interface Offer {
  id: string;
  candidateId: string;
  jobId: string;
  status: "Draft" | "Approval Pending" | "Sent" | "Accepted" | "Declined" | "Expired";
  baseSalary: number;
  bonus: number;
  equity: string;
  joiningDate: string;
  createdAt: string;
}

export const offers: Offer[] = candidates.slice(0, 10).map((c, i) => ({
  id: `off-${7000 + i}`,
  candidateId: c.id,
  jobId: c.appliedJobs[0],
  status: pick(
    ["Draft", "Approval Pending", "Sent", "Sent", "Accepted", "Declined", "Expired"] as const,
    i,
  ),
  baseSalary: 120000 + i * 8000,
  bonus: 15000 + i * 1000,
  equity: `${1000 + i * 200} RSUs / 4yr`,
  joiningDate: `2026-08-${String(1 + (i % 27)).padStart(2, "0")}`,
  createdAt: `2026-07-${String(1 + (i % 9)).padStart(2, "0")}`,
}));

export interface Activity {
  id: string;
  type: string;
  actor: string;
  target: string;
  at: string;
}

export const activities: Activity[] = [
  {
    id: "a1",
    type: "stage_move",
    actor: "Priya Sharma",
    target: "Sofia Rodriguez → Hiring Manager Interview",
    at: "2m ago",
  },
  {
    id: "a2",
    type: "offer_sent",
    actor: "Marcus Chen",
    target: "Aarav Kapoor for Senior React Developer",
    at: "24m ago",
  },
  {
    id: "a3",
    type: "note",
    actor: "David Park",
    target: "Left feedback on Chen Liu",
    at: "1h ago",
  },
  {
    id: "a4",
    type: "new_application",
    actor: "System",
    target: "12 new applications on AWS Cloud Engineer",
    at: "3h ago",
  },
  {
    id: "a5",
    type: "interview_scheduled",
    actor: "Elena Rodriguez",
    target: "Panel interview with Zara Patel",
    at: "5h ago",
  },
  {
    id: "a6",
    type: "hired",
    actor: "Sarah Kim",
    target: "Liam Anderson hired as Data Engineer",
    at: "yesterday",
  },
  {
    id: "a7",
    type: "ai_review",
    actor: "AI Assistant",
    target: "18 resumes scored for Java Developer",
    at: "yesterday",
  },
];

export interface EmailTemplate {
  id: string;
  name: string;
  type: "Interview Invite" | "Offer" | "Rejection" | "Follow-up" | "Acknowledgment";
  subject: string;
  body: string;
  updated: string;
}

export const templates: EmailTemplate[] = [
  {
    id: "t1",
    name: "Application Acknowledgment",
    type: "Acknowledgment",
    subject: "We received your application for {{job_title}}",
    body: "Hi {{candidate_first_name}},\n\nThanks for applying to the {{job_title}} role at {{company}}...",
    updated: "2 days ago",
  },
  {
    id: "t2",
    name: "Recruiter Screen Invite",
    type: "Interview Invite",
    subject: "Next step: 30-min chat about {{job_title}}",
    body: "Hi {{candidate_first_name}},\n\nWe'd love to schedule a short conversation...",
    updated: "1 week ago",
  },
  {
    id: "t3",
    name: "Offer — Standard",
    type: "Offer",
    subject: "Your offer from {{company}}",
    body: "Congratulations {{candidate_first_name}}! We're excited to extend an offer...",
    updated: "3 days ago",
  },
  {
    id: "t4",
    name: "Polite Rejection",
    type: "Rejection",
    subject: "Update on your application",
    body: "Hi {{candidate_first_name}},\n\nThank you again for taking the time...",
    updated: "5 days ago",
  },
  {
    id: "t5",
    name: "Follow-up After Interview",
    type: "Follow-up",
    subject: "Following up on your interview",
    body: "Hi {{candidate_first_name}},\n\nJust checking in after our conversation...",
    updated: "1 day ago",
  },
];

export interface Client {
  id: string;
  name: string;
  industry: string;
  activeJobs: number;
  contact: string;
  status: "Active" | "Prospect" | "Paused";
}

export const clientsList: Client[] = clients
  .filter((c) => c !== "Internal")
  .map((c, i) => ({
    id: `cli-${100 + i}`,
    name: c,
    industry: pick(["Finance", "Healthcare", "Cloud/SaaS", "Retail", "AI/ML"], i),
    activeJobs: 2 + i * 2,
    contact: pick(managers, i),
    status: pick(["Active", "Active", "Prospect", "Paused"] as const, i),
  }));

export interface Vendor {
  id: string;
  name: string;
  specialization: string;
  activeSubmissions: number;
  status: "Active" | "On Hold";
}

export const vendorsList: Vendor[] = [
  {
    id: "v1",
    name: "TalentBridge Partners",
    specialization: "Engineering",
    activeSubmissions: 12,
    status: "Active",
  },
  {
    id: "v2",
    name: "Peak Recruit",
    specialization: "Data & ML",
    activeSubmissions: 7,
    status: "Active",
  },
  {
    id: "v3",
    name: "Northlight Staffing",
    specialization: "Contract",
    activeSubmissions: 3,
    status: "On Hold",
  },
  {
    id: "v4",
    name: "Vertex Search",
    specialization: "Executive",
    activeSubmissions: 5,
    status: "Active",
  },
];

export const funnelData = [
  { stage: "Applied", value: 1240 },
  { stage: "Screening", value: 620 },
  { stage: "Shortlisted", value: 310 },
  { stage: "Interview", value: 160 },
  { stage: "Offer", value: 48 },
  { stage: "Hired", value: 32 },
];

export const hiringTrend = [
  { month: "Jan", hires: 8, offers: 12 },
  { month: "Feb", hires: 11, offers: 14 },
  { month: "Mar", hires: 9, offers: 13 },
  { month: "Apr", hires: 14, offers: 18 },
  { month: "May", hires: 17, offers: 22 },
  { month: "Jun", hires: 15, offers: 19 },
  { month: "Jul", hires: 21, offers: 26 },
];

export const sourcePerformance = [
  { source: "Careers Page", value: 34 },
  { source: "LinkedIn", value: 28 },
  { source: "Referrals", value: 18 },
  { source: "Job Boards", value: 12 },
  { source: "Sourced", value: 8 },
];

export const scoreDistribution = [
  { bucket: "0-40", count: 42 },
  { bucket: "41-60", count: 88 },
  { bucket: "61-75", count: 124 },
  { bucket: "76-90", count: 76 },
  { bucket: "91-100", count: 24 },
];

export function findJob(id: string) {
  return jobs.find((j) => j.id === id);
}
export function findCandidate(id: string) {
  return candidates.find((c) => c.id === id);
}
export function candidatesForJob(jobId: string) {
  return candidates.filter((c) => c.appliedJobs.includes(jobId));
}

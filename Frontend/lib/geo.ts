// Country-dependent option lists for job requisitions and candidate search, so
// an India job offers Indian states and Indian work authorizations instead of
// the US ones.

export const COUNTRIES = [
  "United States",
  "Canada",
  "India",
  "United Kingdom",
  "Australia",
] as const;

export const DEFAULT_COUNTRY = "United States";

const REGIONS: Record<string, readonly string[]> = {
  "United States": [
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "District of Columbia",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
  ],
  Canada: [
    "Alberta",
    "British Columbia",
    "Manitoba",
    "New Brunswick",
    "Newfoundland and Labrador",
    "Northwest Territories",
    "Nova Scotia",
    "Nunavut",
    "Ontario",
    "Prince Edward Island",
    "Quebec",
    "Saskatchewan",
    "Yukon",
  ],
  India: [
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    // Union territories
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
  ],
  "United Kingdom": ["England", "Northern Ireland", "Scotland", "Wales"],
  Australia: [
    "Australian Capital Territory",
    "New South Wales",
    "Northern Territory",
    "Queensland",
    "South Australia",
    "Tasmania",
    "Victoria",
    "Western Australia",
  ],
};

const REGION_LABELS: Record<string, string> = {
  Canada: "Provinces / Territories",
  India: "States / Union Territories",
  "United Kingdom": "Countries",
  Australia: "States / Territories",
};

const WORK_AUTHORIZATIONS: Record<string, readonly string[]> = {
  "United States": [
    "US Citizen",
    "Green Card",
    "GC-EAD",
    "H1-B",
    "H4-EAD",
    "L2-EAD",
    "OPT-EAD",
    "STEM OPT-EAD",
    "CPT",
    "TN Visa",
  ],
  Canada: [
    "Canadian Citizen",
    "Permanent Resident",
    "Open Work Permit",
    "Employer-Specific Work Permit",
    "Post-Graduation Work Permit",
  ],
  India: ["Indian Citizen", "OCI Cardholder", "Employment Visa", "Nepal / Bhutan Citizen"],
  "United Kingdom": [
    "British / Irish Citizen",
    "Settled / Pre-Settled Status",
    "Skilled Worker Visa",
    "Graduate Visa",
    "Dependant Visa",
  ],
  Australia: [
    "Australian Citizen",
    "Permanent Resident",
    "New Zealand Citizen",
    "Temporary Skill Shortage (482)",
    "Temporary Graduate (485)",
    "Working Holiday Visa",
  ],
};

const CURRENCY: Record<string, string> = {
  "United States": "USD",
  Canada: "CAD",
  India: "INR",
  "United Kingdom": "GBP",
  Australia: "AUD",
};

/** The local currency of a country, USD when unknown. */
export function currencyFor(country: string | null | undefined): string {
  return CURRENCY[country ?? DEFAULT_COUNTRY] ?? "USD";
}

/** States/provinces for a country; empty for a country without a list. */
export function regionsFor(country: string | null | undefined): readonly string[] {
  return REGIONS[country ?? DEFAULT_COUNTRY] ?? [];
}

/** What the state field is called in that country ("States" for the US). */
export function regionLabelFor(country: string | null | undefined): string {
  return REGION_LABELS[country ?? DEFAULT_COUNTRY] ?? "States";
}

/** Work-authorization categories that apply to jobs in that country. */
export function workAuthorizationsFor(country: string | null | undefined): readonly string[] {
  return WORK_AUTHORIZATIONS[country ?? DEFAULT_COUNTRY] ?? [];
}

/**
 * The options to render, plus any saved value that isn't one of them (older
 * or imported records) so it stays visible and can be deselected.
 */
export function withSaved(options: readonly string[], saved: readonly string[]): string[] {
  return [...options, ...saved.filter((s) => !options.includes(s))];
}

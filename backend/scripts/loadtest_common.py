"""Names shared by the load-test seed and the load-test runner. Kept free of
app imports so the runner can be installed with httpx alone."""

ORG_SLUG = "loadtest"
RECRUITER_COUNT = 20
RECRUITER_EMAIL = "loadtest-recruiter-{:02d}@loadtest.invalid"

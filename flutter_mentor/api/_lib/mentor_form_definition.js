// Update this link when the Google Form changes.
// Keep MENTOR_FIELD_ORDER in the exact same order as entry.* params in the link.
const MENTOR_PREFILLED_LINK =
  "https://docs.google.com/forms/d/e/1FAIpQLScaKH4o1bXtz6rptxuX22C4MMncdPsbaQHsgq-1taXT0Rzm_Q/viewform?usp=pp_url&entry.1811021320=EMAIL&entry.1690227157=LINKEDIN&entry.1240690540=FIRST_NAME&entry.745059451=LAST_NAME&entry.592131172=DEGREES&entry.243128393=CURRENT_CITY_STATE&entry.234085726=CURRENT_JOB_TITLE&entry.1805619834=CURRENT_COMPANY&entry.1886772630=PREVIOUS_MENTORSHIP&entry.1140508330=INDUSTRY_FOCUS_AREA&entry.1333231717=PREVIOUS_INVOLVEMENT&entry.189983182=PREVIOUS_INVOLVEMENT_ORGANIZATIONS&entry.1588753995=WHY_INTERESTED&entry.1252327633=PROFESSIONAL_EXPERIENCE&entry.1822618015=ABOUT_YOURSELF&entry.1820242654=STUDENTS_INTERESTED&entry.1760218787=ID&entry.856708681=SUBMITTED_AT";

const MENTOR_FIELD_ORDER = [
  "email",
  "linkedin",
  "firstName",
  "lastName",
  "degreesSummary",
  "currentCityState",
  "currentJobTitle",
  "currentCompany",
  "previousMentorship",
  "industryFocusArea",
  "previousInvolvement",
  "previousInvolvementOrgs",
  "whyInterested",
  "professionalExperience",
  "aboutYourself",
  "studentsInterested",
  "submissionId",
  "submittedAt",
];

module.exports = {
  MENTOR_PREFILLED_LINK,
  MENTOR_FIELD_ORDER,
};

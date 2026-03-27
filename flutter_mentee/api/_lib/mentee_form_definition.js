// Update this link when the Google Form changes.
// Keep MENTEE_FIELD_ORDER in the exact same order as entry.* params in the link.
const MENTEE_PREFILLED_LINK =
  "https://docs.google.com/forms/d/e/1FAIpQLScEp0vvZtkpEtWFxPthh5xbGr0rcEt5k6Zd8CjbTeXHT-VskA/viewform?usp=pp_url&entry.949801267=EMAIL&entry.926900860=FIRST_NAME&entry.1983684609=LAST_NAME&entry.1976491083=PRONOUNS&entry.1337254110=EDUCATION_LEVEL&entry.1583993810=GRADUATION_SEMESTER&entry.1943297115=GRADUATION_YEAR&entry.2094001975=DEGREE_PROGRAMS&entry.1479506346=HAS_CONCENTRATION&entry.1579760704=CONCENTRATIONS&entry.2117423693=PHD_SPECIALIZATION&entry.705448099=PREVIOUS_MENTORSHIP&entry.562009089=STUDENT_ORGS&entry.2016076981=EXPERIENCE_LEVEL&entry.867933932=INDUSTRIES_OF_INTEREST&entry.1834469658=ABOUT_YOURSELF&entry.162617210=MATCH_BY_INDUSTRY&entry.549463769=MATCH_BY_DEGREE&entry.1801459898=MATCH_BY_CLUBS&entry.76037252=MATCH_BY_IDENTITY&entry.1948682182=MATCH_BY_GRAD_YEARS&entry.1538022217=HELP_TOPICS&entry.1192108296=SUBMISSION_ID&entry.1799865324=SUBMITTED_AT";

const MENTEE_FIELD_ORDER = [
  "email",
  "firstName",
  "lastName",
  "pronouns",
  "educationLevel",
  "graduationSemester",
  "graduationYear",
  "degreePrograms",
  "hasConcentration",
  "concentrations",
  "phdSpecialization",
  "previousMentorship",
  "studentOrgs",
  "experienceLevel",
  "industriesOfInterest",
  "aboutYourself",
  "matchByIndustry",
  "matchByDegree",
  "matchByClubs",
  "matchByIdentity",
  "matchByGradYears",
  "helpTopics",
  "submissionId",
  "submittedAt",
];

module.exports = {
  MENTEE_PREFILLED_LINK,
  MENTEE_FIELD_ORDER,
};

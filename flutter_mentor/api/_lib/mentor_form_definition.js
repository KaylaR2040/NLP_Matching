// Update this link when the Google Form changes.
// NOTE: Google Form POST Info:
// Drop in the latest prefilled Google Form link here. Keep MENTOR_FIELD_ORDER
// in the exact same order as entry.* params in the link.
const MENTOR_PREFILLED_LINK =
  "https://docs.google.com/forms/d/e/1FAIpQLSey0OLTdTUXmcLp8LLo9UxCuVMrvoXeSm9jDNW9TcMwx5ex6w/viewform?usp=pp_url&entry.1212118616=kaylaradu@gmail&entry.1405593720=www.linkedin&entry.1460354148=Kayla&entry.1280480792=Radu&entry.850687584=she,+her,+two+&entry.1549300576=PhD,+animal+science+&entry.1535534221=CAry&entry.169312866=NC+&entry.2127194621=NEW+York+&entry.1560582362=Software+Engineer&entry.112498215=JD&entry.1972480795=no&entry.1890802982=no&entry.1378992134=no&entry.1154429959=no&entry.76845075=no&entry.1753687772=no&entry.1326101346=no&entry.687618411=no";

const MENTOR_FIELD_ORDER = [
  "email",
  "linkedin",
  "firstName",
  "lastName",
  "pronouns",
  "degreesSummary",
  "currentCity",
  "currentState",
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
];

module.exports = {
  MENTOR_PREFILLED_LINK,
  MENTOR_FIELD_ORDER,
};

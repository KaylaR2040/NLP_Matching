const { randomUUID } = require("crypto");
const { parseBool, parseJsonObject, submitToGoogleForm } = require("./_lib/form_forwarder");

const DEFAULT_MENTOR_FORM_RESPONSE_URL =
  "https://docs.google.com/forms/d/e/1FAIpQLScaKH4o1bXtz6rptxuX22C4MMncdPsbaQHsgq-1taXT0Rzm_Q/formResponse";
const DEFAULT_MENTOR_JSON_ENTRY_ID = "";
const DEFAULT_MENTOR_FIELD_MAP = {
  email: "entry.1811021320",
  linkedin: "entry.1690227157",
  firstName: "entry.1240690540",
  lastName: "entry.745059451",
  degreesSummary: "entry.592131172",
  currentCityState: "entry.243128393",
  currentJobTitle: "entry.234085726",
  currentCompany: "entry.1805619834",
  previousMentorship: "entry.1886772630",
  industryFocusArea: "entry.1140508330",
  previousInvolvement: "entry.1333231717",
  previousInvolvementOrgs: "entry.189983182",
  whyInterested: "entry.1588753995",
  professionalExperience: "entry.1252327633",
  aboutYourself: "entry.1822618015",
  studentsInterested: "entry.1820242654",
  submissionId: "entry.1760218787",
  submittedAt: "entry.856708681",
};

function parseRequestBody(req) {
  if (!req.body) {
    return {};
  }
  if (typeof req.body === "string") {
    try {
      return JSON.parse(req.body);
    } catch (_) {
      return {};
    }
  }
  if (typeof req.body === "object") {
    return req.body;
  }
  return {};
}

module.exports = async (req, res) => {
  if (req.method === "OPTIONS") {
    res.setHeader("Allow", "GET,POST,OPTIONS");
    return res.status(204).end();
  }

  if (req.method === "GET") {
    return res.status(200).json([]);
  }

  if (req.method !== "POST") {
    res.setHeader("Allow", "GET,POST,OPTIONS");
    return res.status(405).json({ detail: "Method not allowed" });
  }

  const data = parseRequestBody(req);
  const submissionId =
    typeof data.submissionId === "string" && data.submissionId
      ? data.submissionId
      : typeof data.id === "string" && data.id
      ? data.id
      : randomUUID();
  const submittedAt =
    typeof data.submittedAt === "string" && data.submittedAt
      ? data.submittedAt
      : typeof data.submitted_at === "string" && data.submitted_at
      ? data.submitted_at
      : new Date().toISOString();
  const degreesSummary = Array.isArray(data.degrees)
    ? data.degrees
        .map((degree) => {
          if (!degree || typeof degree !== "object") {
            return "";
          }
          const level = typeof degree.level === "string" ? degree.level : "";
          const program = typeof degree.program === "string" ? degree.program : "";
          const graduationYear =
            typeof degree.graduationYear === "string" ? degree.graduationYear : "";
          const core = [level, program].filter(Boolean).join(" ");
          if (!core) {
            return "";
          }
          return graduationYear ? `${core} (${graduationYear})` : core;
        })
        .filter(Boolean)
        .join("; ")
    : "";
  const mentorRecord = {
    ...data,
    id: submissionId,
    submissionId,
    submittedAt,
    submitted_at: submittedAt,
    degreesSummary,
  };

  const config = {
    formName: "mentor",
    enabled: parseBool(process.env.MENTOR_GOOGLE_FORM_ENABLED, true),
    required: parseBool(process.env.MENTOR_GOOGLE_FORM_REQUIRED, true),
    responseUrl:
      process.env.MENTOR_GOOGLE_FORM_RESPONSE_URL || DEFAULT_MENTOR_FORM_RESPONSE_URL,
    jsonEntryId: process.env.MENTOR_GOOGLE_FORM_JSON_ENTRY_ID || DEFAULT_MENTOR_JSON_ENTRY_ID,
    fieldMap: parseJsonObject(
      process.env.MENTOR_GOOGLE_FORM_FIELD_MAP_JSON,
      DEFAULT_MENTOR_FIELD_MAP,
    ),
  };

  try {
    const googleForm = await submitToGoogleForm(config, mentorRecord);
    return res.status(200).json({
      success: true,
      message: "Mentor application submitted successfully",
      mentor_id: submissionId,
      data: mentorRecord,
      google_form: googleForm,
    });
  } catch (error) {
    return res.status(502).json({
      detail: `Google Form submission failed: ${error.message}`,
    });
  }
};

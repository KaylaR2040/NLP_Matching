const { randomUUID } = require("crypto");
const { parseBool, parseJsonObject, submitToGoogleForm } = require("./_lib/form_forwarder");

const DEFAULT_MENTEE_FORM_RESPONSE_URL =
  "https://docs.google.com/forms/d/e/1FAIpQLScEp0vvZtkpEtWFxPthh5xbGr0rcEt5k6Zd8CjbTeXHT-VskA/formResponse";
const DEFAULT_MENTEE_JSON_ENTRY_ID = "";
const DEFAULT_MENTEE_FIELD_MAP = {
  email: "entry.949801267",
  firstName: "entry.926900860",
  lastName: "entry.1983684609",
  pronouns: "entry.1976491083",
  educationLevel: "entry.1337254110",
  graduationSemester: "entry.1583993810",
  graduationYear: "entry.1943297115",
  degreePrograms: "entry.2094001975",
  hasConcentration: "entry.1479506346",
  concentrations: "entry.1579760704",
  phdSpecialization: "entry.2117423693",
  previousMentorship: "entry.705448099",
  studentOrgs: "entry.562009089",
  experienceLevel: "entry.2016076981",
  industriesOfInterest: "entry.867933932",
  aboutYourself: "entry.1834469658",
  matchByIndustry: "entry.162617210",
  matchByDegree: "entry.549463769",
  matchByClubs: "entry.1801459898",
  matchByIdentity: "entry.76037252",
  matchByGradYears: "entry.1948682182",
  helpTopics: "entry.1538022217",
  submissionId: "entry.1192108296",
  submittedAt: "entry.1799865324",
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
  const menteeRecord = {
    ...data,
    id: submissionId,
    submissionId,
    submittedAt,
    submitted_at: submittedAt,
  };

  const config = {
    formName: "mentee",
    enabled: parseBool(process.env.MENTEE_GOOGLE_FORM_ENABLED, true),
    required: parseBool(process.env.MENTEE_GOOGLE_FORM_REQUIRED, true),
    responseUrl: process.env.MENTEE_GOOGLE_FORM_RESPONSE_URL || DEFAULT_MENTEE_FORM_RESPONSE_URL,
    jsonEntryId: process.env.MENTEE_GOOGLE_FORM_JSON_ENTRY_ID || DEFAULT_MENTEE_JSON_ENTRY_ID,
    fieldMap: parseJsonObject(
      process.env.MENTEE_GOOGLE_FORM_FIELD_MAP_JSON,
      DEFAULT_MENTEE_FIELD_MAP,
    ),
  };

  try {
    const googleForm = await submitToGoogleForm(config, menteeRecord);
    return res.status(200).json({
      success: true,
      message: "Mentee application submitted successfully",
      mentee_id: submissionId,
      data: menteeRecord,
      google_form: googleForm,
    });
  } catch (error) {
    return res.status(502).json({
      detail: `Google Form submission failed: ${error.message}`,
    });
  }
};

const { randomUUID } = require("crypto");
const { submitToGoogleForm } = require("./_lib/form_forwarder");
const { buildGoogleFormConfig } = require("./_lib/google_form_config");
const { MENTOR_PREFILLED_LINK, MENTOR_FIELD_ORDER } = require("./_lib/mentor_form_definition");

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
  mentorRecord.jsonData = JSON.stringify(mentorRecord, null, 2);

  try {
    const config = buildGoogleFormConfig({
      formName: "mentor",
      envPrefix: "MENTOR_GOOGLE_FORM",
      prefilledLink: process.env.MENTOR_GOOGLE_FORM_PREFILLED_LINK || MENTOR_PREFILLED_LINK,
      fieldOrder: MENTOR_FIELD_ORDER,
      defaultEnabled: true,
      defaultRequired: true,
    });

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

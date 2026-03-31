const { randomUUID } = require("crypto");
const { submitToGoogleForm } = require("./_lib/form_forwarder");
const { buildGoogleFormConfig } = require("./_lib/google_form_config");
const { MENTEE_PREFILLED_LINK, MENTEE_FIELD_ORDER } = require("./_lib/mentee_form_definition");

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
  menteeRecord.jsonData = JSON.stringify(menteeRecord, null, 2);

  try {
    const config = buildGoogleFormConfig({
      formName: "mentee",
      envPrefix: "MENTEE_GOOGLE_FORM",
      prefilledLink: process.env.MENTEE_GOOGLE_FORM_PREFILLED_LINK || MENTEE_PREFILLED_LINK,
      fieldOrder: MENTEE_FIELD_ORDER,
      defaultEnabled: true,
      defaultRequired: true,
    });

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

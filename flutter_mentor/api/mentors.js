const { randomUUID } = require("crypto");
const { parseBool, parseJsonObject, submitToGoogleForm } = require("./_lib/form_forwarder");

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
  const mentorId = typeof data.id === "string" && data.id ? data.id : randomUUID();
  const mentorRecord = {
    ...data,
    id: mentorId,
    submitted_at: data.submitted_at || new Date().toISOString(),
  };

  const config = {
    formName: "mentor",
    enabled: parseBool(process.env.MENTOR_GOOGLE_FORM_ENABLED, false),
    required: parseBool(process.env.MENTOR_GOOGLE_FORM_REQUIRED, false),
    responseUrl: process.env.MENTOR_GOOGLE_FORM_RESPONSE_URL || "",
    jsonEntryId: process.env.MENTOR_GOOGLE_FORM_JSON_ENTRY_ID || "",
    fieldMap: parseJsonObject(process.env.MENTOR_GOOGLE_FORM_FIELD_MAP_JSON, {}),
  };

  try {
    const googleForm = await submitToGoogleForm(config, mentorRecord);
    return res.status(200).json({
      success: true,
      message: "Mentor application submitted successfully",
      mentor_id: mentorId,
      data: mentorRecord,
      google_form: googleForm,
    });
  } catch (error) {
    return res.status(502).json({
      detail: `Google Form submission failed: ${error.message}`,
    });
  }
};

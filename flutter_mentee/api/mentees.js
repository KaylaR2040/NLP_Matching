const { randomUUID } = require("crypto");
const { parseBool, parseJsonObject, submitToGoogleForm } = require("./_lib/form_forwarder");

const DEFAULT_MENTEE_FORM_RESPONSE_URL =
  "https://docs.google.com/forms/d/e/1FAIpQLSes-SnnWAMcXzU_CsX6opYIpKxGu3Ii1BqfhMDUfN9IV4-pqQ/formResponse";
const DEFAULT_MENTEE_JSON_ENTRY_ID = "entry.1048570048";

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
  const menteeId = typeof data.id === "string" && data.id ? data.id : randomUUID();
  const menteeRecord = {
    ...data,
    id: menteeId,
    submitted_at: data.submitted_at || new Date().toISOString(),
  };

  const config = {
    formName: "mentee",
    enabled: parseBool(process.env.MENTEE_GOOGLE_FORM_ENABLED, true),
    required: parseBool(process.env.MENTEE_GOOGLE_FORM_REQUIRED, true),
    responseUrl: process.env.MENTEE_GOOGLE_FORM_RESPONSE_URL || DEFAULT_MENTEE_FORM_RESPONSE_URL,
    jsonEntryId: process.env.MENTEE_GOOGLE_FORM_JSON_ENTRY_ID || DEFAULT_MENTEE_JSON_ENTRY_ID,
    fieldMap: parseJsonObject(process.env.MENTEE_GOOGLE_FORM_FIELD_MAP_JSON, {}),
  };

  try {
    const googleForm = await submitToGoogleForm(config, menteeRecord);
    return res.status(200).json({
      success: true,
      message: "Mentee application submitted successfully",
      mentee_id: menteeId,
      data: menteeRecord,
      google_form: googleForm,
    });
  } catch (error) {
    return res.status(502).json({
      detail: `Google Form submission failed: ${error.message}`,
    });
  }
};

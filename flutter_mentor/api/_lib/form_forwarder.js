function parseBool(value, defaultValue) {
  if (value === undefined || value === null || value === "") {
    return defaultValue;
  }
  return String(value).toLowerCase() === "true";
}

function parseJsonObject(value, defaultValue = {}) {
  if (!value) {
    return defaultValue;
  }

  try {
    const parsed = JSON.parse(value);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed;
    }
  } catch (_) {}

  return defaultValue;
}

function resolvePath(data, path) {
  const parts = String(path).split(".");
  let current = data;
  for (const part of parts) {
    if (!current || typeof current !== "object" || !(part in current)) {
      return undefined;
    }
    current = current[part];
  }
  return current;
}

function stringifyValue(value) {
  if (value === undefined || value === null) {
    return "";
  }
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (Array.isArray(value)) {
    return value.map(stringifyValue).join(", ");
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function buildPayload(config, submissionData) {
  const fieldMap = config.fieldMap || {};
  const entries = Object.entries(fieldMap);
  if (entries.length > 0) {
    const mappedPayload = {};
    for (const [sourcePath, entryId] of entries) {
      const resolved = resolvePath(submissionData, sourcePath);
      if (resolved !== undefined) {
        mappedPayload[entryId] = stringifyValue(resolved);
      }
    }
    if (Object.keys(mappedPayload).length > 0) {
      return mappedPayload;
    }
  }

  if (config.jsonEntryId) {
    return {
      [config.jsonEntryId]: JSON.stringify(submissionData, null, 2),
    };
  }

  throw new Error("Google Form entry configuration is missing");
}

async function submitToGoogleForm(config, submissionData) {
  const enabled = parseBool(config.enabled, false);
  const required = parseBool(config.required, false);
  const responseUrl = (config.responseUrl || "").trim();

  if (!enabled || !responseUrl) {
    return {
      forwarded: false,
      skipped: true,
      status_code: null,
      reason: `${config.formName} Google Form forwarding is disabled or unconfigured`,
    };
  }

  const payload = buildPayload(config, submissionData);
  const encoded = new URLSearchParams(payload).toString();

  try {
    const response = await fetch(responseUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: encoded,
    });

    const ok = response.status < 400;
    if (!ok && required) {
      throw new Error(`Google Form returned HTTP ${response.status}`);
    }

    return {
      forwarded: ok,
      skipped: !ok,
      status_code: response.status,
      reason: ok ? "Submitted to Google Form" : `Google Form returned HTTP ${response.status}`,
    };
  } catch (error) {
    if (required) {
      throw error;
    }
    return {
      forwarded: false,
      skipped: true,
      status_code: null,
      reason: `Google Form request failed: ${error.message}`,
    };
  }
}

module.exports = {
  parseBool,
  parseJsonObject,
  submitToGoogleForm,
};

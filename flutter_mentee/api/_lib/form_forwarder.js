function parseBool(value, defaultValue) {
  if (value === undefined || value === null || value === "") {
    return defaultValue;
  }
  return String(value).toLowerCase() === "true";
}

function normalizeGoogleFormResponseUrl(rawUrl) {
  if (!rawUrl) {
    return "";
  }

  const cleaned = String(rawUrl).trim().replace(/\|/g, "I");
  if (!cleaned) {
    return "";
  }

  try {
    const parsed = new URL(cleaned);
    if (parsed.pathname.endsWith("/viewform")) {
      parsed.pathname = parsed.pathname.replace(/\/viewform$/, "/formResponse");
      parsed.search = "";
    }
    return parsed.toString();
  } catch (_) {
    return cleaned;
  }
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
    return value ? "YES" : "NO";
  }
  if (Array.isArray(value)) {
    return value.map(stringifyValue).join(", ");
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function describeGoogleFormHttpError(statusCode) {
  if (statusCode === 401) {
    return (
      "Google Form returned HTTP 401. This form currently requires Google sign-in " +
      "or organization access. Disable form sign-in restriction, or submit through a " +
      "logged-in browser session for the same Google Workspace domain."
    );
  }
  return `Google Form returned HTTP ${statusCode}`;
}

function buildPayload(config, submissionData) {
  const fieldMap = config.fieldMap || {};
  const entries = Object.entries(fieldMap);
  if (entries.length > 0) {
    const mappedPayload = new URLSearchParams();
    for (const [sourcePath, entryId] of entries) {
      const resolved = resolvePath(submissionData, sourcePath);
      if (resolved !== undefined) {
        if (Array.isArray(resolved)) {
          for (const item of resolved) {
            mappedPayload.append(entryId, stringifyValue(item));
          }
        } else {
          mappedPayload.append(entryId, stringifyValue(resolved));
        }
      }
    }
    if ([...mappedPayload.keys()].length > 0) {
      return mappedPayload;
    }
  }

  if (config.jsonEntryId) {
    const mappedPayload = new URLSearchParams();
    mappedPayload.append(config.jsonEntryId, JSON.stringify(submissionData, null, 2));
    return mappedPayload;
  }

  throw new Error("Google Form entry configuration is missing");
}

async function submitToGoogleForm(config, submissionData) {
  const enabled = parseBool(config.enabled, false);
  const required = parseBool(config.required, false);
  const responseUrl = normalizeGoogleFormResponseUrl(config.responseUrl);

  if (!enabled || !responseUrl) {
    return {
      forwarded: false,
      skipped: true,
      status_code: null,
      reason: `${config.formName} Google Form forwarding is disabled or unconfigured`,
    };
  }

  const payload = buildPayload(config, submissionData);
  const encoded = payload.toString();

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
      const responseText = (await response.text()).slice(0, 500);
      throw new Error(`${describeGoogleFormHttpError(response.status)}. Response snippet: ${responseText}`);
    }

    return {
      forwarded: ok,
      skipped: !ok,
      status_code: response.status,
      reason: ok ? "Submitted to Google Form" : describeGoogleFormHttpError(response.status),
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
  normalizeGoogleFormResponseUrl,
  parseBool,
  parseJsonObject,
  submitToGoogleForm,
};

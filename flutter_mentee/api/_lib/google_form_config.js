const {
  parseBool,
  parseJsonObject,
  normalizeGoogleFormResponseUrl,
} = require("./form_forwarder");

function buildFieldMapFromPrefilledLink(prefilledLink, fieldOrder) {
  if (!Array.isArray(fieldOrder) || fieldOrder.length === 0) {
    throw new Error("fieldOrder must be a non-empty array");
  }

  const parsed = new URL(prefilledLink);
  const entryIds = [];

  for (const [key] of parsed.searchParams.entries()) {
    if (key.startsWith("entry.")) {
      entryIds.push(key);
    }
  }

  if (entryIds.length < fieldOrder.length) {
    throw new Error(
      `Prefilled link has ${entryIds.length} entry ids but at least ${fieldOrder.length} are required`,
    );
  }

  const fieldMap = {};
  for (let index = 0; index < fieldOrder.length; index += 1) {
    fieldMap[fieldOrder[index]] = entryIds[index];
  }
  return fieldMap;
}

function buildGoogleFormConfig({
  formName,
  envPrefix,
  prefilledLink,
  fieldOrder,
  defaultEnabled = true,
  defaultRequired = true,
}) {
  if (!prefilledLink) {
    throw new Error(`Missing prefilledLink for ${formName} form config`);
  }

  const defaultResponseUrl = normalizeGoogleFormResponseUrl(prefilledLink);
  const defaultFieldMap = buildFieldMapFromPrefilledLink(prefilledLink, fieldOrder);

  return {
    formName,
    enabled: parseBool(process.env[`${envPrefix}_ENABLED`], defaultEnabled),
    required: parseBool(process.env[`${envPrefix}_REQUIRED`], defaultRequired),
    responseUrl: process.env[`${envPrefix}_RESPONSE_URL`] || defaultResponseUrl,
    fieldMap: parseJsonObject(process.env[`${envPrefix}_FIELD_MAP_JSON`], defaultFieldMap),
  };
}

module.exports = {
  buildGoogleFormConfig,
};

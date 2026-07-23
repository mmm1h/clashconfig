const KNOWN_SPLASH_POSITIONS = {
  "4063325249679547": true,
  "1034238202898855": true,
  "3161556344065278": true,
  "7341520759123916": true,
};

const payload = parseJson(
  typeof $response.body === "string" ? $response.body : "",
);

if (!payload || !payload.data || typeof payload.data !== "object") {
  $done({});
} else {
  let changed = false;

  for (const positionId of Object.keys(payload.data)) {
    if (KNOWN_SPLASH_POSITIONS[positionId] !== true) {
      continue;
    }

    payload.data[positionId] = {
      ret: 102006,
      external_info: {
        ret: 102006,
        msg: "",
      },
      msg: "",
    };
    changed = true;
  }

  if (changed) {
    $done({ body: JSON.stringify(payload) });
  } else {
    $done({});
  }
}

function parseJson(value) {
  try {
    return JSON.parse(value);
  } catch (_) {
    return null;
  }
}

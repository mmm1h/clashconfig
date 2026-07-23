const XIMALAYA_BUNDLE_ID = "com.gemd.iting";
const SPLASH_PLACEMENT_TYPE = 4;
const KNOWN_V2MI_SPLASH_POSITIONS = {
  "4063325249679547": true,
  "1034238202898855": true,
  "3161556344065278": true,
};
const US_L_SPLASH_POSITION = "7341520759123916";

const requestUrl = typeof $request.url === "string" ? $request.url : "";
const requestMethod = typeof $request.method === "string" ? $request.method : "";
const requestBody = typeof $request.body === "string" ? $request.body : "";
const positionId = getFormValue(requestBody, "posid");
const extension = parseJson(getFormValue(requestBody, "ext"));
const requestInfo = extension && extension.req;
const isXimalayaSplashRequest = Boolean(
  requestInfo &&
    requestInfo.c_pkgname === XIMALAYA_BUNDLE_ID &&
    Number(requestInfo.placement_type) === SPLASH_PLACEMENT_TYPE,
);

let shouldBlock = false;

if (
  requestMethod === "POST" &&
  /^https:\/\/v2mi\.gdt\.qq\.com\/gdt_mview\.fcg(?:\?|$)/.test(requestUrl)
) {
  shouldBlock =
    KNOWN_V2MI_SPLASH_POSITIONS[positionId] === true ||
    isXimalayaSplashRequest;
} else if (
  requestMethod === "POST" &&
  /^https:\/\/us\.l\.qq\.com\/exapp(?:\?|$)/.test(requestUrl)
) {
  shouldBlock =
    positionId === US_L_SPLASH_POSITION &&
    isXimalayaSplashRequest;
}

if (shouldBlock) {
  $done({
    status: "HTTP/1.1 404 Not Found",
    headers: { "Content-Type": "text/plain; charset=utf-8" },
    body: "",
  });
} else {
  $done({});
}

function getFormValue(body, expectedName) {
  for (const field of body.split("&")) {
    const separatorIndex = field.indexOf("=");
    const rawName = separatorIndex === -1 ? field : field.slice(0, separatorIndex);

    if (decodeFormComponent(rawName) !== expectedName) {
      continue;
    }

    const rawValue = separatorIndex === -1 ? "" : field.slice(separatorIndex + 1);
    return decodeFormComponent(rawValue);
  }

  return "";
}

function decodeFormComponent(value) {
  try {
    return decodeURIComponent(value.replace(/\+/g, " "));
  } catch (_) {
    return value;
  }
}

function parseJson(value) {
  try {
    return JSON.parse(value);
  } catch (_) {
    return null;
  }
}

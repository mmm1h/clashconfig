const payload = parseJson(
  typeof $response.body === "string" ? $response.body : "",
);

if (!payload || typeof payload !== "object") {
  $done({});
} else {
  payload.data = [];
  payload.adTypes = [];
  payload.bidSlotList = {};

  if (Object.prototype.hasOwnProperty.call(payload, "totalPageCount")) {
    payload.totalPageCount = 0;
  }

  if (Object.prototype.hasOwnProperty.call(payload, "currentPage")) {
    payload.currentPage = 0;
  }

  $done({ body: JSON.stringify(payload) });
}

function parseJson(value) {
  try {
    return JSON.parse(value);
  } catch (_) {
    return null;
  }
}

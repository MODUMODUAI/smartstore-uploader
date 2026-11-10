// 회원 서버는 UTC로 시각을 저장한다. 화면에는 한국 시간으로 보여 준다.
function seoulClock(value, withYear) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  let text = raw.replace(" ", "T");
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return withYear ? text : text.slice(5);
  if (!/[zZ]$|[+-]\d{2}:?\d{2}$/.test(text)) text += "Z";
  const date = new Date(text);
  if (Number.isNaN(date.getTime())) return raw.replace("T", " ").slice(5, 16);
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(date);
  const get = (type) => parts.find((part) => part.type === type)?.value || "";
  const clock = `${get("month")}-${get("day")} ${get("hour")}:${get("minute")}`;
  return withYear ? `${get("year")}-${clock}` : clock;
}

if (typeof module !== "undefined" && module.exports) module.exports = { seoulClock };

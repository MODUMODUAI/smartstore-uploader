const { staffEntryPlan, STAFF_BLOCKED_VIEWS } = require("./staff_entry.js");
const assert = require("assert");

assert.strictEqual(staffEntryPlan("마스터용", true, true), "master");
assert.strictEqual(staffEntryPlan("테스트용", true, false), "master");
assert.strictEqual(staffEntryPlan("", false, false), "master");
assert.strictEqual(staffEntryPlan("직원용", false, false), "sync");
assert.strictEqual(staffEntryPlan("직원용", false, true), "sync");
assert.strictEqual(staffEntryPlan("직원용", true, false), "products");
assert.strictEqual(staffEntryPlan("직원용", true, true), "staff-password");

for (const name of ["orders", "inquiries", "members", "settings", "collect", "wholesalers"]) {
  assert.ok(STAFF_BLOCKED_VIEWS.includes(name), name);
}
assert.ok(!STAFF_BLOCKED_VIEWS.includes("products"));
assert.ok(!STAFF_BLOCKED_VIEWS.includes("help"));

console.log("staff entry tests ok");

import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { BarList, TrendChart } from "./DashboardCharts";
import StaffManagement from "./StaffManagement";
import EnquiryManagement from "./EnquiryManagement";
import EnquiryForm from "./EnquiryForm";
import LoginAdmin from "./LoginAdmin";
import { ENQUIRY_STATUS_LABELS, ENQUIRY_STATUS_STYLES, OPEN_ENQUIRY_STATUSES, ROLE_LABELS, USER_GROUPS } from "../lib/workflow";

const SUPER = { id: "admin", role: "super_admin", permissions: { manage_staff: true, assign_enquiries: true, move_enquiries: true } };
const DEPT_ADMIN = { id: "a1", role: "department_admin", permissions: { manage_staff: false, assign_enquiries: true } };
const DEPT_STAFF = { id: "s1", role: "department_staff", permissions: { assign_enquiries: false, move_enquiries: false } };

describe("enquiry workflow constants", () => {
  it("match the backend statuses and have a style for each", () => {
    expect(Object.keys(ENQUIRY_STATUS_LABELS)).toEqual(
      ["new", "pending", "in_progress", "awaiting_response", "resolved", "closed"]);
    expect(OPEN_ENQUIRY_STATUSES).toEqual(["new", "pending", "in_progress", "awaiting_response"]);
    for (const status of Object.keys(ENQUIRY_STATUS_LABELS)) expect(ENQUIRY_STATUS_STYLES[status]).toBeTruthy();
    expect(Object.keys(ROLE_LABELS)).toEqual(["super_admin", "department_admin", "department_staff"]);
  });
});

describe("dashboard charts", () => {
  const trend = [
    { date: "2026-10-30", received: 2, resolved: 0 },
    { date: "2026-10-31", received: 0, resolved: 1 },
    { date: "2026-11-01", received: 5, resolved: 3 },
  ];

  it("draws both series with a legend carrying the totals", () => {
    const html = renderToStaticMarkup(<TrendChart data={trend} />);
    expect(html.match(/<path /g)).toHaveLength(2);
    expect(html).toContain("Received (7)");
    expect(html).toContain("Resolved (4)");
    expect(html).toContain("Show table");
    expect(html).toContain('aria-label="Enquiries received (7) and resolved (4) per day"');
  });

  it("bar list shows values and an empty state", () => {
    const html = renderToStaticMarkup(<BarList rows={[{ key: "a", label: "Admissions", value: 3 }, { key: "r", label: "Registrar", value: 1 }]} />);
    expect(html).toContain("Admissions");
    expect(html).toContain(">3<");
    expect(renderToStaticMarkup(<BarList rows={[{ key: "a", label: "A", value: 0 }]} emptyText="Nothing" />)).toContain("Nothing");
  });
});

describe("role-dependent screens", () => {
  it("only a Super Administrator gets the account creation form", () => {
    expect(renderToStaticMarkup(<StaffManagement me={SUPER} />)).toContain("New staff account");
    const deptView = renderToStaticMarkup(<StaffManagement me={DEPT_ADMIN} />);
    expect(deptView).not.toContain("New staff account");
    expect(deptView).toContain("Contact a Super Administrator");
  });

  it("department view hides the department filter and staff cannot reassign", () => {
    const html = renderToStaticMarkup(<EnquiryManagement me={DEPT_STAFF} department="admissions" />);
    expect(html).toContain("Admissions enquiries");
    expect(html).not.toContain(">Department<");
    expect(html).toContain("Awaiting attention (new, pending)");
    const mine = renderToStaticMarkup(<EnquiryManagement me={DEPT_STAFF} mine />);
    expect(mine).toContain("Assigned to me");
  });
});

describe("public enquiry form", () => {
  it("asks who the person is, optionally", () => {
    const html = renderToStaticMarkup(<EnquiryForm question="When is the intake?" />);
    expect(html).toContain("I am a… (optional)");
    for (const label of Object.values(USER_GROUPS)) expect(html).toContain(label);
    expect(html).toContain("Prefer not to say");
  });
});

describe("staff sign-in page", () => {
  it("offers sign-in only (no public registration)", () => {
    const html = renderToStaticMarkup(<MemoryRouter><LoginAdmin /></MemoryRouter>);
    expect(html).toContain("USIUBOT Staff Portal");
    expect(html).toContain("Work email");
    expect(html).toContain("created by the USIUBOT Super Administrator");
    expect(html.toLowerCase()).not.toContain("sign up");
  });
});

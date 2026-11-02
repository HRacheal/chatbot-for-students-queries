import { describe, expect, it } from "vitest";
import { BACKEND_UNREACHABLE, backendUnreachableHandler } from "./devProxy";
import { chatErrorMessage } from "./api";

const fakeResponse = (state = {}) => ({
  headersSent: false,
  writableEnded: false,
  ...state,
  writeHead(status, headers) { this.status = status; this.headers = headers; },
  end(body) { this.body = body; },
});

const REFUSED = Object.assign(new Error("connect ECONNREFUSED 127.0.0.1:5000"), { code: "ECONNREFUSED" });

// Regression: with the backend stopped, Vite answered /api/query with an empty 500.
describe("dev proxy when the backend is not running", () => {
  it("answers 502 with a JSON explanation instead of an empty 500", () => {
    const res = fakeResponse();
    const logs = [];
    backendUnreachableHandler("http://127.0.0.1:5000", (m) => logs.push(m))(REFUSED, { method: "POST", url: "/api/query" }, res);
    expect(res.status).toBe(502);
    expect(res.headers["Content-Type"]).toBe("application/json");
    const body = JSON.parse(res.body);
    expect(body.code).toBe(BACKEND_UNREACHABLE);
    expect(body.error).toContain("not running or not reachable");
    expect(logs[0]).toContain("http://127.0.0.1:5000");
    expect(logs[0]).toContain("ECONNREFUSED");
  });

  it("leaves responses that were already started, and sockets, alone", () => {
    const started = fakeResponse({ headersSent: true });
    backendUnreachableHandler("t", () => {})(REFUSED, {}, started);
    expect(started.status).toBeUndefined();
    expect(() => backendUnreachableHandler("t", () => {})(REFUSED, {}, { destroy() {} })).not.toThrow();
  });
});

describe("chat error messages", () => {
  const failed = (status, data) => ({ response: { status, data } });

  it("explains a backend that is not running", () => {
    const body = JSON.parse((() => {
      const res = fakeResponse();
      backendUnreachableHandler("t", () => {})(REFUSED, {}, res);
      return res.body;
    })());
    expect(chatErrorMessage(failed(502, body))).toContain("not running or not reachable");
  });

  it("never shows an empty or invented answer for a bare server error", () => {
    const message = chatErrorMessage(failed(500, ""));
    expect(message).toContain("could not answer right now");
    expect(message).toContain("no answer was given");
  });

  it("uses the server's own message when there is one", () => {
    expect(chatErrorMessage(failed(500, { error: "An unexpected error occurred. Please try again later." })))
      .toBe("An unexpected error occurred. Please try again later.");
    expect(chatErrorMessage(failed(400, { error: "Question must be at most 2000 characters" })))
      .toBe("Question must be at most 2000 characters");
  });

  it("covers rate limits and lost connections", () => {
    expect(chatErrorMessage(failed(429, ""))).toContain("wait a minute");
    expect(chatErrorMessage(new Error("Network Error"))).toContain("Could not reach the USIUBOT server");
  });
});

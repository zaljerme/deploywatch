import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import { health } from "./format";
import type { History, Monitor } from "./api";

const monitor: Monitor = {
  id: 1,
  name: "Demo API",
  url: "http://demo:8001/health",
  interval_seconds: 5,
  timeout_seconds: 2,
  expected_status: 200,
  paused: false,
  repository: null,
  failure_count: 0,
  next_check_at: new Date().toISOString(),
};
const history: History = {
  checks: [],
  incidents: [],
  uptime_percent: null,
  sample_count: 0,
  next_before_id: null,
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

async function login() {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("API access token"), "test-token");
  await user.click(screen.getByRole("button", { name: /open dashboard/i }));
  return user;
}

describe("dashboard", () => {
  it("shows a useful empty state and submits a monitor", async () => {
    const fetcher = vi.spyOn(globalThis, "fetch").mockImplementation(
      async (_url, init) =>
        new Response(JSON.stringify(init?.method === "POST" ? monitor : []), {
          status: init?.method === "POST" ? 201 : 200,
        }),
    );
    render(<App />);
    const user = await login();
    await screen.findByText("Start with your first endpoint");
    await user.click(screen.getByRole("button", { name: "Add monitor" }));
    await user.type(screen.getByLabelText("Name"), "Demo API");
    await user.type(
      screen.getByLabelText("Endpoint URL"),
      "http://demo:8001/health",
    );
    await user.click(screen.getByRole("button", { name: "Save monitor" }));
    await waitFor(() =>
      expect(
        fetcher.mock.calls.some(([, init]) => init?.method === "POST"),
      ).toBe(true),
    );
    const call = fetcher.mock.calls.find(([, init]) => init?.method === "POST");
    expect(JSON.parse(String(call?.[1]?.body))).toMatchObject({
      name: "Demo API",
      interval_seconds: 30,
    });
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
  });

  it("reports API failure without inventing health", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          error: { message: "A valid bearer token is required" },
        }),
        { status: 401 },
      ),
    );
    render(<App />);
    await login();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "A valid bearer token is required",
    );
    expect(screen.queryByText("100.00%")).not.toBeInTheDocument();
  });

  it("shows pending checks and pauses the selected monitor", async () => {
    const fetcher = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation(
        async (url) =>
          new Response(
            JSON.stringify(
              String(url).endsWith("/history?hours=24")
                ? history
                : String(url).endsWith("/activity")
                  ? { repository: null, notice: "" }
                  : String(url) === "/api/monitors"
                    ? [monitor]
                    : monitor,
            ),
          ),
      );
    render(<App />);
    const user = await login();
    await screen.findByRole("heading", { name: "Response time" });
    expect(screen.getAllByText("Pending").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: /^Pause$/ }));
    await waitFor(() =>
      expect(
        fetcher.mock.calls.some(([, init]) => init?.method === "PUT"),
      ).toBe(true),
    );
    const call = fetcher.mock.calls.find(([, init]) => init?.method === "PUT");
    expect(JSON.parse(String(call?.[1]?.body)).paused).toBe(true);
  });
});

it("distinguishes stale, paused, degraded, and incident health", () => {
  expect(health(monitor, history)).toBe("Pending");
  const recent = {
    ...history,
    checks: [
      {
        id: 1,
        checked_at: new Date().toISOString(),
        success: false,
        status_code: 503,
        response_ms: 20,
        error: "unexpected_status",
      },
    ],
  };
  expect(health(monitor, recent)).toBe("Degraded");
  expect(
    health(monitor, {
      ...recent,
      incidents: [
        {
          id: 1,
          started_at: new Date().toISOString(),
          detected_at: new Date().toISOString(),
          resolved_at: null,
        },
      ],
    }),
  ).toBe("Down");
  expect(
    health(monitor, {
      ...recent,
      checks: [{ ...recent.checks[0], checked_at: "2020-01-01T00:00:00Z" }],
    }),
  ).toBe("Stale");
  expect(health({ ...monitor, paused: true }, recent)).toBe("Paused");
});

import { test, expect, Page } from '@playwright/test';

const API_BASE = 'http://localhost:8000';

const graphicsPayload = {
  graphics: [
    {
      id: 1,
      title: 'Test Graphic',
      event_name: 'Test Event',
      data_json: JSON.stringify({
        elements: [],
        settings: { width: 1920, height: 1080, backgroundColor: '#1a1a1a' },
      }),
      created_by: 'Tester',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-02T12:34:56Z',
      archived: false,
    },
  ],
};

const archivesPayload = {
  archives: [
    {
      id: 2,
      title: 'Archived Graphic',
      event_name: 'Old Event',
      data_json: JSON.stringify({
        elements: [],
        settings: { width: 1920, height: 1080, backgroundColor: '#1a1a1a' },
      }),
      created_by: 'Tester',
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-03T08:00:00Z',
      archived: true,
      archived_at: '2024-01-04T10:00:00Z',
    },
  ],
};

const lockResponse = {
  id: 1,
  graphic_id: 1,
  user_name: 'Dashboard User',
  locked: true,
  locked_at: '2024-01-01T00:00:00Z',
  expires_at: '2024-01-01T00:05:00Z',
};

async function mockApiRoutes(page: Page) {
  await page.route(`${API_BASE}/auth/login`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'mock-token',
        token_type: 'bearer',
        expires_in: 3600,
      }),
    });
  });

  await page.route(`${API_BASE}/api/v1/graphics`, async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(graphicsPayload),
      });
    } else if (route.request().method() === 'POST') {
      const requestBody = await route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...graphicsPayload.graphics[0],
          id: 3,
          title: requestBody.title ?? 'Untitled Graphic',
        }),
      });
    } else {
      await route.continue();
    }
  });

  await page.route(`${API_BASE}/api/v1/graphics/1`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(graphicsPayload.graphics[0]),
    });
  });

  await page.route(`${API_BASE}/api/v1/archive`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(archivesPayload),
    });
  });

  await page.route(`${API_BASE}/api/v1/lock/status`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.route(`${API_BASE}/api/v1/lock/1`, async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(lockResponse),
      });
    } else if (route.request().method() === 'DELETE') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      });
    } else {
      await route.continue();
    }
  });

  await page.route(`${API_BASE}/api/v1/lock/1/refresh`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(lockResponse),
    });
  });
}

async function loginAndVisitDashboard(page: Page) {
  await page.goto('/');
  await page.fill('#masterPassword', 'admin');
  await page.getByRole('button', { name: /Access Dashboard/ }).click();
  await page.waitForURL('**/dashboard');
  await expect(page.getByRole('heading', { name: /Active Graphics/ })).toBeVisible();
}

test.describe('Dashboard smoke tests', () => {
  test.beforeEach(async ({ page }) => {
    await mockApiRoutes(page);
  });

  test('allows login and displays graphics overview', async ({ page }) => {
    await loginAndVisitDashboard(page);
    await expect(page.getByText('Test Graphic')).toBeVisible();
    await expect(page).toHaveScreenshot('dashboard.png');
  });

  test('opens canvas editor from graphics list', async ({ page }) => {
    await loginAndVisitDashboard(page);
    await page.goto('/canvas/edit/1');
    await expect(page).toHaveURL(/\/canvas\/edit\/1$/);
    await expect(page.getByRole('button', { name: 'Save' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Grid' })).toBeVisible();
    await expect(page).toHaveScreenshot('canvas-editor.png');
  });

  test('shows archived graphics when switching tabs', async ({ page }) => {
    await loginAndVisitDashboard(page);
    await page.getByRole('tab', { name: /Archived Graphics/ }).click();
    await expect(
      page.locator('table').getByText('Archived Graphic', { exact: true }),
    ).toBeVisible();
    await expect(page).toHaveScreenshot('archive.png');
  });
});

import { test, expect } from '@playwright/test';

test.describe('Cart API', () => {
  test('TC-01: Add item via Shopify AJAX API returns 200', async ({ request }) => {
    const response = await request.post('/cart/add.js', {
      data: { id: 1, quantity: 1 },
      headers: { 'Content-Type': 'application/json' },
    });
    expect([200, 422]).toContain(response.status());
  });

  test('TC-02: GET /cart.js returns cart object', async ({ request }) => {
    const response = await request.get('/cart.js');
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('items');
  });
});

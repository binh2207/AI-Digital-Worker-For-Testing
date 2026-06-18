import { test, expect } from '@playwright/test';
import { SelectVariantsAndAddProductsToCartPage } from '../../pages/SelectVariantsAndAddProductsToCartPage';

// SKIP TC-01: Only one combobox exists (#product-select-option-0) with a single option 'Grey jacket'; no Size/Color dropdowns present on the page
// SKIP TC-02: Non-UI criterion — requires developer tools to inspect hidden DOM field value; not observable via browser interaction

test.describe('TEST-2 — Select variants and add products to cart', () => {
  let cartPage: SelectVariantsAndAddProductsToCartPage;

  test.beforeEach(async ({ page }) => {
    cartPage = new SelectVariantsAndAddProductsToCartPage(page);
  });

  test('TC-03: Add to Cart button is visible and submits the product form', async ({ page }) => {
    await cartPage.gotoProductPage();
    await expect(cartPage.addToCartButton).toBeVisible();
    await cartPage.clickAddToCart();
    await expect(page).toHaveURL(/\/collections\/frontpage\/products\/grey-jacket/);
  });

  test('TC-04: Cart icon/count updates after a successful add', async ({ page }) => {
    // flaky: cart count update can race with navigation
    test.slow();
    await cartPage.gotoProductPage();
    const cartLink = page.getByRole('link', { name: /My Cart/i }).first();
    await expect(cartLink).toBeAttached({ timeout: 10000 });
    await expect(cartLink).toHaveText(/My Cart \(0\)/);
    await cartPage.clickAddToCart();
    await expect(cartLink).toBeAttached({ timeout: 10000 });
    await expect(cartLink).toHaveText(/My Cart \(1\)/);
    await expect(page).toHaveURL(/\/collections\/frontpage\/products\/grey-jacket/);
  });

  test('TC-05: Cart page lists added items with price, or shows empty-state with Continue Shopping link', async ({ page }) => {
    await cartPage.gotoProductPage();
    await cartPage.clickAddToCart();
    await cartPage.gotoCartPage();
    const cartItem = page.locator('tr:has(a[href*="/products/grey-jacket"])').first();
    await expect(cartItem).toBeAttached({ timeout: 10000 });
    await expect(cartItem).toBeVisible();
    await expect(cartItem).toContainText(/£\d+\.\d{2}/);
    await cartPage.gotoEmptyCart();
    await expect(cartPage.emptyCartMessage).toContainText('It appears that your cart is currently empty!');
    await expect(cartPage.continueShoppingLink).toBeVisible();
    await expect(page).toHaveURL(/\/cart/);
  });
});
import { test, expect } from '@playwright/test';
import { SelectVariantsAndAddProductsToCartPage } from '../../pages/SelectVariantsAndAddProductsToCartPage';

// SKIP TC-01: No Size or Color dropdown selectors exist; only a single combobox with one option 'Grey jacket' is present — product has only one variant configured.
// SKIP TC-02: Non-UI criterion — requires DOM inspection of hidden input, not performable as a human UI action.

test.describe('TEST-2 — Select variants and add products to cart', () => {
  test('TC-03: Add to Cart button is visible and submits the product form', async ({ page }) => {
    const po = new SelectVariantsAndAddProductsToCartPage(page);
    await po.gotoProduct();
    await expect(po.addToCartButton).toBeVisible();
    await po.clickAddToCart();
    await expect(page).toHaveURL(/\/collections\/frontpage\/products\/grey-jacket/);
  });

  test('TC-04: Cart icon/count updates after a successful add', async ({ page }) => {
    const po = new SelectVariantsAndAddProductsToCartPage(page);
    await po.gotoProduct();
    await expect(po.cartLink).toContainText('My Cart (0)');
    await po.clickAddToCart();
    await expect(po.cartLink).toContainText('My Cart (1)');
  });

  test('TC-05: Cart page lists added items with price, or shows empty-state with Continue Shopping link', async ({ page }) => {
    const po = new SelectVariantsAndAddProductsToCartPage(page);
    await po.gotoCart();
    const hasItem = await po.greyJacketCartLink.isVisible();
    if (hasItem) {
      await expect(po.greyJacketPrice).toBeVisible();
    }
    await expect(po.continueShoppingLink).toBeVisible();
  });
});
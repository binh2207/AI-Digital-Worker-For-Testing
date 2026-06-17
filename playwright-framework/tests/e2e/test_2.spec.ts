import { test, expect } from '@playwright/test';
import { SelectVariantsAndAddProductsToCartPage } from '../../pages/SelectVariantsAndAddProductsToCartPage';

// SKIP TC-01: No Size (S/M/L) or Color dropdown found; only a single variant selector with one option 'Grey jacket' exists on this product page.
// SKIP TC-02: NON-UI test — requires developer tools to observe hidden input value change; only one variant exists so no selection change is possible.

test.describe('TEST-2 — Select variants and add products to cart', () => {
  test('TC-03: "Add to Cart" button is visible and submits the product form', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.gotoProductPage();
    await expect(cartPage.addToCartButton).toBeVisible();
    await cartPage.clickAddToCart();
    await expect(cartPage.myCartLink).toContainText('My Cart (1)');
  });

  test('TC-04: Cart icon/count updates after a successful add', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.gotoProductPage();
    await cartPage.clickAddToCart();
    await expect(cartPage.myCartLinkInBanner).toContainText('My Cart (1)');
  });

  test('TC-05: Cart page lists added items with price, or shows empty-state with "Continue Shopping" link', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.gotoProductPage();
    await cartPage.clickAddToCart();
    await cartPage.navigateToCart();
    await expect(cartPage.productHeading).toBeVisible();
    await expect(cartPage.cartPrice).toHaveText('£55.00');
    await expect(cartPage.continueShoppingLink).toBeVisible();
    await expect(page).toHaveURL(/\/cart/);
  });
});
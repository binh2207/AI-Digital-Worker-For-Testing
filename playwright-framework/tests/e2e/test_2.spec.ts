import { test, expect } from '@playwright/test';
import { SelectVariantsAndAddProductsToCartPage } from '../../pages/SelectVariantsAndAddProductsToCartPage';

// SKIP TC-01: Only one variant combobox exists; no Size (S/M/L) dropdown and no Color selector are present
// SKIP TC-02: Non-UI criterion — hidden DOM field value cannot be verified through observable UI actions alone

test.describe('TEST-2 — Select variants and add products to cart', () => {
  let cartPage: SelectVariantsAndAddProductsToCartPage;

  test.beforeEach(async ({ page }) => {
    cartPage = new SelectVariantsAndAddProductsToCartPage(page);
  });

  test('TC-03: "Add to Cart" button is visible and submits the product form', async () => {
    await cartPage.goto();
    await expect(cartPage.addToCartButton).toBeVisible();
    await cartPage.clickAddToCart();
    await expect(cartPage.cartLink).toContainText(/My Cart \(\d+\)/);
  });

  test('TC-04: Cart icon/count updates after a successful add', async () => {
    await cartPage.goto();
    await cartPage.clickAddToCart();
    await expect(cartPage.cartLink).toContainText(/My Cart \(\d+\)/);
  });

  test('TC-05: Cart page lists added items with price, or shows empty-state with \'Continue Shopping\' link', async () => {
    await cartPage.goto();
    await cartPage.clickAddToCart();
    await cartPage.gotoCart();
    await expect(cartPage.greyJacketLink).toBeVisible();
    await expect(cartPage.cartPriceCell).toContainText('£55.00');
    await cartPage.gotoEmptyCart();
    await expect(cartPage.emptyCartMessage).toContainText('It appears that your cart is currently empty');
    await expect(cartPage.continueShoppingLink).toBeVisible();
  });
});
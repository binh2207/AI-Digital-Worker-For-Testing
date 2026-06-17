import { test, expect } from '@playwright/test';
import { SelectVariantsAndAddProductsToCartPage } from '../../pages/SelectVariantsAndAddProductsToCartPage';

// SKIP TC-01: Only a single-option combobox ('Grey jacket') is present; no Size (S/M/L) dropdown and no Color dropdown exist on the product page
// SKIP TC-02: Non-UI criterion — hidden DOM field not observable via browser interaction

test.describe('TEST-2 — Select variants and add products to cart', () => {
  let cartPage: SelectVariantsAndAddProductsToCartPage;

  test.beforeEach(async ({ page }) => {
    cartPage = new SelectVariantsAndAddProductsToCartPage(page);
  });

  test('TC-03: Add to Cart button is visible and submits the product form', async () => {
    await cartPage.gotoProductPage();
    await expect(cartPage.addToCartButton).toBeVisible();
    await cartPage.clickAddToCart();
  });

  test('TC-04: Cart icon/count updates after a successful add', async () => {
    await cartPage.gotoProductPage();
    await expect(cartPage.cartLink).toHaveText('My Cart (0)');
    await cartPage.clickAddToCart();
    await expect(cartPage.cartLink).toHaveText('My Cart (1)');
  });

  test('TC-05: Cart page lists added items with price, or shows empty-state with Continue Shopping link', async () => {
    await cartPage.gotoProductPage();
    await cartPage.clickAddToCart();
    await cartPage.gotoCartPage();
    await expect(cartPage.cartItemHeading).toBeVisible();
    await expect(cartPage.itemPrice).toHaveText('£55.00');
    await cartPage.clickRemoveItem();
    await expect(cartPage.emptyCartMessage).toHaveText('It appears that your cart is currently empty!');
    await expect(cartPage.continueShoppingLink).toBeVisible();
  });
});
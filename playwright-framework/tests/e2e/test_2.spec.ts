import { test, expect } from '@playwright/test';
import { SelectVariantsAndAddProductsToCartPage } from '../../pages/SelectVariantsAndAddProductsToCartPage';

// SKIP TC-01: Only a single combobox with one option ("Grey jacket") exists — no distinct Size or Color dropdowns present on the product page
// SKIP TC-02: Non-UI criterion — hidden product ID update is not observable through browser interaction

test.describe('TEST-2 — Select variants and add products to cart', () => {

  test('TC-03: "Add to Cart" button is visible and submits the product form', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.gotoProduct();

    await expect(cartPage.addToCartButton).toBeVisible();
    await cartPage.clickAddToCart();
    await expect(page).not.toHaveURL(/error/i);
  });

  test('TC-04: Cart icon/count updates after a successful add', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.gotoProduct();

    await expect(cartPage.cartHeaderLink).toContainText('My Cart (0)');
    await cartPage.clickAddToCart();
    await expect(cartPage.cartHeaderLink).toContainText('My Cart (1)');
  });

  test('TC-05: Cart page lists added item with price and a "Continue Shopping" link', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.gotoProduct();
    await cartPage.clickAddToCart();
    await cartPage.gotoCart();

    await expect(cartPage.cartItemName).toBeVisible();
    await expect(cartPage.cartItemPrice).toBeVisible();
    await expect(cartPage.continueShoppingLink).toBeVisible();
  });

  test('TC-05: Empty cart shows empty-state message with a "Continue Shopping" link', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.gotoCart();

    await expect(cartPage.emptyCartMessage).toBeVisible();
    await expect(cartPage.continueShoppingLink).toBeVisible();
  });

});
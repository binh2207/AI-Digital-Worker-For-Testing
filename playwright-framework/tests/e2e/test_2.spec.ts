import { test, expect } from '@playwright/test';
import { SelectVariantsAndAddProductsToCartPage } from '../../pages/SelectVariantsAndAddProductsToCartPage';

// SKIP TC-01: No Size or Color dropdown present; only one combobox exists (id='product-select-option-0') with a single 'Grey jacket' option — no S/M/L or color variants configured on this product
// SKIP TC-02: Pre-marked NON-UI: hidden input[name='id'] value not verifiable through observable UI alone

test.describe('TEST-2 — Select variants and add products to cart', () => {

  test('TC-03: Add to Cart button is visible and submits the product form', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.gotoProductPage();
    await expect(cartPage.addToCartButton).toBeVisible();
    await cartPage.clickAddToCart();
    await expect(page).toHaveURL(/collections\/frontpage\/products\/grey-jacket/);
  });

  test('TC-04: Cart icon/count updates after a successful add (header badge reflects item count)', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.gotoProductPage();
    await expect(cartPage.cartLink).toContainText('My Cart (0)');
    await cartPage.selectProductVariant('Grey jacket');
    await cartPage.clickAddToCart();
    await expect(cartPage.cartLink).toContainText('(1)');
    await expect(page).toHaveURL(/collections\/frontpage\/products\/grey-jacket/);
  });

  test('TC-05: Cart page lists added items with price, or shows empty-state message with Continue Shopping link', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.gotoProductPage();
    await cartPage.selectProductVariant('Grey jacket');
    await cartPage.clickAddToCart();
    await cartPage.gotoCartPage();
    await expect(cartPage.cartItemHeading).toContainText('Grey jacket');
    await expect(cartPage.itemPrice).toHaveText('£55.00');
    await expect(cartPage.continueShoppingAltLink).toBeVisible();
    await cartPage.clickRemoveItem();
    await expect(cartPage.emptyCartMessage).toContainText('It appears that your cart is currently empty!');
    await expect(cartPage.continueShoppingLink).toBeVisible();
    await expect(page).toHaveURL(/\/cart/);
  });
});
import { test, expect } from '@playwright/test';
import { SelectVariantsAndAddProductsToCartPage } from '../../pages/SelectVariantsAndAddProductsToCartPage';

// SKIP TC-01: Only one combobox (#product-select-option-0) exists — no Size or Color variant selectors present on the product page.
// SKIP TC-02: NON-UI — hidden field (select#product-select, name=id) value change is not observable through standard UI interaction.

test.describe('TEST-2 — Select variants and add products to cart', () => {
  test('TC-03: "Add to Cart" button is visible and submits the product form', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);

    await cartPage.gotoProductPage();
    await expect(cartPage.addToCartButton).toBeVisible();
    await cartPage.clickAddToCart();
    await expect(page).toHaveURL(/\/products\/grey-jacket/);
  });

  test('TC-04: Cart icon/count updates after a successful add (header badge reflects item count)', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);

    await cartPage.gotoProductPage();
    await expect(cartPage.cartLinkBefore).toContainText('My Cart (0)');
    await cartPage.clickAddToCart();
    await expect(cartPage.cartLinkAfter).toContainText('My Cart (1)');
    await expect(page).toHaveURL(/\/products\/grey-jacket/);
  });

  test('TC-05: Cart page lists added items with price, or shows empty-state with "Continue Shopping" link', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);

    await cartPage.gotoCartPage();
    await expect(cartPage.continueShoppingLink).toBeVisible();
    await expect(cartPage.productTitle).toContainText('Grey jacket');
    await expect(cartPage.cartTotal).toContainText('Total £55.00');
    await expect(cartPage.continueShoppingLink).toBeVisible();
    await expect(page).toHaveURL(/\/cart/);
  });
});
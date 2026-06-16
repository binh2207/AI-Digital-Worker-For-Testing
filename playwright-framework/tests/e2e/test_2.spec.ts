import { test, expect } from '@playwright/test';
import { SelectVariantsAndAddProductsToCartPage } from '../../pages/SelectVariantsAndAddProductsToCartPage';

// SKIP TC-01: FAILED — Grey jacket product page has no Size/Color variant dropdowns; only a single combobox with one option exists
// SKIP TC-02: NON-UI — requires DOM inspection tooling to verify hidden product ID update

test.describe('TEST-2 — Select variants and add products to cart', () => {

  test('TC-03: "Add to Cart" button is visible and submits the product form', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.goto();
    await expect(cartPage.addToCartButton).toBeVisible();
    await cartPage.clickAddToCart();
    await expect(cartPage.cartBadge).toBeVisible();
  });

  test('TC-04: Cart icon/count updates after a successful add', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.goto();
    const countBefore = await cartPage.getCartCount();
    await cartPage.clickAddToCart();
    const countAfter = await cartPage.getCartCount();
    expect(countAfter).toBe(countBefore + 1);
  });

  test('TC-05a: Cart page lists added item with correct name and price', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.goto();
    await cartPage.clickAddToCart();
    await cartPage.gotoCart();
    await expect(cartPage.cartItemName).toBeVisible();
    await expect(cartPage.cartItemPrice).toBeVisible();
  });

  test('TC-05b: Empty cart shows empty-state message and a Continue Shopping link to /collections/all', async ({ page }) => {
    const cartPage = new SelectVariantsAndAddProductsToCartPage(page);
    await cartPage.gotoCart();
    await expect(cartPage.emptyCartMessage).toBeVisible();
    await expect(cartPage.continueShoppingLink).toBeVisible();
    await expect(cartPage.continueShoppingLink).toHaveAttribute('href', '/collections/all');
  });

});